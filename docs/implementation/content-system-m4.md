# Content system M4: item generators and verifier

Status: **complete, awaiting review.** Branch `content-system`. Plan: [M0](content-system-m0.md),
previous milestone: [M3](content-system-m3.md).

## What was built

`services/api/src/socrat/quiz/generate/`:

| Module | Responsibility |
|---|---|
| `framework.py` | `Draft`/`Option` contract; loads `content/quiz/generators/<template>.py`; one seed → one item (rng seeded by family id + seed); the answer comes **only** from the family's `reference` expression; seed → pool; source digest; manifest reader |
| `harness.py` | Wraps statement snippets into one program per language (Python, C++20, Java 21), compiles once, runs them in order. A crash, exception or timeout loses only that snippet; compile errors are isolated by bisection |
| `verify.py` | Rejects items whose executed code disagrees (see below); writes manifest entries |
| `mutate.py` | Defect catalogue (`content/quiz/defects.yaml`) and whole-line edits per language |
| `trace.py`, `story.py`, `counterexample.py` | Building blocks for trace tables, pattern-in-a-story items and counterexample search (unit-tested; not yet used by a family) |

`scripts/content/validate_quiz.py` verifies every generated family and writes
`content/quiz/verified.json`; `--check` (now in CI after atom validation) fails when any seed is
rejected or the manifest is stale. **A generated item reaches learners only if the manifest lists
it with the current source digest** (family file + generator file + defect catalogue +
framework version), and the item's digest matches.

### What the verifier checks, per seed

- The generator does not crash, keeps the `Draft` contract, and is deterministic.
- Every distractor carries a misconception from the taxonomy; the answer carries none.
- `output_prediction`/`trace`: the shown code prints the reference answer in every language,
  and no distractor equals it.
- `bug_spot`: the buggy code runs and prints something else (the defect is observable). Each
  option's fixed snippet is run: only the answer may print the reference output.
- `fill_blank`: each option is substituted into the blank and run: only the answer may print
  the reference output (otherwise **ambiguous**).
- Unspecified behaviour: Python runs twice with different hash seeds, and all languages must
  agree. Disagreement rejects the item.
- Duplicates (same prompt, code and option set as an earlier seed) are excluded and listed,
  not treated as errors.

### Proof families (task 18), all `provisional`, `review: null`, `origin: original`

| Family | Concept | Format, band | Generator | Items |
|---|---|---|---|---|
| `quiz:dsa:sliding-window:fixed-window-sum` | dsa:sliding-window | output prediction, B2 | parameterised template | 100 (70 practice / 30 assessment) |
| `quiz:dsa:binary-search:boundaries` | dsa:binary-search | bug spotting, B4 | mutation from the defect catalogue | 100 (70 / 30) |
| `quiz:zero:for-loops:accumulator` | zero:for-loops | fill-the-blank, B3 | template with blanks | 100 (69 / 31; one spare seed covers a duplicate) |

Every item has code in Python, C++ and Java and 4 options. Families have no `pattern` yet;
M5 links them when the pattern files exist.

### New misconception IDs (D6), appended to `content/atoms/misconceptions.yaml`

`window-off-by-one`, `stop-after-first`, `confuse-index-value`, `lower-vs-upper-bound`,
`half-open-bound`, `exclude-candidate-mid`, `lo-hi-confusion`, `off-by-one-output`,
`overwrite-not-accumulate`, `count-not-sum`, `bound-instead-of-variable`, `product-not-sum`,
`accumulator-init-one`, `accumulator-starts-at-first`, `accumulator-starts-at-bound`,
`loop-bound-off-by-one`, `trace-step-slip`. Each is used by a distractor
(`trace-step-slip` by `trace.options`). The `-repair` IDs are unchanged.

### Engine integration

`pools.bank` now includes verified generated items (pool from the seed range). They are served
by the M3 engine behind `adaptive_quiz_enabled`, with the family's hint ladder. Because the
families have no human review record, their answers write responses and ratings but **no
mastery evidence** (§8.7); legacy items still do.

## How to run

```
uv run python scripts/content/validate_quiz.py          # verify and rewrite the manifest
uv run python scripts/content/validate_quiz.py --check  # what CI runs (about 12 s)
uv run pytest services/api/tests/test_quiz_generators.py
```

Changing a family file, its generator or `defects.yaml` makes that family's manifest entry
stale. Its items stop being served until the manifest is regenerated.

## Acceptance

| Criterion | Result | Evidence |
|---|---|---|
| 300 verified items | Pass | `validate_quiz.py --check`: 300 items, 0 rejected, 11.7 s |
| Deterministic per seed | Pass | `test_proof_families_are_deterministic_and_distinct` |
| Rejects a broken generator | Pass | `test_broken_generator_is_rejected`, `test_draft_contract_and_taxonomy_are_enforced` |
| Rejects ambiguous options | Pass | `test_ambiguous_options_are_rejected` (fill-blank with two working fills) |
| Rejects unspecified behaviour | Pass | `test_hash_order_output_is_rejected_as_unspecified` (set order), `test_languages_that_disagree_are_rejected` (`-7 // 2` vs `-7 / 2`) |
| Also rejected | Pass | wrong answers, unobservable defects, nondeterministic generators |
| Only verified items are served | Pass | `test_only_verified_items_reach_the_bank` (tampered digest drops 1 item; stale source drops the family) |
| Engine serves them, no evidence before review | Pass | `test_generated_items_are_served_but_write_no_evidence_until_reviewed` |
| Lint, types, tests | Pass | ruff and mypy clean; pytest 360 passed, 24 skipped, 90.34% coverage; atoms 99 adapters; content build unchanged |
| e2e | Not run | Still blocked by the local `socrat.e2e.db` (revision `0011`, content-foundry); see M3 |

## Findings

1. **`eval` with a locals dict hides names from comprehensions**, so a reference like
   `max(sum(a[i:i+k]) for i in ...)` failed. Values are now passed as globals. The verifier
   caught this on the first run.
2. **Seed order mattered for de-duplication.** Seeds were first walked assessment-first, so a
   duplicate would have kept the assessment copy. They now go in seed order.
3. **Small parameter spaces collide.** The accumulator first had about 1,300 combinations and
   collided within 100 seeds. Widened to about 10,000; one collision remains (seeds 12 and 39),
   so the family has one spare seed. Duplicates are judged by what the learner sees, ignoring
   option order.

## Decisions and assumptions

- **Snippets are statement blocks**, like the existing items' code; the harness supplies
  `main`, `#include <bits/stdc++.h>`/`using namespace std;` and `import java.util.*;`.
  Generators therefore cannot define functions inside snippets.
- **Option text per language**: fill-blank options display their fill in the learner's
  language (`i <= n` in C++/Java, `n + 1` in Python). Bug-fix options are worded in plain
  language so one text fits every language.
- **Generators import from `socrat.quiz.generate`** and may run trusted Python in process
  (`run_python`) to choose inputs. The verifier re-checks everything in all three languages.
- **Assessment seeds are in the repo**, not secret (§8.9 "secret and rotated"). Assessment modes
  still fail closed (D3), so nothing is exposed today. Secret seed handling is deferred until
  calibrated assessments exist.
- **Reviews**: tooling never writes `review`. Generated items count as evidence only after a
  human adds a review record to the family (and regenerates the manifest).
- **`Catalog.quiz_root`** was added so the bank can find generators and the manifest.

## Needs a human

- Review a sample of generated items (content.md §8.6: the first 500 items need 100% human
  review). Run `validate_quiz.py` after adding `provenance.review` to a family.
- M1's legal and license-verification items remain open; the e2e database issue from M3 remains.
