import logging
import bottle
import datetime
import urllib
import mimetypes
import os
import json
from jsonobject import (
    PropertySet,
    Property,
    EnumProperty,
    wrap_dict,
    get_schema,
)

from .system import current_system
from .web import (
    Create,
    FetchById,
    FetchByQuery,
    UpdateById,
    UpdateByIdAndQuery,
    PatchById,
    DeleteById,
)


# WEB
#####


class App:
    BASE = '/entry'

    @classmethod
    def create(self):
        app = bottle.Bottle()

        app.route(
            path='/',
            callback=FetchByQuery(get_entries, QueryClass=EntryQuery),
        )
        app.route(
            path='/<id:int>',
            callback=FetchById(get_entry_by_id),
        )
        app.route(
            path='/<id:int>',
            method='PUT',
            callback=UpdateById(update_entry_by_id, Entry),
        )
        app.route(
            path='/<id:int>/metadata',
            method='PATCH',
            callback=PatchById(patch_entry_metadata_by_id),
        )
        app.route(
            path='/<id:int>',
            method='PATCH',
            callback=PatchById(patch_entry_by_id),
        )
        app.route(
            path='/',
            method='POST',
            callback=Create(create_entry, Entry),
        )
        app.route(
            path='/<id:int>',
            method='DELETE',
            callback=DeleteById(delete_entry_by_id),
        )
        app.route(
            path='/<id:int>/state',
            method='PUT',
            callback=UpdateByIdAndQuery(update_entry_state, QueryClass=StateQuery),
        )
        app.route(
            path='/<id:int>/dl/<store>/<version:int>.<extension>',
            callback=download,
        )
        app.route(
            path='/<id:int>/dl/<store>.<extension>',
            callback=download_latest,
        )

        return app


# DESCRIPTOR
############


class State(EnumProperty):
    new = 'new'
    pending = 'pending'
    keep = 'keep'
    todo = 'todo'
    final = 'final'
    wip = 'wip'
    purge = 'purge'


class Access(EnumProperty):
    private = 'private'
    public = 'public'


class Purpose(EnumProperty):
    original = 'original'
    proxy = 'proxy'
    thumb = 'thumb'
    check = 'check'
    raw = 'raw'
    derivative = 'derivative'


class Type(EnumProperty):
    image = 'image'
    video = 'video'
    audio = 'audio'
    document = 'document'
    other = 'other'


class Variant(PropertySet):
    store = Property()
    mime_type = Property()
    size = Property(int)
    purpose = Property(enum=Purpose, default=Purpose.original)
    source_purpose = Property(enum=Purpose)
    version = Property(int, default=0)
    source_version = Property(int, default=0)
    width = Property(int)
    height = Property(int)
    angle = Property(int)
    mirror = Property()
    description = Property()

    _patchable = 'description', 'angle', 'mirror', \
                 'source_version', 'source_purpose', \
                 'size', 'width', 'height'

    def __repr__(self):
        return '<Variant %s/%i (%s)>' % (self.purpose.value, self.version, self.mime_type)

    def get_extension(self):
        if self.mime_type == 'image/jpeg':
            return '.jpg'
        elif self.purpose is Purpose.raw:
            return '.' + self.mime_type.split('/')[1]
        else:
            extensions = mimetypes.guess_all_extensions(self.mime_type)
            if len(extensions) == 0:
                return ''
            else:
                return extensions[-1]

    def get_filename(self, id):
        extension = self.get_extension()
        hex_id = '%08x' % (id)
        version = '_%i'  % self.version if self.version > 0 else ''
        filename = hex_id + version + extension
        return os.path.join(self.store, filename)


class Backup(PropertySet):
    method = Property()
    key = Property()
    url = Property()
    source_purpose = Property(enum=Purpose, default=Purpose.original)
    source_version = Property(int, default=0)


