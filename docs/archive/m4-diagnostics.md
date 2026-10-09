# M4 diagnostic and evidence operations

**Scope:** Repository implementation, objective readiness diagnostics, immutable learning evidence, protected calibration/replay, and policy rollback. Live content, deployed staging proof, and accountable approvals remain separate [M4 gate](../delivery/milestones/m4-gate.md) requirements.

## Enablement and content

Deploy schema revision `0004` before the M4 application. Local Compose enables `SOCRAT_DIAGNOSTICS_ENABLED=true`; `.env.example` and staging default it to false. Disabling the flag stops learner creation, responses, and completion while preserving authenticated owned status/results and restricted operator replay. It does not delete data or disable incident correction.

Publish compatible launch-purpose packs through the M2 review pipeline. New `diagnostics` and `misconception_taxonomy` fields are optional additions to schema `1.0.0`; absent/empty declarations preserve older canonical digests. Old releases remain readable but cannot provide executable diagnostics without a new immutable pack version. Re-export contracts with `scripts/validation/export-m4-contracts.py` and run schema drift tests.

Every diagnostic declaration names its blueprint, explicit track/language coverage, response kinds/private validators, stage mappings, concept scope, evidence minimum, uncertainty margin, duration, and item budget. Objective readiness is an explicit limited scope. Implementation evidence is unavailable until M6 supplies the authenticated scoring adapter; no learner code executes in the API. A human-rubric response stays pending with zero evidence and no automatic keyword/model grading.

Use original reviewed item families with replacement inventory. Diagnostic families cannot overlap practice or baseline/weekly/final forms. Public responses contain only the current prompt and choices, never scoring keys, reference solutions, hidden tests, future items, or full pack payloads. Repository and browser fixtures are synthetic; they are not release approvals. Browser fixture seeding targets only the isolated `socrat.e2e.db` and never activates the synthetic pack head.

## Diagnostic lifecycle

`POST /api/v1/goals/{goal_id}/diagnostics` creates or resumes one session for an owned, accepted M3 goal. Saved waitlist goals do not qualify. Creation rechecks all immutable goal pins and launch-purpose releases. A maximum of ten new sessions per learner in 24 hours bounds creation; one session per confirmed goal prevents duplicate baselines. A terminal session does not silently restart or reuse exposed families. An operator must review a failed terminal session and arrange a fresh goal/approved form if another diagnostic is needed.

`GET /api/v1/diagnostics/{id}` and `/next` read the persisted current item. Selection runs in the write transaction and records stage/candidates/clock/source watermark. Responses bind to server-issued attempt IDs, session revision, and idempotency keys; changed retry payloads return `409`. Matching retries preserve the evidence effect and return current saved status; the live `server_time` may advance.

Foundations has a maximum 15-minute window; other routes have a maximum 45 minutes. Timing is measured by the server. Reload/resume does not extend the deadline. Accommodations require a reviewed blueprint/time policy; no learner-controlled extension exists. Timeouts and inventory/runner/review gaps yield limited results rather than stable/full placement. Self-report affects the first stage only. Verified evidence changes probe need and difficulty; deterministic ID ordering resolves ties.

Stable stopping requires the blueprint's independent/family coverage and placement/prerequisite thresholds to remain unchanged within its configured uncertainty margin. Full placement additionally requires implementation and diverse evidence. Results explain unknown concepts, confidence, missing evidence, and the Foundations bridge while retaining declared intent. Diagnostic completion alone is not activation; M5 must supply the first plan.

## Evidence, projections, and privacy

All learner scoring commands lock the canonical user row. Response facts, raw answer artifact, append-only evidence, mastery effect, projection, audit, and outbox commit atomically. Evidence is ordered by per-learner sequence and uniquely attributed to its logical source; deliveries cannot double-score it. PostgreSQL and SQLite triggers reject updates/deletes of finalized attempts, response facts, evidence, mastery events, and policy reviews. Session pins and finalized result snapshots are also protected.

`diagnostic_answers` contains restricted raw responses and can be erased separately under the reviewed artifact-retention/deletion procedure. Immutable response rows contain digests and scoring metadata. Raw answers are absent from learner-state/evidence endpoints, general analytics events, logs, and metrics. A digest is not an anonymization guarantee; retain it only within the protected evidence boundary. Full account export/deletion and identifier pseudonymization remain M10 work and require privacy approval before live collection.

Learner state separates mastery, confidence, retention, independent/assisted evidence, family/form diversity, misconception signals, time ratios, due dates, and version pins. Unobserved concepts have insufficient evidence even though the neutral Beta prior is .50. Passive actions, invalid content, failures, pending scores, and hint levels 4–5 have zero capability weight. Diagnostic weights are capped at .8 and cannot satisfy the unseen-assessment mastery gate. Stricter pack prerequisites, independent/family requirements, and retention days are respected.

Retention is evaluated with an explicit clock, never by erasing historical mastery nightly. Current owned learner-state reads recalculate time-sensitive state from authoritative facts. This initial implementation replays the ledger for decisions/reads; retained snapshots support comparison but do not yet optimize large histories. Measure latency before expanding beyond the scoped cohort.

## Blocked diagnostics

