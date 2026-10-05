# M4 gate — Diagnostic and learner-state core

**Decision:** NOT YET PASSED.

**Current evidence:** Repository implementation for objective readiness diagnostics, deterministic learner state, replay/correction/policy operations, protected calibration view, and automated local/browser/PostgreSQL rehearsals. See the [index](m4-index.md), [validation report](../validation/m4-validation-report.md), and [operations guide](../../operations/m4-diagnostics.md). No reviewed launch inventory, hosted CI result, cloud staging journey/dashboard, empirical learner calibration, or human approval is claimed.

| Exit requirement | Required repository evidence | Required external evidence |
|---|---|---|
| Executable, consistent contracts | Versioned diagnostic/evidence/model schemas; scoring-policy conflicts reconciled; old pack digests preserved | Product/Learning/Engineering review of scoring, uncertainty, timing, priors, mastery and provisional gates; ADR decision recorded |
| Placement reviewed across tracks/languages | Gold fixtures and deterministic journeys for Foundations/Interview/Competitive × Python/C++/Java, including beginner bridges and unavailable inventory | Learning review of expected placements; reviewed launch-purpose content and explicit per-cell coverage |
| Honest staged diagnosis | Reproducible selection, server-backed resume, minimum coverage and early-stop fixtures, timeout/limited/pending states | Staging journeys with published blueprints, accessible timing/copy review; runtime-dependent full coverage held until M6 |
| Idempotency and exact replay | Real PostgreSQL races; source/concept uniqueness; canonical sequence replay; duplicate/reorder/gap properties; transaction-failure injection | Hosted CI results and staging incident/correction rehearsal |
| Evidence-safe learner state | Passive/self-report/failure invariance; assistance/diversity gates; prerequisite rules; bounded Beta updates; clock-controlled retention and misconceptions | Learning/Data review of estimates and uncertainty; no synthetic claim of empirical calibration |
| Safe API and protected content | Ownership, CSRF/Origin, strict validation, limits, immutable facts, flag behavior, and answer-key/hidden-test secrecy checks | Security/Privacy review of live collection, retention/deletion design and operational access |
| Calibration dashboard live | Versioned segmented queries, outcome-pairing fixtures, exclusions and empty/insufficient-data states; protected view | Staging dashboard accessible to authorized operators, correct cohort labeling, alert ownership; later learner outcomes required for empirical calibration |
| Prior-policy rollback works | Shadow replay/comparison, immutable policy revisions, active pointer switch/rollback, compatibility failure tests | Demonstrated staging rollback using current evidence without deleting history; opaque approval reference for policy promotion |
| Additive migration and restore | Expected revision `0004`, inherited-data rehearsal, updated revision/restore checks, existing quality gates | Isolated staging restore and compatible application rollback proof |
| Prior gates accounted for | M0–M3 pending items tracked without rewriting history | Relevant staging/auth/content prerequisites completed or explicitly deferred by the accountable owner for the scoped release |

The gate review must state whether the accepted scope is objective diagnostic placement or full diagnostic placement including implementation evidence. Objective-only acceptance requires an explicit Product/Learning scope decision and visible limited coverage; it does not satisfy coding-dependent launch claims.

Complete implementation, attach an M4 validation report containing actual local and hosted results, exercise the M4 operational runbook on staging, and record real reviewer decisions through opaque private references. Reviewer identities and learner responses remain outside the repository.

Operational rollback disables new diagnostic/scoring writes or restores the retained compatible policy/projection. Preserve source evidence and owned result reads. Do not drop the expanded schema or edit historical evidence to simulate rollback.
