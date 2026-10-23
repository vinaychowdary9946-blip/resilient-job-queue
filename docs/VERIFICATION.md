# Verification record

## Reproduce

From the repository root:

```sh
python -m unittest discover -s tests -v
```

Domain tests exercise actual state transitions, validation, and failure cases. API tests start a loopback server on an ephemeral port and send real HTTP requests. No external customer systems are called. Randomized planner tests use a fixed seed for reproducibility.

Local validation uses Python 3.12. GitHub Actions defines a broader OS/version matrix; a configured workflow is not evidence that all hosted jobs have passed. Consult the Actions tab for current results.

## Browser scenarios

- Queue: duplicate enqueue, claim, expire lease, reject stale completion, retry, complete, reset.
- Planner: valid release plan, known slack, downstream impact, cycle rejection and recovery.
- Ledger: receipt and shipment, negative-stock rejection, duplicate command, version conflict, reset and export.

Public demos use browser memory, not the Python database. They are intended for design exploration. No load-test, uptime, penetration-test, or production performance claim is made.
