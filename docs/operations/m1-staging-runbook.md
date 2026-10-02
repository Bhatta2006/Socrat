# M1 staging operations runbook

**Environment:** private OCI staging in India South (`ap-hyderabad-1`)  
**Runtime owner:** Engineering  
**Status:** executable procedure; no cloud deployment has yet been claimed

This runbook governs the first external environment. It does not authorize a Terraform apply. The owner must inspect an OCI plan, verify Always Free eligibility and the USD 55 budget ceiling, and explicitly approve the apply before resources are created.

## Preconditions

- `main` is protected and the `secret-scan` and `verify` checks pass for the exact release commit.
- GHCR contains API and web images for that commit, each selected by its `sha256` digest rather than a mutable tag.
- The OCI host was created from the reviewed Terraform plan and cloud-init completed successfully.
- An owned DNS name resolves to the host and ports 80/443 reach Caddy.
- The approved OIDC application has the exact HTTPS callback URL and logout URL.
- The API's dedicated outbound bridge can reach the approved OIDC discovery, token, and signing-key endpoints. Internal services remain isolated; the API publishes no host port. This bridge does not enforce a provider-only destination allow-list.
- `/opt/socrat/runtime` contains the repository's `infra/runtime/staging` and `scripts/operations` trees from the release commit.
- `/opt/socrat/secrets` contains the five files listed in the [runtime contract](../../infra/runtime/staging/README.md), owned by the deployment account with mode `0600`.
- The operator can authenticate to GHCR without printing the token and has verified the server's SSH host key out of band.

Stop if any precondition is uncertain. Do not substitute a paid OCI shape, expose an internal port, enable developer login, or weaken TLS to make a deployment proceed.

## First-time host verification

Run these on the staging host after cloud-init has completed:

```bash
cloud-init status --wait
docker version
docker compose version
find /opt/socrat/secrets -maxdepth 1 -type f -printf '%f %m %u:%g\n'
```

Expected secret-file mode is `600`; do not print file contents. Sign out and reconnect once after cloud-init so Docker group membership is active.

## Deploy an immutable release

Record the 40-character Git commit and the two registry digests from the successful GitHub Actions run. On the staging host, run from the matching runtime bundle:

```bash
cd /opt/socrat/runtime
python3 scripts/operations/release.py \
  --state-dir /var/lib/socrat/releases \
  --compose-file /opt/socrat/runtime/infra/runtime/staging/compose.yaml \
  deploy \
  --commit '<40-character-git-commit>' \
  --api-image 'ghcr.io/bhatta2006/socrat-api@sha256:<64-hex-digest>' \
  --web-image 'ghcr.io/bhatta2006/socrat-web@sha256:<64-hex-digest>' \
  --staging-host '<owned-staging-hostname>' \
  --tls-email '<operations-email>' \
  --oidc-issuer 'https://<approved-issuer>' \
  --oidc-client-id '<approved-client-id>' \
  --secrets-dir /opt/socrat/secrets
```

The controller first validates the fully rendered Compose model, pulls digest-pinned images, runs the migration, waits for container health, and checks the external HTTPS readiness endpoint. Only then does it atomically promote the release pointer. If activation fails and a previous release exists, it reactivates that release automatically.

Verify independently:

```bash
curl --fail --silent --show-error "https://<owned-staging-hostname>/api/health/ready"
docker compose --project-name socrat-staging \
  --env-file "/var/lib/socrat/releases/$(cat /var/lib/socrat/releases/current).env" \
  --file /opt/socrat/runtime/infra/runtime/staging/compose.yaml ps
```

Never pass the five runtime secrets as command-line or environment values.

## PostgreSQL backup and restoration drill

Create the dump on encrypted host storage, then restore it into a disposable database in the same PostgreSQL container. Use only a Socrat-produced trusted archive:

