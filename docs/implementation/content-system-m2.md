# Content system M2: schemas, loaders and validation

Status: **complete, awaiting review.** Branch `content-system`. Plan: [M0](content-system-m0.md),
previous milestone: [M1](content-system-m1.md).

## What was built

- **Patterns** (`catalog/patterns.py`): `content/patterns/<course>/<concept>/<pattern>.yaml`.
  References are validated against the catalog: concept, native problems, external IDs in the
  13,889-record practice index, atoms in the concept's pack, misconception IDs, and the quiz family.
- **Quiz families and bank items** (`catalog/quizbank.py`): `content/quiz/<course>/<concept>/<family>.yaml`
  with a generator spec (template file must exist; practice and assessment seed ranges must not
  overlap) and/or static items with per-option misconception tags. `legacy_items()` wraps the 234
  concept-embedded items read-only with global keys, formats and bands.
- **Projects** (`catalog/projects.py`): milestones, rubric totalling 100, self-review, provenance.
- **JSON contracts**: `contracts/schemas/content-{pattern,quiz-family,project,atom-pack}.schema.json`,
  written by `scripts/content/export_contracts.py`; a test fails when one drifts from its model.
- **Runtime tables**: migration `0009_quiz_runtime` adds `quiz_responses`, `learner_abilities`,
  `item_ratings`, `item_calibrations`. Nothing writes to them yet.

Patterns, families and projects all require `provenance`, start `provisional`, cannot become
`calibrated` without a human review record, and are covered by the M1 license gate.

## How to run

```
uv run pytest services/api/tests/test_patterns.py services/api/tests/test_quizbank.py \
  services/api/tests/test_projects.py services/api/tests/test_quiz_runtime_tables.py
uv run python scripts/content/export_contracts.py      # after changing an authoring schema
uv run alembic upgrade head                             # 0009_quiz_runtime
```

## Acceptance

| Criterion | Result | Evidence |
|---|---|---|
| Unit tests for valid and invalid files | Pass | 33 new tests across patterns (15), quiz families (12), projects (6) |
| A pattern referencing a missing concept or problem fails | Pass | `test_broken_references_fail_validation` (unknown concept, native problem, external problem, misconception, atom); `test_variant_must_point_at_a_listed_problem` |
| No change to existing API responses | Pass | No content files added; catalog digest identical before and after (`23fcbcec…`); API tests and e2e (39) pass |
| Migration additive and reversible | Pass | `test_upgrade_creates_the_tables_and_downgrade_removes_only_them`; learner rows erased with the account |
| Lint, types, tests | Pass | ruff and mypy (Linux) clean; pytest 294 passed, 89.13% coverage; e2e 39 passed |

## Decisions and assumptions

- **Item storage**: Appendix B's `quiz_item` table is replaced by content files plus
  `item_ratings` (current difficulty) and `item_calibrations` (health, approval). Items remain
  versioned with the rest of the content.
- **Pattern templates**: §3.3 requires per-language templates; the §3.2 schema has none, so
  `template` (≤ 25 lines per language) was added. Compiling them is M5.
- **Variant ladder**: bands must be non-decreasing; a variant's `problem` must be listed under
  `problems`. The 5–7-variant pack requirement is checked in M5's pack lint, not the schema.
- **External IDs**: `leetcode:<slug>`, `cf:<id>`, `cses:<n>` only, matching the practice index.
- **Legacy bands** (D11): difficulty 1→B1, 2→B2, 3→B3, 4→B5, 5→B6; items with code start at B2.
  Today's items map to B1–B3 only. Pool assignment is M3.
- **`item_calibrations.flags`** was added for M7's flag rules.
- **New misconception IDs** (D6) are not added yet; they arrive with the first real distractors (M4).

## Needs a human

Nothing new. M1's legal and license-verification items remain open.
