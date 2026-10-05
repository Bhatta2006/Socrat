# M4 — Diagnostic and learner-state core

**Status:** Repository implementation delivered for objective diagnostic scope; external gate remains pending. The implementation sequence below records the plan and milestone boundaries.

**Prepared:** 2026-10-02, following the owner's confirmation that M3 implementation is complete. The recorded hosted/staging/content/human gates remain pending in the [M3 gate](m3-gate.md); this plan does not change their evidence status.

**Outcome:** A learner with an accepted, confirmed goal can complete a staged diagnostic and inspect per-concept placement, confidence, and evidence. The deterministic learner-state core can reproduce those decisions from immutable evidence and versioned policy, and supply state to M5 without depending on an LLM.

**Estimate:** Three engineering weeks, as specified by PRD §36.2, assuming the documented team and concurrent content/review support. This is a sequencing estimate, not a calendar commitment; real content, review, and staging readiness control the release date.

## Implemented repository increment

| Slice | Evidence |
|---|---|
| Diagnostic authoring and backward compatibility | [Strict additive pack schema](../../../services/api/src/socrat/skillpacks/schema.py), [diagnostic contracts](../../../services/api/src/socrat/diagnostics/contracts.py), exported JSON Schema and retained historical canonical payloads |
| Immutable source evidence and atomic writes | [Revision 0004](../../../services/api/migrations/versions/0004_diagnostic_evidence.py), separate raw answer artifacts, user-lock serialization and database mutation guards |
| Deterministic learner state | [Versioned policy](../../../services/api/src/socrat/learnerstate/policy.py), [pure projector](../../../services/api/src/socrat/learnerstate/projector.py), [transactional service](../../../services/api/src/socrat/learnerstate/service.py) |
| Staged controller and safe scoring boundary | [Controller](../../../services/api/src/socrat/diagnostics/service.py), [objective and verified-run adapter contract](../../../services/api/src/socrat/diagnostics/scoring.py), [owned/admin API](../../../services/api/src/socrat/diagnostics/routes.py) |
| Learner and operator UI | [Diagnostic flow](../../../apps/web/src/app/diagnostic.tsx) and [protected calibration panel](../../../apps/web/src/app/calibration.tsx) |
| Verification and operations | [Gold/property tests](../../../services/api/tests/test_learner_state.py), [PostgreSQL race rehearsal](../../../services/api/tests/test_diagnostics_postgres.py), [browser journeys](../../../tests/e2e/diagnostics.spec.ts), [operations guide](../../operations/m4-diagnostics.md), [validation report](../validation/m4-validation-report.md) |

Objective readiness is explicitly scoped. Coding-dependent full placement and qualitative grading remain gated on M6/M9; no isolated runner or AI assistance is enabled. Local synthetic results do not substitute for reviewed launch inventory or the external release gate.

## 1. Project context and existing integration points

Socrat V1 prepares Foundations, Interview, and Competitive learners in Python, C++, and Java. Its reusable engine owns eligibility, evidence, mastery, prerequisites, and planning deterministically; skill packs supply reviewed domain content and policy overlays. AI assistance is bounded and introduced later.

The normative sources are the [PRD](../../product/v1-product-requirements.md) (§8.4, §10, §18, §26, §36, §39), [policy matrices](../../product/deterministic-policy-matrices.md), [glossary](../../product/domain-glossary.md), [content standard](../../product/content-standard.md), [metric contract](../../product/metric-contract.md), [API conventions](../../architecture/api-conventions.md), and [ADR-0004](../../architecture/adr/0004-append-only-evidence-and-replay.md). ADR-0004 is still Proposed; acceptance must be recorded through the accountable architecture review.

