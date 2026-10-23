# Validation record

Release v1.0, 23 October 2026.

## Local execution

- Primary experiment: 1,152 trials, 1,008 injected worker exits; all database integrity checks passed.
- Second complete run: another 1,152 trials and 1,008 exits. Semantic summaries matched exactly. Diagnostic timings differ.
- Independent verifier passed on both complete runs; the full factorial grid and 32 summary groups were checked.
- JSON summary and CSV matched. SHA-256 of both raw files is in evidence/replication-check.json.
- 16 research test methods passed, no skips; includes a 32-case subprocess crash matrix, 16 concurrent destination requests, expiry boundaries, conflict detection, malformed input, witness reproduction and deliberate evidence tampering.
- Existing parent queue suite: 19 tests passed.
- Two-history ambiguity witness reproduced equal persistent client state and different remote effect counts (0 and 1).
- Research JavaScript and shared portfolio JavaScript passed Node syntax checks. All 62 local links/references across home/research pages resolved; no duplicate HTML IDs.
- Browser: professor/hiring switch, 32 scenario/workload filter combinations, recorded trial display, dark appearance and 375 CSS-pixel mobile frames checked. Both home/research content widths fit their mobile viewports.
- Four-page report and one-page brief were rendered and visually reviewed. PDF fonts are embedded.

These are completed local checks, not independent external replication. Hosted research CI passed all six Windows/Ubuntu configurations on Python 3.10, 3.12 and 3.13. The separate parent queue workflow also passed.

## Reproduce validation

```sh
python verify.py evidence/results.json
python verify.py evidence/replication.json
python -m unittest -v test_lab
python witness.py
```

For another full run use lab.py run --seeds 12 --output evidence/new-run.json and verify.py evidence/new-run.json. Compare semantic summaries, not raw bytes or wall time.

## Boundaries

No physical power-loss, public network, live external provider, multi-host, production security, energy or throughput validation was performed. The provider remains in the controller process. The published metrics are deterministic synthetic outcomes with explicit incomplete-work accounting.

## Portability correction

The first hosted matrix exposed open SQLite connection handles during Windows temporary-file cleanup. The connection context now closes handles in a finally block, with a regression test that rejects use after context exit. Both full evidence runs were regenerated against the corrected lab source and reverified; semantic summaries remained identical.

## Hosted verification

All six research jobs passed: https://github.com/vinaychowdary9946-blip/resilient-job-queue/actions/runs/40007082064

Each job verified the released evidence, ran the 16 research tests, reproduced a two-seed factorial run, verified its output and reproduced the paired witness. The parent queue matrix also passed: https://github.com/vinaychowdary9946-blip/resilient-job-queue/actions/runs/40007082335

The code commit tested was 0e792f2511c098d380814b20e21ce3c563451139. Subsequent documentation updates do not change the measured implementation.
