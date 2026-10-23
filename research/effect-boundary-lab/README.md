# Effect Boundary Lab

**When is a retry still safe after the destination forgets?**

An independent empirical systems study by Vinay Muppalla. This artifact crosses the local-database boundary of the earlier Worker Crash Lab: real worker processes call a loopback HTTP destination with its own SQLite database and expiring duplicate-protection records.

[Professor and hiring-team views](https://vinaychowdary9946-blip.github.io/research/) · [Technical report](paper.md) · [Research brief](brief.md) · [Study protocol](PROTOCOL.md) · [Raw evidence](evidence/results.json) · [Related work](RELATED_WORK.md) · [Discussion guide](DISCUSSION_GUIDE.md)

## Recorded results

1,152 trials = 4 policies x 8 scenarios x 3 synthetic payload variants x 12 input seeds. The factorial run injected 1,008 worker process exits. These are repeated deterministic fault schedules, not estimates of real-world incident frequency. All databases passed integrity checks. The independent verifier recomputes every effect-derived metric and all 32 summary groups.

| Policy | Trials | Excess effects | Missing effects | False confirmations | Quarantined |
|---|---:|---:|---:|---:|---:|
| Naive replay | 288 | 216 | 0 | 0 | 0 |
| Local receipt | 288 | 108 | 0 | 36 | 0 |
| Destination key | 288 | 36 | 0 | 0 | 0 |
| Guarded retry | 288 | 0 | 36 | 0 | 72 |

Missing guarded effects are explicitly quarantined, not reported as completed. The guard trades automatic completion for safety. No policy dominates every metric. Payment, stock and notification payloads use the same append-effect implementation; they are not three production integrations.

## Reproduce

Python 3.10+; standard library only; Windows and Linux compatible source. Run from this directory:

```sh
python lab.py run --seeds 12 --output evidence/results.json
python verify.py evidence/results.json
python witness.py
python -m unittest -v test_lab
```

The experiment uses temporary databases, loopback HTTP and real child-process termination with exit code 73. A different child exit fails the run. The virtual clock controls retention; it is not elapsed network time. Expect a few minutes for the full run. A two-seed smoke run uses `--seeds 2 --output evidence/smoke.json`.

`witness.py` produces two histories with identical durable client intent records and different remote outcomes (zero versus one effect). Both pause after the retention horizon. This is an executable ambiguity counterexample, not a new impossibility theorem.

## Files

- `lab.py`: provider, worker, four policies, subprocess harness, aggregation
- `verify.py`: independent evidence and source-fingerprint checks
- `witness.py`: paired durable-state ambiguity example
- `test_lab.py`: contracts, concurrency, HTTP validation, 32-case crash matrix, tamper detection
- `evidence/results.json`, `.csv`: per-trial records and summary
- `paper.md`, `paper.pdf`: public technical report, not peer reviewed
- `brief.md`, `research-brief.pdf`: concise discussion brief
- `PROTOCOL.md`, `RELATED_WORK.md`, `VALIDATION.md`: design, prior work and verification

## Contribution and status

The contribution is this integrated, inspectable benchmark and paired ambiguity witness. Idempotency keys, payload binding, durable receipts and quarantine are existing ideas. No first-in-world algorithm, distributed exactly-once guarantee, accepted publication, production deployment or universal profile fit is claimed. The report is suitable for public technical release and research discussions; scholarly acceptance needs external assessment.

The HTTP provider is a local experimental fixture, not a secure production API. It trusts a virtual clock, has no authentication, and has no independent process restart or power-loss tests. There is no multi-worker client coordination, external provider integration, automatic reconciliation, throughput result or energy measurement. See the protocol for further limits.

Code and accompanying materials are covered by the repository MIT license.