| Existing asset | M4 use and current gap |
|---|---|
| [Confirmed goals](../../../services/api/src/socrat/onboarding/routes.py) | Use the owned `LearnerGoal` snapshot: declared/active track, first diagnostic stage, language, target, and selected pack pins. Waitlisted goals are also persisted, so a saved goal alone does not authorize diagnosis. |
| [Routing policy](../../../services/api/src/socrat/onboarding/policy.py) | Honor the initial stage and Foundations bridge; self-report selects the start, never earned capability. |
| [Skill-pack contract](../../../services/api/src/socrat/skillpacks/schema.py) | Concepts, exercises, assessment inventory, diagnostic blueprints, immutable versions, and basic mastery criteria exist. Structured response validators, diagnostic branch/stop rules, stable misconception definitions, and complete scoring policy do not. |
| [Persistence](../../../services/api/src/socrat/models.py) | Users, sessions, audit/outbox, pack releases, and goals exist. Diagnostic sessions, attempts, evidence, and learner projections do not. |
| [Outbox worker](../../../services/api/src/socrat/worker.py) | Existing worker records internal delivery receipts. It is not a mastery projector or an external analytics sink. Core state updates must not depend on that receipt. |
| [Web onboarding](../../../apps/web/src/app/onboarding.tsx) | Add a diagnostic entry action for accepted goals and an owned, resumable diagnostic/results flow. |

## 2. Scope and milestone boundaries

M4 delivers:

- Track/language-aware staged diagnostic creation, item delivery, response finalization, resume, and completion.
- Objective selected-response, structured tracing, and language-readiness items with deterministic scoring; rubric-based explanations can be collected with pending-review status.
- An append-only source evidence ledger, deterministic mastery/confidence/retention projections, controlled misconception signals, evidence reads, correction/replay tooling, and policy rollback.
- Protected calibration views and metrics segmented by track/language, with honest empty/insufficient-data states.
- Synthetic gold fixtures, real PostgreSQL concurrency/replay checks, browser journeys, migration rehearsal, and documented operational procedures.

M5 owns curricula, daily plans, workload adaptation, and recovery scheduling. M6 owns isolated Python/C++/Java execution. M7 owns the complete learning session/content experience. M8 owns AI tutoring. M9 owns the complete assessment/review workflow and operational spaced repetition; M10 expands learner dashboards and privacy workflows.

**Runner boundary:** M4 implements a versioned scoring-adapter interface and test doubles for implementation evidence. It must not run learner code in the API process. Before M6, runtime-dependent items are explicitly unavailable. A diagnostic blueprint requiring implementation evidence cannot be declared fully satisfied by trace/selection items; return a blocked or limited placement result with the missing evidence named. Partial completion cannot produce full placement or a Mastered claim. Full coding-dependent diagnostics require the M6 integration and a subsequent gate review.

**Qualitative boundary:** Free-text explanations are not graded through keyword matching or an LLM. Preserve bounded responses in restricted storage and mark them pending review; unresolved evidence cannot satisfy completion requirements or mastery gates. Ship an objective blueprint only when reviewers approve its stated placement scope.

**Content boundary:** Repository fixtures are test data. Real learner diagnosis requires reviewed launch-purpose packs, compatible diagnostic blueprints, and sufficient released inventory for the requested track/language. Missing inventory produces an explicit reason and no fabricated item.

## 3. Resolve contracts before implementation

The following are implementation decisions to freeze in a versioned machine-readable M4 policy/schema and matching product documentation. They are proposed defaults, not claims of completed Product/Learning review.

