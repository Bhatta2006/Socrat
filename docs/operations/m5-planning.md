# M5 planning operations

Set `SOCRAT_PLANNING_ENABLED=true` only with released practice coverage and completed diagnostics. Local Compose enables it; staging and `.env.example` default off. Upgrade Alembic to `0005` before enabling. Rollback disables the flag and retains the additive schema, revisions, commands, and evidence. Do not downgrade a live learning database or mutate historical snapshots.

Owned endpoints:

- `GET /api/v1/goals/{goal_id}/curriculum`: saved active revision, explanatory decisions, and evidence/policy refresh status.
- `POST /api/v1/goals/{goal_id}/curriculum/commands`: `generate`, `confirm`, `refresh`, `lighter`, `recover`, `pause`, or `resume`.
- `GET /api/v1/daily-plan?goal_id=...&date=YYYY-MM-DD`: day state and best independent action; omitted date uses the goal timezone.
- `GET /api/v1/admin/planning/revisions/{revision_id}/replay`: administrator-only snapshot digest and deterministic decision verification. Replay remains available for historical quarantined content.

All commands need Origin, CSRF, `idempotency_key`, and `expected_revision`. Retrying the same key/body returns the original response; changing its body returns `idempotency_key_reused`. A concurrency conflict requires loading the latest revision before creating a new command. Confirmation additionally needs the saved `reviewed_digest`; a new day, evidence, or scoring policy requires refresh and renewed review. Every schedule edit creates a draft and needs confirmation.

Generate example:

```json
{"action":"generate","expected_revision":0,"idempotency_key":"first-plan","weekdays":[0,2,4],"minutes":30}
```

An unfeasible date returns estimates and alternatives; explicit `recover` with a later date or `no_fixed_date` creates a revised draft. Lighter-day edits reduce the schedule's session budget for the new horizon. Rest dates do not accumulate debt. Repeated misses reduce the proposed budget without changing mastery or the declared goal. Future milestones are estimates; future days use current verified prerequisites.

`plan.confirmed`, `plan.adapted`, and `plan.content_gap` events share the command transaction. Confirmation does not emit activation. Diagnose gaps using saved `decisions[].rejected_by`, due deferrals, candidate score components, and graph pins. Do not fix a gap by enabling assessment items, bypassing prerequisites, or fabricating runtime health.

Regenerate machine contracts with `python scripts/validation/export-m5-contracts.py`; tests detect drift. Run API tests, Ruff, mypy, web typecheck/build, and desktop/mobile browser acceptance. Configure `SOCRAT_TEST_POSTGRES_URL` with an isolated test database service for race and immutable-trigger verification. Run the staging restore script with expected revision `0005` and record private approval references in the gate.
