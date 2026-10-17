# Content system M7: item calibration

Status: **complete, awaiting review.** Branch `content-system`. Plan: [M0](content-system-m0.md),
previous milestone: [M6](content-system-m6.md). This is the last milestone of the plan.

## What was built

| Piece | What it does |
|---|---|
| Migration `0011_quiz_response_choice` | Adds a nullable `quiz_responses.choice` (the authored option index), recorded by the engine on every answer. Distractor rates need it. Additive and reversible. |
| `calibration/stats.py` (pure) | Percent correct, point-biserial discrimination against the learner's pattern θ, distractor counts, the strong learners' (top third) most-picked distractor, median time, and the §8.7 repair flags: `too-hard` (< 10%), `too-easy` (> 95%), `low-discrimination` (< 0.15), `attractive-distractor` (> 60% of strong learners), `slow` (median > 3× expected). Flags start at 30 responses. |
| `calibration/job.py` | `run` stores statistics and flags in `item_calibrations`; it **never changes a status and never writes `approved_by`**. `transition` is the only way to change a status. It needs a named person (empty names and tooling names such as `ci`, `bot` or `claude` are refused), a statistics row, and for `calibrated` at least 30 responses and no flags. Allowed moves: provisional → calibrated or retired; calibrated → retired, or back to provisional for repair. Retired is final; the record is kept. |
| Engine honours approvals | `quiz.service.items_for` applies human-approved statuses over the content files. Calibrated items freeze their rating, retired items are never served, and calibrated assessment items are what lets assessment modes run instead of failing closed (D3). |
| `calibration/report.py` | Markdown report: item health and flagged items, coverage per course × band × pool and per pilot pattern, success-zone share per track (§9.6 zones), atom gaps, provenance completeness. Aggregates and item keys only. |
| `scripts/content/calibrate.py` | `stats`, `set-status <item> --to … --approver "Full Name"`, `report [--out file]`; the database comes from `SOCRAT_DATABASE_URL` or `--database-url` |

## How to run

```
uv run alembic upgrade head                                  # 0011_quiz_response_choice
uv run python scripts/content/calibrate.py stats
uv run python scripts/content/calibrate.py set-status <item key> --to calibrated --approver "Full Name"
uv run python scripts/content/calibrate.py report --out calibration-report.md
```

## Acceptance

| Criterion | Result | Evidence |
|---|---|---|
| Stats job and flag rules | Pass | `test_point_biserial_matches_the_formula`, `test_a_healthy_item_has_no_flags`, one synthetic test per rule, `test_no_flags_before_thirty_responses`, `test_stats_job_writes_health_but_never_status_or_approval` |
| Status CLI needs ≥ 30 responses and a named human approver | Pass | `test_status_changes_need_a_person_enough_responses_and_no_flags`, `test_cli_runs_stats_status_and_report` |
| Report without PII | Pass | `test_report_has_every_section_and_no_learner_data`: no enrollment or user ids, no subjects |
| Engine uses approved statuses | Pass | `test_the_engine_honours_approved_statuses` (calibrated, retired, assessment availability) |
| Lint, types, tests | Pass | ruff and mypy clean; pytest 388 passed, 24 skipped, 90.9% coverage; content checks green |
| e2e | Not run | Still blocked by the local `socrat.e2e.db` (see M3) |

## Findings

1. **Distractor rates were not measurable before this milestone.** `quiz_responses` stored
   correctness but not the chosen option. Migration 0011 adds it; responses recorded before it
   have no choice and count only toward percent correct, discrimination and time.
2. **Legacy content has no provenance at all.** The first report on a fresh database shows 0% for
   the 61 concepts, 234 concept quiz items, 85 problems and 30 atom packs (M1 made the field
   optional so nothing changed meaning). All 12 pilot patterns, 12 pattern packs and 13 quiz
   families have it.
3. **The pilot's band gaps are visible.** No pattern has B7, and the two reused M4 families sit
   on one generated band (lower/upper bound: B4; accumulator: B3).

## Decisions and assumptions

- **Ability for discrimination** = the learner's current θ for the item's pattern
  (`learner_abilities`), the closest thing to "concept ability" the engine keeps. With no row,
  the learner counts as 0, which only happens for responses written outside the engine.
- **Expected time** = half the family's `time_limit_s`; legacy items, which have no limit, use
  60 s. So `slow` means a median over 1.5× the time limit, or over 3 minutes for legacy items.
- **Strong learners** = the top third of responders to that item by θ.
- **Calibrated items keep being measured**: `run` updates their statistics and flags, and the
  report lists flagged calibrated items for repair; moving them back is a human decision.
- **Success-zone share** is reported per item (percent correct inside the track's zone), since
  the engine does not store P at answer time.
- **The 2PL IRT comparison** (§8.7, after ≥ 300 responses per item) is out of scope.

## Needs a human

- Approvals are the point of this milestone: only a named person can calibrate or retire items,
  and only after real responses exist. There are none yet.
- Decide whether to backfill provenance for legacy content (finding 2).
- Earlier items remain open: review of the M5 packs, taxonomy consolidation, M1 legal and
  license verification, and the stale e2e database.
