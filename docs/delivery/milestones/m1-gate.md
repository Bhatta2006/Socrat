# M1 gate — Platform foundation

**Decision:** NOT YET PASSED  
**Reason:** The local vertical slice is implemented and verified, but the milestone explicitly requires a real IaC-created staging environment and operational evidence.

| Exit criterion | Evidence | Result |
|---|---|---|
| Monorepo and reproducible local foundation | Locked Python/npm dependencies, Compose topology, web/API/worker sources | Pass locally |
| Authentication and object authorization | API acceptance suite plus desktop/mobile browser journey | Pass locally with development identity; managed OIDC integration pending |
| Audit and durable outbox | Transaction/rollback/idempotency acceptance tests | Pass locally; PostgreSQL concurrency rehearsal pending |
| Backup and restore | SQLite isolated backup/restore acceptance test; PostgreSQL smoke scripts authored | Partial — managed/staging PostgreSQL exercise pending |
| CI quality gates | Workflow includes format, types, coverage, migration, builds, E2E, and dependency audits | Authored, not executed by a hosted protected repository |
| Staging from infrastructure as code | OCI Hyderabad stack formats and validates locally with provider 9.7.1 | Partial — no plan/apply or created staging resources; account access intentionally absent |
| Deploy and rollback demonstrated | Requires staging and immutable registry | Pending |
| Telemetry visible and actionable | Private Prometheus endpoint and structured safe logs implemented | Partial — backend, dashboards, alerts, and access controls pending |
| Human M0 obligations retained | M0 gate remains `NOT YET PASSED` | Pass — no false completion |

## Inputs needed to finish the gate

1. Confirm the account is a persistent OCI tenancy and create a dedicated staging compartment in the Hyderabad home region.
2. Purchase the final domain, then approve managed identity, secret-store, registry, and observability services after security/privacy review.
3. Provide workload-identity access to the staging compartment through the protected CI environment.
4. Run the Terraform plan/apply, deployment, OIDC, PostgreSQL backup/restore, telemetry, and rollback drills; attach timestamps and immutable release IDs.
5. Obtain named Engineering, Security/Privacy, and Operations sign-off.

Local test success is necessary evidence, not a substitute for these operational gates.
