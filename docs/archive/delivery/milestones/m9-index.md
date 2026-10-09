# M9 — Assessment, mastery, and retention

The owner authorized M9 repository implementation on 6 October 2026, superseding the earlier condition that engineering wait for all M7/M8 prerequisites. Implementation and validation continued on 7 October. This authorization does not pass the inherited release gates or authorize deployment.

Socrat's core loop remains Goal → Diagnose → Plan → Learn → Practice → Assess → Adapt → Verify. M9 supplies protected baseline, weekly, final, and retention forms to the existing deterministic learner-state engine. Assessment completion is distinct from mastery: the existing independent-success, unseen-assessment, form-diversity, confidence, latest-score, prerequisite and seven-day gates still apply.

## Structure

- `services/api/src/socrat/assessment/`: strict authoring/command contracts, publication inventory audit, transactional workflow and owned/admin routes.
- `models.py` and migration `0009`: sessions, issued family exposures, append-only responses/reviews/disputes, and separable answer artifacts.
- `skillpacks/schema.py`: additive private assessment specifications, protected inventory, parallel-form equivalence, reviewed keys/rubrics, explicit language coverage and weekly unfamiliar/mixed tasks. Empty declarations are omitted from canonical serialization to preserve historic pack digests.
- `execution/`: assessment-item admission through the existing signed broker; healthy Submit results stage responses, Run has no scoring authority, and tutor access is forbidden in protected modes.
- `learnerstate/`: existing mastery gates and append-only corrections; reviewed scheduling candidate `1.1.0`, with legacy policies retained.
- `apps/web/src/app/assessment.tsx`: start/resume, text/code responses, review status, historical results, scoring disputes and retention entry alongside the confirmed goal.
- `contracts/`: generated command/schema/policy artifacts. `scripts/validation/export-m9-contracts.py` regenerates M9 artifacts; the M4 exporter includes all retained learner policies.

## Implemented behavior

Forms pin the released pack digest, blueprint, scoring specifications, language, track, environment/tool restriction, learning policy and deadline. Issuance counts as exposure even after abandonment, expiry, exclusion or language/version changes within the same pack key. A consumed family cannot be selected for another protected form. Baseline/final parallel groups match concept coverage, difficulty, cognitive processes, time and pass threshold, with separate families. Weekly forms require unfamiliar and mixed tasks.

Objective responses use exact private keys. Code results use the broker's authenticated correctness tests; code alone does not certify complexity or explanation. Curated 0–4 qualitative criteria require an independent human reviewer. There is no model grading authority. Item/form boundary scores wait for review. Ambiguous items and failed execution exclude the form without mastery updates; a fresh unexposed form is required. Finalization writes evidence, projections and telemetry atomically. Duplicate commands and callbacks cannot manufacture evidence.

Learner disputes enter the protected review queue. Reviewers can uphold the original score or exclude its evidence with an append-only correction. Historical results remain visible with current-evidence/dispute markers. Post-finalization score changes require a fresh assessment rather than rewriting past facts.

Scheduling policy `1.1.0` requires the existing reviewed replay/promotion process. Its first capable evidence anchors a two-day review, then successful checks expand toward 7, 14 and 30 days and subsequently by 1.8×, capped at 365 days. Scores ≥.8 expand, .6–.79 keep the interval, and <.6 request repair before restarting at two days. Representations progress recall → small implementation → mixed problem → retention assessment. Ordinary retention forms fit 25% of session capacity; an actively failing prerequisite permits a larger check. Early recall cannot satisfy seven-day mastery. Practice does not postpone a scheduled check. Multi-item retention advances once per concept/form.

## Remaining release work

Use the [M9 gate](m9-gate.md), [validation record](../validation/m9-validation-report.md), and [operations guide](../../operations/m9-assessments.md). Real reviewed parallel forms and all retention representations across the intended cells, independent boundary-score/calibration judgments, accessibility review, hosted telemetry/rollback/outage acceptance and inherited M6–M8 gates remain open. Synthetic fixtures and local tests do not replace those artifacts. Local Compose enables assessment development; standalone/staging configuration defaults off.
