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
        self.setup_server()
        self.setup_database()
        self.setup_plugins()

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
        self.server_adapter = self.config['Server'].get('adapter', 'cherrypy')

    def setup_database(self):
        self.entry_root = os.path.join(self.root, 'entry')
        self.entry = jsondb.Database(self.entry_root)
        self.entry.define('by_taken_ts', lambda o: {o['taken_ts']: None})
        self.entry.define('by_date', lambda o: {o['taken_ts'][10:]: None})

        self.date_root = os.path.join(self.root, 'date')
        self.date = jsondb.Database(self.date_root)
        self.date.define('by_date', lambda o: {o['date']: None})

    def setup_plugins(self):
        self.plugin_workers = self.config['Plugin'].getint('workers')
        self.plugin_config = {}
        for section in self.config.sections():
            if section.startswith("Plugin:"):
                method = section[7:]
                self.plugin_config[method] = {k.replace(' ', '_'): v for k, v in self.config.items(section)}
                logging.info('Loaded plugin config for %s.', method)


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


#class Database:
#    def __init__(self, root_path):
#        self.lock = threading.Lock()
#        self.root_path = root_path
#        self.data_folder = os.path.join(self.root_path, 'data')
#        self.date_folder = os.path.join(self.root_path, 'date')
#        os.makedirs(self.data_folder, exist_ok=True)
#        os.makedirs(self.date_folder, exist_ok=True)
#
#        self.id_counter_file = os.path.join(self.root_path, 'id_counter')
#        self.load_entries()
#
#    def next_id(self):
#        with self.lock:
#            try:
#                with open(self.id_counter_file, 'r') as f:
#                    current = int(f.readline())
#            except IOError:
#                current = 0
#            with open(self.id_counter_file, 'w') as f:
#                f.write(str(current + 1))
#            return current
#
#    def load_entries(self):
#        with self.lock:
#            logging.info("Loading entries...")
#            self.entries = []
#            self.entries_by_id = {}
#            self.dates = {}
#            for r, ds, fs in os.walk(self.data_folder):
#                for f in fs:
#                    if f.endswith('.json'):
#                        path = os.path.join(r, f)
#                        with open(path, 'rb') as f:
#                            s = f.read().decode('utf8')
#                            entry = json.loads(s)
#                            self._read_entry(entry)
#            self._sort()
#            logging.info("Loaded %i entries.", len(self.entries))
#
#    def _read_entry(self, entry):
#        self.entries.append(entry)
#        self.entries_by_id[entry.get('id')] = entry
#        date = (entry.get('taken_ts') or '')[:10]
#        self._load_date(date, entry)
#
#    def _sort(self):
#        self.entries.sort(key=lambda e: e.get('taken_ts'), reverse=True)
#
#    def _load_date(self, date, entry):
#        if not date:
#            return
#        if date not in self.dates.keys():
#            try:
#                path = os.path.join(self.date_folder, date + '.json')
#                with open(path, 'rb') as f:
#                    s = f.read().decode('utf8')
#                    date_data = json.loads(s)
#                    date_data['entries'] = {
#                        entry['id']: entry['state']
#                    }
#                    self.dates[date] = date_data
#            except OSError:
#                self.dates[date] = {
#                    'entries': {
#                        entry['id']: entry['state'],
#                    },
#                }
#        else:
#            if not 'entries' in self.dates[date].keys():
#                self.dates[date]['entries'] = {}
#            self.dates[date]['entries'][entry['id']] = entry['state']
#
#    def sort(self):
#        with self.lock:
#            self._sort()
#
#    def get(self, id):
#        return self.entries_by_id[id]
#
#    def update(self, id, new_entry):
#        with self.lock:
#            old_entry = self.entries_by_id[id]
#            index = self.entries.index(old_entry)
#            self.entries[index] = new_entry
#            self.entries_by_id[id] = new_entry
#            path = os.path.join(
#                    self.data_folder,
#                    self.get_json_filename(id)
#            )
#            tmp_path = path + '.tmp'
#            with open(tmp_path, 'wb') as f:
#                s = json.dumps(new_entry, indent=2, sort_keys=True)
#                f.write(s.encode('utf8'))
#            os.remove(path)
#            os.rename(tmp_path, path)
#
#            date = (new_entry.get('taken_ts') or '')[:10]
#            self._load_date(date, new_entry)
#
#    def create(self, id, new_entry):
#        with self.lock:
#            self._read_entry(new_entry)
#            path = os.path.join(
#                self.data_folder,
#                self.get_json_filename(id)
#            )
#            with open(path, 'wb') as f:
#                s = json.dumps(new_entry, indent=2, sort_keys=True)
#                f.write(s.encode('utf8'))
#
#    def delete(self, id):
#        with self.lock:
#            entry = self.entries_by_id[id]
#            self.entries.remove(entry)
#            del self.entries_by_id[id]
#            path = os.path.join(
#                self.data_folder,
#                self.get_json_filename(id)
#            )
#            os.remove(path)
#            date = (entry.get('taken_ts') or '')[:10]
#            date_info = self.dates.get(date)
#            if date_info is not None:
#                try:
#                    del date_info['entries'][id]
#                except KeyError:
#                    pass
#
#    def count(self):
#        return len(self.entries)
#
#    def get_page(self, offset, page_size):
#        if offset >= len(self.entries):
#            return []
#        return self.entries[offset:offset + page_size]
#
#    def get_day(self, date):
#        that_day = list(reversed(
#            [(index, entry) for index, entry in enumerate(self.entries)
#             if entry.get('taken_ts', '').startswith(date)]
#        ))
#        if len(that_day) == 0:
#            return None, [], None
#        earliest = that_day[0][0]
#        latest = that_day[-1][0]
#        before = None if earliest == self.count() - 1 else earliest + 1
#        after = None if latest == 0 else latest - 1
#        if before is not None:
#            before = self.entries[before].get('taken_ts')[:10]
#        if after is not None:
#            after = self.entries[after].get('taken_ts')[:10]
#        return before, [e[1] for e in that_day], after
#
#    def get_json_filename(self, id):
#        return '%08x.json' % (id)
#
#    def get_ids_in_state(self, state):
#        with self.lock:
#            return list([entry.get('id') for entry in self.entries
#                         if entry.get('state') == state])
#
#    def get_date_info(self, date):
#        date_info = self.dates.get(date, {})
#        date_info['date'] = date
#        return date_info
#
#    def get_dates(self, query_str=''):
#        with self.lock:
#            result = []
#            for date in reversed(sorted(self.dates.keys())):
#                if not date.startswith(query_str):
#                    continue
#                date_info = self.dates[date]
#                post = dict(date_info)
#                post['date'] = date
#                result.append(post)
#            return result
#
#    def update_date_info(self, date, new_date_info):
#        new_date_info = dict(
#            short=new_date_info.get('short'),
#            full=new_date_info.get('full'),
#            mimetype=new_date_info.get('mimetype', 'text/plain'),
#        )
#        with self.lock:
#            path = os.path.join(self.date_folder, date + '.json')
#            with open(path, 'wb') as f:
#                s = json.dumps(new_date_info, indent=2, sort_keys=True)
#                f.write(s.encode('utf8'))
#            self.dates[date] = dict(new_date_info)
#
#    def delete_date_info(self, date):
#        with self.lock:
#            path = os.path.join(self.date_folder, date + '.json')
#            try:
#                os.remove(path)
#            except OSError:
#                pass
#            try:
#                del self.dates[date]
#            except KeyError:
#                pass
