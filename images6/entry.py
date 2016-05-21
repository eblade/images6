import logging
import bottle
import datetime
import urllib
import mimetypes

from enum import Enum

from .system import current_system
from .types import PropertySet, Property
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
            callback=FetchByQuery(get_entries),
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


class State(Enum):
    new = 0
    pending = 1
    keep = 2
    descard = 3


class Access(Enum):
    private = 0
    public = 1


class Purpose(Enum):
    original = 0
    proxy = 1
    thumb = 2
    check = 3


class Entry(PropertySet):
    id = Property(int)
    mime_type = Property()
    original_filename = Property()
    import_folder = Property()
    state = Property(enum=State)
    access = Property(enum=Access, default=Access.private)
    variants = Property(dict)
    tags = Property(list)
    taken_ts = Property()
    metadata = Property(wrap=True)
    backups = Property(list)

    urls = Property(dict)

    self_url = Property()

    def calculate_urls(self):
        self.self_url = '%s/%s' % (App.BASE, self.file_name)
        for variant, file_name in self.variants.items():
            self.urls[variant] = '%s/%s/dl/%s/%s' % (
                App.BASE, self.file_name, variant, file_name
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
    def FromQuery(self):
        eq = EntryQuery()

        if bottle.request.query.prev_offset not in (None, ''):
            eq.prev_offset = bottle.request.query.prev_offset
        if bottle.request.query.offset not in (None, ''):
            eq.order = bottle.request.query.offset
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


class Variant(PropertySet):
    store = Property()
    mime_type = Property()
    size = Property(int)
    purpose = Property(enum=Purpose, default=Purpose.original)
    version = Property(int)
    width = Property(int)
    height = Property(int)

    def get_filename(self, id):
        extensions = mimetypes.guess_all_extensions(self.mime_type)
        if len(extensions) == 0:
            extension = ''
        else:
            extension = extensions[-1]
        hex_id = '%08x' % (id)
        version = '_%i'  % self.version if self.version > 0 else ''
        filename = hex_id + version + extension
        return os.path.join(self.store, filename)


#####
# API


def get_entries(query=None):
    if query is None:
        offset = 0
        page_size = 25
    else:
        offset = query.offset
        page_size = query.page_size
    entry_data = current_system().get_page(offset, page_size)


def get_entry_by_id(id):
    return Entry.FromDict(current_system().get_data(id))


def update_entry_by_id(id, ed):
    current_system().update(id, ed.to_dict())
    return get_entry_by_id(id)


def create_entry(ed):
    id = current_system().next_id()
    ed.id = id
    current_system().update(id, ed.to_dict())
    return get_entry_by_id(id)


def delete_entry_by_id(id):
    current_system().delete(id)