```bash
release_id="$(cat /var/lib/socrat/releases/current)"
env_file="/var/lib/socrat/releases/${release_id}.env"
archive="$(bash scripts/operations/backup-postgres.sh \
  --output-directory /var/lib/socrat/backups \
  --compose-file /opt/socrat/runtime/infra/runtime/staging/compose.yaml \
  --project-name socrat-staging \
  --env-file "$env_file")"
bash scripts/operations/restore-smoke.sh \
  --archive "$archive" \
  --compose-file /opt/socrat/runtime/infra/runtime/staging/compose.yaml \
  --project-name socrat-staging \
  --env-file "$env_file"
```

The success condition is the expected schema revision in the isolated restore database: M2 uses `0002`. For historical M1 archives, pass `--expected-revision 0001` (PowerShell: `-ExpectedRevision 0001`). Record archive checksum, byte size, start/end UTC timestamps, release ID, and result. Uploading encrypted backups to the private OCI bucket and exercising download restoration remain mandatory before the milestone gate can pass; do not claim an off-host backup until that has been observed.

## Roll back

Rollback reactivates the prior digest-pinned release and health-checks it before changing the pointers:

```bash
cd /opt/socrat/runtime
python3 scripts/operations/release.py \
  --state-dir /var/lib/socrat/releases \
  --compose-file /opt/socrat/runtime/infra/runtime/staging/compose.yaml \
  rollback
```

Confirm the external readiness endpoint and current release pointer. Schema rollback is not automatic: migrations must remain backward-compatible through expand/migrate/contract sequencing. If no prior release exists, stop and diagnose instead of editing release pointers manually.

## Private telemetry access

Grafana is bound to `127.0.0.1:3001` on the host. From a trusted administrator workstation:

```bash
ssh -N -L 3001:127.0.0.1:3001 ubuntu@<staging-host>
```

Open `http://127.0.0.1:3001`, authenticate with the secret-file-backed admin credential, and review the provisioned **Socrat API** dashboard. Prometheus is not published. The dashboard must show request rate, 5xx ratio, and p95 latency without learner identifiers or request bodies.

The repository defines alert rules and severities, but an accountable external notification receiver is not yet configured. Until it is tested, alert presence is evidence only—not proof that a human will be notified.

## API unavailable

1. Confirm `https://<host>/api/health/live` and `/api/health/ready` independently.
2. Inspect `docker compose ... ps` and bounded logs for `caddy`, `api`, `migrate`, and `postgres`; do not paste secrets or user payloads into tickets.
3. If the current release caused the outage, run the rollback procedure.
4. If PostgreSQL is unhealthy, preserve the volume and logs; do not recreate or delete it. Escalate to the database recovery procedure.
5. Record detection, acknowledgement, mitigation, recovery UTC timestamps, request ID samples, and release IDs.

## High server error rate

1. Use the dashboard to correlate the 5xx ratio with request rate and the deployment timestamp.
2. Query structured logs by opaque request ID and route template; never by learner profile values.
3. Roll back if errors began with the current release and the previous release is schema-compatible.
4. If errors predate deployment, preserve evidence and isolate the failing dependency before restarting anything.

## High latency

1. Compare p95 latency with request rate, container resource use, PostgreSQL health, and worker backlog.
2. Check for CPU throttling or memory pressure before changing limits.
3. Stop load generation if it risks data integrity. Roll back a release-correlated regression.
4. Do not scale beyond the reviewed OCI budget or Terraform limits without a new plan and approval.

## Required evidence and sign-off

For the M1 gate, store a redacted evidence note under `docs/delivery/validation` containing:

- successful protected CI URL and commit;
- reviewed Terraform plan summary and explicit apply approval;
- OCI resource IDs/region without credentials;
- release ID and API/web image digests;
- managed OIDC login/logout/expiry results;
- backup upload, isolated restore, checksum, and measured duration;
- rollback release IDs and recovery duration;
- dashboard screenshots or query results and a delivered test notification;
- Engineering, Security/Privacy, and Operations decisions, reviewed versions, UTC dates, and opaque private evidence references. Actual approver identities and authenticated approvals may be held in a restricted register rather than published.

Use the [staging evidence record](../delivery/validation/m1-staging-evidence.md) for redacted results, including PostgreSQL worker concurrency and off-host restoration. No live drill is marked passed before it is observed.

The milestone remains `NOT YET PASSED` until every item is observed in the real staging environment.
