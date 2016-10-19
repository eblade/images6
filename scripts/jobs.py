import requests
from images6.job import JobFeed
from images6.job import raw, jpg, imageproxy
from images6.job import State


r = requests.get('http://localhost:8888/job?page_size=10000')

jobs = JobFeed.FromDict(r.json())

for job in jobs.entries:
    if job.state == State.done:
        continue
    print("%10d  %5d  %20s %15s" % (job.id, job.options.entry_id, job.method, job.state))
