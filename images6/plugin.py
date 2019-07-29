import logging
import bottle
import threading
import time

from lindh.jsonobject import wrap_dict

from .multi import Pool
from .system import current_system


# WEB
#####


class App:
    BASE = '/plugin'

    @classmethod
    def create(self):
        app = bottle.Bottle()

        app.route(
            path='/',
            callback=get_plugins_dict,
        )
        app.route(
            path='/<method>/trig',
            method='POST',
            callback=lambda method: trig_plugin(method),
        )
        app.route(
            path='/status',
            method='GET',
            callback=get_status,
        )

        return app

    @classmethod
    def run(self, **kwargs):
        def service(**kwargs):
            with Pool(**kwargs) as pool:
                App.pool = pool
                while True:
                    time.sleep(1)
        
        pool_thread = threading.Thread(
            target=service,
            name='plugin_pool',
            args=(),
            kwargs=kwargs,
        )
        pool_thread.daemon = True
        pool_thread.start()


def get_plugins_dict():
    entries = []
    for name in sorted(plugins.keys()):
        entries.append({
            'name': name,
            'trig_url': get_trig_url(plugin),
        })

    return {
        '*schema': 'PluginFeed',
        'count': len(entries),
        'entries': entries,
    }


def trig_plugin(method, payload=None):
    payload = payload or wrap_dict(bottle.request.json)
    print(payload.to_json())
    if payload is None:
        raise bottle.HTTPError(400)

    PluginClass = plugins.get(method)
    if PluginClass is None:
        raise bottle.HTTPError(404)

    plugin = PluginClass(**current_system().plugin_config.get(method, {}))
    name = App.pool.spawn(plugin.run, payload)

    return {
        'method': method,
        'name': name,
    }


def get_status():
    pass


def get_trig_url(name):
    return '%s/%s/trig' % (App.BASE, name)



# PLUGIN HANDLING
#################

plugins = {}


def register_plugin(module):
    plugins[module.method] = module


def get_plugin(method):
    return plugins[method]


class GenericPlugin(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key.replace(' ', '_'), value)

    def run(self, *args, **kwargs):
        raise NotImplemented
