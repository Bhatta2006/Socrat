# M10 accountability and privacy operations

## Configuration and API

Apply `alembic upgrade head` before starting API/worker; readiness requires `0010`. Local Compose enables `SOCRAT_DASHBOARD_ENABLED` and `SOCRAT_REMINDERS_ENABLED`. Both default off for standalone/staging; the reminder flag must agree on API and worker. Privacy and preferences are available independently of learning feature switches.

| Endpoint | Purpose |
|---|---|
| GET /api/v1/progress?goal_id=… | Own goal summary; defaults to most recent goal |
| GET /api/v1/preferences | Defaults and saved revision |
| PATCH /api/v1/preferences | Full validated preferences with expected_revision |
| GET /api/v1/reminders | Own current-day inbox, rechecked against consent/quiet/pause/rest/completion |
| POST /api/v1/reminders/check | Enqueue eligible in-app reminder under learner lock |
| POST /api/v1/reminders/{id}/opened | Idempotent acknowledgement |
| POST /api/v1/goals/{id}/assessment-deferral | One 24-hour defer of the exact due cycle |
| POST /api/v1/privacy/export | JSON download; no server-side export object retained |
| POST /api/v1/privacy/delete | Exact confirmation DELETE MY DATA; revokes all sessions and returns private receipt |
| GET /api/v1/privacy/requests/{id} | Receipt status with X-Privacy-Token header; no authenticated session required |
| GET /api/v1/admin/privacy/requests | Restricted queue, cleanup context and overdue marker |
| POST /api/v1/admin/privacy/requests/{id}/cleanup | Restricted external-task evidence, private-review:<opaque-reference> |

Mutations require the configured Origin and session CSRF token. The receipt endpoint uses a hashed, constant-time checked bearer token; do not put it in a URL. Operator endpoints use the existing explicit content-admin allowlist. Admin requests never grant access to another learner's export.

## Reminders

Consent defaults off. Eligibility requires a confirmed non-paused plan with a non-rest day and no completed session. There is one in-app message per learner/local date, within 60 minutes of the chosen reminder time. Quiet hours override consent; overnight windows and DST folds use the IANA timezone. Matching quiet boundaries silence the whole day. Old messages do not spill into a later local day. Disable the reminder flag to stop scheduling and hide the inbox; this does not disable learning.

The worker polls durably; the foreground browser can also request a consent-checked check. No external email or push delivery occurs, no recipient list is collected, and no third-party notification sender is configured.

## Deletion and external cleanup

1. The learner exports if desired, then explicitly requests deletion. Save the returned private receipt. Sessions are revoked immediately and re-login is denied while the original account awaits erasure.
2. The worker processes queued requests in a transaction, locks the learner, sets erasing, deletes owned children before parents and removes associated outbox/delivery records. Normal updates remain forbidden; erasure guards authorize DELETE only for rows resolving to this learner. A crash rolls back both authorization and deletion; retry uses the queue.
3. Receipt status becomes awaiting_external_cleanup after database cleanup. Published packs and other learners' review records remain intact. If these retain an author/reviewer reference, the identity is cleared and shared_editorial_lineage remains pending.
4. A restricted operator reads the cleanup queue. Before purging backups, store the opaque user/resource IDs in an approved private erasure manifest outside the repository. Reconcile databases, replicas, backups, execution-host artifacts/logs, analytics exports and any deployed object stores. Enforce the 30-day deadline, and review shared editorial free text separately. Protected aggregate metrics expose incomplete requests by status and overdue counts; staging alerts flag a queued backlog after ten minutes and overdue cleanup after five minutes. Alert delivery and escalation still require a hosted drill.
5. When provider cleanup is pending, use the private request window and provider inventory to locate processing. Verify the actual provider deletion or documented no-retention terms, including failed/rolled-back model calls and any earlier provider configuration. Never infer provider deletion from store=false alone. If current telemetry/configuration reports no model use, independently reconcile that classification in the privacy review; adapters do not retain vendor-specific deletion handles.
6. Submit separate private-review evidence for each pending task. Completion requires database plus every external task; the service clears restricted cleanup context only then. The operator keeps required restore tombstones in approved private storage until all affected backups expire. Public receipts expose task status, not cleanup context or identities.

To check a saved receipt after closing the UI, use Check a saved deletion receipt on the signed-out workspace; the file is read locally and only its ID/token are sent for status retrieval. Alternatively issue GET /api/v1/privacy/requests/<receipt-id> with X-Privacy-Token from its JSON file. Use a local client that does not log headers; never share the file publicly.

## Restore and retention

Restore into an isolated database with learner traffic disabled. Migrate to 0010, then run `python scripts/operations/reapply-erasure.py --private-manifest <private-json-file>` using the restore target's `SOCRAT_DATABASE_*` configuration. The file is a JSON array of opaque learner UUIDs and must stay outside version control. The script removes previously erased learner data before traffic is permitted and creates pending operator cleanup records for the restored copy. Run existing restore integrity/readiness checks and reconcile tombstones before enabling traffic. Default restore checks now expect 0010.

The worker sweeps raw drafts, terminal execution sources and tutor artifacts once per day after 365 days. Derived scoring facts remain replayable; active job sources are preserved. Monitor abandoned jobs and apply runner expiry before relying on raw-source expiry. External/provider retention and backup TTLs require deployment-specific enforcement and evidence.

## Accessibility release acceptance

Local browser checks cover keyboard disclosures, focus into evidence panels, labelled consent/time inputs, reduced motion, mobile reflow, export/deletion controls and receipt states. They are partial checks. Independently audit all critical learning flows for WCAG 2.2 AA, including contrast, screen reader output, editor alternatives, focus obstruction, touch targets, errors and timer accommodations. Record findings privately, resolve them and link the approval in the M10 gate.
