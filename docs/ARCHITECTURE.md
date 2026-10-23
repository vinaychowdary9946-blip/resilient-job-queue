# Architecture and decisions

## Use case

Report generation and other background work can be delivered twice or abandoned when a worker crashes. This project persists jobs, assigns bounded leases, and rejects stale worker acknowledgments.

## Core design

A BEGIN IMMEDIATE transaction serializes enqueue, claim, and completion. A unique request key prevents duplicate job creation; UUID lease tokens prevent an expired worker from acknowledging a later attempt. Attempts increase on claim. The final abandoned attempt is moved to dead state on the next claim. Retry delay is uniformly sampled between zero and min(60, 2^attempts) seconds. Retry budgets stop indefinite retry amplification.

## Tradeoffs

At-least-once delivery: a handler can perform a side effect and crash before acknowledgment. External side effects must implement their own idempotency using the job key. There is no distributed broker, lease heartbeat, priority scheduling, or multi-host coordination. SQLite permits one writer at a time. Expired leases are recovered on the next claim. The included worker only prints a payload; it does not contact a reporting service.

## Runtime boundaries

The Python engine is the durable implementation. The browser simulation demonstrates the same domain concepts with synthetic data and an in-memory clock or event list; it is not a hosted distributed service. POST /api exposes Python behavior locally. The development server binds to loopback only and rejects foreign browser origins. It has no authentication, rate limiting, TLS, or service manager: do not expose it directly to the internet.

## Operational considerations

Keep databases on local disks and back up with SQLite's backup API or a controlled shutdown; do not copy an active database without its WAL state. Test restoration before relying on backups. Do not write credentials or personal data into example payloads. For a public deployment, place an authenticated application server behind TLS, implement request quotas, structured logs, monitoring and access controls, and exercise recovery under load. No production throughput or SLA is claimed.
