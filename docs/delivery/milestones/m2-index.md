# M2 — Skill-pack kernel

**Status:** Repository implementation verified; hosted PostgreSQL, staging, and human gate pending.

**Started:** 2026-10-02

**Authority:** Owner explicitly directed moving to M2 while deferring remaining M1 work. M0 and M1 gates remain unpassed.

## Scope

Domain-neutral declarative packs, prerequisite graphs, versioning, language adapters, import/review/publish/quarantine administration, immutable releases, and bad-content rollback. Onboarding, learner-state updates, planning, code execution, and AI remain later milestones.

## Deliverables

| Artifact | Purpose |
|---|---|
| [Schema](../../../contracts/schemas/skill-pack.schema.json) | Machine-readable authoring contract exported from the typed model |
| [Typed kernel](../../../services/api/src/socrat/skillpacks/schema.py) | Semantic validation, deterministic graph ordering, coverage, and digest |
| [Editorial service](../../../services/api/src/socrat/skillpacks/service.py) | Transactional import/review/publish/quarantine/rollback |
| [Editorial API](../../../services/api/src/socrat/skillpacks/routes.py) | Explicit admin authorization and protected content boundary |
| [Fixtures](../../../contracts/fixtures/skill-packs/) | DSA versions plus a non-DSA writing pack, all synthetic and excluded from the public catalogue |
| [Authoring instructions](../../operations/m2-content-authoring.md) | Offline validation, authenticated administration, and recovery |
| [Migration](../../../services/api/migrations/versions/0002_skill_pack_kernel.py) | Additive pack, pointer, review tables and database immutability controls |
| [Acceptance suite](../../../services/api/tests/test_skill_packs.py) | Contract, authorization, lifecycle, immutability, and rollback checks |
| [PostgreSQL rehearsal](../../../services/api/tests/test_skill_packs_postgres.py) | Real database release locking and concurrent outbox delivery in CI |
| [M2 gate](m2-gate.md) | Explicit exit evidence and remaining work |
| [Validation report](../validation/m2-validation-report.md) | Local acceptance results and explicit environment limits |

## Boundaries

Pack source is data. The kernel never runs starter code, solutions, arbitrary plugins, or model output. Runtime verification belongs to M6; actual launch content needs the content standard's evidence and human reviews. Reviewed metadata and language attestations are not a claim of actual runtime execution.

Corrections create new versions. All imported source payloads are immutable, including drafts; review state and active pointers are stored separately. Old versions remain available to authorized editors for replay. Quarantined/retired versions cannot be activated. Public catalogue responses omit assessment items, solutions, tests, and private review data.
