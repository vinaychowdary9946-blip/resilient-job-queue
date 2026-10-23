# Research and interview discussion guide

## A clear introduction

Effect Boundary Lab asks when a background worker can safely retry an external action after a crash. The destination may have completed the action even when the worker has no saved result. The study compares four recovery policies and shows why avoiding duplicates can also leave work unfinished.

## Questions and answers

**What is the practical problem?** A data connector or worker can send a request successfully and crash before saving confirmation. Restarting the worker does not undo what the second system already did.

**Why is a queue's duplicate protection insufficient?** Avoiding duplicate jobs and avoiding duplicate external effects are different boundaries. The destination must enforce the operation's identity, or the application needs authoritative reconciliation.

**What do the four policies do?** Naive replay resends. A local receipt reuses a saved local result. A destination key asks the second service to recognise the same operation. Guarded retry also checks the payload and stops unresolved work once the known protection horizon is reached.

**What is the strongest comparison?** Guarded retry versus a destination that already atomically enforces stable keys and payload matching. The keyed baseline performs well within its retention contract. The experiment does not claim that a simple guard outperforms established workflow products.

**What was the important result?** In 36 delayed-retry trials per policy, the destination-key baseline created a second effect after its receipt was removed. The guard avoided those excess effects by quarantining. Across all guarded trials it quarantined 72 operations; 36 had no effect. That is a safety/completion trade-off.

**Why are there many trials if the outcome is deterministic?** The factorial design checks all declared combinations and varies input values. These repetitions are validation, not a sample of real incident probabilities or proof of a reliability percentage.

**What is the paired witness?** Two terminated workers leave equal local intent rows. One died before dispatch; the other after external success. Their remote outcomes differ. A worker looking only at those local records cannot distinguish them.

**What is new?** This artifact's integrated failure matrix, inspectable evidence, independent metric checker and paired demonstration. The study does not establish a new primitive, theorem or first-of-kind policy. The related-work table documents existing concepts.

**Why is this useful for PhD discussions?** It presents a precise question, controlled variables, baselines, outcome definitions, evidence, limitations and a testable next research step. It does not replace formal admission requirements or prior research preparation.

**Why is this useful for jobs?** It demonstrates implementation and debugging across transactions, HTTP, processes and OS differences. The Windows handle-cleanup defect and regression test are a concrete portability lesson. Employer relevance is strongest for backend, data-platform, testing and workflow roles.

**What would make the next version stronger?** Add an authenticated destination lookup that can reconcile an uncertain intent. Test what evidence is sufficient to resolve it and when stale or unavailable evidence must still cause quarantine. Then evaluate real network failures and concurrent clients.

**What should not be claimed?** Production deployment, real payments, real sent notifications, measured energy savings, general network-failure coverage, a universal exactly-once guarantee, accepted publication or first-in-world novelty.

## Live walkthrough

1. Open the evidence explorer with the expired-after-effect schedule. Compare duplicates and quarantines.
2. Select expiry-before-send. Explain why the guarded policy leaves the requested effect missing.
3. Select changed retry. Explain the difference between a wrong-payload effect and false confirmation.
4. Open the paired witness, protocol and raw JSON.
5. Reproduce the artifact and run the independent verifier before presenting it.

## Questions to ask a prospective supervisor

- Is reliable external-action recovery a fit for the group's current research?
- Would authenticated reconciliation or a formal model produce a stronger research contribution?
- What research preparation and evidence are required for PhD or MPhil entry?
- Which realistic workloads, collaborators and independent replication resources are available?
- Is funding attached to a specific project or separately competitive?