**Alert owner:** Content release owner with Engineering support. `SocratDiagnosticContentBlocked` opens a ticket after ten minutes with a stored `blocked_content`/`blocked_runtime` session.

Quarantine/retirement prevents new item use and scoring under the withdrawn version. An in-flight response is preserved as excluded zero-quality evidence. The learner receives a blocked/limited state; the service never repins to new content silently. An unclear-item report excludes that response and selects a fresh family where inventory permits. Credibility review and automated multi-report quarantine belong to the broader content incident workflow; an unverified report alone does not withdraw an entire pack.

Identify affected evidence via restricted source/pack queries. Review validity, publish a fixed immutable version, and use append-only corrections for invalid historical evidence. Notify materially affected learners through the accountable support process; no automated message send is implemented here.

## Pending review

**Alert owner:** Learning Design reviewer with Content operations. `SocratDiagnosticReviewBacklog` opens a ticket when more than ten stored pending sessions remain for thirty minutes.

M4 collects and preserves qualitative responses but has no live grading approval queue. Pending evidence cannot change mastery or support full placement. Finalizing a limited result records the missing evidence explicitly. Publish a reviewed objective blueprint for the appropriate scope or await M9's review integration; never invent an automated score to clear the backlog.

## Correction and exact replay

Operator endpoints require the existing authenticated admin allowlist, exact Origin, and session CSRF. Retained architecture assumptions about managed identity/MFA still require M1 staging evidence.

- `POST /api/v1/admin/learner-state/{user_id}/replay` accepts retained `policy_version` and explicit `as_of`. It validates envelopes/ownership/content/policy digests, rejects conflicting duplicates/missing sequences, and returns the candidate projection and canonical digest. It does not switch policy.
- `POST /api/v1/admin/learner-state/{user_id}/corrections` accepts a source `event_id` plus an opaque `evidence_reference`. It appends one idempotent invalidation, rebuilds state, returns directly affected diagnostic IDs, and retains original facts.
- Corrections and withdrawn content mark relevant historical result reads as requiring fresh placement review. Stored result snapshots remain unchanged; downstream consumers use current learner-state and the exposed validity annotation.

If replay fails, preserve the ledger, disable new scoring when appropriate, inspect sequence/version integrity privately, and investigate the incident. Do not publish an incomplete projection or alter facts to remove a gap.

## Policy promotion and rollback

New learners use policy `1.0.0`. Retained `1.0.1` is a conservative shadow candidate with .9 weight scaling; it is never selected automatically. Both configurations and their digests are exported in [the policy artifact](../../contracts/product/m4-learning-policies.json). Learning/Data review must justify any live promotion; the API records the supplied opaque approval reference rather than claiming it validates the human decision.

1. Dry-run replay on the candidate version with an explicit clock and inspect concept/placement/prerequisite differences against the baseline.
2. Review gold cases and cohort calibration; record the accountable private approval reference.
3. `POST /api/v1/admin/learner-state/{user_id}/policy` sends the replay version, clock, projection digest, and reference. Stale digests or an unfinalized pinned diagnostic block promotion.
4. To roll back, repeat replay/promotion for the previously retained version on the complete current history. The active/previous policy pointer and append-only review record preserve the switch. New evidence collected under the candidate remains in the ledger and is reinterpreted through the reviewed retained policy.

Application rollback requires a revision-compatible image and preserved expanded schema; M3 readiness expects `0003`, so an unmodified older M3 image is not compatible with `0004`. Prefer disabling diagnostics or a compatible M4 image/policy rollback. Never drop learner data as an operational rollback.

## Calibration and monitoring

Authorized operators see the diagnostic calibration panel in the workspace; its API is `GET /api/v1/admin/diagnostics/calibration`. It reports track/language cohorts, placement/limited/review counts, exclusions, and prediction-versus-next-clean-unseen-assessment/retention pairs at matching pack/language/concept scope. Invalidated, assisted, unfinalized, operationally failed, or wrong-language evidence cannot become a calibration outcome. The versioned query uses five bins and requires twenty pairs before reporting a Brier score; smaller cohorts display insufficient data. Development/test cohorts are labeled synthetic. Query/model/content changes require review; real efficacy needs subsequent learner outcomes.

The private Prometheus scrape adds `socrat_diagnostic_sessions{track,language,status}`. It reports persisted command status; learner reads also apply current deadline/content validity. HTTP route/status metrics continue to expose errors and replay-command failures. Labels contain no learner IDs, answers, item IDs, or payloads. Restrict metric/dashboard access using the M1 runbook and investigate per-cell limits before wider rollout.

## Verification and release

Run inherited M0–M3 checks, M4 gold/property/API/browser checks, real PostgreSQL races and immutable guards, schema drift, formatting/types/build, migration/backup/restore, and alert validation. Local Docker rehearsal is not cloud staging or a hosted CI result. The M4 [validation report](../delivery/validation/m4-validation-report.md) records the actual executed evidence.

Before enabling a live cell, attach content/placement reviews, privacy/security approval, managed-login staging journeys, restore/rollback rehearsals, and calibration-view access proof to the [gate](../delivery/milestones/m4-gate.md). Objective-only placement requires an explicit scoped Product/Learning acceptance; full implementation-dependent diagnosis remains held for M6/M7.
