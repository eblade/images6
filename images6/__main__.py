import os
import sys
import logging
import argparse

# Logging
FORMAT = '%(asctime)s [%(threadName)s] %(filename)s +%(levelno)s ' + \
         '%(funcName)s %(levelname)s %(message)s'
logging.basicConfig(
    format=FORMAT,
    level=logging.DEBUG,
)

from .system import System

from . import web
from . import entry
from . import date
from . import importer
from . import deleter
from . import publish
from .ingest import image

from . import plugin
from .plugins import flickr, raw, amend


if __name__ == '__main__':
    # Options
    parser = argparse.ArgumentParser(usage='python -m images6')

    parser.add_argument(
        '-c', '--config',
        default=os.getenv('IMAGES6_CONFIG', 'images.ini'),
        help='specify what config file to run on')

    parser.add_argument(
        '-g', '--debug', action='store_true',
        help='show debug messages')

    parser.add_argument(
        'command', nargs='*', default=['serve'],
        help='command to run')

    args = parser.parse_args()

    # Config
    system = System(args.config)
    logging.info("*** Done setting up Database.")

    command, args = args.command[0], args.command[1:]
    if command == 'serve':

        # Apps
        logging.info("*** Setting up apps...")
        app = web.App.create()
        for module in (
            entry,
            date,
            importer,
            deleter,
            publish,
            plugin,
        ):
            logging.info(
                "Setting up %s on %s..." % (module.__name__, module.App.BASE)
            )
            app.mount(module.App.BASE, module.App.create())
            if hasattr(module.App, 'run'):
                logging.info(
                    "Setting up %s backend..." % (module.__name__)
                )
                module.App.run(workers=system.plugin_workers)
        logging.info("*** Done setting up apps.")

        # Serve the Web-App
        app.run(
            host=system.server_host,
            port=system.server_port,
            server=system.server_adapter,
        )

    elif command == 'select':
        from .select import select
        for line in select(args):
            print(line)

    else:

        logging.error('unknown command "%s"', command)
        sys.exit(-1)
