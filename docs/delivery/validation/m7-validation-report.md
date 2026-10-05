# M7 initial validation record

Date: 5 October 2026. Scope: normal-session and Competitive timed/upsolve repository increments, synthetic content, and broker test doubles. M7 remains incomplete.

The initial tests cover all nine track/language combinations for normal sessions, server-backed reload, idempotent start/commands, pause/resume, sequential content unlock, code-attempt ownership, signed Submit advancement, hidden/reference secrecy, and exactly one completion event. Additional cases cover CSRF, cross-user ownership, stale revisions, content quarantine, operational-failure retry, local-date command cutoff, ungraded text completion, and terminal abandonment. These tests do not run a real sandbox or establish released content coverage.

Validation performed:

- First-increment Python regression/coverage suite: 185 passed, 33 skipped; total coverage 91.80%, above CI's 85% threshold. Skips reflect unavailable dedicated-host gVisor and unconfigured PostgreSQL, rather than passes. Separate isolated PostgreSQL validation passed all three selected checks: M7 session persistence/immutable pins, concurrent start/receipt replay, and the existing diagnostic schema-revision check. Both M7 PostgreSQL checks passed again after the final session validation refinements.
- Browser acceptance: 10 passed across desktop and mobile, covering new Today text sessions plus existing planner and Python/C++/Java Monaco journeys. The Today test seeds an isolated synthetic pack and uses real local APIs, verifies pause/reload/resume/completion, checks hostile text remains inert, and verifies no text mastery evidence is produced. Editor tests use API-shaped fixtures, not sandbox execution.
- Ruff lint/format, mypy, TypeScript checking, and the production web build passed.

The browser run used existing Chromium under `.cache/ms-playwright`. The first launch attempt looked in the default user cache and failed before running tests; correcting `PLAYWRIGHT_BROWSERS_PATH` allowed all ten checks to pass. Existing mobile Monaco clipboard/cancellation warnings remain observable in the browser logs.

PostgreSQL tests use `SOCRAT_TEST_POSTGRES_URL` and isolated temporary databases. The local container uses its own Compose project; no production database is involved. Real content-bank release evidence, mixed/variant Competitive journeys, calibration/dogfood, and staged accessibility/runtime journeys remain required by the [M7 gate](../milestones/m7-gate.md). Deferred M6 gVisor checks remain deferred.

## Competitive timing and upsolve increment

This increment adds server-enforced timing to planned independent blocks, a pinned untimed-practice option, error classification, and separate seen upsolve attempts. Nine new API cases cover Python/C++/Java timeout-to-upsolve source preservation, deadline reset rejection, exact-boundary admission, pending/on-time late-scored Submit handling, unsuccessful versus unscored operational outcomes, untimed choice immutability, admission-time solve duration across pauses, and the session feature kill switch. Exported input schema drift has a separate passing check.

The final full Python suite passed 194 tests, with 35 environment-dependent skips and 91.86% coverage, above CI's 85% gate. The exported-schema drift test, added after that full suite was collected, passed separately. Four PostgreSQL acceptance tests passed, including the timed/upsolve journey and simultaneous upsolve retries creating exactly one additional code attempt. Final Ruff, mypy, TypeScript checks, and the production web build pass.

Browser acceptance passed ten existing desktop/mobile planner/editor/normal-session checks and two new timed UI checks. The new checks verify a timer survives reload, Submit becomes disabled after expiry, and transitioning immediately after an editor change saves that change before creating the upsolve draft. The timer UI uses API-shaped fixtures; authoritative admission and signed-result behavior are tested with real APIs and synthetic broker results. The first timed UI attempt exposed incomplete diagnostic fixture fields; correcting that fixture produced two passes without changing diagnostic behavior. Existing mobile Monaco clipboard/cancellation warnings remain visible.

No dedicated-host sandbox, live content-bank, duration-calibration, or learner-outcome acceptance is inferred from these results.
