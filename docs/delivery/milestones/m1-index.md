# M1 — Platform foundation

**Status:** IN PROGRESS  
**Scope:** Monorepo, environments, delivery controls, identity/profile, feature flags, audit/outbox, API conventions, and base design system.

## Implemented locally

- npm/Python monorepo with locked dependencies and repeatable commands;
- Next.js TypeScript web app using a minimal monochrome daisyUI foundation;
- FastAPI modular application package with validated settings and health endpoints;
- managed-OIDC integration boundary plus fail-closed environment rules;
- hashed server-side sessions, rotation/revocation, expiry, CSRF, and origin validation;
- self-profile update and negative cross-user authorization behavior;
- atomic audit/outbox records and an idempotent worker batch;
- Alembic schema, local PostgreSQL Compose topology, and backup/restore scripts;
- security headers, request IDs, low-cardinality metrics, and feature flags defaulting off;
- CI definition for formatting, typing, tests, coverage, migrations, build, browser journeys, and dependency audits.
- validated OCI Terraform for a Hyderabad private-staging host, network boundary, backup bucket, and USD 55 monthly budget alerts.

## Not represented as complete

- The managed identity provider has not been selected or tested.
- OCI Hyderabad and the USD 55 planning ceiling are approved; Terraform validates locally, but no cloud resources have been created.
- CI is authored but has not run in an actual protected repository.
- Local SQLite restore and browser checks pass; PostgreSQL container restore cannot run on this machine because Docker is unavailable.
- Telemetry is exposed locally, but no approved observability backend or alert route exists.
- Deploy, canary, and rollback cannot be demonstrated until a staging target and immutable image registry exist.

The authoritative decision is in [the M1 gate](m1-gate.md). Research and vendor choices are recorded in [M1 foundation research](../../research/m1-foundation-research.md).