class Entry(PropertySet):
    id = Property(int, name='_id')
    type = Property(enum=Type, default=Type.image)
    revision = Property(name='_rev')
    mime_type = Property()
    original_filename = Property()
    import_folder = Property()
    state = Property(enum=State)
    access = Property(enum=Access, default=Access.private)
    variants = Property(type=Variant, is_list=True)
    tags = Property(list)
    taken_ts = Property()
    metadata = Property(wrap=True)
    backups = Property(type=Backup, is_list=True)
    title = Property()
    description = Property()

    urls = Property(dict, calculated=True)
    state_url = Property(calculated=True)

    self_url = Property(calculated=True)
    original_url = Property(calculated=True)
    thumb_url = Property(calculated=True)
    proxy_url = Property(calculated=True)
    check_url = Property(calculated=True)
    raw_url = Property(calculated=True)
    derivative_url = Property(calculated=True)

    _patchable = 'title', 'description', 'tags'

    def get_variant(self, purpose, version=None):
        variants = [variant for variant in self.variants
                    if variant.purpose == Purpose(purpose)]
        if len(variants) == 0:
            return None
        if version is None:  # take latest
            return sorted(
                variants,
                key=lambda variant: variant.version
            ).pop()
        else:
            try:
                return [variant for variant in variants if variant.version == version][0]
            except IndexError:
                return None

    def get_filename(self, purpose, version=None):
        variant = self.get_variant(purpose, version=version)
        if variant is None:
            return None
        else:
            return variant.get_filename(self.id)

    def get_next_version(self, purpose):
        variants = [variant for variant in self.variants
                    if variant.purpose == Purpose(purpose)]
        if len(variants) == 0:
            return 0
        return max([variant.version for variant in self.variants
                    if variant.purpose is purpose]) + 1

    def calculate_urls(self):
        self.self_url = '%s/%i' % (App.BASE, self.id)
        self.state_url = '%s/%i/state' % (App.BASE, self.id)
        self.urls = {}
        for variant in self.variants:
            if not variant.purpose.value in self.urls.keys():
                self.urls[variant.purpose.value] = {}
            url = '%s/%i/dl/%s/%i%s' % (
                App.BASE,
                self.id,
                variant.store,
                variant.version,
                variant.get_extension()
            )
            self.urls[variant.purpose.value][variant.version] = url
            if variant.purpose is Purpose.original:
                self.original_url = url
            elif variant.purpose is Purpose.proxy:
                self.proxy_url = url
            elif variant.purpose is Purpose.thumb:
                self.thumb_url = url
            elif variant.purpose is Purpose.check:
                self.check_url = url
            elif variant.purpose is Purpose.raw:
                self.raw_url = url
            elif variant.purpose is Purpose.derivative:
                self.derivative_url = url


class EntryFeed(PropertySet):
    count = Property(int)
    total_count = Property(int)
    offset = Property(int)
    date = Property()
    entries = Property(Entry, is_list=True)


class EntryQuery(PropertySet):
    prev_offset = Property(int)
    offset = Property(int, default=0)
    page_size = Property(int, default=25, required=True)
    date = Property()
    delta = Property(int, default=0)
    reverse = Property(bool, default=False)

    @classmethod
    def FromRequest(self):
        eq = EntryQuery()

        if bottle.request.query.prev_offset not in (None, ''):
            eq.prev_offset = bottle.request.query.prev_offset
        if bottle.request.query.offset not in (None, ''):
            eq.offset = bottle.request.query.offset
        if bottle.request.query.page_size not in (None, ''):
            eq.page_size = bottle.request.query.page_size
        if bottle.request.query.date not in (None, ''):
            eq.date = bottle.request.query.date
        if bottle.request.query.delta not in (None, ''):
            eq.delta = int(bottle.request.query.delta)
        if bottle.request.query.reverse not in (None, ''):
            eq.reverse = (bottle.request.query.reverse == 'yes')

        return eq

    def to_query_string(self):
        return urllib.parse.urlencode(
            (
                ('prev_offset', self.prev_offset or ''),
                ('offset', self.offset),
                ('page_size', self.page_size),
                ('date', self.date),
                ('delta', str(self.delta)),
                ('reverse', 'yes' if self.reverse else 'no'),
            )
        )


class StateQuery(PropertySet):
    state = Property()
    soft = Property(bool, default=False)

    @classmethod
    def FromRequest(self):
        sq = StateQuery()
        if bottle.request.query.state not in (None, ''):
            sq.state = bottle.request.query.state
        if bottle.request.query.soft not in (None, ''):
            sq.soft = bottle.request.query.soft == 'yes'

        return sq


#####
# API


