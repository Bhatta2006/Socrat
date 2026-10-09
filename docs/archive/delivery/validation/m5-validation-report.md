# M5 local validation report

Date: 5 October 2026. Scope: repository implementation and local synthetic validation. Hosted CI, staging drills, real content coverage, learner-effect evidence, and human approvals are not claimed.

Implemented the deterministic prerequisite closure and conditional curriculum, fourteen-day planner, released/calibrated practice filtering, stable candidate scores and reasons, protected assessment separation, track policies, bounded difficulty, weekly reserve, feasibility alternatives, recovery, confirmation, lighter workload, explicit weekdays, pause/resume, immutable revisions and commands, atomic events, ownership/CSRF, replay, additive schema `0005`, and learner controls.

| Check | Actual local result |
|---|---|
| API regression and coverage | 149 passed, 5 PostgreSQL-only tests skipped; 92.79% statement coverage, above the required 85% |
| Generated planning simulation | 2,000 scenarios, each producing identical repeat plans; prerequisite, inventory, independent-action, review and daily-capacity invariants; generated practice/assessment/retention histories with invalid, assisted, slow, and misconception outcomes |
| Browser regression | 26 passed across desktop and mobile, including all nine diagnostic track/language cells and planning confirmation/reload/pause/resume/lighter/recovery |
| Static checks | Ruff formatting/lint and mypy passed |
| Web checks | TypeScript and Next.js production build passed |
| Inherited prototype | 13 Node tests passed |
| Documentation and M0 contract checks | 156 passed, 0 failed; local links and placeholder checks passed |
| Contract consistency | Exported planning policy and command schema match application definitions; invalid schedules and unreviewed confirmation rejected |

Focused evidence tests cover immutable SQLite revisions, original retry responses and request-key conflicts, single confirmation event, stale revisions, ownership, flag behavior, quarantine, protected historical replay, impossible-date confirmation, seven-day recovery with no backlog, stable workload after reduction, evidence-driven in-progress/completed day states, and blocking further actions after evidence changes.

The initial run skipped five PostgreSQL cases because Docker was unavailable. On 5 October 2026, after the owner enabled Docker, all five PostgreSQL rehearsals passed locally, including same-key generation, different-key stale revision rejection, inherited release/onboarding/diagnostic races, and immutable triggers. An isolated PostgreSQL 17 container used a dynamically assigned localhost port because Windows reserved port 5432. Backup and restore passed at schema `0005`. The rehearsal also fixed Windows PowerShell 5.1 path-method compatibility in both backup/restore scripts. Hosted CI, staging rollback, and accountable operational approval remain pending.

The browser tests use isolated synthetic content; no production pack was published. Code exercises remain unavailable pending M6. Full content/session execution and independent submission production belong to M7, and real sequestered assessment delivery belongs to M9. Plan confirmation does not count as activation. Existing M0–M4 unpassed gates remain open in their original records.