| Issue found in current documents | Proposed M4 resolution and validation |
|---|---|
| PRD §§10.3/14.2 use hint multipliers `1/.85/.70/.50/.30/.10`; policy matrix §6 uses `1/.85/.65/.35/0/0` | Use matrix §6 as the proposed evidence-authority contract. Levels 4–5 are learning-only, and assessment requires no assistance. Distinguish no-help level 0 from a tutor interaction currently labeled level 0. Reconcile the PRD, matrix, schema, and fixtures before enabling scoring. |
| Branch priors versus self-report-only start behavior | Default to `Beta(2,2)` for unverified concepts. Self-report may choose the first probe; it cannot create stronger mastery, confidence, or skip decisions. Any branch-specific prior needs reviewed evidence justification and its own fixtures. |
| Unspecified diversity, bands, interval, and stop parameters | Version evidence weights, per-concept attribution, diversity/family caps, band boundaries, retention half-lives/intervals, uncertainty bounds, minimum blueprint coverage, and replacement/exposure limits. Unknown concepts display insufficient evidence even if the prior mean is .50. Estimates ≥.80 without all gates remain Capable or provisional with an explicit missing-gate reason. |
| Beta update versus maximum .15 event change | Define effective-weight capping against the pre-event state so the persisted posterior and displayed mean remain mathematically consistent. Test both positive and negative caps, multi-concept attribution, and two-band movement requiring two independent pieces of evidence. |
| Prerequisite thresholds differ between readiness and loss-of-readiness rules | Treat mastery grant readiness (PRD §18.1: effective mastery ≥.75, respecting pack edges) separately from the below-.60 safeguard in §18.3. Document precedence for stricter pack requirements and preserve historical evidence on a later readiness loss. |
| Diagnostic evidence versus unseen mastery assessment | Diagnostic evidence establishes placement. Default it to ineligible for the unseen-assessment mastery gate unless a separately reviewed blueprint explicitly authorizes that use and exposure controls prove it. No implicit weekly-assessment weight for diagnostic items. |
| Replay and time-sensitive retention | Separate canonical evidence state from a retention view evaluated at an explicit `as_of` time. Store clock inputs used in decisions; identical evidence, versions, and clock produce identical canonical output. |
| Blueprint availability and stable early stopping | Stop for stable placement only after required concept/evidence coverage and a conservative uncertainty check pass. Timeout, inventory exhaustion, pending review, or unavailable runtime yields a distinct incomplete/limited outcome, never a stability claim. |

## 4. Implementation sequence

### M4-01 — Freeze policy and executable diagnostic contracts

Extend the skill-pack schema with structured response kinds, private scoring specifications, stage/branch mappings, target/language coverage, minimum evidence coverage, uncertainty and time budgets, and taxonomy definitions with observable signatures and repair references. Support the first stages already produced by M3 rather than inventing a separate routing vocabulary.

Define evidence schemas for mode, type, score, assistance, independence, novelty/family, operational validity, quality, attribution, event sequence, timestamps, and content/graph/scoring/model/policy versions. Reject non-finite scores, unknown references, malformed responses, and unsupported language combinations. Keep the core domain-neutral and include a non-DSA objective diagnostic fixture.

Choose an explicit schema compatibility/versioning path. Previously released pack payloads and digests must stay unchanged; old packs without executable diagnostics remain readable and explicitly unavailable for M4. Export and drift-check the JSON Schema. Publish new pack versions through the existing M2 review/release process.

**Acceptance:** One reviewed policy definition drives docs, schema, and gold fixtures; historical M2/M3 fixture digests remain stable; all nine track/language cells have a coverage declaration, including explicit unavailable cells.

### M4-02 — Add evidence persistence and transactional boundaries

Add the next additive migration, expected revision `0004`, retaining earlier identity/content/goal tables. Proposed tables:

| Entity | Required behavior |
|---|---|
| Diagnostic session | Owned goal, declared/active track, language, pinned pack/blueprint/policy versions, status, time budget, revision, recorded stop reason, and one active session per configured goal scope. |
| Diagnostic item attempt/exposure | Persist the selected item and family before delivery, server-issued attempt ID, selection reasons, timestamps, finalized response reference, scoring status, and immutable final result. Autosaves may be mutable; finalized records may not. |
| Evidence event | Append-only authoritative facts, stable source ID, per-aggregate sequence, schema/version pins, validity and independence. Corrections reference earlier events and preserve history. |
| Mastery event | Append-only projection effect with before/after state, model version, reason codes, and unique source/concept/projection-version constraint. One source may map to multiple concepts, with at most one effect per concept. |
| Learner concept projection | Rebuildable snapshot keyed by learner, pack/concept version, applicable language scope, and model version, with source watermark and evaluated clock. |
| Policy/projection revision | Immutable config/digest, replay provenance, validation comparison, and active revision pointer. |

