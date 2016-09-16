import logging
import bottle
import datetime
import urllib
import json
from jsonobject import PropertySet, Property, EnumProperty

from .system import current_system
from .web import (
    FetchByKey,
    FetchByQuery,
    UpdateByKey,
    PatchByKey,
    DeleteByKey,
)


# WEB
#####


class App:
    BASE = '/date'

    @classmethod
    def create(self):
        app = bottle.Bottle()

        app.route(
            path='/',
            callback=FetchByQuery(get_dates, QueryClass=DateQuery),
        )
        app.route(
            path='/<key>',
            callback=FetchByKey(get_date),
        )
        app.route(
            path='/<key>',
            method='PUT',
            callback=UpdateByKey(update_date, Date),
        )
        app.route(
            path='/<key>',
            method='PATCH',
            callback=PatchByKey(patch_date),
        )
        app.route(
            path='/<key>',
            method='DELETE',
            callback=DeleteByKey(delete_date),
        )

        return app


# DESCRIPTOR
############


class Date(PropertySet):
    date = Property()
    short = Property()
    full = Property()
    mimetype = Property(default='text/plain')

    count = Property(int, default=0, calculated=True)
    count_per_state = Property(dict, calculated=True)
    entries = Property(dict, calculated=True)

    self_url = Property(calculated=True)
    date_url = Property(calculated=True)

    def calculate_urls(self):
        self.self_url = App.BASE + '/' + self.date
        self.date_url = '/entry?date=' + self.date

        n_all = 0
        n_new = 0
        n_pending = 0
        n_keep = 0
        n_purge = 0

        for entry, state in self.entries.items():
            n_all += 1
            if state == 'new':
                n_new += 1
            elif state == 'pending':
                n_pending += 1
            elif state == 'keep':
                n_keep += 1
            elif state == 'purge':
                n_purge += 1

        self.count = n_all
        self.count_per_state = {
            'new': n_new,
            'pending': n_pending,
            'keep': n_keep,
            'purge': n_purge,
        }


class DateFeed(PropertySet):
    count = Property(int)
    entries = Property(Date, is_list=True)


class DateQuery(PropertySet):
    year = Property(int)
    month = Property(int)

    @classmethod
    def FromRequest(self):
        q = DateQuery()

        if bottle.request.query.year not in (None, ''):
            q.year = bottle.request.query.year
        if bottle.request.query.month not in (None, ''):
            q.month = bottle.request.query.month

        return q

    def to_query_string(self):
        return urllib.parse.urlencode(
            (
                ('year', str(self.year) or ''),
                ('month', str(self.month) or ''),
            )
        )


# API
#####


def get_dates(query=None):
    if query is None:
        query_str = ''

    else:
        logging.info(query.to_query_string())
        if query.month is not None:
            sk = (query.year, query.month)
            ek = (query.year, query.month, None)
        elif query.year is not None:
            sk = (query.year, )
            ek = (query.year, None)
        else:
            sk = None
            ek = None

    dates = [Date.FromDict(date) for date
             in current_system().date.view('by_date', startkey=sk, endkey=ek, include_docs=True)]
    [date.calculate_urls() for date in dates]
    return DateFeed(
        count=len(dates),
        entries=dates,
    )


def get_date(date):
    k = [int(x) for x in date.split('-')]
    date = Date.FromDict(current_system().date.view('by_date', key=k))
    date.calculate_urls()
    return date


def update_date(date, date_info):
    date_info.calculate_urls()
    date_info = date_info.to_dict()
    current_system().database.update_date_info(date, date_info)
    return get_date(date)


def patch_date(date, patch):
    logging.debug('Patch for %s: \n%s', date, json.dumps(patch, indent=2))
    date_info = get_date(date)

    for key, value in patch.items():
        if key in ('short', 'full'):
            setattr(date_info, key, value)

    return update_date(date, date_info)


def delete_date(date):
    current_system().database.delete_date_info(date)
