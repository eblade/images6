import logging
import bottle
import datetime
import urllib
import mimetypes
import os

from .system import current_system
from .types import PropertySet, Property, EnumProperty
from .metadata import register_metadata_schema
from .web import (
    Create,
    FetchById,
    FetchByQuery,
    UpdateById,
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

        return app


# DESCRIPTOR
############


class State(EnumProperty):
    new = 'new'
    pending = 'pending'
    keep = 'keep'
    discard = 'discard'


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

    def get_filename(self, id):
        if self.mime_type == 'image/jpeg':
            extension = 'jpg'
        else:
            extensions = mimetypes.guess_all_extensions(self.mime_type)
            if len(extensions) == 0:
                extension = ''
            else:
                extension = extensions[-1]
        hex_id = '%08x' % (id)
        version = '_%i'  % self.version if self.version > 0 else ''
        filename = hex_id + version + extension
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

    self_url = Property()

    def calculate_urls(self):
        self.self_url = '%s/%i' % (App.BASE, self.id)
        self.urls = {}
        logging.info(self.variants)
        for variant in self.variants:
            if not variant.purpose.value in self.urls.keys():
                self.urls[variant.purpose.value] = {}
            self.urls[variant.purpose.value][variant.version] = '%s/%i/dl/%s/%i' % (
                App.BASE, self.id, variant.store, variant.version
            )


class EntryFeed(PropertySet):
    count = Property(int)
    total_count = Property(int)
    prev_link = Property()
    next_link = Property()
    offset = Property(int)
    entries = Property(list)


class EntryQuery(PropertySet):
    prev_offset = Property(int)
    offset = Property(int, default=0)
    page_size = Property(int, default=25, required=True)

    @classmethod
    def FromRequest(self):
        eq = EntryQuery()

        if bottle.request.query.prev_offset not in (None, ''):
            eq.prev_offset = bottle.request.query.prev_offset
        if bottle.request.query.offset not in (None, ''):
            eq.offset = bottle.request.query.offset
        if bottle.request.query.page_size not in (None, ''):
            eq.page_size = bottle.request.query.page_size

        return eq

    def to_query_string(self):
        return urllib.parse.urlencode(
            (
                ('prev_offset', self.prev_offset or ''),
                ('offset', self.offset),
                ('page_size', self.page_size),
            )
        )


#####
# API


def get_entries(query=None):
    if query is None:
        offset = 0
        page_size = 25
    else:
        logging.info(query.to_query_string())
        offset = query.offset
        page_size = query.page_size

    entry_data = current_system().database.get_page(offset, page_size)
    entries = [Entry.FromDict(entry) for entry in entry_data]
    for entry in entries:
        entry.calculate_urls()
    return EntryFeed(
        count=len(entry_data),
        offset=offset,
        entries=entries,
        total_count=current_system().database.count(),
    )


def get_entry_by_id(id):
    return Entry.FromDict(current_system().database.get(id))


def update_entry_by_id(id, ed):
    current_system().database.update(id, ed.to_dict())
    return get_entry_by_id(id)


def create_entry(ed):
    id = current_system().database.next_id()
    ed.id = id
    current_system().database.create(id, ed.to_dict())
    return get_entry_by_id(id)


def delete_entry_by_id(id):
    current_system().database.delete(id)
