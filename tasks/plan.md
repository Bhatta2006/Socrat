# Implementation Plan: Socrat content system (Content Master Plan pilot)

## Overview
Build the foundation and a working pilot of the pattern-based content system: provenance and
license hygiene, pattern/quiz schemas, an adaptive quiz engine with partitioned pools,
sandbox-verified item generators, 12 original provisional pattern packs, and pattern-aware
planner hooks, all behind flags that default off. Recon, capability map, schemas and open
decisions: `docs/implementation/content-system-m0.md`.

## Architecture decisions (pending approval, see M0 §10)
- Items are content files (like today's embedded quiz items); only runtime state is in the DB.
- Mastery stays the PRD's Beta-Bernoulli model; Elo θ is used for item selection and reporting.
- Existing models gain only optional fields; no existing file, ID, API or test changes meaning.
- Verification of generated items uses the authoring runner, not the learner execution broker.
- Flags: `adaptive_quiz_enabled`, `pattern_planner_enabled`, both default `False`.

## Commands (every task)
```
uv run ruff format --check services/api services/execution
uv run ruff check services/api services/execution
uv run mypy services/api/src services/execution/src
uv run python scripts/content/build.py
uv run python scripts/content/validate_atoms.py
uv run pytest --cov=socrat --cov-fail-under=85
```

## Task list
Tasks are recorded with acceptance and verification in `tasks/todo.md`.

### M1 provenance
1. Provenance + source models, optional on Concept/QuizItem/Problem (S)
2. `content/sources/registry.yaml` from Appendix A + license-gate validator (M)
3. LICENSE / NOTICE.md / ATTRIBUTION.md drafts + static attribution page (M)
4. Inventory generator moved into `scripts/content/inventory.py`, rights/review columns filled or `unknown` (M)
5. Link health: extend `check_links.py`, `--live`, fixtures, CSV (M)
Checkpoint M1: all content loads; gate rejects adapted-from-unverified; inventory has no empty rights cells; report.

### M2 content-schemas
6. Pattern schema + loader + cross-reference validation (concept, problems, atoms, misconceptions) (M)
7. Quiz family / bank item / generator-spec schemas + loader; wrap the 234 items read-only (M)
8. Project schema + JSON contracts in `contracts/schemas/` (S)
9. Runtime tables migration (`quiz_responses`, `learner_abilities`, `item_ratings`, `item_calibrations`) + downgrade test (M)
Checkpoint M2: valid/invalid fixture tests; API responses unchanged (golden); report.

### M3 quiz-engine
10. Config object + rating math (P, update, K schedules, clamping) with unit tests (S)
11. Pools: stable-hash partition of existing items, band mapping table, family seed ranges (S)
12. Selection: candidate filter, target choice, seeded tie-break, ladder guarantees, interleave (M)
13. Modes + stop rules + cold start + roll-up; assessment modes fail closed to legacy (D3) (M)
14. API (next-item, submit-answer, session-summary) behind `adaptive_quiz` + evidence via `mastery.apply` (M)
15. Simulator + property tests (ladder, accuracy ±0.07, no repeats, exposure, assessment isolation) (M)
Checkpoint M3: flag off = unchanged behaviour (golden); simulator suite green; report.

### M4 item-generators
16. Generator framework (template, params, seeds per pool) + verifier (S/M)
17. Defect catalogue + mutation generator; trace, story and counterexample generators (M)
18. Proof families: fixed-window-sum, binary-search/boundaries, zero/for-loops/accumulator in 3 languages (M)
19. Verifier rejects broken generator, ambiguous options and unspecified behaviour; 100 items/family (S)
Checkpoint M4: 300 verified items, deterministic per seed; report with new misconception IDs.

### M5 pilot-content
20–23. Pattern packs in batches of three (DSA ×2 batches, Zero, CP): cues, templates ×3 languages, worked/faded, visualizer ≤12 steps, ladder, pitfall micro, classifier, quiz family ≥12 items over ≥4 bands (M each)
24. Atom/length lint script + full verification run (S)
Checkpoint M5: schema + sandbox verification + lint pass; everything provisional, review null; report.

### M6 pattern-planner
25. Pattern priority scoring module + weights config + unit tests (S)
26. Pattern triggers into the composer behind `pattern_planner` (M)
27. Session templates (intro, drill, mixed review) + hard-constraint property tests (M)
28. Golden tests for three learner states (S)
Checkpoint M6: flag off unchanged; property and golden tests green; report.

### M7 item-calibration
29. Stats job (pct correct, point-biserial, distractor rates, median time) + flag rules (M)
30. Status transition CLI requiring ≥30 responses and a named human approver (S)
31. Markdown report (item health, coverage per band, success-zone share, atom gaps, provenance completeness), no PII (M)
Checkpoint M7: synthetic-data tests; report.

## Risks and mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Empty calibrated assessment pool | High | D3: engine assessments fail closed to existing services |
| Generator volume for M5 | Med | M4 before M5; families reused across patterns |
| Simulator-dependent accuracy test flaky | Med | Fixed seeds, many simulated learners, assert on mean |
| Migration number conflict with Foundry branch | Med | D1 branch choice; additive single migration |
| Unverified licenses | High | Registry gate in CI; pilot adapts from nothing |

## Open questions
See `docs/implementation/content-system-m0.md` §10 (D1–D12).
