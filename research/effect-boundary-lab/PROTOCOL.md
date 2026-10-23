# Study protocol v1

Recorded with the released artifact; this is not a preregistration. Date: 23 October 2026.

## Questions

RQ1: Which crash windows remain unsafe when a local receipt cannot commit atomically with an external effect?
RQ2: What happens to stable-key retries after the provider removes its receipt?
RQ3: What automatic-completion cost accompanies conservative retention-aware quarantine?
RQ4: Can two different remote outcomes leave equal durable client state?

## System and assumptions

The controller hosts a threaded loopback HTTP service. Destination and worker persist in separate SQLite WAL databases with synchronous=FULL. Each worker is a fresh Python subprocess. The provider commits an append-effect record and its optional deduplication receipt in one transaction. Keys bind to canonical JSON SHA-256; a changed payload returns 409 while the receipt exists. The provider removes receipts at virtual age >=10, but preserves effect records for the audit oracle. The worker has no access to that oracle.

All policies persist an intent before dispatch; only local_receipt and guarded use saved local results to suppress later dispatch. All keyed calls use one stable logical identity within each isolated trial. Guarded additionally rejects local payload changes and refuses unresolved redispatch at age >=10. There is one logical operation per trial, one initial invocation and one retry. A clean trial still includes a duplicate invocation; it is a no-crash replay control, not a single-call latency baseline.

## Factorial design

Four policies; eight scenarios; three payload labels; twelve seeds. Seeds change an integer value and are paired across policy/scenario/workload. The labels payment, stock and notification share one append-effect implementation. Fixed execution order and loopback execution preclude throughput or domain-general performance conclusions.

| Scenario | Initial worker exit point | Retry time / payload |
|---|---|---|
| clean | no crash, duplicate invocation | time 1, unchanged |
| before_send | after durable intent, before HTTP | time 1 |
| after_effect | after HTTP success, before local result | time 1 |
| before_receipt_commit | after local UPDATE, before COMMIT | time 1 |
| after_receipt | after local COMMIT | time 1 |
| expired_after_effect | after HTTP success, before local result | time 20, receipt expires |
| expiry_before_send | after durable intent, before HTTP | time 20, no original effect |
| changed_retry | after local COMMIT | time 1, value increases by one under same identity |

## Outcome definitions

Excess effects = max(effect_count - 1, 0) per original logical intent. A changed-payload effect under a reused identity counts as an excess effect and also as wrong payload; these metrics overlap and must not be added as disjoint incident totals. Missing = no original or other effect exists after recovery. False confirmation = recovery reports a specific effect as confirmed but its payload hash does not equal the retry payload. Thus an unsafe new effect can be wrong payload without being a false confirmation. Quarantine and conflict are explicit worker outcomes, not confirmed success.

Read the raw effects, payloads and recovery records rather than relying only on totals. The independent verifier recalculates effect counts, hashes, wrong payload, missing and false confirmation, validates complete factorial coverage and compares aggregates. Request counts are fixture observations; no latency/energy benefit is claimed from them. Wall seconds include process startup and filesystem noise and are diagnostic only.

## Repeated runs and reporting

Domain outcomes are deterministic for these scripted schedules. Seeds vary values, not failure probability. No p-values or confidence intervals are presented as evidence of production reliability. A second full run should produce identical semantic summaries; wall seconds and environment metadata may differ. Source fingerprints identify the exact lab implementation. Assertions must remain enabled; use the documented commands without Python -O.

## Threats to validity

Provider is a thread in the surviving controller process, not a separate remote host or separate provider process. Worker exits are real; loss before receiving the HTTP response is not injected. Retention is virtual and immediate on the next request, not a model of a named vendor's exact cleanup schedule. Unresolved guarded state assumes a durable monotonic time basis and a known provider retention contract; wall-clock skew, lost local storage and provider policy changes are not handled.

Client concurrency, multi-host partitions, disk/power failures, server failures, transaction isolation alternatives, queue scheduling and network reordering are not evaluated. Destination concurrency is checked separately with 16 keyed HTTP requests, not by the factorial worker experiment. Production integration must use authentication, transport security, durable identities, trustworthy time, reconciliation and operational ownership. This artifact cannot execute payments or send messages to real users.

## Responsible interpretation

This is an original implementation and bounded technical study of established concepts. Its distinctive evidence package is the tested factorial matrix plus equal-state/different-outcome witness. Novelty beyond that artifact has not been established by an exhaustive systematic review. Replication and independent review are needed before any journal/conference submission claims.
