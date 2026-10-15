# Course Foundry M1: isolated backend foundations

Status: implemented locally; no push, deployment, crawling or publication.
Date: 15 October 2026. Builds on the [M0 plan](course-foundry-m0.md).

The owner authorized M1 after M0 and reiterated that future pushes must target `refined` only when authorized. No frontend files are part of this change. The pre-existing `apps/web/next-env.d.ts` change remains unstaged. M2–M7 are the **six remaining implementation phases** after this milestone.

## What was built

- Twelve isolated `foundry_` tables: the ten requested entities plus durable stage checkpoints and global controls. Migration `0008_foundry` follows `0007_learning_sessions`; metadata registration and readiness head are updated. There are no learner-table changes, backfills or pgvector dependencies.
- Validated `SOCRAT_FOUNDRY_` configuration for budgets, retry/lease timing, crawl limits, discovery filters and Explorer proposal thresholds. Processing defaults off; M1 refuses live operation even if requested through configuration.
- A separate worker with PostgreSQL row/advisory locks, ownership tokens, expiring leases, content/pipeline-version idempotency, stage hash chains and transactional checkpoint/effect writes. SQLite is restricted to single-worker `--once` development.
- Durable document/token reservations, shared daily job/token limits, a database kill switch checked at every reservation and checkpoint, cumulative wall deadlines across restarts, bounded retries/backoff, and parking after three handled failures or process crashes. Logs contain job/stage IDs and fixed reason codes, never exception bodies, resource payloads or credentials.
- Deterministic fixture tests plus real PostgreSQL integration tests for concurrent requests, advisory lock exclusion, atomic global reservations and migration reversal. No external HTTP/model calls are made.

The default handlers are **stubs**, S0–S8 and S10. Successful traversal ends as `needs_human` with `stub_pipeline_complete`; it does not create a pack, pass a content gate or expose anything to learners. There is no practice-candidate table or assessment generation. The worker imports neither the planner nor the mastery/assessment services.

The clarified product intent is preserved: one shared build/index per canonical skill, reused across learners; personalization happens later from reviewed shared material. M1 deduplicates an identical canonical job request. Paraphrase/alias resolution belongs to M4, actual resource acquisition/indexing to M2–M3, and curriculum induction/quality review to M5–M6. A request payload must describe skill-level build inputs, not individual learner settings or identities. Quality is not inferred from popularity or a successful pipeline run. Restricted/unknown rights never become permission to copy merely because a source is cited.

## Files and interfaces

| Path | Responsibility |
|---|---|
| `services/api/src/socrat/foundry/config.py` | Validated offline-first configuration |
| `services/api/src/socrat/foundry/models.py` | Foundry-owned records, identities, constraints and rights/storage safeguards |
| `services/api/src/socrat/foundry/jobs.py` | `JobRequest`, `enqueue`, `StageContext.reserve`, `StageResult`, `run_once` |
| `services/api/src/socrat/foundry/worker.py` | Separate process, `--once`, synthetic `--stub-skill` smoke path |
| `services/api/migrations/versions/0008_foundry_foundations.py` | Frozen, reversible schema migration; seeds the global controls row |
| `services/api/migrations/env.py`, `services/api/src/socrat/schema_revision.py` | Metadata registration and supported schema head |
| `services/api/tests/foundry/` | Fixture-based acceptance and opt-in PostgreSQL integration tests |

Stage handlers prepare `StageResult` records outside a database transaction. The runner commits those records and the corresponding stage checkpoint in one transaction, rejecting records targeting non-Foundry tables. A crash before commit leaves no partial stage effects; a crash after commit resumes at the next stage. Reservations commit before work and stay charged even after a failed attempt. A replaced/expired owner cannot checkpoint.

Hashes include canonical JSON input and pipeline version through the job identity. Identical completed or parked requests return the same job; new input is blocked while a build for that skill is active. Refresh/review/requeue controls are not implemented by this milestone. A pipeline version mismatch parks rather than silently mixing stage versions.

The wall deadline starts on first claim and includes retry waits/downtime. There is no background heartbeat: a future adapter must reserve immediately before every attempt and finish within its current lease and remaining wall budget. M2/M3 must use bounded network/parser/model operations; M1 has no such adapters to execute. SQLite does not provide PostgreSQL multi-worker/advisory-lock guarantees.

Sources default to `link_only`. Database constraints reject raw-object storage without an eligible license class/confidence and reject chunks referencing link-only sources. Source/chunk policy and skill references are tied by a composite foreign key. Unknown/unfetched sources have nullable fetch evidence; immutable robots/fetch snapshots arrive in M2, vector/FTS columns and full ingestion validation in M3. Candidate nodes/edges/packs are draft/pending only; only Explorer proposals can be represented. No API or worker publication path exists.

## Run an offline smoke job

From the repository root, in a separate PowerShell session, use a disposable database rather than the running demo or production database:

