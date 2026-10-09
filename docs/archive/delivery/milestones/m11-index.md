# M11 — Internal alpha and operational hardening

Scope for this work: automated local testing, requested on 7 October 2026. Human testing is deferred by the owner. This does not approve beta admission or mark the entire milestone complete.

## Automated coverage

- 200 independently migrated synthetic learner journeys, balanced across Foundations, Interview and Competitive in Python, C++ and Java (22 or 23 journeys per cell). Each journey covers login/onboarding, diagnostic, reviewed plan, session pause/resume, retries, signed sample and submit callbacks, completion, read-only progress, export, session revocation, worker erasure and protected deletion receipts.
- Existing desktop/mobile browser regression, including assessment, code editing, tutoring, timed sessions, progress and privacy controls.
- Real PostgreSQL migration, locking, concurrent review/submission/consent, immutable records and erasure checks.
- A local PostgreSQL read contention baseline: 200 authenticated progress requests with eight concurrent readers; check successful responses and unchanged learning evidence. Timing is diagnostic, not a hosted SLO pass.
- Injected worker transaction failure and exactly-once retry; SQLite backup restoration verifies saved session and evidence survive.
- Existing queue failure, forged runner callback, sandbox startup failure, tutor timeout/fallback, content quarantine/replay, assessment protections, erasure replay after restore and release rollback checks remain part of the regression suite.

The execution results in API journeys are signed synthetic callbacks. No Python/C++/Java learner code is executed by those journey tests. Fresh databases and generated IDs exercise repeated lifecycle transactions, not 200 distinct curriculum designs or real learner outcomes. Human and hosted acceptance remain separate.

See the [gate](m11-gate.md) and [automated validation report](../validation/m11-validation-report.md).
