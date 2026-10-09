# Demo reachability audit — 7 October 2026

Branch: `sathish`. Baseline: the clean checkout before demo changes. This is a reachability audit, not a release gate approval.

`Yes` means source evidence exists. `No` means a fresh learner cannot use it. `Unverified` means the required runtime check could not be executed. The final matrix must distinguish these statuses rather than treating source or passing unit tests as browser verification.

| Capability | API exists | UI exists | Clickable from clean install | Real content | Actually executes | Evidence |
|---|---|---|---|---|---|---|
| F-01 Authentication/profile | Yes | Yes | Yes (development login) | N/A | Unverified | `main.py`, `workspace.tsx` |
| F-02 Goal/onboarding | Yes | Yes | Form only; no accepted learning route | No | No | `onboarding/routes.py`, `onboarding/policy.py`, `onboarding.tsx` |
| F-03 Diagnostic | Yes | Yes | No | No | No | `diagnostics/service.py`, `diagnostic.tsx` |
| F-04 Learner state/adaptation | Yes | Partial | No learning evidence to adapt | No | No | `learnerstate/`, `planning/`, `dashboard.tsx` |
| F-05 Learning/practice | Yes | Yes | No | Draft only | No | `learning/`, `learning-session.tsx`, `contracts/content/m7-arrays-pilot-draft.json` |
| F-06 Socratic help | Yes | Yes | No | No usable launch exercises | No | `tutor/`, `tutor.tsx` |
| F-07 Coding workspace | Yes | Yes | No | No | No | `execution/`, `code-workspace.tsx`, `runner/docker_backend.py` |
| F-08 Assessment | Yes | Yes | No | No | No | `assessment/`, `assessment.tsx` |
| F-09 Dashboard/accountability | Yes | Yes | Account panels only | No learning evidence | No learning journey | `accountability/`, `dashboard.tsx`, `account-controls.tsx` |
| M1 Platform/auth/privacy/operations | Yes | Partial | Profile reachable | N/A | Unverified | `main.py`, migrations, `compose.yaml` |
| M2 Skill-pack graph/version/review | Yes | Admin API only | No learner pack | Fixtures only | No | `skillpacks/`, `contracts/fixtures/skill-packs/` |
| M3 Three-track routing | Yes | Yes | All launch goals blocked | No | No | `onboarding/policy.py:matching_pack` |
| M4 Diagnostic/evidence/replay | Yes | Partial | No | No | No | `diagnostics/`, `learnerstate/` |
| M5 Curriculum/recovery | Yes | Yes | No | No | No | `planning/`, `planner.tsx` |
| M6 Python/C++/Java execution | Yes | Yes | No | No | No | Execution disabled in Compose; production backend requires runsc |
| M7 Lessons/timed/upsolve/Today | Yes | Yes | No | Draft only | No | `learning/content.py`, `learning/audit.py`, `learning-session.tsx` |
| M8 Curated hints/model fallback | Yes | Yes | No | No runnable practice | No | `tutor/policy.py`, `tutor/gateway.py` |
| M9 Weekly/final/retention | Yes | Yes | No | No | No | `assessment/`, `accountability/retention.py` |
| M10 Progress/reminders/export/delete | Yes | Yes | Settings panels reachable | No learning evidence | Unverified | `accountability/`, `account-controls.tsx` |
| M11 Journeys/incident/restore | Yes (test harnesses) | Partial | No real complete journey | Synthetic tests | No learner code in reported journeys | `docs/delivery/validation/m11-validation-report.md` |

## Baseline findings

- There is one `apps/web/src/app/page.tsx`; screen switching is component state rather than URL navigation.
- The root layout selects `wireframe`; global CSS selects Arial. There is no shared application navigation.
- Fixtures have `purpose: fixture`. The arrays draft is explicitly not publishable. Fresh-install routing requires launch content and therefore blocks learning.
- The E2E seed imports test helpers and creates synthetic launch copies inside `socrat.e2e.db`. It is not a user installation mechanism.
- Compose has no runner and does not enable execution. The dedicated production Docker backend requires gVisor, signature verification, and unified cgroups.
- `temp.py` is scratch code. Tooling directories are not product assets and should be excluded from the Docker context.

## Baseline runtime evidence and constraints

`docker version` and the requested `docker compose up --build` cannot run: Docker is absent from PATH and `C:/Program Files/Docker/Docker/resources/bin/docker.exe` does not exist. No Docker installation or production environment change is inferred from this task.

The local Python runtime is 3.12.14; Node is 24.21.0. `npm run dev` initially failed on missing esbuild; `npm ci` restored the lockfile dependencies. A fresh SQLite database `.cache/demo-before.db` is migrated for a local baseline browser capture. This is explicitly a fallback, not the required clean-clone Compose proof.

Baseline screenshot: `docs/demo/before.png` (local source runtime; capture recorded separately). Container startup timing and container execution remain unverified until a Docker host is available.
`before.png` was inspected: the first restored local dev request returned a Next.js 404 despite the root page existing. This unexpected runtime failure is captured as baseline evidence; it needs investigation before any route is counted as reachable.


## Recovery implementation and proof on `ramkrsna1`

The table above is the initial source audit. The following records the recovered local development path. No milestone or release gate is approved.

| Capability | Current learner entry | Recorded local proof |
|---|---|---|
| F-01 / M1 profile and login | `/login`, `/onboarding`, `/settings` | Fresh signed-in desktop/mobile learners; profile persisted; normal export/deletion |
| F-02 / M3 goals and routing | Three-step reviewed onboarding | Original demo pack; all nine track/language cells have inventory; fresh Foundations journeys in all languages |
| F-03 / M4 diagnostic and evidence | `/diagnostic`, `/progress` | Real objective responses, persisted diagnostic, separately displayed independent/assisted evidence |
| F-04 / M5 adaptation and recovery | `/plan`, `/demo` | Fourteen-day review/confirm, baseline-triggered refresh, actual clock jump and missed-day recalculation; worker heartbeat checked before recovery |
| F-05 / M2 / M7 learning content | `/today`, `/session/[id]` | Fourteen concepts, 126 language/track lessons, original exercises; fresh retrieval/instruction/guided/independent/exit journeys |
| F-06 / M8 Socratic help | Coding workspace reasoning panel | Curated levels one and two, new reasoning between requests, level-two assistance carried into real Submit |
| F-07 / M6 coding execution | CodeMirror workspace | All languages compiled, diagnostics shown in Problems/gutter, fixes executed, twenty-case signed Submits finalized; all 252 references independently executed |
| F-08 / M9 assessment and retention | `/assessments`, `/demo` | Baseline, weekly and delayed retention through clicks; current sample forms cover the two root concepts |
| F-09 / M10 accountability and privacy | `/progress`, `/settings` | Distinct assisted/independent evidence; quiet hours, JSON export, deletion receipt and session revocation |
| M7 competitive timed/upsolve | Sample C++ competitive learner | Seven actual native historical sessions, including one timed block; service and fixture UI regression cover timed/upsolve. A real native browser timer-expiry/upsolve recording remains open |
| M11 validation and operations | Native Windows launcher and CI | Signed-reference results, desktop/mobile videos and screenshots; fresh-database Windows start. Clean-clone timing, hosted CI completion and optional Docker proof remain open |

See [the verification ledger](VERIFICATION.md) for exact pass counts and explicit limitations. `before.png` remains a failed local baseline capture rather than successful clean-clone Compose proof. The new native path avoids the Docker Desktop journal stalls encountered later in recovery.