```powershell
$env:PYTHONPATH = 'services/api/src;services/execution/src'
$env:SOCRAT_DATABASE_URL = 'sqlite:///.cache/foundry-m1-smoke.db'
$env:SOCRAT_FOUNDRY_ENABLED = 'true'
uv run --frozen alembic upgrade head
uv run --frozen python -m socrat.foundry.worker --once --stub-skill git
```

Expected final structured log: `job_parked`, reason `stub_pipeline_complete`, state `needs_human`. Repeating the same request adds no duplicate job or checkpoints. No keys, downloads or model spend are needed. Without `SOCRAT_FOUNDRY_ENABLED=true`, the CLI exits with a clear error. Do not enable the separate worker in the demo/staging stack yet.

For a global operational stop, set the existing `global` row's `kill_switch` to true through an authorized DB session. Missing controls also fail closed. Turning the switch off does not automatically restart a parked job; human resume/review tooling is later work. The environment kill flag provides an additional stop.

The application readiness head advances to `0008_foundry`. Before starting an updated API, apply the normal reviewed Alembic migration step. Existing demo data was not migrated; no demo restart was performed as part of M1. Downgrades belong only on disposable test databases or an explicitly reviewed rollback, because they discard Foundry records.

## Test commands and acceptance evidence

```powershell
$foundryTemp = Join-Path (Get-Location).Path ('.cache/foundry-tests-' + [guid]::NewGuid().ToString('N'))
uv run --frozen pytest --basetemp $foundryTemp --cov=socrat --cov-report=term-missing --cov-fail-under=85
uv run --frozen ruff check services/api services/execution
uv run --frozen ruff format --check services/api services/execution
uv run --frozen mypy services/api/src services/execution/src
```

Set `SOCRAT_TEST_POSTGRES_URL` to an explicitly authorized test server to include the PostgreSQL gates. Each integration test creates a random `foundry_test_<uuid>` schema, migrates it, and drops only that schema in cleanup. It never drops the supplied database or uses the running demo's data. CI already supplies this URL to pytest; no CI workflow changes are needed. Without it, four PostgreSQL integration cases explicitly skip. Unit tests use their own migrated SQLite databases and fake clocks.

M1 local PostgreSQL tests use a new loopback-only PostgreSQL **18.3** instance on port 55438, separate from the existing service on port 5432. No database credentials or data were taken from that service. CI's existing PostgreSQL 17 job remains the check for the deployed major version; a hosted run is not claimed here.

| Acceptance criterion | Evidence |
|---|---|
| Migration upgrade/downgrade | Passed on SQLite and PostgreSQL; existing user retained; all twelve Foundry tables removed/recreated; SQLite schema matches model metadata |
| Stub traversal and recovery | Passed: stage hash chain, duplicate enqueue, crash after one checkpoint, partial stage rollback, expired-owner rejection, and no learner/catalog writes |
| Budgets and stop controls | Passed: document, per-job/global token, daily job and wall-time bounds; live-disabled guard; fresh DB kill flag; missing controls; retry reservations remain charged |
| Multi-worker safety | Passed on PostgreSQL: concurrent first requests yield one skill/job, advisory lock excludes even an expired-but-running worker, concurrent reservations cannot overspend |
| Retry/poison behavior | Passed: exponential backoff, bounded attempts, repeated process-crash parking, and secret-safe logging |
| Full backend regression suite | Passed: 259 tests, 24 dedicated-host cases skipped, 89.48% coverage |

Final validation results:

- Full backend suite: **259 passed, 24 skipped, 3 warnings in 170.18 seconds**, including all four PostgreSQL integration tests. Coverage **89.48%**, above the 85% gate. This adds 38 passing M1 cases to the M0 baseline. The 24 skips require the dedicated gVisor host. Log: `.cache/foundry-m1-pytest.log` (local/untracked).
- CLI smoke: migration plus a real `--once --stub-skill git` invocation passed against a new disposable SQLite database. An identical second invocation also passed without running stages again.
- Ruff lint: passed across both backend services. Formatting passed for all M1 files; the full check still reports the same **17 pre-existing unformatted files** recorded in M0. No formatter was applied to them.
- Foundry mypy: passed. Full backend mypy still reports the same two existing optional-type errors in `explainer/routes.py`, lines 105 and 136. This milestone does not claim an overall clean type/format gate.
- No frontend code, dependencies, content packs, learner logic, shared development data or remote branches were modified by this milestone. Temporary PostgreSQL schemas were removed by fixtures and the test-only database process was stopped after validation.

## Assumptions, deviations and next gate

The M0 proposal keeps learner publication deferred and uses an isolated backend. This M1 authorization does not implement or silently resolve the later Explorer/PRD runtime contract conflict. Manifest design and learner-release decisions must be revisited before M5/M6. There are no open M1 TODOs allowing a live fetch, provider call, publication or learner-state mutation.

No scraping/parser/vector/object-store dependencies were added. No frontend build, frontend typecheck or browser E2E was run. Existing unrelated backend formatting/type failures are recorded separately rather than changed in this milestone. After local commit, stop for the owner's M1 review; **do not push**. The next authorized phase would be M2, compliance and acquisition.
