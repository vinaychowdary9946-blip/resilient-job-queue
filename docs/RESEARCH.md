# Engineering research

Reviewed 2026-10-23. These references inform design decisions; the project implementation is original, not copied source code.

## Primary references

- https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
- https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- https://www.sqlite.org/lang_transaction.html

## Application to this project

A BEGIN IMMEDIATE transaction serializes enqueue, claim, and completion. A unique request key prevents duplicate job creation; UUID lease tokens prevent an expired worker from acknowledging a later attempt. Attempts increase on claim. The final abandoned attempt is moved to dead state on the next claim. Retry delay is uniformly sampled between zero and min(60, 2^attempts) seconds. Retry budgets stop indefinite retry amplification.

## What this does not establish

Using an established pattern does not establish novelty, production readiness, or measured business impact. Tests validate bounded scenarios, not every operating condition. All examples are synthetic. The browser implementation and Python implementation run in different environments and are documented separately.
