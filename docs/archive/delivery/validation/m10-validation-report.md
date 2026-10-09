# M10 local validation — 7 October 2026

Repository validation only; this record does not approve hosted rollout, real launch content, independent accessibility conformance or provider/storage cleanup.

## Completed checks

| Check | Result |
|---|---|
| Full desktop/mobile Playwright suite | 64 passed, including all existing learning journeys and the new dashboard, preferences, export, deletion, saved-receipt and keyboard/reflow flows |
| M10 services and exported contracts | 20 passed; 92% statement coverage of socrat.accountability before the final saved-session priority adjustment |
| PostgreSQL erasure and concurrency | M10 erasure guard/concurrent preferences passed; existing assessment start/finalization and concurrent-review tests passed after preserving target-learner editorial locking |
| Affected foundation/execution/deployment checks | 53 passed in an earlier affected-suite run; the added privacy alert names were subsequently incorporated into the exact deployment contract |
| Complete API regression snapshot with real PostgreSQL | 403 passed, 24 skipped, 2 failures on the in-flight snapshot; the reviewer-lock correction and privacy alert contract were applied while/after that run, then covered by the focused final rerun below |
| Production Next.js build | Passed, including TypeScript and static page generation |
| Python types | Passed across 72 source files |
| Ruff lint/format and patch whitespace | Passed |
| SQLite migration/restore | Existing foundation upgrade/downgrade/backup tests passed with schema 0010; synthetic browser database upgraded to the completed migration |
| Restore erasure replay | Private-manifest reapplication removes restored learner rows before traffic; repeated application on an already removed learner is harmless |

The initial SQLite-only full run passed 374 checks and skipped 44; an existing secrecy assertion matched hidden-answer digits in a random UUID. The assertion now checks learner-visible content while retaining the reference-solution check. Its affected execution suite subsequently passed. The PostgreSQL full-run failures above are recorded instead of claiming that an in-flight run automatically picks up file changes.

Final focused rerun: **31 passed** covering PostgreSQL assessment and M10 concurrency, deployment contracts, M10 services and schema/restore contracts. The reviewer-lock regression and the exact privacy alert contract both passed. The additional saved-session regression and PostgreSQL worker-lock checks subsequently passed (**2 passed**).

## Coverage of M10 requirements

- Progress is owner-scoped, read-only and correction-aware; diagnostic participation does not become a practice solve trend. Unknown goals are hidden from other accounts.
- Preferences enforce CSRF/Origin, known timezones and clock formats, explicit consent and revision conflict handling.
- Reminders deduplicate by local date and respect planned days, pause/completion, consent withdrawal and quiet windows, including overnight/all-day quiet and DST folds.
- Weekly checks survive an inactive retention policy; defer is durable, expires after 24 hours and cannot repeat within the same cycle. Paused plans do not accumulate missed-day counts.
- Export and erasure cover learner-owned diagnostic, planning, code, tutor and protected assessment records across Python/C++/Java. Private tests/keys, signatures and reference solutions stay out of exports.
- Deletion revokes every login, prevents re-login to the pending account, supports a private retry receipt and erases guarded facts only inside the authorized transaction. Published content and other learners' records remain intact.
- Cleanup requires restricted operator evidence. Public receipt access needs its token. Monitoring exposes aggregate backlog/overdue counts without learner/request identifiers.
- Raw-artifact retention preserves scoring facts and active execution sources.
- Desktop/mobile screenshots in `.cache/m10-progress-desktop.png` and `.cache/m10-progress-mobile.png` were inspected; browser assertions verified no horizontal overflow and focus into the evidence panel.

## Pending external acceptance

- Independent WCAG 2.2 AA audit across all critical flows, including screen readers and coding accommodations.
- Live database/replica/backup/object-store/host-log/provider inventory reconciliation, deletion within 30 days, and re-erasure on deployed restore.
- Provider-specific deletion/no-retention evidence and historical/failed-call reconciliation; no vendor cleanup is implied by store=false or artifact removal.
- Hosted worker/restart, alerts, escalation, deployment rollback and real-content nine-cell acceptance.
- Dedicated gVisor execution/security/load and other inherited M0–M9 gates.

Twenty-four execution/environment-dependent checks in the real-PostgreSQL full run remained skipped; this session did not attest the dedicated runner plane. The ephemeral PostgreSQL verifier uses synthetic credentials and is removed at closeout.
