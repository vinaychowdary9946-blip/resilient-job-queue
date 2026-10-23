# Resilient Job Queue

Report generation and other background work can be delivered twice or abandoned when a worker crashes. This project persists jobs, assigns bounded leases, and rejects stale worker acknowledgments.

Independent engineering project built around realistic failure scenarios. Examples use synthetic data; no customer deployment or commercial impact is claimed.

**[Live interactive demo](https://vinaychowdary9946-blip.github.io/demos/resilient-job-queue/)** · [Architecture](docs/ARCHITECTURE.md) · [API guide](docs/API.md) · [Verification](docs/VERIFICATION.md)

## What it does

Idempotent enqueue with payload conflict detection; atomic claims; lease recovery; capped exponential retry with full jitter; dead-letter state; durable SQLite storage.

## Run locally

Requires Python 3.10+; no pip installation, paid service, or API key is required. From this repository directory:

```sh
python queue_engine.py enqueue --key report-001
python queue_engine.py work
python queue_engine.py list
python -m unittest discover -s tests -v
python server.py
```

Open http://127.0.0.1:8000 for the browser simulation. The local server also exposes POST /api for the actual Python engine; see [API examples](docs/API.md). The visual simulation is deliberately separate from the backend and keeps its data in browser memory. Reloading clears it. SQLite files persist local API and CLI data across restarts.

## Repository map

- `queue_engine.py` — domain implementation and CLI
- `server.py` — loopback development server and JSON API
- `web/` — interactive browser simulation, no dependencies
- `tests/` — domain, concurrency, and HTTP tests
- `examples/` — reproducible inputs
- `docs/` — architecture, API contracts, research, validation, and operations

## Engineering boundaries

At-least-once delivery: a handler can perform a side effect and crash before acknowledgment. External side effects must implement their own idempotency using the job key. There is no distributed broker, lease heartbeat, priority scheduling, or multi-host coordination. SQLite permits one writer at a time. Expired leases are recovered on the next claim. The included worker only prints a payload; it does not contact a reporting service.

## Development

Run tests from the repository root. GitHub Actions is configured for Python 3.10, 3.12, and 3.13 on Linux and Windows. Local validation and hosted CI results are reported separately in the verification guide.

MIT license. Contributions should include a reproducible failing scenario and a regression test.
