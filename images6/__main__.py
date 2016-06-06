import os
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
from . import importer
from . import deleter
from .ingest import image


if __name__ == '__main__':
    # Options
    parser = argparse.ArgumentParser(usage="images")
    parser.add_argument(
        '-c', '--config',
        default=os.getenv('IMAGES_CONFIG', 'images.ini'),
        help='specify what config file to run on')
    parser.add_argument(
        '-g', '--debug', action="store_true",
        help='show debug messages')

    args = parser.parse_args()

    # Config
    system = System(args.config)
    logging.info("*** Done setting up Database.")

    # Web-Apps
    logging.info("*** Setting up Web-Apps...")
    app = web.App.create()
    for module in (
        entry,
        importer,
        deleter,
    ):
        logging.info(
            "Setting up %s on %s..." % (module.__name__, module.App.BASE)
        )
        app.mount(module.App.BASE, module.App.create())
    logging.info("*** Done setting up Web-apps.")

    # Serve the Web-App
    app.run(
        host=system.server_host,
        port=system.server_port,
    )
