import logging
import configparser
import os
import threading
import json
import jsondb


def current_system():
    return current_system.system
current_system.system = None


class System:
    def __init__(self, config_path):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.name = self.config['Images']['name']
        self.fullname = self.config['Images'].get('full name', self.name)
        self.proxy_size = self.config['Images'].getint('proxy size', 1280)
        self.thumb_size = self.config['Images'].getint('thumb size', 200)
        self.check_size = self.config['Images'].getint('check size', 300)

        logging.info("Config read from %s", config_path)

        self.setup_filesystem()
        self.setup_import()
        self.setup_export()
        self.setup_server()
        self.setup_database()
        self.setup_jobs()

        current_system.system = self
        logging.info("System registered.")


    def setup_filesystem(self):
        self.root = os.path.expanduser(os.path.expandvars(self.config['Filesystem']['root']))
        self.mount_root = os.path.expanduser(os.path.expandvars(self.config['Filesystem']['mount root']))
        self.media_root = os.path.join(self.root, 'media')
        os.makedirs(self.media_root, exist_ok=True)
        logging.debug("Root path: %s", self.root)

    def setup_import(self):
        self.import_folders = {}
        for section in self.config.sections():
            if section.startswith("Import:"):
                name = section[7:]
                config = {k.replace(' ', '_'): v for k, v in self.config.items(section)}
                import_folder = ImportFolder(name, self.root, **config)
                self.import_folders[name] = import_folder

    def setup_export(self):
        self.export_folders = {}
        for section in self.config.sections():
            if section.startswith("Export:"):
                name = section[7:]
                config = {k.replace(' ', '_'): v for k, v in self.config.items(section)}
                export_folder = ExportFolder(name, self.root, **config)
                self.export_folders[name] = export_folder

    def setup_server(self):
        self.server_host = self.config['Server']['host']
        self.server_port = int(self.config['Server']['port'])
        self.server_adapter = self.config['Server'].get('adapter', 'cherrypy')

    def setup_database(self):
        self.db = dict()

        def sum_per(field, values):
            result = {}
            for value in values:
                v = value.get(field)
                if v in result:
                    result[v] += 1
                else:
                    result[v] = 1
            result['total'] = len(values)
            return result

        def each_tag(value):
            for subvalue in value.get('tags', []):
                yield (subvalue, None)

        def each_tag_with_taken_ts(value):
            for subvalue in value.get('tags', []):
                yield ((subvalue, value.get('taken_ts')), None)

        self.entry_root = os.path.join(self.root, 'entry')
        entry = jsondb.Database(self.entry_root)
        entry.define(
            'by_taken_ts',
            lambda o: (tuple(int(x) for x in o['taken_ts'][:10].split('-')) + (o['taken_ts'][11:],), None)
        )
        entry.define(
            'state_by_date',
            lambda o: (o['taken_ts'][:10], {'state': o['state']}),
            lambda keys, values, rereduce: sum_per('state', values)
        )
        entry.define(
            'by_date',
            lambda o: (tuple(int(x) for x in o['taken_ts'][:10].split('-')), None)
        )
        entry.define(
            'by_state',
            lambda o: (o['state'], None)
        )
        entry.define(
            'by_state_and_taken_ts',
            lambda o: ((o['state'], o['taken_ts']), None)
        )
        entry.define(
            'by_source',
            lambda o: ((o['import_folder'], o['original_filename']), None)
        )
        entry.define(
            'by_tag',
            each_tag,
            lambda keys, values, rereduce: len(values),
        )
        entry.define(
            'by_tag_and_taken_ts',
            each_tag_with_taken_ts,
        )
        self.db['entry'] = entry

        self.date_root = os.path.join(self.root, 'date')
        date = jsondb.Database(self.date_root)
        date.define(
            'by_date',
            lambda o: (o['_id'], None)
        )
        self.db['date'] = date

        self.job_root = os.path.join(self.root, 'job')
        job = jsondb.Database(self.job_root)
        job.define(
            'by_state',
            lambda o: ((o['state'], o['release'], o['priority']), None),
        )
        job.define(
            'by_updated',
            lambda o: (10000000000 - int(o['updated']), None),
        )
        job.define(
            'stats',
            lambda o: (None, {'state': o['state']}),
            lambda keys, values, rereduce: sum_per('state', values),
        )
        self.db['job'] = job

    def setup_jobs(self):
        self.job_workers = self.config['Job'].getint('workers')
        self.job_config = {}
        for section in self.config.sections():
            if section.startswith("Job:"):
                method = section[4:]
                self.job_config[method] = {k.replace(' ', '_'): v for k, v in self.config.items(section)}
                logging.info('Loaded job config for %s.', method)


