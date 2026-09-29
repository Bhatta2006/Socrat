# Socrat M0 — Product proof and specifications

**Milestone:** M0  
**Status:** In progress  
**Started:** 2026-09-29  
**Target duration:** Two weeks  
**Normative parent:** [V1 product requirements](../../product/v1-product-requirements.md)

M0 converts the V1 PRD into contracts that product, engineering, learning design, security, and operations can implement without inventing product behavior. Documents in this directory are normative for M1 unless a later architecture decision record explicitly supersedes them.

## Deliverables

| Artifact | Purpose | State |
|---|---|---|
| [M0 gate](m0-gate.md) | Evidence-based entry and exit decision | In progress |
| [Concierge pilot](../../research/concierge-pilot.md) | Fifteen-person validation protocol | Ready to recruit |
| [Concierge prototype](../../../prototypes/concierge/) | Goal → routing → diagnostic → plan → help → evidence → recovery walkthrough | Built; automated and browser golden-path checks passing |
| [Domain glossary](../../product/domain-glossary.md) | Shared product and learning vocabulary | Candidate |
| [Goal templates](../../product/goal-templates.md) | Exact contracts for the three launch goals | Candidate |
| [Policy matrices](../../product/deterministic-policy-matrices.md) | Deterministic routing, planning, help, and fallback rules | Candidate |
| [Metric contract](../../product/metric-contract.md) | Frozen definitions and analysis boundaries | Candidate |
| [Threat model](../../security/threat-model.md) | Assets, trust boundaries, threats, controls, and verification | Candidate |
| [Content standard](../../product/content-standard.md) | Authoring, review, release, and quarantine requirements | Candidate |
| [Architecture decisions](../../architecture/adr/) | Binding technical boundaries | Candidate |
| [Machine contract](../../../contracts/product/m0-contracts.json) | Testable product constants and policies | Candidate |
| [M0 contract tests](../../../scripts/validation/test-m0-contracts.ps1) | Automated structural and consistency checks | 116/116 passing |
| [Validation report](../validation/m0-validation-report.md) | Reproducible automated and browser evidence | Passing; human gates excluded |

## Authority order

When two artifacts conflict, resolve them in this order:

1. A formally accepted, newer ADR.
2. The machine-readable M0 contract for exact enums, thresholds, and invariants.
3. The M0 policy and goal documents.
4. The V1 PRD.
5. Informative examples and prototypes.

Conflicts are release blockers. Do not silently choose one interpretation.

## Change control

- Every material change must include an owner, reason, effective version, affected metrics/events, migration impact, and rollback approach.
- Changes to goal meaning, mastery, assessment separation, content release, privacy, or sandbox boundaries require Product, Engineering, and Learning Design approval; Security/Privacy also approves changes affecting its boundary.
- Candidate contracts become `approved` only after the M0 gate is signed.
- Pilot evidence is append-only. Corrections add a new entry and preserve the original.

## External reference baseline

M0 uses these sources as design inputs, not as claims of certification:

- [NIST Secure Software Development Framework 1.1](https://csrc.nist.gov/pubs/sp/800/218/final)
- [OWASP Threat Modeling Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [NIST Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- [WCAG 2.2 Recommendation](https://www.w3.org/TR/WCAG22/)
- [ACM/IEEE-CS/AAAI CS2023](https://csed.acm.org/), especially Algorithmic Foundations and Software Development Fundamentals

## What “M0 complete” means

M0 is complete only when the gate in `m0-gate.md` is fully evidenced. Authored documents alone do not pass the milestone. In particular, at least five representative learners in each launch track must complete the prototype flow, material findings must be adjudicated, and accountable humans must sign the frozen scope, metrics, risks, and architecture decisions.
