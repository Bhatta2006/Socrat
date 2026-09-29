# ADR-0003: Use a versioned, domain-neutral skill-pack contract

- **Status:** Proposed
- **Date:** 2026-09-29
- **Decision owners:** Engineering, Learning Design, Product
- **Review by:** M0 gate

## Context

DSA is the only V1 course content, but the company vision includes many courses and skills. Hard-coding DSA entities and rules into the platform would make every new domain a rewrite. An over-generalized plugin runtime would add risk before a second domain is proven.

## Decision

Define a declarative, versioned skill pack containing:

- metadata and supported evidence/tool modalities;
- concepts and observable competency contracts;
- prerequisite DAG and track/goal overlays;
- content and exercise metadata with language/tool variants;
- diagnostic and assessment blueprints;
- deterministic policy configuration within platform-supported rule primitives;
- coverage, rights, review, release, quarantine, and migration metadata.

Skill packs are data/configuration, never arbitrary executable server code. Published versions are immutable. The platform loads DSA plus a tiny non-DSA fixture in M2 to prove absence of DSA-specific branches; the fixture is not launch content.

## Consequences

- Future domains can reuse goal, evidence, planning, assessment, and analytics systems.
- V1 must separate concept intent from Python/C++/Java implementations.
- Platform primitives may need deliberate extension for a truly new evidence modality.
- Validation, compatibility, and migration tooling are required before content scale.

## Rejected alternatives

- DSA-specific schema: fastest prototype, but contradicts the declared product boundary.
- Arbitrary code plugins: flexible but creates supply-chain, isolation, and upgrade risk.
- Build multiple launch domains now: dilutes content quality and V1 hypothesis testing.

## Verification

- Schema/DAG validation rejects cycles, missing IDs, invalid overlays, or unsupported modalities.
- DSA and non-DSA fixture import through the same path without conditional application code.
- A prior published pack can be loaded and decisions replayed after a newer version exists.

