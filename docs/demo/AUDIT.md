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