def get_entries(query=None):
    if query is None:
        offset = 0
        page_size = 100
        date = None
        delta = 0
        reverse = False

    else:
        logging.info(query.to_query_string())
        offset = query.offset
        page_size = query.page_size
        date = query.date
        delta = query.delta
        reverse = query.reverse

    if date is None:
        entry_data = current_system().db['entry'].view(
            'by_taken_ts',
            include_docs=True
        )

    else:
        if date == 'today':
            date = datetime.date.today()
        else:
            date = (int(part) for part in date.split('-', 2))
            date = datetime.date(*date)
        date += datetime.timedelta(days=delta)
        entry_data = current_system().db['entry'].view(
            'by_taken_ts',
            startkey=(date.year, date.month, date.day),
            endkey=(date.year, date.month, date.day, any),
            include_docs=True
        )

    entries = [Entry.FromDict(entry.get('doc')) for entry in entry_data]
    for entry in entries:
        entry.calculate_urls()
    return EntryFeed(
        date=date.isoformat(),
        count=len(entries),
        offset=offset,
        entries=entries if not reverse else list(reversed(entries)),
    )


def get_entry_by_id(id):
    entry = Entry.FromDict(current_system().db['entry'][id])
    entry.calculate_urls()
    return entry


def get_entry_by_source(folder, filename):
    entry_data = list(current_system().db['entry'].view(
        'by_source',
        key=(folder, filename),
        include_docs=True
    ))
    if len(entry_data) > 0:
        return Entry.FromDict(entry_data[0]['doc'])
    else:
        return None



def update_entry_by_id(id, entry):
    entry.id = id
    logging.debug('Updating entry to\n%s', entry.to_json())
    entry = Entry.FromDict(current_system().db['entry'].save(entry.to_dict()))
    logging.debug('Updated entry to\n%s', entry.to_json())
    return entry


def update_entry_state(id, query):
    try:
        state = getattr(State, query.state)
    except AttributeError:
        raise bottle.HTTPError(400)

    entry = get_entry_by_id(id)

    if query.soft and entry.state != State.pending:
        return entry

    entry.state = state
    return update_entry_by_id(id, entry)


def patch_entry_metadata_by_id(id, patch):
    entry = get_entry_by_id(id)
    logging.debug('Metadata Patch for %d: \n%s', id, json.dumps(patch, indent=2))
    metadata_dict = entry.metadata.to_dict()
    metadata_dict.update(patch)
    metadata = wrap_dict(metadata_dict)
    entry.metadata = metadata
    logging.debug(entry.to_json())
    current_system().db['entry'].save(entry.to_dict())

    if 'Angle' in patch:
        options = get_schema('ImageProxyOptions')()
        options.entry_id = id
        #trig_plugin('imageproxy', options)

    return get_entry_by_id(id)


def patch_entry_by_id(id, patch):
    logging.debug('Patch for %d: \n%s', id, json.dumps(patch, indent=2))
    entry = get_entry_by_id(id)

    for key, value in patch.items():
        if key in Entry._patchable:
            setattr(entry, key, value)
        elif key == 'variants':
            purpose = value['purpose']
            version = value['version']
            variant = entry.get_variant(purpose, version=version)
            for key, value in value.items():
                if key in Variant._patchable:
                    setattr(variant, key, value)

    logging.info(entry.to_json())
    current_system().db['entry'].save(entry.to_dict())
    return get_entry_by_id(id)


def create_entry(ed):
    if ed.taken_ts is None:
        ed.taken_ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logging.debug('Create entry\n%s', ed.to_json())
    return Entry.FromDict(current_system().db['entry'].save(ed.to_dict()))


def delete_entry_by_id(id):
    current_system().db['entry'].delete(id)


def download(id, store, version, extension):
    download = bottle.request.query.download == 'yes'
    entry = get_entry_by_id(id)
    for variant in entry.variants:
        if variant.store == store and variant.version == version and variant.get_extension() == '.' + extension:
            return bottle.static_file(
                variant.get_filename(id),
                download=download,
                root=current_system().media_root
            )

    raise HTTPError(404)


def download_latest(id, store, extension):
    download = bottle.request.query.download == 'yes'
    entry = get_entry_by_id(id)
    chosen = None
    for variant in entry.variants:
        if variant.store == store and variant.get_extension() == '.' + extension:
            if chosen is None:
                chosen = variant
            elif chosen.version < variant.version:
                chosen = variant

    if chosen is not None:
        return bottle.static_file(
            chosen.get_filename(id),
            download=download,
            root=current_system().media_root
        )
    else:
        raise HTTPError(404)
