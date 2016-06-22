import logging
import bottle
import datetime
import urllib
import mimetypes
import os

from .system import current_system
from .types import PropertySet, Property, EnumProperty
from .web import (
    Create,
    FetchById,
    FetchByQuery,
    UpdateById,
    UpdateByIdAndQuery,
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

        return app


# DESCRIPTOR
############


class State(EnumProperty):
    new = 'new'
    pending = 'pending'
    keep = 'keep'
    purge = 'purge'


class Access(EnumProperty):
    private = 'private' 
    public = 'public'


class Purpose(EnumProperty):
    original = 'original'
    proxy = 'proxy'
    thumb = 'thumb'
    check = 'check'


class Variant(PropertySet):
    store = Property()
    mime_type = Property()
    size = Property(int)
    purpose = Property(enum=Purpose, default=Purpose.original)
    version = Property(int, default=0)
    width = Property(int)
    height = Property(int)

    def __repr__(self):
        return '<Variant %s/%i (%s)>' % (self.purpose.value, self.version, self.mime_type)

    def get_extension(self):
        if self.mime_type == 'image/jpeg':
            return 'jpg'
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
        filename = hex_id + version + '.' + extension
        return os.path.join(self.store, filename)


class Entry(PropertySet):
    id = Property(int)
    mime_type = Property()
    original_filename = Property()
    import_folder = Property()
    state = Property(enum=State)
    access = Property(enum=Access, default=Access.private)
    variants = Property(type=Variant, is_list=True)
    tags = Property(list)
    taken_ts = Property()
    metadata = Property(wrap=True)
    backups = Property(list)

    urls = Property(dict)
    state_url = Property()

    self_url = Property()
    original_url = Property()
    thumb_url = Property()
    proxy_url = Property()
    check_url = Property()

    def calculate_urls(self):
        self.self_url = '%s/%i' % (App.BASE, self.id)
        self.state_url = '%s/%i/state' % (App.BASE, self.id)
        self.urls = {}
        logging.info(self.variants)
        for variant in self.variants:
            if not variant.purpose.value in self.urls.keys():
                self.urls[variant.purpose.value] = {}
            url = '%s/%i/dl/%s/%i.%s' % (
                App.BASE, self.id, variant.store, variant.version, variant.get_extension()
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


class EntryFeed(PropertySet):
    count = Property(int)
    total_count = Property(int)
    prev_link = Property()
    next_link = Property()
    offset = Property(int)
    date = Property()
    previous_date = Property()
    next_date = Property()
    entries = Property(list)


class EntryQuery(PropertySet):
    prev_offset = Property(int)
    offset = Property(int, default=0)
    page_size = Property(int, default=25, required=True)
    date = Property()
    delta = Property(int)

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

        return eq

    def to_query_string(self):
        return urllib.parse.urlencode(
            (
                ('prev_offset', self.prev_offset or ''),
                ('offset', self.offset),
                ('page_size', self.page_size),
                ('date', self.date),
                ('delta', str(self.delta)),
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
        page_size = 25
        date = None
        delta = 0

    else:
        logging.info(query.to_query_string())
        offset = query.offset
        page_size = query.page_size
        date = query.date
        delta = query.delta

    if date is None:
        entry_data = current_system().database.get_page(offset, page_size)
        before = None
        after = None

    else:
        if date == 'today':
            date = datetime.date.today()
        else:
            date = (int(part) for part in date.split('-', 2))
            date = datetime.date(*date)
        date += datetime.timedelta(days=delta)
        before, entry_data, after = \
            current_system().database.get_day(date.isoformat())

    entries = [Entry.FromDict(entry) for entry in entry_data]
    for entry in entries:
        entry.calculate_urls()
    return EntryFeed(
        date=date,
        count=len(entry_data),
        offset=offset,
        entries=entries,
        total_count=current_system().database.count(),
        previous_date=before,
        next_date=after,
    )


def get_entry_by_id(id):
    entry = Entry.FromDict(current_system().database.get(id))
    entry.calculate_urls()
    return entry


def update_entry_by_id(id, ed):
    current_system().database.update(id, ed.to_dict())
    return get_entry_by_id(id)


def update_entry_state(id, query):
    try:
        state = getattr(State, query.state)
    except AttributeError:
        raise bottle.HTTPError(400)

    entry = get_entry_by_id(id)

    if query.soft and entry.state != 'pending':
        return entry

    entry.state = state
    return update_entry_by_id(id, entry)


def create_entry(ed):
    id = current_system().database.next_id()
    ed.id = id
    current_system().database.create(id, ed.to_dict())
    return get_entry_by_id(id)


def delete_entry_by_id(id):
    current_system().database.delete(id)


def download(id, store, version, extension):
    download = bottle.request.query.download == 'yes'
    entry = get_entry_by_id(id)
    for variant in entry.variants:
        if variant.store == store and variant.version == version and variant.get_extension() == extension:
            return bottle.static_file(variant.get_filename(id), download=download, root=current_system().media_root)
