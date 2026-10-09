# M3 — Onboarding and deterministic routing

**Status:** Repository implementation verified locally; hosted PostgreSQL, staging, launch content and human gate pending.

**Started:** 2026-10-02. The owner authorized M3 after pushing M2. Earlier M0/M1/M2 gates remain unpassed.

| Deliverable | Evidence |
|---|---|
| Foundations, Interview and Competitive forms | [Learner flow](../../../apps/web/src/app/onboarding.tsx), including Python/C++/Java, schedule, explicit date state, experience and track-specific fields |
| Deterministic entry policy | [Typed inputs and resolver](../../../services/api/src/socrat/onboarding/policy.py); ordered eligibility, exact target coverage, beginner bridges and feasibility warnings |
| Review then confirm | [Authenticated API](../../../services/api/src/socrat/onboarding/routes.py); CSRF/origin protection, stale-review rejection, idempotent confirmation and private history |
| Version pins and persistence | [Additive revision 0003](../../../services/api/migrations/versions/0003_onboarding.py), preserving prior identity/content tables |
| Explicit released targets | [Pack contract](../../../services/api/src/socrat/skillpacks/schema.py) and [JSON Schema](../../../contracts/schemas/skill-pack.schema.json); empty declarations provide no coverage and preserve pre-M3 digests |
| Funnel reconciliation | Atomic `goal.created`/`route.confirmed` events and restricted reconciliation endpoint; missing, duplicate and orphan events detected |
| Verification | [API acceptance](../../../services/api/tests/test_onboarding.py), [PostgreSQL rehearsal](../../../services/api/tests/test_onboarding_postgres.py), [browser journeys](../../../tests/e2e/onboarding.spec.ts), [validation report](../validation/m3-validation-report.md) |

Zero coding experience never rejects a learner. Accepted Interview/Competitive beginners retain their declared goal and begin with Foundations when both target and bridge content are released. Unavailable content produces a precise waitlist, including when no launch pack exists. Self-report selects an initial check, never mastery or accelerated placement.

M4 implements the diagnostics named by these routes. No diagnostic execution, mastery update, curriculum plan, code runner or AI assistance is enabled by M3. See the [operations instructions](../../operations/m3-onboarding.md) and [gate](m3-gate.md).
