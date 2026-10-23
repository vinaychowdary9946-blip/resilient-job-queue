# Local API guide

Start `python server.py`, then send JSON to `http://127.0.0.1:8000/api`. The API is a development interface on loopback, not an internet-facing service.

Example (Python, Windows/Linux/macOS):

```python
import json
from urllib.request import Request, urlopen
payload = {'action': 'enqueue', 'key': 'report-001', 'payload': {'report': 'daily-sales'}}
request = Request("http://127.0.0.1:8000/api", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
with urlopen(request) as response:
    print(json.load(response))
```

Success: HTTP 200 with a JSON result. Invalid domain commands: HTTP 400 with `{"error":"..."}`. Unknown routes: 404. Foreign browser origins: 403. Request bodies are limited to 100,000 bytes. SQL uses bound parameters. No arbitrary Python, shell command, or user-supplied handler execution is supported.

## Actions
- `enqueue`: `key`, JSON `payload`, optional `max_attempts` (1–20).
- `claim`: optional `lease` (seconds, >0 and <=3600). Returns one leased job or null. Save its `id` and `token`.
- `finish`: `id`, `token`, optional `error`. Omit error for success; include an error message for failure.
- `list`: returns all jobs.
- `report`: `id`, `token`; commits a local report and deduplication receipt while the lease is valid.
- `reports`: returns committed local report rows.

Do not acknowledge a job after its lease expires. Claim returns raw payload as a JSON-encoded string. Consumers decode it before processing. External effects must be idempotent.
