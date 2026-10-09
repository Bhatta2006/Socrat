# M3 onboarding operations

## Enable and verify

Run migrations to `head` (revision `0003`) before starting the current API. Local Compose and browser acceptance configuration enable `SOCRAT_ONBOARDING_ENABLED=true`. Standalone and deployed settings default to false; the staging Compose setting may be explicitly enabled after its prerequisite checks. Disable the flag to hide the flow and return 404 on onboarding routes. Learning sessions, execution and AI remain disabled.

Authenticate, save an adult-confirmed profile, select a goal, review the normalized statement/route, and confirm. For unsupported coverage, confirmation saves a waitlist request without an active track or diagnostic. Ineligible requests cannot be confirmed. Unknown or malformed required fields return `input_confirmation_required`; correct the input before review.

## Released coverage

Only active, released `purpose: launch` packs in domain `data_structures_and_algorithms` qualify. Synthetic fixtures never qualify. Each relevant pack goal (`foundations`, `interview`, `competitive`) must declare `released_targets` with exact `outcome`, optional `value`, `role_level`, and `platform_or_format`. For example, an Interview target can declare:

```json
{"outcome":"screen_readiness","value":null,"role_level":"new_grad","platform_or_format":null}
```

Competitive targets must match both the requested platform and exact target value. Foundations/Interview outcomes must also match explicitly. All concepts in the selected track require exercise coverage, and every relevant code exercise requires the chosen language variant. A beginner bridge requires a released Foundations track with explicit targets. Reviewed target declarations describe the intended coverage; they do not replace content, assessment or runtime review.

Add declarations by creating and reviewing a new immutable pack version. Existing releases with absent/empty declarations retain their original digest and remain readable, but provide no M3 goal coverage. Never change historical payloads or turn committed fixtures into actual launch content.

## Review, retry and replay

`POST /api/v1/onboarding/preview` accepts the typed structured goal. `POST /api/v1/onboarding/confirm` additionally requires its `review_digest`, `reviewed: true` and a caller-generated `idempotency_key`. Both require the session and CSRF token; global writes also require the configured Origin. An identical successful retry returns the original goal. Reusing a key with different inputs returns 409. A concurrent insertion may return `concurrent_goal_confirmation_retry`; retry the identical body/key.

Availability, eligibility, policy or local date changes invalidate a pending review with `goal_review_stale`; preview again and require another explicit confirmation. The learner-confirmed timezone governs the local date. Date warnings compare released concept estimates against the chosen budget; they are lower-bound warnings, never guaranteed completion predictions. Self-report affects only the first diagnostic stage.

Saved goals contain structured input, declared and active tracks, reason codes, warning codes, first stage, policy/template versions, coverage digest and release list, selected pack pins, local evaluation date, and UTC confirmation time. `GET /api/v1/onboarding/goals` returns only the signed-in learner's latest 100 goals. These snapshots support replay using retained immutable packs and the recorded date. A later quarantine does not rewrite history; M4 must recheck content eligibility before diagnosis.

## Reconcile and recover

Configured content administrators may call `GET /api/v1/onboarding/reconciliation`. It compares committed goals with exactly one event of each kind, reports missing/duplicate/orphan events through the ratio, and requires 0.99 or better. No goals/events yields `null`, not a successful empty-cohort score. This measures the transactional source funnel; also verify delivery and downstream analytics before claiming the live gate.

Goal, audit and outbox changes commit in one transaction. Event payloads contain opaque actor/resource identifiers; submitted target text and personal display names are excluded. Delivery follows the existing outbox worker. Restore smoke tooling now defaults to revision `0003`; historical backups require their explicit historical revision. Migration downgrade is a disposable development operation and deletes M3 goal records; use flags and revision-compatible application images for deployed rollback.