Separate language-specific readiness from language-neutral DSA concepts through explicit mappings. Cross-language evidence transfer requires a policy rule; it cannot happen because concept names match. Reuse state across goals only when version, scope, and recency rules permit it.

Finalize response, evidence, mastery effect, projection, audit record, and outbox events in one database transaction. Allocate sequence numbers under database locks and protect active-session/finalization uniqueness with constraints. Idempotency keys bind to request digests; matching retries return the original result and changed payloads return `409`.

Enforce append-only behavior through the service and database permissions/constraints appropriate to the deployed role. Keep raw responses outside analytics payloads; specify ownership, access, artifact retention/deletion, and privacy-deletion compatibility with non-identifying audit history.

**Acceptance:** Real PostgreSQL races produce one logical response/evidence effect; injected failures leave no partial state or event; migration preserves prior records and restoration works at the new revision.

### M4-03 — Build the deterministic learner-state projector

Create a separate learner-state module with pure scoring/projection functions and a transactional service. Implement the reviewed weighted Beta update, weight/quality/assistance gates, family diversity, independent versus assisted counts, band safeguards, mastery/provisional gates, retention evaluation, and stable reason codes.

Passive views, self-report, invalid/quarantined items, operational failures, and pending scores have zero mastery effect. Successful delayed checks restore retention and lengthen configured intervals; failed checks reopen the concept while retaining history. M4 computes due dates/state; M9 delivers recurring review activities.

Store only approved misconception codes. Deterministic signatures reference the source evidence; clear a flag only through the configured two independent counterexamples plus a delayed success. Unknown or qualitative proposals stay pending and cannot become confirmed state.

**Acceptance:** Exact gold-state transitions, bounded updates, no false Mastered/provisional claims, clock-controlled retention, and a domain-neutral fixture pass. Passive/invalid inputs leave capability state unchanged.

### M4-04 — Implement staged diagnostic control and owned APIs

Resolve the accepted M3 goal and its exact pinned releases. Recheck current quarantine/retirement/eligibility at creation, selection, and scoring without silently repinning to a newer pack. Quarantine during an attempt blocks scoring and triggers an audited replacement or incident review.

Select a deterministic eligible candidate using stage, prerequisite frontier, verified evidence, blueprint coverage need, difficulty, exposure/family, remaining budget, and a stable item-ID tie break. Record candidates/baseline reasons needed for replay. Recent verified evidence may shorten diagnosis only within the reviewed scope; self-report never skips unverified prerequisites.

Persist item selection before returning it. `GET next` reads that persisted selection; advancing the selection happens within a write transaction. Finalization can use a recorded `completed`, `limited`, `pending_review`, `blocked_content`, `expired`, or `abandoned` outcome, with placement sufficiency represented separately from session terminal status.

Proposed endpoints, subject to the typed contract:

- `POST /api/v1/goals/{goal_id}/diagnostics`: idempotent creation or resume of an allowed session.
- `GET /api/v1/diagnostics/{diagnostic_id}` and `/next`: owned status/current item, with public fields only.
- `POST /api/v1/diagnostics/{diagnostic_id}/responses`: finalize the current server-issued attempt, score through the approved adapter, and persist the next selection or stop decision.
- `POST /api/v1/diagnostics/{diagnostic_id}/complete`: idempotent result finalization; reject a premature full-placement claim.
- `GET /api/v1/diagnostics/{diagnostic_id}/result` and owned learner-state/evidence reads: per-concept band, confidence/evidence counts, exclusions, missing evidence, misconceptions, prerequisite readiness, and version pins for M5.

