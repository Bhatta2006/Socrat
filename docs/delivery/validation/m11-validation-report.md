# M11 automated local validation — 7 October 2026

The owner requested automated testing and deferred human testing. Results below cover the local repository and an ephemeral PostgreSQL 16 container containing synthetic data. No deployed production/staging services or external providers were changed.

## Results

| Check | Result |
|---|---|
| Full existing API regression | 388 passed, 45 skipped, no failures (11 minutes 40 seconds); 21 PostgreSQL skips exercised successfully in the separate PostgreSQL run, 24 dedicated execution-host checks remain skipped |
| 200 independent synthetic API journeys | 200 passed, no skips or failures (14 minutes 15 seconds); all nine track/language cells covered |
| Real PostgreSQL migration/locking/concurrency regression | 21 passed |
| Concurrent PostgreSQL progress reads | 1 passed: 200 requests, 8 concurrent readers, all successful, unchanged learning evidence; measured p95 approximately 371 ms |
| Injected worker crash/retry and saved-session backup restore | 2 passed |
| Full desktop/mobile Playwright suite | 64 passed; process exit 0 and `test-results/.last-run.json` records no failures |
| Product prototype regression | 13 passed |
| Production web build and TypeScript | Passed |
| Python lint, formatting and types | Passed: 135 files formatted; 72 source files type checked |

Raw local pytest records are `.cache/m11-api-baseline.xml`, `.cache/m11-journeys.xml`, `.cache/m11-postgres.xml`, `.cache/m11-load.xml` and `.cache/m11-recovery.xml`. These ignored files contain only local synthetic test results; retain them locally or as private CI artifacts. The temporary PostgreSQL container was stopped and removed after its checks completed.

The full API regression started before the new M11 modules were added. The three new modules are exercised separately in the journey, load and recovery runs; the PostgreSQL regression was selected separately. Counts must not be presented as one combined full-suite run or as distinct learner journeys.

## What was added

- `test_m11_journeys.py`: 200 complete API lifecycle cases, each with a fresh migrated database, distributed over all nine track/language cells. Counts are 23 each for Foundations/Python and Foundations/C++; 22 for each remaining cell.
- `test_m11_postgres.py`: successful owned progress responses under eight-way concurrent reads, without evidence mutation. This is a local in-process baseline for one synthetic learner, not mixed-traffic load against a hosted deployment or a beta concurrency declaration.
- `test_m11_recovery.py`: a worker failure at transaction commit must leave delivery pending and no receipt; retry delivers once. SQLite backup recovery must retain the completed session and identical learning evidence.
- The existing complete-session scenario is now reusable. Its secrecy assertion checks learner-visible block content rather than matching hidden-answer digits against random identifiers, while continuing to prohibit reference-solution fields anywhere in the response.

Existing regression exercises broker failure and forged callbacks without mastery writes, signed job tamper rejection, model timeouts/fallback/review, content quarantine and replay, protected assessments, rollback selection, restore erasure replay and PostgreSQL concurrent commands.

## Repeat the checks

From the repository root with the project's development dependencies and Chromium installed:

```powershell
.\.venv\Scripts\python.exe -m pytest services/api/tests --ignore=services/api/tests/test_m11_journeys.py --ignore=services/api/tests/test_m11_postgres.py --ignore=services/api/tests/test_m11_recovery.py -q --junitxml=.cache/m11-api-baseline.xml
.\.venv\Scripts\python.exe -m pytest services/api/tests/test_m11_journeys.py -q --junitxml=.cache/m11-journeys.xml
# Set SOCRAT_TEST_POSTGRES_URL to an isolated disposable PostgreSQL database only.
.\.venv\Scripts\python.exe -m pytest services/api/tests -k postgres -q -o junit_family=legacy --junitxml=.cache/m11-postgres.xml
.\.venv\Scripts\python.exe -m pytest services/api/tests/test_m11_recovery.py -q --junitxml=.cache/m11-recovery.xml
$env:PLAYWRIGHT_JUNIT_OUTPUT_FILE='.cache/m11-browser.xml'
npm.cmd run test:e2e -- --reporter=list,junit
npm.cmd run test:m0
npm.cmd run typecheck
npm.cmd run build
.\.venv\Scripts\python.exe -m ruff check services/api services/execution
.\.venv\Scripts\python.exe -m ruff format --check services/api services/execution
.\.venv\Scripts\python.exe -m mypy services/api/src services/execution/src
```

The normal CI pytest discovery includes the new cases automatically. A PostgreSQL run must use a database role permitted to create/drop the per-test disposable databases. Dedicated runner checks stay opt-in and must use attested gVisor runtimes; Docker Desktop is not a substitute.

## Remaining M11 acceptance

Human journeys are deferred, not counted or waived. Seven days of healthy deployed error budgets, production-equivalent load and hosted restore/queue/model/runner-compromise/rollback game days are unexecuted. Admin/support/incident response still need operator rehearsal. Earlier accessibility, content, provider/privacy and dedicated execution gates retain their status. Local passing tests do not establish zero Sev1/2 production incidents or beta readiness.

Browser output contains non-failing Monaco clipboard permission/cancellation warnings. Python emits existing collection warnings for the `TestInput` protocol class; the load run emitted a JUnit-family warning while successfully retaining its timing properties. These warnings did not fail the checks.
