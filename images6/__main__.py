import os
import sys
import logging
import argparse



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

    # Logging
    FORMAT = '%(asctime)s [%(threadName)s] %(filename)s +%(levelno)s ' + \
             '%(funcName)s %(levelname)s %(message)s'
    logging.basicConfig(
        format=FORMAT,
        level=logging.DEBUG if args.debug else logging.INFO,
    )

    # Load modules
    from .system import System

    from . import web
    from . import entry
    from . import date
    from . import importer
    from . import deleter
    from . import publish

    from . import job
    from .job import imageproxy, jpg, raw
    #from .job import flickr, raw, amend

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
            job,
        ):
            logging.info(
                "Setting up %s on %s..." % (module.__name__, module.App.BASE)
            )
            app.mount(module.App.BASE, module.App.create())
            if hasattr(module.App, 'run'):
                logging.info(
                    "Setting up %s backend..." % (module.__name__)
                )
                module.App.run(workers=system.job_workers)
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

    elif command == 'amend':
        dates = args
        for date_s in dates:
            print('Amending date %s...' % date_s)
            d = entry.get_entries(entry.EntryQuery(date=date_s))
            for e in d.entries:
                print(' - Entry %d (%s) %s/%s' % (e.id, e.state.value, e.import_folder, e.original_filename))
                if e.state is entry.State.pending:
                    print('   - Entry is Pending')
                    if e.original_filename.endswith('.DNG') or e.original_filename.endswith('.RAF'):
                        print('   - Entry is Raw')
                        jpg_filename = e.original_filename[:-4] + '.JPG'
                        print('   - Look for JPG %s/%s' % (e.import_folder, jpg_filename))
                        jpg = entry.get_entry_by_source(e.import_folder, jpg_filename)
                        if jpg is None:
                            print('   - Found no JPG Entry')
                            print('     ---> Delete Raw Entry %d' % e.id)
                            e.state = entry.State.purge
                            entry.update_entry_by_id(e.id, e)
                            continue
                        print('   - Found JPG Entry %s (%s)' % (jpg.id, jpg.state.value))
                        if jpg.get_filename(entry.Purpose.raw) is None:
                            print('     ---> Copy metadata from JPG Entry %d into Raw Entry %d' % (jpg.id, e.id))
                            e.metadata = jpg.metadata
                            e.title = jpg.title
                            e.description = jpg.description
                            e.state = jpg.state
                            entry.update_entry_by_id(e.id, e)
                            print('     ---> Purge JPG Entry %d', jpg.id)
                            jpg.state = entry.State.purge
                            entry.update_entry_by_id(jpg.id, jpg)

                        else:
                            print('   - JPG Entry already has Raw file')
                            print('     ---> Change source to %s' % e.original_filename)
                            jpg.original_filename = e.original_filename
                            entry.update_entry_by_id(jpg.id, jpg)
                            print('     ---> Purge Raw Entry %d' % e.id)
                            e.state = entry.State.purge
                            entry.update_entry_by_id(e.id, e)
                            continue


    else:

        logging.error('unknown command "%s"', command)
        sys.exit(-1)
