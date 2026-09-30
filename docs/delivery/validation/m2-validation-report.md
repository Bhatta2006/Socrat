# M2 local validation report

**Date:** 2026-09-30
**Kernel result:** PASS locally
**M2 milestone result:** IN PROGRESS — human content release and coverage verification remain

## Verified

| Check | Result |
|---|---|
| API and operations suite | 60 passed; 88.33% statement coverage |
| Python lint and types | Ruff and mypy passed |
| M0 regression | 13 prototype tests and 134 document/contract checks passed |
| M2 fixture import | Draft DSA and tiny non-DSA manifests validated and imported through one endpoint |
| Release controls | Role and CSRF checks, assessment-blueprint review, immutable digest, pinned prior version, one active version per pack |
| Quarantine | Item filtered from runtime load; rollback follows recorded release history rather than semantic-version order; reason/audit records verified |
| Graph and coverage contract | Transitive prerequisite closure, required/optional overlap, evidence-mode compatibility, explicit track/language cells, release-evidence requirement, and removed-concept mapping covered by tests |
| Migration | Existing `0002` skill-pack row preserved through additive `0003` release-history migration in SQLite |
| Web | TypeScript typecheck and optimized production build passed; build contains `/` and `/admin/skill-packs` routes |
| Operator screen | Role-aware import/inspect/review/publish/quarantine UI; desktop/mobile browser checks cover mocked API errors and controls plus a real API/database journey with separate test accounts |
| Browser regression | Previously 12 desktop/mobile checks passed across operator controls and the existing account journey; after the contract update, the real API/database operator journey passed again on desktop and mobile (2 checks) |
| DSA resource hub | All eight nominated sources indexed: 5,779 unique metadata records, 3,792 canonical LeetCode/CSES problem links, 37,714 historical company signals; 41-topic difficulty matrix and query command generated |
| Candidate selection contract | Tests cover rights/release and topic gates, language, prerequisite, exposure, time and difficulty filters; learner performance and company preference affect only eligible ranking; stale or invented LLM IDs fall back to deterministic baseline |

The API and integrated browser tests use migrated SQLite databases. Hosted PostgreSQL workflow and rollback, managed OIDC, and a real staging release still require later work. The integrated browser fixture uses synthetic evidence references and publishes/quarantines only isolated test content; it is not a human content approval. Both checked-in packs remain draft and no learner content is published.

The [resource hub](../../product/dsa-resource-hub.md) is also draft. All 5,779 imported records are `review_required`; 1,208 have no reliable topic and 1,625 have no difficulty band, mainly among source-only references. All 3,792 canonical problem links have a provisional difficulty band; 108 still need topic review and 211 are out of scope. Provider labels and category/week priors are provisional. No external item was counted as a curated internal practice or sequestered assessment item. The pool is not yet wired to learner accounts or daily plans.
