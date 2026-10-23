# Related work and novelty assessment

Checked 23 October 2026. Targeted public primary-source review, not an exhaustive systematic review. Search themes included idempotent retries, payload binding, retention expiry, durable RPC results, transactional outbox and quarantine. No source code was copied into the implementation.

| Primary source | Established idea | How this study differs / does not differ |
|---|---|---|
| Malcolm Featonby, AWS Builders' Library, Making retries safe with idempotent APIs | Caller-provided operation identity, semantic equivalence and retry safety | We test controlled failure windows; identity and safe retry are not new contributions. |
| Stripe, Idempotent requests, API reference | Parameter matching; API v1 key pruning after at least 24 hours, after which reuse can execute a new request | Our TTL=10 virtual units is a fixture, not a Stripe reproduction or vendor benchmark. |
| Collin Lee et al., Implementing Linearizability at Large Scale and Low Latency, SOSP 2015, DOI 10.1145/2815400.2815416 | RIFL durably records completed RPC results and coordinates their lifecycle | We do not implement RIFL or claim comparable guarantees; we expose assumptions of a much smaller HTTP fixture. |
| Chris Richardson, Idempotent Consumer | Commit processed-message evidence with the business database update | A local-only receipt cannot atomically wrap the fixture's external HTTP mutation. |
| AWS Prescriptive Guidance, Transactional outbox | Local write/event consistency; consumers still need duplicate handling | No outbox implementation comparison or performance superiority is claimed. |
| Temporal activity documentation | Activities can execute repeatedly; called services enforce effect idempotency | This study isolates the external-effect boundary without a workflow product. |
| swarmproof/exactly-once, public source repository | Existing middleware explicitly describes quarantining ambiguous effects | Quarantine is prior art; our artifact contributes a bounded factorial measurement and independently checked witness, not the policy itself. |
| Genliang Zhu and Chu Wang, Fault-Tolerant Budget Conservation in Distributed Multi-Agent Delegation, arXiv:2610.00349 (2026 preprint) | Abstract describes durable reservations, quarantine and crash-injected experiments for agent budgets | Adjacent, more formal work. Only abstract-level scope was reviewed here; no proof or performance comparison is asserted. |

## References

1. https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
2. https://docs.stripe.com/api/idempotent_requests
3. https://doi.org/10.1145/2815400.2815416 (author manuscript: https://sigops.org/s/conferences/sosp/2015/current/2015-Monterey/126-lee-online.pdf)
4. https://microservices.io/patterns/communication-style/idempotent-consumer.html
5. https://docs.aws.amazon.com/en_en/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
6. https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/activities/activity-definition.mdx
7. https://github.com/swarmproof/exactly-once
8. https://arxiv.org/abs/2610.00349

## Publication position

Publish as an open technical report and reproducible artifact. A stronger scholarly submission would need external replication, broader destination contracts, realistic failures, formal specification or a validated new method, and an expanded literature review. No venue acceptance or first-of-kind claim is warranted by this targeted review.
