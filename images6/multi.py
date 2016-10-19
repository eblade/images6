import threading
import time
import logging


class Pool(object):
    def __init__(self, workers=1, join=True, timeout=60):
        logging.info("Create pool with %i workers (%s, timeout=%i).",
                     workers, 'join' if join else 'no join', timeout)
        self.start_time = time.time()

        self.worker_count = workers
        self.join = join
        self.timeout = timeout

        self.resource = threading.BoundedSemaphore(workers)

        self.threads_lock = threading.Lock()
        self.threads = {}

        self.timing_lock = threading.Lock()
        self.counter = 0
        self.avg_time = 0

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        logging.debug("Exit pool.")
        if self.join:
            for thread in self.threads.values():
                thread.join(self.timeout)
                logging.debug("Exit joined %s. (%s)", thread.name,
                        "timed out" if thread.is_alive() else "ok")
        total_time = time.time() - self.start_time
        logging.info("Ran %i tasks in %f seconds (avg %f seconds per task).",
                self.counter, total_time, self.avg_time)

    def _control(self, thread):
        try:
            logging.debug("Start control thread for %s.", thread.name)
            start_time = time.time()
            thread.start()
            thread.join(self.timeout)
            end_time = time.time()
            logging.debug("Control thread joined %s. (%s)", thread.name,
                    "timed out" if thread.is_alive() else "ok")

            with self.timing_lock:
                self.avg_time = (self.avg_time + (end_time - start_time)) / 2

        finally:
            try:
                with self.threads_lock:
                    del self.threads[thread.name]

            finally:
                self.resource.release()
                logging.debug("Exit control thread for %s.", thread.name)

    def spawn(self, worker, *args, blocking=True, **kwargs):
        logging.debug("Start spawn.")
        if not self.resource.acquire(blocking=blocking):
            return None
        logging.debug("Acquired resource.")

        log_id = log_id_generator.next()
        worker_thread = threading.Thread(
            target=worker,
            name='worker_%s' % log_id,
            args=args,
            kwargs=kwargs,
        )
        worker_thread.daemon = True

        control_thread = threading.Thread(
            target=self._control,
            name='control_%s' % log_id,
            args=(worker_thread, ),
        )
        control_thread.daemon = True

        with self.threads_lock:
            self.threads[worker_thread.name] = control_thread

        logging.debug("Spawn starts control thread %s.", control_thread.name)
        control_thread.start()

        return worker_thread.name


class LogIdGenerator(object):
    """
    Thread-safe incrementer.

    Use like this:

        log_id = LogId()
        first_id = log_id.next()
        next_id = log_id.next()
        # ...
    """
    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()

    def next(self):
        self._lock.acquire()
        returned_id = self._count
        self._count += 1
        self._lock.release()
        return returned_id


log_id_generator = LogIdGenerator()
