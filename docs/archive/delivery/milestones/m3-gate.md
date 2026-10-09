# M3 gate — Onboarding and deterministic routing

**Decision:** NOT YET PASSED.

Local implementation and synthetic acceptance checks are complete. A hosted M3 PostgreSQL result, deployed staging journeys, reviewed launch coverage and real role approvals are not evidenced. Pushing M2 does not substitute for its remaining [gate](m2-gate.md), and the owner previously deferred M1 staging setup.

| Exit requirement | Repository result | Remaining evidence |
|---|---|---|
| Decision table covers routing combinations | 864 combinations across tracks, adult eligibility, supported/unsupported language, commitment and language experience; coverage and validation boundaries tested separately | Engineering/Product review of policy version 1.0.0 |
| Beginners accepted transparently | Synthetic released coverage accepts Foundations and bridges Interview/Competitive without relabeling intent | Reviewed Foundations content and target declarations; live journeys in all nine track/language cells |
| Identical inputs and versions yield identical routes/reasons | Pure policy and stored coverage/date/version snapshots; stale review rejected; repeated confirmations reuse one goal | Hosted PostgreSQL concurrent confirmation and staging content-change rehearsal |
| Analytics reconciliation at least 99% | Synthetic committed-goal corpus reconciles at 100%; missing/duplicate/orphan events detected | Reconcile staging cohort and delivered analytics sink; no production result claimed |
| Safe learner boundary | Authentication, origin/CSRF, private goal history, explicit review, minimum effort and adult confirmation | Security/Privacy approval and managed Google login in staging |

Complete the hosted checks, resume M1 staging, review/publish real target coverage through M2, exercise onboarding and content rollback, attach opaque private approval references, then decide this gate. Reviewer names may remain private; actual reviews must happen.

Deployment requires schema revision `0003`. Disable onboarding for operational rollback; do not drop confirmed learner data or assume an older revision-specific image can serve this database.
