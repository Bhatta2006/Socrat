# Documentation index

## Product

- [V1 product requirements](product/v1-product-requirements.md) — complete product and delivery contract
- [Domain glossary](product/domain-glossary.md) — normative vocabulary
- [Goal templates](product/goal-templates.md) — Foundations, Interview, and Competitive goal contracts
- [Deterministic policy matrices](product/deterministic-policy-matrices.md) — routing, selection, help, mastery, and fallback authority
- [Metric contract](product/metric-contract.md) — outcome, funnel, quality, and guardrail definitions
- [Content standard](product/content-standard.md) — concept/exercise/assessment authoring and release bar

## Research

- [M0 concierge pilot](research/concierge-pilot.md) — recruitment, protocol, observations, and pass criteria
- [M0 pilot plan](research/m0-pilot-plan.md) — confirmed arrangements, recruitment targets, session checklist, and closeout
- [Private review record](research/m0-private-review-record-template.md) — approval evidence with identities outside the repository
- [Recruitment and consent template](research/pilot-recruitment-and-consent.md) — must be completed and privacy-approved before use
- [Session record template](research/pilot-session-record-template.md) — copy outside the repository for each participant
- [Pilot synthesis template](research/pilot-synthesis-template.md) — redacted aggregate evidence and decision
- [`prototypes/concierge`](../prototypes/concierge/) — disposable interactive M0 prototype; not production architecture

Pilot evidence containing personal data must not be committed here. Store only approved redacted synthesis and opaque participant IDs.

## Architecture

- [Dependency assessment](architecture/dependency-assessment.md) — adopt/conditional/reject decisions for candidate repositories
- [API conventions](architecture/api-conventions.md) — versioning, auth, errors, transactions, telemetry, and migrations
- [OCI staging cost plan](architecture/oci-staging-cost-plan.md) — Hyderabad free-first topology, USD 55 ceiling, and production evolution
- [M1 foundation research](research/m1-foundation-research.md) — primary-source research and unresolved vendor decisions
- [Architecture decision records](architecture/adr/) — numbered, immutable decision history

Current ADRs:

- [ADR-0001: Modular monolith](architecture/adr/0001-modular-monolith.md)
- [ADR-0002: Deterministic authority with bounded AI](architecture/adr/0002-deterministic-authority-bounded-ai.md)
- [ADR-0003: Versioned skill-pack contract](architecture/adr/0003-versioned-skill-pack-contract.md)
- [ADR-0004: Append-only evidence and replay](architecture/adr/0004-append-only-evidence-and-replay.md)
- [ADR-0005: Isolated code-execution plane](architecture/adr/0005-isolated-code-execution-plane.md)
- [ADR-0006: Managed services and data boundaries](architecture/adr/0006-managed-services-and-data-boundaries.md)

## Security

- [V1 threat model](security/threat-model.md) — assets, trust boundaries, risk register, and verification program

## Operations

- [M1 staging runbook](operations/m1-staging-runbook.md) — immutable deploy, backup/restore, rollback, telemetry access, and incident response
- [M1 account setup](operations/m1-account-setup.md) — confirmed hostname/account inputs and pending identity, DNS, and access configuration
- [M2 content authoring](operations/m2-content-authoring.md) — schema validation, editorial API, publication, quarantine, and rollback
- [`infra/runtime/staging`](../infra/runtime/staging/) — executable private-staging runtime contract

## Delivery

- [M0 index](delivery/milestones/m0-index.md)
- [M0 gate](delivery/milestones/m0-gate.md)
- [M0 validation report](delivery/validation/m0-validation-report.md)
- [M1 index](delivery/milestones/m1-index.md)
- [M1 gate](delivery/milestones/m1-gate.md)
- [M1 local validation report](delivery/validation/m1-validation-report.md)
- [M1 staging evidence record](delivery/validation/m1-staging-evidence.md) — live drills and private sign-off references; not yet exercised
- [M2 index](delivery/milestones/m2-index.md)
- [M2 gate](delivery/milestones/m2-gate.md)
- [M2 validation report](delivery/validation/m2-validation-report.md)
- [M3 index](delivery/milestones/m3-index.md)
- [M3 gate](delivery/milestones/m3-gate.md)
- [M3 validation report](delivery/validation/m3-validation-report.md)
- [M3 onboarding operations](operations/m3-onboarding.md)
- [M4 diagnostic and evidence operations](operations/m4-diagnostics.md)
- [M4 implementation plan](delivery/milestones/m4-index.md)
- [M4 gate](delivery/milestones/m4-gate.md)
- [M4 validation report](delivery/validation/m4-validation-report.md)

- [M5 deterministic planner](delivery/milestones/m5-index.md)
- [M5 gate](delivery/milestones/m5-gate.md)
- [M5 validation](delivery/validation/m5-validation-report.md)
- [M5 planning operations](operations/m5-planning.md)

- [M6 execution platform](delivery/milestones/m6-index.md)
- [M6 gate](delivery/milestones/m6-gate.md)
- [M6 validation](delivery/validation/m6-validation-report.md)
- [M6 execution operations](operations/m6-execution.md)
- [Execution threat model](security/execution-threat-model.md)

- [M7 learning-session implementation](delivery/milestones/m7-index.md)
- [M7 gate](delivery/milestones/m7-gate.md)
- [M7 initial validation](delivery/validation/m7-validation-report.md)
- [M7 learning-session operations](operations/m7-learning-sessions.md)
- [M7 session content authoring](operations/m7-content-authoring.md)

## Machine-readable contracts

- [`contracts/product/m5-planning-policy.json`](../contracts/product/m5-planning-policy.json)
- [`contracts/schemas/planning-command.schema.json`](../contracts/schemas/planning-command.schema.json)
- [`contracts/schemas/learning-session-start.schema.json`](../contracts/schemas/learning-session-start.schema.json)
- [`contracts/schemas/learning-session-command.schema.json`](../contracts/schemas/learning-session-command.schema.json)

Machine contracts live outside `docs` so CI and application tooling can consume them directly:

- [`contracts/product/m0-contracts.json`](../contracts/product/m0-contracts.json)
- [`contracts/schemas/m0-contracts.schema.json`](../contracts/schemas/m0-contracts.schema.json)
- [`contracts/schemas/skill-pack.schema.json`](../contracts/schemas/skill-pack.schema.json)
- [`contracts/schemas/learning-evidence.schema.json`](../contracts/schemas/learning-evidence.schema.json)
- [`contracts/product/m4-learning-policies.json`](../contracts/product/m4-learning-policies.json)

## Documentation rules

- Use lower-case kebab-case file names except conventional root files.
- Put documents by durable ownership/domain, not by temporary sprint or milestone folder.
- Milestone files belong under `delivery/milestones`; product/security/architecture artifacts remain in their domain folders.
- ADRs are numbered. Accepted ADRs are not rewritten to hide history; supersede them with a new ADR.
- Normative thresholds/enums also live in machine-readable contracts and are tested for drift.
- Never commit secrets, direct participant identifiers, raw production exports, or unredacted provider payloads.
