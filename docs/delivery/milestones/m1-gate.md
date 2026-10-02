# M1 gate — Platform foundation

**Decision:** NOT YET PASSED  
**Reason:** The local vertical slice is implemented and verified, but the milestone explicitly requires a real IaC-created staging environment and operational evidence.

## Closeout work — 2026-10-02

The staging API previously joined only the externally isolated backend network, which would block managed OIDC discovery/token exchange. It now also joins a dedicated outbound bridge, with no API host port published and no other internal service attached to that bridge. Static staging and release tests pass; real provider connectivity and Docker runtime proof remain pending. This bridge is not a destination allow-list and needs Security review with the chosen provider.

Live evidence and private approver references will be recorded in the [staging evidence record](../validation/m1-staging-evidence.md). No OCI provisioning, deployment, OIDC exercise, off-host restoration, notification delivery, or rollback has been performed in this session.

The owner confirmed an OCI account with Hyderabad home region, supplied `socrat.dathcodes.dev`, approved `sathishdutt0@gmail.com` for operational/spending alerts, and confirmed private role reviews. Google sign-in is selected, but its application and credentials are not configured. DNS control, OCI entitlement/access, actual resource creation, and delivered alerts remain unverified. The [account setup checklist](../../operations/m1-account-setup.md) records the next steps.

On 2 October 2026, the owner explicitly deferred remaining M1 work and authorized moving to M2 repository engineering. M1 remains NOT YET PASSED; no operational gate was waived or falsely completed.

| Exit criterion | Evidence | Result |
|---|---|---|
| Monorepo and reproducible local foundation | Locked Python/npm dependencies, Compose topology, web/API/worker sources | Pass locally |
| Authentication and object authorization | API acceptance suite plus desktop/mobile browser journey | Pass locally with development identity; managed OIDC integration pending |
| Audit and durable outbox | Transaction/rollback/idempotency acceptance tests | Pass locally; PostgreSQL concurrency rehearsal pending |
| Backup and restore | SQLite acceptance test plus PostgreSQL 17 dump/isolated restore in hosted CI | Partial — staging off-host upload/download restore still pending |
| CI quality gates | [Protected-main run 36601938034](https://github.com/Bhatta2006/Socrat/actions/runs/36601938034) on commit `b69ec31` passed secret scan, format, types, 85%+ coverage, migration, PostgreSQL restore, production builds, E2E, audits, staging validators, Terraform tests, and attested image publication | Pass — `main` requires up-to-date `secret-scan` and `verify` checks through pull requests |
| Staging from infrastructure as code | OCI Hyderabad stack formats and validates locally with provider 9.7.1 | Partial — no plan/apply or created staging resources; account access intentionally absent |
| Deploy and rollback demonstrated | Health-gated release controller and rollback tests; attested GHCR API digest `sha256:555568e1…65158` and web digest `sha256:c4621bee…ad01` | Partial — real staging drill pending |
| Telemetry visible and actionable | Private Prometheus/Grafana configuration, dashboard, three alert rules, and runbook validate in hosted CI | Partial — real data and delivered notification test pending |
| Human M0 obligations retained | M0 gate remains `NOT YET PASSED` | Pass — no false completion |

## Inputs needed to finish the gate

1. Confirm the account is a persistent OCI tenancy and create a dedicated staging compartment in the Hyderabad home region.
2. Provide an owned staging hostname (the final company name is not required), then approve managed identity and the alert-notification route after security/privacy review.
3. Provide workload-identity access to the staging compartment through the protected CI environment.
4. Run the Terraform plan/apply, deployment, OIDC, PostgreSQL backup/restore, telemetry, and rollback drills; attach timestamps and immutable release IDs.
5. Obtain accountable Engineering, Security/Privacy, and Operations sign-off. Actual identities and authentic decisions may stay in restricted storage; record role, reviewed version, date, decision, and opaque evidence reference here. No approval is inferred from a private-name preference.

Local test success is necessary evidence, not a substitute for these operational gates.
