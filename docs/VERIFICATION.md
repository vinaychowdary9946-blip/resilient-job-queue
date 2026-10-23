# Verification record

## Reproduce

From the repository root:

```sh
python -m unittest discover -s tests -v
```

Domain tests exercise actual state transitions, validation, and failure cases. API tests start a loopback server on an ephemeral port and send real HTTP requests. No external customer systems are called. Randomized planner tests use a fixed seed for reproducibility.

## Verified results — 2026-10-23

- Local Python 3.12: **10 tests passed** in this repository.
- Hosted CI: **all six matrix jobs passed**, covering Python 3.10, 3.12 and 3.13 on Ubuntu and Windows.
- [Verified CI run](https://github.com/vinaychowdary9946-blip/resilient-job-queue/actions/runs/39996431889). This records the implementation commit; consult Actions for subsequent runs.
- Deployed browser checks passed for the applicable core scenarios below. Desktop layout was visually inspected; responsive CSS is included, but physical mobile-device testing was not performed.

## Browser scenarios

- Queue: duplicate enqueue, claim, expire lease, reject stale completion, retry, complete, reset.
- Planner: valid release plan, known slack, downstream impact, cycle rejection and recovery.
- Ledger: receipt and shipment, negative-stock rejection, duplicate command, version conflict, reset and export.

Public demos use browser memory, not the Python database. They are intended for design exploration. No load-test, uptime, penetration-test, or production performance claim is made.
