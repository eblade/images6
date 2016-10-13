import logging
import bottle
import threading
import time

from jsonobject import (
    PropertySet,
    Property,
    EnumProperty,
    wrap_dict,
    get_schema,
)


from .multi import Pool
from .system import current_system

from .web import (
    Create,
    FetchById,
    FetchByQuery,
    PatchById,
)


# WEB
#####


class App:
    BASE = '/job'

    @classmethod
    def create(self):
        app = bottle.Bottle()

        app.route(
            path='/',
            callback=FetchByQuery(get_jobs, QueryClass=JobQuery)
        )
        app.route(
            path='/<id:int>',
            callback=FetchById(get_job_by_id)
        )
        app.route(
            path='/<id:int>',
            method='PATCH',
            callback=PatchById(patch_job_by_id),
        )
        app.route(
            path='/',
            method='POST',
            callback=Create(create_job, Job),
        )

        return app

    @classmethod
    def run(self, **kwargs):
        def service(**kwargs):
            with Pool(**kwargs) as pool:
                App.pool = pool
                while True:
                    new_job_ids = [d['id'] for d in current_system().db['job'].view(
                        'by_state',
                        startkey=('new', None, None),
                        startkey=('new', any, any)
                    )]
                    for job_id in new_job_ids:
                        job = Job.FromDict(current_system().db['job'][job_id])
                        
                    time.sleep(1)


        
        pool_thread = threading.Thread(
            target=service,
            name='job_pool',
            args=(),
            kwargs=kwargs,
        )
        pool_thread.daemon = True
        pool_thread.start()


# DESCRIPTOR
############


class State(EnumProperty):
    new = 'new'
    acquired = 'acquired'
    active = 'active'
    ok = 'ok'
    held = 'held'
    failed = 'failed'


class Job(PropertySet):
    id = Property(int, name='_id')
    revision = Property(name='_rev')
    method = Property(required=True)
    state = Property(enum=State, default=State.new)
    release = Property()
    options = Property(wrap=True)

    self_url = Property(calculated=True)

    _patchable = ('state', )

    def calculate_urls(self):
        self.self_url = '%s/%i' % (App.BASE, self.id)


class JobStats(PropertySet):
    new = Property(int, none=0)
    acquired = Property(int, none=0)
    active = Property(int, none=0)
    ok = Property(int, none=0)
    held = Property(int, none=0)
    failed = Property(int, none=0)
    total = Property(int, none=0)


class JobFeed(PropertySet):
    count = Property(int)
    total_count = Property(int)
    offset = Property(int)
    date = Property()
    stats = Property(JobStats, calculated=True)
    entries = Property(Job, is_list=True)


class JobQuery(PropertySet):
    prev_offset = Property(int)
    offset = Property(int, default=0)
    page_size = Property(int, default=25, required=True)
    state = Property(enum=State)

    @classmethod
    def FromRequest(self):
        eq = EntryQuery()

        if bottle.request.query.prev_offset not in (None, ''):
            eq.prev_offset = bottle.request.query.prev_offset
        if bottle.request.query.offset not in (None, ''):
            eq.offset = bottle.request.query.offset
        if bottle.request.query.page_size not in (None, ''):
            eq.page_size = bottle.request.query.page_size
        if bottle.request.query.state not in (None, ''):
            eq.state = getattr(State, bottle.request.query.state)

        return eq

    def to_query_string(self):
        return urllib.parse.urlencode(
            (
                ('prev_offset', self.prev_offset or ''),
                ('offset', self.offset),
                ('page_size', self.page_size),
                ('state', str(self.date)),
            )
        )


# API
#####


def get_jobs(query):
    if query is None:
        offset = 0
        page_size = 100
        state = None

    else:
        logging.info(query.to_query_string())
        offset = query.offset
        page_size = query.page_size
        state = None if query.state is None else str(query.state)

    data = current_system().db['job'].view(
        'by_state',
        startkey=(state, None, None),
        endkey=(state, any, any),
        include_docs=True,
    )

    stats = JobStats.FromDict(current_system().db['job'].view(
        'stats',
        group=True,
    ))

    entries = []
    for i, d in enumerate(data):
        if i < offset:
            continue
        elif i > offset + page_size:
            break
        entries.append(wrap_dict(d))

    return JobFeed(
        offset=offset,
        count=len(entries),
        total_count=stats.total,
        page_size=page_size,
        stats=stats,
        entries=entries,
    )


def get_job_by_id(id):
    job = Job.FromDict(current_system().db['job'][id])
    job.calculate_urls()
    return job


def create_job(job):
    if job.method is None:
        raise bottle.HTTPError(400, 'Missing parameter "method".')
    job.state = State.new
    job._id = None
    jon._rev = None
    job = Job.FromDict(current_system().db['job'].save(job.to_dict()))
    logging.debug('Created job\n%s', job.to_json())
    return job


def patch_job_by_id(id, patch):
    logging.debug('Patch job %d: \n%s', id, json.dumps(patch, indent=2))
    job = get_job_by_id(id)
    for key, value in patch.items():
        if key in Job._patchable:
            setattr(job, key, value)

    job = Job.FromEntry(current_system().db['entry'].save(entry.to_dict()))
    return job




# PLUGIN HANDLING
#################

plugins = {}


def register_job_handler(module):
    plugins[module.method] = module


def get_plugin(method):
    return plugins[method]


class GenericJob(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key.replace(' ', '_'), value)

    def run(self, *args, **kwargs):
        raise NotImplemented

