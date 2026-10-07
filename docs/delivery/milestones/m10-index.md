# M10 — Dashboard, accountability, and privacy

Status: repository implementation; external release acceptance remains open. The owner requested M10 engineering on 7 October 2026 after M1–M9 implementation. Earlier content, operational, runtime, provider and human gates retain their recorded status.

## Implemented scope

- Today-first, goal-scoped progress endpoint and responsive dashboard: diagnostic, plan review, start/resume, protected assessment, recovery, pause/rest, program outcome, pending review and withdrawn-content states.
- Capability bands, confidence and uncertainty; independent and assisted weekly trends; reviewed evidence, assessment comparisons and mastery changes. Corrections remove invalid evidence from trends and mark historical assessment scores as superseded. Reading progress never writes mastery or evidence.
- Next seven days, existing immutable planner revisions, lighter workloads and missed-day recovery without accumulating practice debt. Schedule changes still require review and confirmation.
- Reviewed assessment due states and one durable 24-hour defer per check cycle. Assessment admission and contamination controls remain in M9.
- Revision-checked preferences; explicit in-app reminder consent; IANA timezone and overnight/all-day quiet windows; reduced motion. Reminders use the same confirmed plan, suppress paused/rest/completed days, expire at local-day end and deduplicate per learner/date. No email or browser-push provider is configured.
- Authenticated/CSRF-protected JSON export with explicit allowed fields. Private tests, reference solutions, form keys, credentials and other learners' work are excluded.
- Queued erasure, immediate session revocation, protected receipt access, worker cleanup, learner-scoped immutable-record deletion guards and operator evidence for external cleanup. Raw code/tutor artifacts have a 365-day default retention sweep.
- Migration `0010`, schema exports, restore erasure tooling, local Compose enablement and default-off staging dashboard/reminder switches.

## Boundaries

Reminder delivery is the in-app inbox. Provider messaging, push subscriptions and email identity collection are outside this slice. Optional secondary nudges are not enabled.

Database erasure does not certify deletion from backups, replicas, execution-host logs or model providers. The receipt remains pending until an authorized operator supplies private evidence. An opaque shared author/reviewer shell is retained only when another learner's reviews or immutable published content still reference it; those editorial records need separate privacy review. Cleanup context is restricted to operators and removed when all tasks complete.

WCAG keyboard/focus/reflow checks are implemented locally; a complete independent WCAG 2.2 AA audit remains a release gate. No hosted deletion drill, provider attestation or inherited gate is claimed by this implementation.

See the [gate](m10-gate.md), [operations](../../operations/m10-accountability-privacy.md), [data map](../../security/m10-data-map.md), and [validation](../validation/m10-validation-report.md).
