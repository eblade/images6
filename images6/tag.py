import logging
import bottle
import urllib
from jsonobject import PropertySet, Property, Query

from .system import current_system
from .web import (
    FetchByQuery,
)
from .entry import Entry


# WEB
#####


class App:
    BASE = '/tag'

    @classmethod
    def create(self):
        app = bottle.Bottle()

        app.route(
            path='/',
            callback=FetchByQuery(get_tags, QueryClass=TagQuery),
        )

        return app


# DESCRIPTOR
############


class Tag(PropertySet):
    tag = Property()
    count = Property(int, default=0)
    self_url = Property(calculated=True)

    def calculate_urls(self):
        self.self_url = '%s?%s' % (
            App.BASE,
            TagQuery(tag=self.tag).to_query_string(),
        )


class TagFeed(PropertySet):
    page_size = Property(int)
    offset = Property(int)
    entries = Property(Tag, is_list=True)


class TagEntryFeed(PropertySet):
    tag = Property()
    page_size = Property(int)
    offset = Property(int)
    entries = Property(Entry, is_list=True)


class TagQuery(Query):
    offset = Property(int, default=0)
    page_size = Property(int, default=25)
    tag = Property()


# API
#####


def get_tags(query=None):
    if query is None:
        offset = 0
        page_size = 0
        tag = None

    else:
        logging.info(query.to_query_string())
        offset = query.offset
        page_size = query.page_size
        tag = query.tag

    if tag is not None:
        return get_tag(tag, offset, page_size)

    tag_iter = current_system().db['entry'].view('by_tag', group=True)

    tags = [
        Tag(
            tag=tag_data['key'],
            count=tag_data['value']
        )
        for n, tag_data
        in enumerate(tag_iter)
        if n >= offset and n < offset + page_size
    ]
    [tag.calculate_urls() for tag in tags]

    return TagFeed(entries=tags, offset=offset, page_size=page_size)


def get_tag(tag, offset, page_size):
    tag_iter = current_system().db['entry'].view(
        'by_tag',
        no_reduce=True,
        key=tag,
        include_docs=True,
    ) 

    entries = [
        Entry.FromDict(data['doc'])
        for n, data
        in enumerate(tag_iter)
        if n >= offset and n < offset + page_size
    ]
    [entry.calculate_urls() for entry in entries]

    return TagEntryFeed(
        tag=tag,
        entries=entries,
        offset=offset,
        page_size=page_size,
    )
