# ADR-0001: Start with a modular monolith

- **Status:** Proposed
- **Date:** 2026-09-29
- **Decision owners:** Engineering, Product
- **Review by:** M0 gate

## Context

V1 must support auth, goals, diagnostics, learner state, deterministic planning, content, practice, assessment, analytics, and bounded AI. A small team needs strong transactional consistency and fast iteration. Untrusted code execution has a fundamentally different risk and scaling boundary.

## Decision

Build the authoritative application as a modular monolith with explicit internal modules and one PostgreSQL ownership model. Deploy these processes separately from the same versioned application where operationally useful:

- web client;
- HTTP API;
- background worker;
- execution broker/control plane.

Code-execution workers are a separate security plane and are never linked into the application process. Module APIs and database ownership are enforced in code and tests; modules do not reach into each other’s tables through ad hoc queries.

Initial modules: identity/profile, goals/routing, skill packs/content, diagnostic, evidence/mastery, curriculum/planning, attempts/assessment, tutor/AI gateway, notifications, analytics/outbox, and administration.

## Consequences

- Transactions, replay, and policy versioning are simpler than in early microservices.
- Deployments remain operationally manageable for a 5–7 engineer team.
- Poor module discipline could create a large coupled application; architecture tests and ownership rules are required.
- A module may be extracted only after measured scale, isolation, reliability, or team-ownership pressure justifies it.

## Rejected alternatives

- Microservices from day one: excessive coordination, distributed failure, and observability cost before boundaries are proven.
- Backend-as-a-service as the domain core: conflicts with append-only evidence, replay, policy authority, and runner isolation.
- One process including learner code: unacceptable trust-boundary collapse.

## Verification

- M1 dependency rules prevent circular module access.
- Each module names its commands, reads, events, tables, and owner.
- Execution worker credentials and network paths cannot reach application data.

