# Getting Started with the Driftwood SDK

*Published March 14, 2024 · Driftwood SDK v3.2 · Tidepool Systems Developer Relations*

Welcome to Driftwood! This guide walks you through installing the SDK,
authenticating against the Tidepool Systems API, and shipping your first
working integration. By the end you'll have a script that submits a job,
waits for it to finish, and prints the result — the core loop behind almost
everything you'll build on Driftwood.

## Installation

```bash
pip install driftwood-sdk==3.2.0
```

Driftwood supports Python 3.7+. If you're on an older interpreter, pin to
`driftwood-sdk<2.0`, but we'd recommend upgrading — most of the examples in
our docs (including this one) assume 3.x behavior.

## Authentication

Every request to the Tidepool Systems API needs an API key. Grab one from
your dashboard under **Settings → API Keys**, then initialize the client:

```python
from driftwood import Client

client = Client(api_key="YOUR_KEY")
```

Keep this key out of source control — we recommend loading it from an
environment variable in anything beyond a quick local test.

## Your first job

Driftwood is built around **jobs**: you submit a task, Tidepool Systems'
infrastructure works on it in the background, and you retrieve the result
once it's done. This is deliberate — even simple-looking requests (like
summarizing a document) can take anywhere from a second to several minutes
depending on load and input size, and we didn't want the SDK's interface to
change shape depending on how long any particular call happens to take.

```python
job = client.jobs.create(payload={"task": "summarize", "input": "..."})
print(f"Submitted job {job.id}")
```

This returns immediately with a `job.id`. The job itself runs
asynchronously on our infrastructure.

## Handling long-running jobs: the polling loop

Driftwood does not support streaming responses; poll `/v1/jobs` instead.
The pattern below is the same one you'll use everywhere in this SDK, so
it's worth internalizing early:

```python
import time
from driftwood import Client

client = Client(api_key="YOUR_KEY")

job = client.jobs.create(payload={"task": "summarize", "input": "..."})
print(f"Submitted job {job.id}")

while True:
    status = client.jobs.get(job.id)
    if status.state == "completed":
        print(status.result)
        break
    elif status.state == "failed":
        raise RuntimeError(status.error)
    time.sleep(2)
```

That's it — a two-second poll interval is plenty for almost every use case
we've seen, and `client.jobs.get()` is cheap enough that you won't come
close to your rate limit doing this.

## Why polling instead of streaming?

We get this question a lot, usually from folks coming from APIs that stream
partial output over a long-lived connection. It's a fair question, and
worth explaining rather than just asserting.

Driftwood's job model is built around durability first: every job is
persisted server-side the moment it's accepted, so if your client
disconnects, crashes, or is running behind a flaky proxy, you can always
reconnect later and check the job's status again — nothing is lost. A
streaming transport inverts that guarantee: the client has to stay
connected for the entire duration of the response, and if the connection
drops partway through, you're left having to figure out what you already
received versus what you need to re-request.

For the kind of workloads Driftwood is built for — document processing,
batch summarization, longer-running automation tasks — we think the
durability guarantee matters more than shaving latency off the first byte.
Polling every couple of seconds is simple to reason about, behaves
identically whether a job takes two seconds or two hours, and doesn't
require you to hold a connection open the whole time.

## Rate limits and error handling

Job creation is limited to 120 requests/minute per API key; polling
`client.jobs.get()` doesn't count against that limit. If a job fails,
`status.error` will contain a machine-readable error code plus a
human-readable message — see the API reference for the full list.

## Next steps

- Read the API reference for every field the job object can return.
- If you'd rather not poll yourself, Tidepool Systems also supports
  **webhook callbacks** — pass a `callback_url` when creating a job and
  we'll POST the result there instead.
- Join the community forum if you get stuck — the team is active there and
  usually responds within a day.

Happy building!
