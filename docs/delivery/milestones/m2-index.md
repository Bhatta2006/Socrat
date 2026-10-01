# M2 — Skill-pack kernel

**Status:** IN PROGRESS
**Started:** 2026-09-30
**Normative parent:** [V1 product requirements](../../product/v1-product-requirements.md), especially §§11, 26, 30, and 34; [content standard](../../product/content-standard.md); [ADR-0003](../../architecture/adr/0003-versioned-skill-pack-contract.md).

## Scope

- Domain-neutral, versioned manifest for goals, concepts, prerequisite edges, language adapters, content metadata, assessment blueprints, mastery policy, and track overlays.
- Validated import and review; role-separated publish and urgent quarantine/rollback controls.
- A sample DSA pack and a tiny non-DSA test fixture through the same import path.
- Released content remains immutable and can be loaded by pinned version; unreleased or quarantined artifacts are not eligible for learner selection.

M2 establishes the authoring and runtime contract. Full DSA content, reference-solution execution, calibrated assessments, and learner routing belong to later milestones. Sample content stays draft until it passes the full content standard.

See [the M2 gate](m2-gate.md) for evidence and remaining work.
The [M2 closeout handoff](m2-closeout.md) states the exact product-owner inputs and staging rehearsal.

## Implemented locally

- Importable [draft DSA sample](../../../contracts/skill-packs/dsa-sample.json) and [non-DSA fixture](../../../contracts/skill-packs/non-dsa-fixture.json), validated against the same [JSON Schema](../../../contracts/schemas/skill-pack.schema.json).
- Versioned database records with an active-release constraint, review sign-offs, immutable manifest hashes, item and pack quarantine records, and transactional audit/outbox events.
- Operator endpoints for import, inspection, review, publish, and quarantine, plus a public published-pack catalogue and pinned-version metadata reads.
- Runtime loader that verifies the digest and omits quarantined and assessment items from general content selection.
- Track/language eligibility loader that returns only explicitly released cells and filters content to that track and language.
- Recorded active-release history for deterministic rollback, with an additive `0003` migration that preserves existing M2 versions.
- Role-aware internal operator screen at `/admin/skill-packs` for import, inspection, review, publication, and quarantine.
- Draft [DSA resource hub](../../product/dsa-resource-hub.md) indexing all eight nominated sources as metadata and links, with canonical problem IDs, source references, provisional topic/difficulty labels, historical company signals, and a policy-bounded selector contract. Every imported record remains review-required.

The operator workflow is in the [M2 content guide](../../operations/m2-content-admin.md). Local checks and remaining gate work are in [M2 validation](../validation/m2-validation-report.md).
