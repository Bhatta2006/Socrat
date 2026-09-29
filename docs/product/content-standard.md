# DSA content and assessment standard

**Scope:** V1 DSA skill pack and the domain-neutral contracts later skill packs must satisfy.  
**Reference baseline:** ACM/IEEE-CS/AAAI CS2023 Algorithmic Foundations and Software Development Fundamentals inform coverage; they do not define Socrat’s track order or validate its assessments.

## Principles

1. Every released artifact serves an observable capability.
2. Concepts are language-neutral; implementation variants are language-specific.
3. Practice teaches; assessment verifies. Their item inventories and exposure policies are separate.
4. Deterministic tests and expert review establish release validity. AI may draft, never release.
5. A missing language variant is visibly unavailable, not translated at runtime.
6. Accessibility is part of correctness, not a later copy pass.
7. Rights and provenance must be known before an artifact enters the repository.

## Concept contract

Every concept version includes:

- stable ID, display name, domain, version, and lifecycle state;
- observable competency statement beginning with an action verb;
- required and recommended prerequisites with rationale;
- representations: explanation, trace/visual where useful, examples/non-examples;
- evidence modes: recognize, trace, explain, implement, analyze, transfer, retain;
- common misconceptions with observable signals and repair links;
- mastery evidence requirements and minimum diversity;
- track overlays and released difficulty/rating bands;
- estimated learning/practice durations with calibration status;
- accessibility notes and terminology definitions;
- owner, reviewers, source/provenance, and change history.

A concept is too broad if a learner can be strong in one part and weak in another while receiving the same next-action decision.

## Exercise contract

Every exercise version includes:

- stable ID, immutable version, title, statement, constraints, input/output, examples, and explanation;
- primary and secondary concept mappings;
- mode eligibility: practice, diagnostic, assessment, contest simulation;
- difficulty evidence and calibration state, not only an author label;
- intended strategies, invariants, complexity expectations, and misconception tags;
- estimated time by track/band with uncertainty;
- exposure/cooldown and near-duplicate family ID;
- at least one trusted reference solution per released language;
- starter code and function/IO contract per released language;
- deterministic public and hidden tests, including edge/boundary cases;
- resource limits calibrated per runtime;
- rights/provenance and external-link fallback;
- accessibility/copy review, reporting route, owner, and rollback ID.

## Language-variant requirements

For each released Python, C++, or Java variant:

- compile/run against a pinned runtime image;
- reference solution passes all tests within limits with safety margin;
- intentionally wrong solutions fail the expected tests;
- cross-language semantic fixture produces equivalent accepted/rejected outcomes;
- integer range, recursion depth, Unicode/IO, ordering, floating-point, and timeout differences are addressed where relevant;
- diagnostics shown to learners are sanitized and useful;
- templates do not reveal the target algorithm.

Release can be language-specific only when the coverage matrix marks unavailable languages explicitly. The planner must never select an unavailable variant.

## Test quality

Minimum internal release set:

- nominal examples;
- empty/minimum and maximum valid constraints where meaningful;
- off-by-one and duplicate cases;
- sorted/reverse/adversarial shapes where relevant;
- overflow/precision cases where relevant;
- complexity-killing cases for slower strategies;
- randomized/property cases where an oracle is reliable;
- mutation checks proving common wrong implementations fail;
- hidden-test secrecy check.

At least 20 boundary/random cases are required where applicable. Count alone is not sufficient; reviewers approve coverage against the intended strategy and misconception model.

## Assessment requirements

- Baseline and final forms share a blueprint but use non-isomorphic items.
- Assessment items never appear in practice, tutor context, examples, or public analytics.
- Items cover multiple evidence types; code correctness alone cannot prove explanation or analysis.
- Objective/code scores are deterministic.
- Qualitative scoring uses a versioned rubric, evidence citation, confidence, and human-review thresholds.
- Threshold-adjacent or low-confidence qualitative results enter review before mastery changes.
- Exposure, similarity, solve-rate anomalies, and leakage are monitored; signals trigger review, never automatic cheating accusations.
- Every form has a retirement and replacement plan.

## AI-assisted authoring

AI-generated drafts must be labeled with provider/model/prompt version and author request. Before release they undergo the same human review and deterministic verification as human drafts, plus:

- factual and ambiguity review without trusting generated explanation;
- independent reference solution or derivation;
- license/provenance check preventing imitation/copying of restricted problems;
- similarity scan against internal and licensed inventory;
- adversarial and mutation tests;
- no generated assessment item release without full learning-design review.

The first 500 generated problems, if generation is enabled, receive 100% expert review. Later sampling may change only through an approved quality decision supported by defect data.

## Accessibility and inclusive language

- Meet WCAG 2.2 AA for rendered content and interaction used in the critical journey.
- Do not encode meaning only through color, animation, or spatial position.
- Diagrams have equivalent text; traces can be navigated without pointer-only interaction.
- Code and mathematical notation work with zoom, reflow where possible, keyboard navigation, and assistive technology review.
- Avoid culture-specific assumptions, idioms, names, or contexts that are irrelevant to the competency.
- Timed modes have a documented accommodation path that preserves the intended evidence construct.
- Errors say what happened and what the learner can do next; avoid shaming language.

## Rights and provenance

Allowed sources:

- original work with documented author assignment;
- permissively licensed material compatible with distribution and modification;
- external links/metadata used under verified terms without copying protected content.

Every asset records source, author, license/terms snapshot date, permitted uses, attribution, and owner. Unknown provenance blocks release. External content removal must not strand a curriculum path.

## Review roles

| Role | Required judgment |
|---|---|
| Author | Completeness, intent, source, initial tests |
| Domain reviewer | Correctness, strategy, complexity, ambiguity |
| Language reviewer | Idiomatic implementation and runtime behavior for each released language |
| Assessment reviewer | Blueprint validity, independence, form comparability |
| Accessibility/copy reviewer | Comprehension, interaction alternatives, inclusive language |
| Release owner | Evidence complete, conflicts resolved, version published |

The author cannot be the only domain, language, or release reviewer. Assessment items require learning-design approval.

## Lifecycle

`draft → technical_review → learning_review → language_verified → staged → released → quarantined/retired`

Promotion is explicit and audit logged. Released versions are immutable. Fixes create a new version; urgent defects quarantine the old version immediately.

## Quarantine and repair

One credible learner report pauses scoring for the affected attempt and opens review. Two credible independent reports automatically quarantine the item from new selection. Automated anomaly rules may also quarantine.

Repair requires:

1. identify every exposed attempt and downstream mastery/plan decision;
2. classify whether evidence is still valid;
3. recompute or remove evidence through an auditable repair event;
4. substitute an equivalent valid item where needed;
5. notify materially affected learners in plain language;
6. publish a new content version and regression fixture;
7. document root cause and prevention for repeated/material defects.

Deletion is not repair. Preserve the audit trail and legal retention rules.

## Release checklist

- [ ] Observable competency and prerequisite mappings approved
- [ ] Statement, constraints, examples, and expected complexity unambiguous
- [ ] Rights/provenance complete
- [ ] Reference solution passes in every released language
- [ ] Wrong-solution/mutation and boundary tests pass quality review
- [ ] Resource limits and cross-language fixtures verified
- [ ] Mode, exposure, family, and assessment separation correct
- [ ] Difficulty/duration labeled with calibration state
- [ ] Accessibility/copy review complete
- [ ] Owner, reviewers, immutable version, and rollback ID recorded
- [ ] Staging canary produces no unexpected runtime/scoring result

