"""Take care of import jobs and copying files. Keep track of import modules"""

import logging
import mimetypes
import os
import re
import base64
import bottle

from jsonobject import wrap_raw_json
from threading import Thread, Event, Lock

from .web import ResourceBusy
from .system import current_system
from .localfile import FolderScanner
from .entry import (
    Entry,
    State,
    get_entry_by_id,
    create_entry,
    update_entry_by_id,
)
from .job import Job, create_job


re_clean = re.compile(r'[^A-Za-z0-9_\-\.]')


# WEB
#####


class App:
    BASE = '/importer'

    @classmethod
    def create(self):
        app = bottle.Bottle()

        app.route(
            path='/',
            callback=get_importers_dict,
        )
        app.route(
            path='/<name>/trig',
            method='POST',
            callback=lambda name: trig_import(name),
        )
        app.route(
            path='/status',
            method='GET',
            callback=get_status,
        )

        return app


def get_importers_dict():
    entries = []
    for name in sorted(current_system().import_folders.keys()):
        entries.append({
            'name': name,
            'trig_url': get_trig_url(name),
        })

    return {
        '*schema': 'ImportFeed',
        'count': len(entries),
        'entries': entries,
    }


def trig_import(name):
    if ImportJob.lock.acquire(blocking=False):
        folder = current_system().import_folders[name]
        ImportJob(folder)
        return {'result': 'ok'}
    else:
        raise ResourceBusy('ImportJob')


def get_status():
    if ImportJob.files == 0:
        progress = 100
    else:
        progress = int((ImportJob.imported + ImportJob.failed) / ImportJob.files * 100)
    return {
        '*schema': 'ImportStatus',
        'folder_name': ImportJob.folder_name,
        'status': ImportJob.status,
        'files': ImportJob.files,
        'imported': ImportJob.imported,
        'failed': ImportJob.failed,
        'progress': progress,
    }


def get_trig_url(name):
    return '%s/%s/trig' % (App.BASE, name)


# IMPORT MODULE HANDLING
########################

mime_map = {}


def register_import_module(mime_type, module):
    mime_map[mime_type] = module


def get_import_module(mime_type):
    import_module = mime_map.get(mime_type, None)
    return import_module


class GenericImportModule(object):
    def __init__(self, folder, file_path, mime_type):
        self.folder = folder
        self.file_path = file_path
        self.full_path = folder.get_full_path(file_path)
        self.mime_type = mime_type


# IMPORT MANAGER
################


class ImportJob:
    lock = Lock()
    status = 'idle'
    files = 0
    imported = 0
    failed = 0
    folder_name = None

    def __init__(self, folder):
        logging.debug("Setting up import thread [Importer_%s].", folder.name)
        ImportJob.status = 'acquired'
        ImportJob.folder_name = folder.name
        thread = Thread(
            target=import_job,
            name="Importer_%s" % (folder.name),
            args=(folder, )
        )
        thread.daemon = True
        thread.start()


def import_job(folder):
    try:
        logging.info("Started importer thread for %s", repr(folder))
        ImportJob.status = 'scanning'
        ImportJob.files = 0
        ImportJob.imported = 0
        ImportJob.failed = 0

        full_path = None
        if folder.type == 'card':
            # Look for any device mounted under /media/, having a file <system>.images6
            folder.path = None
            pre_scanner = FolderScanner(current_system().mount_root, extensions=['images6'])
            wanted_filename = '.'.join([current_system().name, 'images6'])
            for filepath in pre_scanner.scan():
                filepath = os.path.join(current_system().mount_root, filepath)
                logging.debug('Found file %s', filepath)
                filename = os.path.basename(filepath)
                if filename == wanted_filename:
                    folder_name = open(filepath).readlines()[0].strip()
                    if folder_name == folder.name:
                        folder.path = os.path.dirname(filepath)
                        logging.info('Importing from %s (%s)', folder.path, folder.name)
                        break

        if folder.path is None:
            logging.error('Could not find %s', folder.name)
            raise Exception('Could not find %s' % folder.name)

        # Scan the root path for files matching the filter
        scanner = FolderScanner(folder.path, extensions=folder.extensions)
        for filepath in scanner.scan():
            if not folder.is_known(filepath):
                folder.add_to_import(filepath)
                ImportJob.files += 1
                logging.debug('To import %s.', filepath)

        # Create entries and import jobs for each found file
        ImportJob.status = 'importing'
        for file_path in folder:
            logging.debug("Importing %s", file_path)
            full_path = folder.get_full_path(file_path)

            # Try to obtain an import module (a job that can import the file)
            mime_type = guess_mime_type(full_path, raw=(folder.mode in ('raw', 'raw+jpg')))
            ImportModule = get_import_module(mime_type)

            if ImportModule is None:
                logging.error('Could not find an import module for %s', mime_type)
                ImportJob.failed += 1
                folder.add_failed(file_path)
                continue

            # Create new entry or attach to existing one
            entry = None
            new = None
            if folder.derivatives:
                # Try to see if there is an entry to match it with
                file_name = os.path.basename(file_path)
                m = re.search(r'^[0-9a-f]{8}', file_name)
                if m is not None:
                    hex_id = m.group(0)
                    logging.debug('Converting hex %s into decimal', hex_id)
                    entry_id = int(hex_id, 16)
                    logging.debug('Trying to use entry %s (%d)', hex_id, entry_id)
                    try:
                        entry = get_entry_by_id(entry_id)
                        new = False
                    except KeyError:
                        logging.warn('There was no such entry %s (%d)', hex_id, entry_id)

            if entry is None:
                logging.debug('Creating entry...')
                entry = create_entry(Entry(
                    original_filename=os.path.basename(file_path),
                    state=State.new,
                    import_folder=folder.name,
                    mime_type=mime_type,
                ))
                logging.debug('Created entry %d.', entry.id)
                new = True

            options = ImportModule.Options(
                entry_id=entry.id,
                source_path=file_path,
                mime_type=mime_type,
                is_derivative=not new,
                folder=folder.name,
            )
            job = create_job(Job(
                method=ImportModule.method,
                options=options,
            ))

            ImportJob.imported += 1
            folder.add_imported(file_path)
            logging.info("Created job %d for %s", job.id, full_path)

        ImportJob.status = 'done'

    except Exception as e:
        logging.error('Import thread failed for %s: %s', full_path, str(e))
        ImportJob.status = 'error'
        raise e

    finally:
        ImportJob.lock.release()
        logging.debug("Import thread closing.")


def guess_mime_type(file_path, raw=False):
    if raw:
        mime_type = 'image/' + os.path.splitext(file_path)[1].lower().replace('.', '')
    else:
        mime_type = mimetypes.guess_type(file_path)[0]
    logging.debug("Guessed MIME Type '%s' for '%s'", mime_type, file_path)
    return mime_type
