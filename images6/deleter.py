#!/usr/bin/env python3

import os
import logging
import bottle

from threading import Thread, Event, Lock
from datetime import datetime, timedelta

from .system import current_system
from .web import ResourceBusy
from .entry import get_entry_by_id, update_entry_by_id, delete_entry_by_id
from .job import Job, create_job
from .job.delete import DeleteJobHandler


# WEB
#####


class App:
    BASE = '/purger'

    @classmethod
    def create(self):
        app = bottle.Bottle()

        app.route(
            path='/trig',
            method='POST',
            callback=trig_purge,
        )

        app.route(
            path='/status',
            callback=get_status,
        )

        return app



def trig_purge():
    if PurgeJob.lock.acquire(blocking=False):
        PurgeJob()
        return {'result': 'ok'}
    else:
        raise ResourceBusy


def get_status():
    if PurgeJob.to_delete == 0:
        progress = 100 
    else:
        progress = int((PurgeJob.deleted + PurgeJob.failed) / PurgeJob.to_delete * 100)
    return {
        '*schema': 'PurgeStatus',
        'status': PurgeJob.status,
        'to_delete': PurgeJob.to_delete,
        'deleted': PurgeJob.deleted,
        'failed': PurgeJob.failed,
        'progress': progress,

    }


def get_trig_url():
    return '%s/trig' % (App.BASE, )


# PURGE MANAGER
###############


class PurgeJob:
    lock = Lock()
    status = 'idle'
    to_delete = 0
    deleted = 0
    failed = 0

    def __init__(self):
        logging.info("Setting up purge thread [Purger]")
        PurgeJob.status = 'acquired'

        thread = Thread(
            target=purge_job,
            name="Purger",
            args=()
        )
        thread.daemon = True
        thread.start()


def purge_job():
    logging.info("Started purge thread.")
    try:
        PurgeJob.status = 'reading'
        system = current_system()
        ids_to_purge = [v['id'] for v in system.db['entry'].view('by_state', key='purge')]
        PurgeJob.to_delete = len(ids_to_purge)
        PurgeJob.status = 'deleting'

        for id in ids_to_purge:
            entry = get_entry_by_id(id)
            logging.info("Deleting entry %i." % (entry.id))

            while len(entry.variants) > 0:
                variant = entry.variants.pop()
                logging.info("Creating delete job for %s.", variant)
                delete_job = Job(
                    method=DeleteJobHandler.method,
                    options=DeleteJobHandler.Options(
                        entry_id=entry.id,
                        variant=variant,
                    )
                )
                delete_job = create_job(delete_job)
                logging.info("Created delete job %d.", delete_job.id)
                entry = update_entry_by_id(id, entry)

            delete_entry_by_id(id)
            PurgeJob.deleted += 1
            logging.info("Deleted entry %i.", entry.id)

        PurgeJob.status = 'done'

    except Exception as e:
        logging.error('Purge thread failed: %s', str(e))
        PurgeJob.status = 'error'
        raise e

    finally:
        PurgeJob.lock.release()
        logging.debug("Purge thread closing.")