class ImportFolder:
    def __init__(self, name, system_root, type=None, mode=None, path=None, remove_source=False, extension=None, derivatives=False):
        logging.info("Setting up import folder %s", name)
        assert type is not None, 'Import type required'
        assert type, 'Import type required (card or folder)'
        self.name = name
        self.type = type
        self.path = os.path.expandvars(os.path.expanduser(path)) if path else None
        if type == 'folder': assert path, 'Import path required for folder'
        self.auto_remove = (remove_source == 'yes')
        self.mode = mode
        if type == 'card': assert mode, 'Import mode required for card (raw or jpg)'
        self.extensions = extension.strip().lower().split()
        assert extension, 'Import extension required'
        self.derivatives = derivatives
        if type == 'card': assert not derivatives, 'Import derivatives only applies for folder type'

        if type == 'folder':
            try:
                os.makedirs(self.path, exist_ok=True)
            except Exception as e:
                logging.error("Import Folder %s not reachable: %s.", self.path, str(e))

        self.imported_file = os.path.join(
                system_root, name + '_imported.index')
        self.failed_file = os.path.join(
                system_root, name + '_failed.index')
        try:
            with open(self.imported_file) as f:
                self.imported = set([
                    line.strip() for line in f.readlines() if line
                ])
        except IOError:
            self.imported = set()
        try:
            with open(self.failed_file) as f:
                self.failed = set([
                    line.strip() for line in f.readlines() if line
                ])
        except IOError:
            self.failed = set()
        self.to_import = set()

    def __repr__(self):
        return '<ImportFolder %s%s %s>' % ('-' if self.auto_remove else '+', self.name, self.path)

    def is_imported(self, path):
        return path in self.imported

    def is_known(self, path):
        return any((
            path in self.imported,
            path in self.failed,
        ))

    def add_imported(self, path):
        self.imported.add(path)
        with open(self.imported_file, 'a') as f:
            f.write(path + '\n')

    def add_to_import(self, path):
        self.to_import.add(path)

    def add_failed(self, path):
        self.failed.add(path)
        with open(self.failed_file, 'a') as f:
            f.write(path + '\n')

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return self.to_import.pop()
        except KeyError:
            raise StopIteration

    def get_full_path(self, filepath):
        return os.path.join(self.path, filepath)


class ExportFolder:
    def __init__(self, name, system_root, type='folder', mode=None, path=None, filename=None, backup=False, backup_type=None, longest_side=None):
        logging.info("Setting up export folder %s", name)
        assert type is not None, 'Import type required'
        assert type == 'folder', 'Import type required (folder)'
        self.name = name
        self.type = type
        self.path = os.path.expandvars(os.path.expanduser(path)) if path else None
        if type == 'folder': assert path, 'Export path required for folder'
        self.filename = filename or None
        self.mode = mode
        self.backup = (backup == 'yes')
        self.backup_type = backup_type
        if self.backup: assert backup_type in ('google', ), 'backup option requires backup type'
        self.longest_side = None if longest_side is None else int(longest_side)

        if type == 'folder':
            try:
                os.makedirs(self.path, exist_ok=True)
            except Exception as e:
                logging.error("Export Folder %s not reachable: %s.", self.path, str(e))

    def __repr__(self):
        return '<ExportFolder %s%s %s>' % ('+' if self.backup else '-', self.name, self.path)

    def get_full_path(self, filepath):
        return os.path.join(self.path, filepath)
