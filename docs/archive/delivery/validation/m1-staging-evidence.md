# M1 staging evidence record

**Status:** Not exercised; M1 remains NOT YET PASSED.

Fill this record with observed staging results only. A configuration check or mocked test is not a completed live drill. Keep credentials, raw learner data, reviewer names, signed approvals, sensitive account details, and full Terraform plans in restricted storage. Repository entries contain redacted summaries and opaque private evidence references.

## External inputs

| Input | Current evidence |
|---|---|
| OCI account and Hyderabad home region | Owner confirmed on 2026-10-02; entitlement, persistence, and authenticated access still need verification |
| Dedicated staging compartment and approved workload access | Not provided |
| Owned staging hostname and DNS control | Owner supplied `socrat.dathcodes.dev`; read-only lookup on 2026-10-02 found a Vercel CNAME. DNS administration and existing use remain unverified; no change made |
| Managed OIDC issuer/application | Owner chose Google on 2026-10-02; provider review, application, credentials, and integration still pending |
| Approved operational and spending-alert route | Owner approved `sathishdutt0@gmail.com`; routing configuration and delivered tests remain pending |
| Protected deployment environment and authenticated release access | Not verified in this session |

## Infrastructure and release

Record exact protected CI URL/commit, reviewed plan reference, explicit apply approval, region/resource references, cloud-init completion, DNS/TLS proof, release ID, API/web digests, and release activation timestamps. The hostname and approved identity-provider callback must match the deployed origin.

**Result:** Not run.

## Managed identity and authorization

Record actual OIDC sign-in, state/nonce/PKCE behavior, profile persistence, logout/session revocation, expiry, CSRF/origin denial, and a second-user authorization test. Check outbound discovery/token/signing-key connectivity from the API. Confirm development login is disabled and identity failure does not create a session.

**Result:** Not run.

## PostgreSQL audit and outbox concurrency

Exercise concurrent worker batches against the deployed PostgreSQL database with synthetic events. Verify committed events are delivered once, rolled-back events are never delivered, and no event is lost. Attach event counts, worker results, version, and redacted evidence reference.

**Result:** Not run.

## Off-host backup and restoration

Record encrypted archive creation, checksum/size, private OCI bucket upload, retrieval into a separate location, checksum verification, decryption, isolated restoration, schema/data verification, and cleanup. Record start/end timestamps and measured recovery duration. Confirm the backup retention/encryption/key-access arrangements. A same-host dump/restore alone does not pass this gate.

**Result:** Not run.

## Deployment and rollback

Record successful promotion of a digest-pinned release and rollback to an actual previous compatible release. Verify HTTPS readiness and application behavior after both operations. Record release IDs, schema compatibility, timestamps, and recovery duration. Do not invent a prior release for a first deployment.

**Result:** Not run.

## Telemetry and delivered notification

Record actual dashboard/query results for requests, 5xx errors, and latency. Configure an approved notification route, trigger a controlled test, and confirm receipt and acknowledgement by the responsible person. Record the alert/receipt timestamps and private evidence reference. Alert rules alone do not show notification delivery.

**Result:** Not run.

## Private sign-off

The owner confirmed on 2026-10-02 that Engineering, Security/Privacy, and Operations reviews will happen privately. No completed decision or approval has been supplied.

Keep actual approver identities, responsibility, reviewed versions, authentic decisions, findings, and signed evidence in a restricted register. Publish only these fields:

| Role | Private record reference | Reviewed version | Decision | Date |
|---|---|---|---|---|
| Engineering | Not supplied | Not supplied | Pending | Not recorded |
| Security/Privacy | Not supplied | Not supplied | Pending | Not recorded |
| Operations | Not supplied | Not supplied | Pending | Not recorded |

## Gate decision

M1 stays NOT YET PASSED until every operational requirement and approval in the [M1 gate](../milestones/m1-gate.md) is evidenced. The unpassed M0 learner and approval obligations remain in force.
