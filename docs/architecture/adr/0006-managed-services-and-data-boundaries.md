# ADR-0006: Prefer managed infrastructure while retaining portable domain contracts

- **Status:** Proposed
- **Date:** 2026-09-29
- **Decision owners:** Engineering, Security/Privacy, Finance
- **Review by:** M0 gate; vendor selection by M1

## Context

A small team must deliver a reliable beta without becoming a database, identity, queue, analytics, and observability operations company. At the same time, learning evidence and policy behavior must remain portable and auditable, and vendors must not receive unrestricted personal/code data.

## Decision

Prefer managed PostgreSQL, object storage, identity, durable queue, secrets, email, observability, and product analytics when they satisfy region, DPA, deletion, export, security, reliability, and cost requirements. Keep authoritative domain models, event schemas, policy configuration, and skill packs under Socrat control.

Use provider adapters and explicit data-minimization contracts at LLM, analytics, notification, identity, and object-storage boundaries. Do not build a generic abstraction for hypothetical portability; isolate only capabilities with material switching/privacy risk.

Final vendors and regions are a separate M1 procurement/security decision. Conditional open-source projects in `dependency-assessment.md` are not automatically authorized.

## Consequences

- Faster delivery and less undifferentiated operational work.
- Vendor outage, price, region, and contractual risks require fallbacks/exit plans.
- Self-hosting remains justified for the code-execution plane and where privacy/security needs demand it.
- Data inventory and provider deletion/export tests are required.

## Rejected alternatives

- Self-host everything: exceeds V1 operational capacity and does not inherently improve security.
- Single backend platform controlling identity, database, business rules, and functions: weakens domain/replay boundaries and increases concentrated lock-in.
- Abstract every dependency: creates unused layers and hides real provider behavior.

## Verification

- Vendor scorecard records region, subprocessors, DPA, retention, deletion, SLO, export, cost, and exit process.
- Sensitive payload tests prove analytics/observability/LLM receive only allow-listed fields.
- Restore/export/delete and provider-outage exercises pass before launch.

