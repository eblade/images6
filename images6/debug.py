import logging
import bottle
import json


from .system import current_system



# WEB
#####


class App:
    BASE = '/debug'

    @classmethod
    def create(self):
        app = bottle.Bottle()

        app.route(
            path='/map/<db>/<view>',
            callback=raw_map,
        )

        app.route(
            path='/reduce/<db>/<view>',
            callback=raw_reduce,
        )

        app.route(
            path='/include/<db>/<view>',
            callback=raw_include,
        )

        return app


# API
#####


def raw_map(db, view):
    return json.dumps(
        list(current_system().db[db].view(view, no_reduce=True)),
        indent=2,
    ) + '\n'


def raw_reduce(db, view):
    return json.dumps(
        list(current_system().db[db].view(view, group=True)),
        indent=2,
    ) + '\n'


def raw_include(db, view):
    return json.dumps(
        list(current_system().db[db].view(view, no_reduce=True, include_docs=True)),
        indent=2,
    ) + '\n'
