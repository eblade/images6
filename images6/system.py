import logging
import configparser
import os
import threading
import json


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
        self.setup_server()
        self.setup_database()

        current_system.system = self
        logging.info("System registered.")


    def setup_filesystem(self):
        self.root = os.path.expanduser(os.path.expandvars(self.config['Filesystem']['root']))
        self.media_root = os.path.join(self.root, 'media')
        os.makedirs(self.media_root, exist_ok=True)
        logging.debug("Root path: %s", self.root)

    def setup_import(self):
        self.import_folders = {}
        for name, path in self.config['Import'].items():
            path = os.path.expanduser(os.path.expandvars(path))
            logging.debug("Loading import folder '%s': %s", name, path)
            if name.startswith('-'):
                name = name[1:]
                auto_remove = True
            else:
                auto_remove = False
            import_folder = ImportFolder(name, path, self.root, auto_remove)
            self.import_folders[name] = import_folder

    def setup_server(self):
        self.server_host = self.config['Server']['host']
        self.server_port = int(self.config['Server']['port'])

    def setup_database(self):
        self.database_root = os.path.join(self.root, 'database')
        self.database = Database(self.database_root)


class ImportFolder:
    def __init__(self, name, path, system_root, auto_remove):
        self.name = name
        self.path = path
        self.auto_remove = auto_remove
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            logging.error("Import Folder %s not reachable: %s.", path, str(e))

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


class Database:
    def __init__(self, root_path):
        self.lock = threading.Lock()
        self.root_path = root_path
        self.data_folder = os.path.join(self.root_path, 'data')
        os.makedirs(self.data_folder, exist_ok=True)

        self.id_counter_file = os.path.join(self.root_path, 'id_counter')
        self.load_entries()

    def next_id(self):
        with self.lock:
            try:
                with open(self.id_counter_file, 'r') as f:
                    current = int(f.readline()) 
            except IOError:
                current = 0
            with open(self.id_counter_file, 'w') as f:
                f.write(str(current + 1))
            return current
    
    def load_entries(self):
        with self.lock:
            logging.info("Loading entries...")
            self.entries = []
            self.entries_by_id = {}
            for r, ds, fs in os.walk(self.data_folder):
                for f in fs:
                    if f.endswith('.json'):
                        path = os.path.join(r, f)
                        with open(path, 'rb') as f:
                            s = f.read().decode('utf8')
                            entry = json.loads(s)
                            self._read_entry(entry)
            self._sort()
            logging.info("Loaded %i entries.", len(self.entries))

    def _read_entry(self, entry):
        self.entries.append(entry)
        self.entries_by_id[entry.get('id')] = entry

    def _sort(self):
        self.entries.sort(key=lambda e: e.get('taken_ts'), reverse=True)

    def sort(self):
        with self.lock:
            self._sort()

    def get(self, id):
        return self.entries_by_id[id]

    def update(self, id, new_entry):
        with self.lock:
            old_entry = self.entries_by_id[id]
            index = self.entries.index(old_entry)
            self.entries[index] = new_entry
            self.entries_by_id[id] = new_entry
            path = os.path.join(
                    self.data_folder,
                    self.get_json_filename(id)
            )
            tmp_path = path + '.tmp'
            with open(tmp_path, 'wb') as f:
                s = json.dumps(new_entry, indent=2, sort_keys=True)
                f.write(s.encode('utf8'))
            os.remove(path)
            os.rename(tmp_path, path)

    def create(self, id, new_entry):
        with self.lock:
            self._read_entry(new_entry)
            path = os.path.join(
                self.data_folder,
                self.get_json_filename(id)
            )
            with open(path, 'wb') as f:
                s = json.dumps(new_entry, indent=2, sort_keys=True)
                f.write(s.encode('utf8'))

    def delete(self, id):
        with self.lock:
            entry = self.entries_by_id[id]
            self.entries.remove(entry)
            del self.entries_by_id[id]
            path = os.path.join(
                self.data_folder,
                self.get_json_filename(id)
            )
            os.remove(path)

    def count(self):
        return len(self.entries)

    def get_page(self, offset, page_size):
        if offset >= len(self.entries):
            return []
        return self.entries[offset:offset + page_size]
    
    def get_json_filename(self, id):
        return '%08x.json' % (id)
