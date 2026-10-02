# M2 gate — Skill-pack kernel

**Decision:** NOT YET PASSED

**Reason:** Repository engineering passes local checks (57 tests, 90.10% statement coverage, lint/types/Compose). Two PostgreSQL rehearsals are configured in CI but skipped locally. M1 staging was explicitly deferred, so a deployed M2 slice and real editorial reviews are not evidenced. See the [validation report](../validation/m2-validation-report.md).

| Exit requirement | Repository evidence | Remaining gate |
|---|---|---|
| Domain-neutral schema and graph | Typed schema, strict fields, reference/overlay checks, DAG ordering | Engineering/Learning Design contract review |
| DSA and tiny non-DSA fixture use identical import path | Synthetic DSA and writing fixtures plus acceptance tests | Repeat in staging; neither fixture is launch content |
| Explicit language availability | Per-exercise Python/C++/Java variants and coverage flags; missing variants never synthesized | Content/runtime verification before real content release |
| Versioning and immutable publishing | Canonical SHA-256, immutable source records, database triggers, independent review stages | PostgreSQL hosted/staging evidence and approval of schema migration |
| Import/review/publish/quarantine admin | Authenticated HTTP tools, exact issuer+subject allow-list, CSRF/origin checks, audit/outbox | Approved administrator identities and live managed-OIDC exercise |
| Bad-content rollback | Quarantine restores previous eligible release or leaves no active pack; pinned payload retained | Staging drill with release/version evidence |
| Operability | Additive migration, recovery revision checks, existing route metrics/logging | Dashboard, alerts, restore, deployment/rollback proof after resuming M1 |

## Required human evidence

Engineering and Learning Design approve the pack contract, review workflow, and version/migration behavior. Security/Privacy approves editorial roles and protected content handling. Content-specific domain, language, accessibility, assessment, and release approvals remain governed by the [content standard](../../product/content-standard.md).

Actual reviewer identities and authentic decisions may remain private. Publish role, reviewed version, decision/date, and opaque private evidence reference only. No synthetic test identity or fixture approval counts as human sign-off.

## Completion procedure

1. Run the full repository checks and PostgreSQL rehearsal; attach results to the validation report.
2. Resume the deferred M1 account/environment setup and deploy the exact verified M2 artifacts to staging.
3. Import DSA and writing fixtures through the same editor path, exercise the full lifecycle and quarantine rollback, and verify assessment secrecy and explicit language availability.
4. Rehearse migration and restore at revision `0002`; confirm any prior application selected for rollback accepts that revision. Original M1 images require `0001` and are not automatically compatible.
5. Collect private role approvals and live evidence. Only then mark this gate passed.
