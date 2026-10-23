# Worker Crash Lab — recruiter walkthrough

## The engineering question

A worker commits a business result, then dies before acknowledging its queue job. A retry can repeat the result even though the queue itself prevents duplicate job creation. Can a local business operation survive this ambiguity without duplicate records?

## What was built

A durable SQLite queue, a transactional report-and-receipt handler, and a subprocess failure harness. The protected handler stores the report and a receipt keyed by job ID in the same transaction. After a crash and lease recovery, it returns the receipt instead of inserting another report. The queue acknowledgment remains a separate step, so delivery is still at-least-once.

The control condition uses the same queue, report table, inputs, lease timing and crash points, but omits the receipt. This isolates the local idempotent handler's effect. The control is intentionally unprotected, not a comparison against a commercial broker.

## Reproduce

Requires Python 3.10+ and no external packages. From this repository root:

```sh
python -m unittest discover -s tests -v
python crash_lab.py --jobs 50 --output evidence/crash-results.json
```

The experiment creates temporary databases. Every initial child worker exits using `os._exit(73)`. A non-73 exit fails the run, rather than being counted as an injected failure. Recovery uses a virtual clock to expire leases without sleeps; process exits and SQLite writes are real.

| Failure point | Unprotected reports | Protected reports | Completed jobs per handler |
|---|---:|---:|---:|
| Before report write | 50 | 50 | 50 |
| Before transaction commit | 50 | 50 | 50 |
| After report commit, before acknowledgment | 100 | 50 | 50 |
| After acknowledgment | 50 | 50 | 50 |

**Recorded result:** 400 process exits across 8 scenarios. All 400 job executions recovered to completed state, no reports were missing, and every database passed `PRAGMA integrity_check`. The protected scenarios recorded zero duplicate report rows. The unprotected commit-before-ack scenario recorded 50 duplicate rows.

These are 400 independent scenario jobs, not 400 unique customer reports. Counts are deterministic for this experiment and are not throughput measurements. The JSON records platform, Python version, source hashes, and every job's attempt count and effect count.

## Verify the evidence

- `evidence/crash-results.json`: raw recorded run.
- `queue_engine.py`: `apply_local_report` implements the report/receipt transaction.
- `crash_lab.py`: control handler, failure injection, recovery and integrity audit.
- `tests/test_crash_lab.py`: real-process experiment as a regression test.
- `web/crash.js`: browser reconstruction and table loaded from recorded evidence.

To verify source linkage, compare SHA-256 of `queue_engine.py` and `crash_lab.py` with `source_sha256` in the JSON. On Windows use `Get-FileHash`; on Unix use `sha256sum`. Rerunning may change environment metadata; compare domain outcomes, not byte-for-byte report equality.

## Limits and the next engineering decision

The atomicity boundary is one local SQLite database. This does not make an external email, HTTP request, payment or file write atomic with a database transaction. External services require an idempotency key accepted by the destination or an appropriate reconciliation protocol. The experiment does not simulate disk failure, power loss, network partitions, malicious database modification, or sustained concurrent traffic. It is a bounded process-crash experiment, not proof against all failures.

## Interview explanation

“I built a crash-recovery lab around a durable background queue. I deliberately terminated workers between writing a report and acknowledging a job, reproduced duplicate results in a control handler, then prevented duplicates within one SQLite database using transactional receipts. I published raw evidence and a reproduction command, and tested the recovery on Windows and Linux.”

The distinctive contribution is the integrated failure demonstration and auditable evidence. Idempotent consumers and database transactions are established patterns; no worldwide novelty or research originality is claimed.

## Primary design references

- AWS: https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
- SQLite: https://www.sqlite.org/atomiccommit.html
- SQLite WAL constraints: https://www.sqlite.org/wal.html
