# M9 assessment and retention operations

## Rollout and rollback

Apply `alembic upgrade head` to reach schema `0009` before deploying the API. The restore smoke scripts now expect `0009`. `SOCRAT_ASSESSMENTS_ENABLED` defaults false and is false in `.env.example`; local Compose sets it true. The feature endpoint reports `assessments`. No private deployment settings or provider credentials are changed by this implementation.

Publish only independently reviewed content. Packs opting into `assessment_forms` must pass the launch inventory audit for all declared track/language cells, including every retention representation. Missing forms remain unavailable. Fixture declarations are for tests only. Use the existing editorial lifecycle and protected pack details endpoint to inspect `assessment_coverage`, then complete independent calibration and release acceptance. Never place keys, reference solutions or hidden vectors in learner responses.

Disable the assessment flag to stop learner/admin access and new broker admission. In-flight protected Submit callbacks become excluded when the switch is off. Preserve schema/evidence and restore the flag only after reviewing the incident. A failed/expired/ambiguous form is unscored and requires fresh inventory. Historical released policy implementations and pack versions remain retained. A code rollback must use an API compatible with schema 0009; do not drop assessment evidence as an incident response.

## Learner commands

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/goals/{goal_id}/assessments` | Start/resume baseline, weekly, final or retention with a durable idempotency key |
| `GET /api/v1/goals/{goal_id}/assessments` | Owned saved forms/history |
| `GET /api/v1/assessments/{id}` | Sanitized form/status/result, excluding scoring keys and solutions |
| `POST /api/v1/assessments/{id}/responses` | Text answer/problem report with item, revision and idempotency key |
| `POST /api/v1/assessments/{id}/complete` | Atomic finalization or pending review/unscored outcome |
| `POST /api/v1/assessments/{id}/items/{item_id}/dispute` | Queue a finalized score concern |
| `GET /api/v1/goals/{goal_id}/retention` | Due concepts/representations under the promoted spaced policy |

All reads are owned; writes require session, origin, CSRF and the canonical learner lock. Start reserves every issued item's family across languages and versions of the same pack key. A baseline must complete before later checks; weekly repeat checks have a seven-day cooldown. Repeating a consumed form returns a fresh-content gap rather than relabeling it unseen. An excluded or expired baseline can be replaced with another unexposed baseline form.

Code assessments create attempts through `POST /api/v1/goals/{goal_id}/code-attempts` with `assessment_item_id`. The broker validates issued item ownership, pack/digest, active deadline and runtime health; clients cannot manufacture protected scope. Existing execution flags, quotas, signed manifests, leases and hidden-output redaction apply. Sample Run never changes scores. Submit's admission timestamp controls timeliness, so queue latency does not subtract points. Healthy callbacks stage a response; failed callbacks exclude it. Unreceived/expired callbacks cannot become evidence. Complexity, reasoning and prohibited behavior need reviewed tests or separate curated qualitative items; correctness tests alone do not establish them.

## Independent review and disputes

`GET /api/v1/admin/assessments/reviews` requires an explicitly configured content administrator. It exposes restricted answers, curated criteria, staged outcomes and open disputes. `POST /api/v1/admin/assessments/items/{item_id}/review` requires current session revision, idempotency key, evidence reference, rationale and `accept`/`exclude`. The learner cannot review their own response even if they are an administrator.

Human-rubric acceptance requires exactly the authored criterion IDs with integer scores 0–4. Objective/code boundary reviews uphold deterministic scores rather than inventing a replacement. Whole-form threshold-adjacent results require review of every item. Responses remain separate from immutable human decisions. The learner finishes the form after reviews resolve; qualitative/boundary pending results do not change mastery.

For a finalized dispute, acceptance upholds the original outcome; exclusion appends an evidence invalidation and recomputes learner state. Historical result snapshots show `evidence_current` and `dispute_pending`. Regrading requires new independent evidence. The existing learner-state correction endpoint remains available for incidents spanning withdrawn content. Reviewer references must point to real independent review evidence, not generated opinions.

## Spaced policy promotion

Use the protected learner-state replay/policy endpoints to shadow `1.1.0`, independently inspect the projection digest, then promote it with an accountable evidence reference. All unfinished diagnostics/assessments pin their learning policy and block promotion. Finalize/expire old sessions first. Defaults remain `1.0.0`; an older learner policy cannot run the new spaced workflow until promotion. Existing policy rollback uses the same reviewed mechanism.

The schedule is replay-derived, not a nightly mutation. First capable evidence starts the interval. New practice does not move the due date. Scores below .6 suspend ordinary reviews until independent successful repair; a failed seven-day check removes retention confirmation. Two-day checks are useful recall evidence but cannot count as seven-day proof. Retention forms must declare their actual representation, and selection requires it to match every due concept in scope. If inventory for that representation is missing, return a content gap. Ordinary form time is capped to 25% of the goal's session minutes; a failing prerequisite is an explicit exception. The planner's existing protected weekly reservation and due-practice behavior remain; dedicated protected retention is entered through this workflow.

## Telemetry and artifacts

Atomic outbox events include assessment start, item completion, review, dispute, completion, exclusion, expiry and retention completion. Payloads contain identifiers rather than answers, code, rubric keys or review rationale. Protected metrics expose `socrat_assessment_sessions{kind,track,language,status}` alongside HTTP counts/duration. Pending-review and excluded counts can be alerted through the existing operations stack; deployed alert delivery is still an external gate.

Assessment answers are separable artifacts; raw code remains in the existing separable broker artifacts. Dispute/review rationale is restricted operational content. Privacy/export/deletion workflows belong to M10 and must account for these tables; M9 does not claim those workflows are finished. Historical review/exposure/evidence records are append-only. Use approved privacy procedures rather than ad hoc database deletion.

Regenerate contracts with `python scripts/validation/export-m4-contracts.py` and `python scripts/validation/export-m9-contracts.py`. Local validation uses `python -m pytest services/api/tests/test_assessment.py services/api/tests/test_retention_m9.py services/api/tests/test_m9_contracts.py`; PostgreSQL concurrency tests additionally require `SOCRAT_TEST_POSTGRES_URL` pointing to an isolated test server. Browser acceptance is `npm run test:e2e -- tests/e2e/assessment.spec.ts --workers=1`.
