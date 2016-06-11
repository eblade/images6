import logging
import bottle
import datetime
import urllib

from .system import current_system
from .types import PropertySet, Property, EnumProperty
from .web import (
    FetchById,
    FetchByQuery,
    UpdateById,
    DeleteById,
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
            path='/<date>',
            callback=FetchById(get_date),
        )
        app.route(
            path='/<date>',
            method='PUT',
            callback=UpdateById(update_date, Date),
        )
        app.route(
            path='/<date>',
            method='DELETE',
            callback=DeleteById(delete_date),
        )

        return app


# DESCRIPTOR
############


class Date(PropertySet):
    date = Property()
    short = Property()
    full = Property()
    mimetype = Property(default='text/plain')

    self_url = Property()
    date_url = Property()

    def calculate_urls(self):
        self.self_url = App.BASE + '/' + self.date
        self.date_url = '/entry?date=' + self.date


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
    date = Date.FromDict(current_system().database.get_date(date))
    date.calculate_urls()
    return date


def update_date(date, date_info):
    current_system().database.update_date_info(date, date_info.to_dict())
    return get_date_info(date)


def delete_date(date):
    current_system().database.delete_date_info(date)
