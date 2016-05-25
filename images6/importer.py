"""Take care of import jobs and copying files. Keep track of import modules"""

import logging
import mimetypes
import os
import re
import base64
import bottle

from threading import Thread, Event, Lock

from .web import ResourceBusy
from .system import current_system
from .entry import Entry, create_entry, update_entry_by_id
from .metadata import wrap_raw_json


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
    for name in current_system().import_folders.keys():
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
        progress = 0
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


# LOCAL FOLDER SCANNER
######################


class FolderScanner(object):
    def __init__(self, basepath, ext=None):
        self.basepath = basepath
        self.ext = ext

    def scan(self):
        for r, ds, fs in os.walk(self.basepath):
            for f in fs:
                if not self.ext or f.split('.')[-1].lower() in self.ext:
                    p = os.path.relpath(os.path.join(r, f), self.basepath)
                    if not p.startswith('.'):
                        yield p


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

        scanner = FolderScanner(folder.path, ext='jpg')
        for filepath in scanner.scan():
            if not folder.is_known(filepath):
                folder.add_to_import(filepath)
                ImportJob.files += 1
                logging.debug('To import %s.', filepath)

        ImportJob.status = 'importing'
        for file_path in folder:
            logging.debug("Importing %s", file_path)
            full_path = folder.get_full_path(file_path)

            mime_type = guess_mime_type(full_path)
            ImportModule = get_import_module(mime_type)

            if ImportModule is None:
                logging.error('Could not find an import module for %s', mime_type)
                ImportJob.failed += 1
                folder.add_failed(file_path)
                continue

            import_module = ImportModule(folder, file_path, mime_type)
            try:
                logging.debug("Run import module %s", ImportModule.__name__)
                import_module.run()
                logging.debug("Import module ran successfully.")
            except Exception as e:
                logging.error('Import failed for %s: %s', full_path, str(e))
                ImportJob.failed += 1
                folder.add_failed(file_path)
                import_module.clean_up()
                raise e

            ImportJob.imported += 1
            folder.add_imported(file_path)
            logging.debug("Imported %s", full_path)

        ImportJob.status = 'done'

    except Exception as e:
        logging.error('Import thread failed for %s: %s', full_path, str(e))
        ImportJob.status = 'error'
        raise e

    finally:
        ImportJob.lock.release()
        logging.debug("Import thread closing.")


def guess_mime_type(file_path):
    mime_type = mimetypes.guess_type(file_path)[0]
    logging.debug("Guessed MIME Type '%s' for '%s'", mime_type, file_path)
    return mime_type