Apply existing session, exact Origin/CSRF, object ownership, strict input, and error conventions. Bound request sizes and creation/submission frequency. Never send answer keys, reference solutions, hidden tests, future protected items, or full pack payloads to the browser.

**Acceptance:** Identical input/evidence/version/clock selects identical items and stop reasons; no prerequisite or exposure escape; failure items add zero evidence and get fair replacements; limited coverage cannot masquerade as complete placement.

### M4-05 — Deliver learner diagnostic and evidence views

Add the accepted-goal entry action, beginner-friendly instructions, accessible response controls, server-backed resume, progress/time guidance, retry/replacement states, and a result/evidence view. Foundations takes 10–15 minutes; experienced routes target 25–45 minutes, with approved accommodations and a versioned server-clock policy. A Foundations bridge retains the original Interview/Competitive intent in the results.

Show bands, counts, uncertainty, and missing evidence in plain language. Distinguish pending review, limited coverage, and a completed placement. M5's plan action remains unavailable until implemented; diagnostic completion alone does not count as full activation.

For HTML/JSX implementation, follow the repository web instructions and the required daisyUI skills. Review desktop/mobile reflow, keyboard operation, focus on errors, labels, zoom, and time accommodations.

**Acceptance:** Browser journeys cover beginner, experienced, bridge, resume, duplicate submission, waitlist, expiry, operational replacement, and honest results across all nine cells using synthetic inventory; unavailable cells visibly block. No score specification leaks in browser responses.

### M4-06 — Add replay, correction, and policy rollback

Provide restricted dry-run replay and comparison tooling. Rebuild from authoritative events in stored aggregate-sequence order, not delivery or wall-clock order; detect missing sequences and do not publish an incomplete projection. Deduplicate deliveries by event/source identity. Record out-of-order buffering/recovery separately from learner evidence.

Corrections append invalidation/replacement events and regenerate affected projections. Do not edit old evidence or old before/after records. Replay a candidate policy into a separate projection revision, compare placement/mastery/prerequisite decisions, and record the reviewed migration decision before switching the active pointer. Roll back to the previous retained compatible policy/projection without discarding evidence collected since the switch. Unsupported event versions block promotion explicitly.

**Acceptance:** Same versions plus clock yield byte-equivalent canonical state; duplicate/reordered delivery cannot change results; gap detection blocks publication; correction identifies affected learners; policy switch and rollback preserve source facts and reproduce prior-policy results on the current history.

### M4-07 — Calibration, operations, and gate evidence

Expose protected aggregate diagnostics and a calibration dashboard. Track starts/completions and incomplete reasons, timing, replacement rates, score distributions, coverage gaps, event reconciliation, replay mismatch, review backlog, and predicted versus later eligible unseen outcomes. Segment every learning metric by track/language; avoid learner/item IDs as high-cardinality metric labels.

Pair predictions with subsequent valid independent outcomes at matching scope and versions. Separate synthetic data and actual learner cohorts. Empty cohorts show insufficient data; a working dashboard is not proof of calibrated learning effectiveness. Version binning, cohort exclusions, minimum sample rules, and metric queries. Keep sensitive answers out of logs and metric events.

Add a `diagnostics_enabled` flag defaulting off in staging and a policy-version gate. Global disable prevents new diagnosis/scoring while preserving owned status/results and operator replay. Follow local synthetic rehearsal → real PostgreSQL CI → reviewed content → private staging canary → gate decision. Rehearse quarantine during a session, outbox outage, restore, stale browser submissions, and policy rollback; create an M4 operations runbook and validation report from actual results.

**Acceptance:** Protected dashboard works in staging, alert ownership and response steps exist, synthetic/live cohorts stay distinct, rollback/restore evidence is attached, and the [M4 gate](m4-gate.md) has an honest decision.

