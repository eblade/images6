import logging
import bottle
import datetime
import urllib
from jsonobject import PropertySet, Property, EnumProperty

from .system import current_system
from .web import (
    FetchByKey,
    FetchByQuery,
    UpdateByKey,
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
    only = Property()

    count = Property(int, default=0)
    count_per_state = Property(dict)
    entries = Property(dict)

    self_url = Property()
    date_url = Property()

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
    entries = Property(list)


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
        if query.year is not None:
            query_str = '%04d-' % (query.year)
        elif query.month is not None:
            query_str = '%04d-%02d-' % \
                (datetime.date.today().year, query.month)
        elif query.month is None and query.year is None:
            query_str = ''
        else:
            query_str = '%04d-%02d-' % (query.year, query.month)

    dates = [Date.FromDict(date) for date 
             in current_system().database.get_dates(query_str)]
    [date.calculate_urls() for date in dates]
    return DateFeed(
        count=len(dates),
        entries=dates,
    )


def get_date(date):
    date = Date.FromDict(current_system().database.get_date_info(date))
    date.calculate_urls()
    return date


def update_date(date, date_info):
    old_date_info = current_system().database.get_date_info(date)
    if date_info.only == 'short':
        old_date_info['short'] = date_info.short
        date_info = old_date_info
    elif date_info.only == 'full':
        old_date_info['full'] = date_info.full
        date_info = old_date_info
    else:
        date_info = date_info.to_dict()
    current_system().database.update_date_info(date, date_info)
    return get_date(date)


def delete_date(date):
    current_system().database.delete_date_info(date)
