# M1 — Platform foundation

**Status:** IN PROGRESS  
**Scope:** Monorepo, environments, delivery controls, identity/profile, feature flags, audit/outbox, API conventions, and base design system.

## Implemented and repository-verified

- npm/Python monorepo with locked dependencies and repeatable commands;
- Next.js TypeScript web app using a minimal monochrome daisyUI foundation;
- FastAPI modular application package with validated settings and health endpoints;
- managed-OIDC integration boundary plus fail-closed environment rules;
- hashed server-side sessions, rotation/revocation, expiry, CSRF, and origin validation;
- self-profile update and negative cross-user authorization behavior;
- atomic audit/outbox records and an idempotent worker batch;
- Alembic schema, local PostgreSQL Compose topology, and backup/restore scripts;
- security headers, request IDs, low-cardinality metrics, and feature flags defaulting off;
- CI gates for formatting, typing, tests, coverage, migrations, builds, browser journeys, dependency audits, PostgreSQL restoration, staging configuration, and infrastructure tests;
- validated OCI Terraform for a Hyderabad private-staging host, network boundary, backup bucket, and USD 55 monthly budget alerts;
- digest-pinned staging Compose runtime with file-scoped secrets, private services, Caddy TLS ingress, and bounded resources;
- private Prometheus/Grafana telemetry contract with provisioned alerts, dashboard, and operator access procedure;
- health-gated immutable release promotion, automatic recovery, explicit rollback, and Linux/Windows backup/restore tools;
- GHCR multi-architecture publishing and GitHub artifact attestations after successful `main` verification.

## Not represented as complete

- The managed identity provider has not been selected or tested.
- OCI Hyderabad and the USD 55 planning ceiling are approved; Terraform validates locally, but no cloud resources have been created.
- Hosted CI passed for pull request 11, including real PostgreSQL dump/restore and both production container builds; repository protection is being applied before merge.
- Telemetry configuration, dashboards, and alerts validate, but no external notification receiver has been approved or exercised.
- Deploy and rollback behavior is unit-tested, but cannot be operationally demonstrated until an owned hostname, managed OIDC application, OCI compartment/access, and alert recipient exist.

The authoritative decision is in [the M1 gate](m1-gate.md). Research and vendor choices are recorded in [M1 foundation research](../../research/m1-foundation-research.md).