## 5. Suggested delivery order and effort

| Window | Engineering work | Content/review dependency | Demonstrable result |
|---|---|---|---|
| Week 1 | M4-01, M4-02, M4-03 | Resolve conflicting policy and approve objective blueprints/taxonomy | Versioned contracts, additive schema, transaction/replay fixtures, pure learner-state core |
| Week 2 | M4-04, M4-05 | Review item inventory, placement gold cases, copy/accessibility across nine cells | Owned resumable synthetic diagnostic journey and evidence results |
| Week 3 | M4-06, M4-07; broaden required integration checks | Real launch content and accountable reviews; M1 staging inputs | Replay/correction/rollback tools, live protected calibration view, staging rehearsals and gate evidence |

Critical path: freeze contracts → persist immutable evidence → project state → control diagnostics → learner journey → incident replay/calibration → release review. Content authoring and staging preparation can progress alongside engineering, but missing approvals are not filled in by automated test results.

## 6. Validation strategy

- **Gold fixtures:** all nine cells; true beginner, syntax-only bridge, inconsistent intermediate, strong verified prior, prerequisite gaps, language-specific failures, competitive target ceiling, and sparse/contradictory evidence. Learning reviewers approve expected placement rather than deriving expected answers from the implementation.
- **Property tests:** add Hypothesis as an M4 development dependency, as already adopted in the dependency assessment. Verify replay identity, bounds, passive invariance, deduplication, family/diversity caps, assistance gates, prerequisites, limited completion, and deterministic selection/stop decisions.
- **PostgreSQL integration:** concurrent creation/response/completion; event-sequence allocation; rollback injection; outbox interruption; immutable writes; corrections; migration and isolated restore. SQLite checks alone cannot satisfy these gates.
- **API/security:** cross-owner reads/writes, stale revision, altered item IDs, idempotency payload conflicts, malformed/non-finite scores, answer-key secrecy, quarantine races, server-time budget, request bounds, and disabled flag behavior.
- **Browser/accessibility:** desktop/mobile critical journeys, reload/resume, keyboard/focus/labels, beginner and bridge copy, limited results, retries, and protected operator access. Human accessibility review remains recorded separately.
- **Regression:** retain M0–M3 validation, unchanged historical pack digests, Ruff formatting/lint, mypy, TypeScript, optimized web build, API coverage at the existing 85% floor, dependency/secret checks, and local Markdown/contract validation. Run the affected browser suite and real PostgreSQL CI.

## 7. Carry-forward risks and decisions

| Dependency/risk | Treatment |
|---|---|
| M0–M3 hosted, operational, content, and sign-off evidence remains pending | Proceed with this owner-requested plan and repository engineering preparation; do not declare those gates passed. Staging deployment and launch require the actual prerequisite evidence. |
| Real diagnostic launch inventory is absent | Author and review through M2; use purpose-marked fixtures for engineering only. Verify replacement inventory and evidence coverage before enabling each cell. |
| M6 runner is not available | Deliver objective diagnostic scope and limited results honestly; integrate coding scoring later through the adapter. Recheck full diagnostic coverage at M6/M7. |
| M9 assessment/review capability is not available | Implement conservative gates and pending status in M4; avoid granting mastery from incomplete diagnostic proof. |
| Candidate heuristic is not calibrated | Version defaults and review fixtures; dashboard exposes uncertainty and sample sufficiency. Empirical validity needs subsequent independent outcomes. |
| Privacy deletion and immutable audit need compatible design | Minimize event data, separate identifiers/artifacts, review retention/deletion before live collection, and leave full user-facing export/delete workflow to M10. |

The repository increment is implemented for objective readiness with explicit M6/M9 boundaries. Its engineering validation and external milestone gate are separate recorded outcomes; reviewed launch inventory, accountable policy decisions, and deployed staging proof remain outstanding. The detailed exit checklist is in the [M4 gate](m4-gate.md).
