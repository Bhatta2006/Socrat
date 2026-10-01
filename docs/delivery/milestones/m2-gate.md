# M2 gate — Skill-pack kernel

**Decision:** IN PROGRESS

| Exit criterion | Required evidence | Result |
|---|---|---|
| Domain-neutral schema and DAG | Invalid IDs, cycles, overlays, modalities, and references rejected | Pass locally — strict Pydantic/JSON Schema; tests cover transitive prerequisite closure, overlay overlap, and concept/evidence-mode consistency |
| Import and review | DSA and a tiny non-DSA fixture use one path; approval roles are distinct | Pass locally — both draft fixtures imported; author and reviewer roles separated; operator browser journey uses separate named test accounts against the real API and migrated SQLite database |
| Immutable publishing | Published content hash/version never changes; pinned old versions still load | Pass locally — digest checked on load; version keys unique; prior version replay tested |
| Quarantine and rollback | Bad content immediately excluded; prior good release can be reactivated with audit trail | Pass in local checks and an [isolated PostgreSQL CI rehearsal](https://github.com/Bhatta2006/Socrat/actions/runs/36827298106) — item exclusion, rollback through the recorded active-release chain, audit/outbox delivery; no learner evidence yet to repair |
| Language/track coverage | Explicit unavailable variants and released coverage; no runtime translation | Contract implemented locally — version-2 manifests declare each track/language cell as draft, released, or unavailable; candidate drafts and unexplained unavailable cells are rejected. The checked-in DSA coverage remains draft. Runtime execution belongs to M6. |
| Human release bar | Required reviews and evidence references for any released candidate | Contract implemented locally — role separation and immutable evidence references are required for candidates; no human-reviewed DSA content or staging canary is claimed. The sample DSA pack remains draft. |

M1's deferred staging checks and M0's learner-pilot/sign-off checks remain tracked in their own gates. M2 code may proceed under the product-owner progression decision without treating those checks as passed.

See [M2 local validation](../validation/m2-validation-report.md) and the [content operator guide](../../operations/m2-content-admin.md). Both sample manifests deliberately remain `draft`; neither is available to learners.

The [DSA resource hub](../../product/dsa-resource-hub.md) is a draft candidate index for editorial work. Its external problem links and solution references do not satisfy released content, language coverage, or assessment evidence.

## Remaining M2 work

1. Exercise the release and rollback workflow against PostgreSQL in staging with real operator identities, including audit/outbox delivery and an actual bad-content canary. The local browser journey and isolated PostgreSQL CI rehearsal do not establish this operational result. The product owner has chosen to integrate staging at the end of the current repository work.
2. Have independent named operators inspect real evidence artifacts and demonstrate the review decision path in staging. Evidence references and API sign-offs alone are not human approval. Use isolated test content for the M2 kernel rehearsal; neither checked-in draft is learner eligible.

The [PRD M2 exit gate](../../product/v1-product-requirements.md#363-milestone-plan-and-exit-gates) calls for a sample DSA pack and tiny non-DSA fixture loading, schema/DAG checks, immutable publishing, and bad-content rollback. A full released DSA curriculum, reference-solution execution, and calibrated assessments are later milestones. Do not hold M2 open for those later deliverables or claim they are complete now. See the [closeout handoff](m2-closeout.md).
