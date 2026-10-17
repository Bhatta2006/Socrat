# Content system M5: pilot pattern packs

Status: **complete, awaiting review.** Branch `content-system`. Plan: [M0](content-system-m0.md),
previous milestone: [M4](content-system-m4.md).

Everything in this milestone is **original, provisional and unreviewed** (`status: provisional`,
`review: null`, atom packs `draft`). Nothing new reaches learners by default: pattern atoms are
not read by the session composer, and the quiz families are served only by the M3 engine behind
`adaptive_quiz_enabled`, where unreviewed families write no mastery evidence.

## What was built

### Tooling (task 24 and support)

| Piece | What it does |
|---|---|
| Pattern atom packs | `content/atoms/<course>/<concept>/<pattern>.yaml` (`PatternAtomPack`, `Catalog.pattern_atoms`). Patterns resolve their atom IDs against the concept pack and their own pack. |
| `classify` atom kind | The "classify these 3 problems" drill (interactive, needs steps) |
| `Pattern.template_io` | stdin and expected output; every template is run with the M1 `check_adapter` runner |
| `Draft.format` | Generated items carry their own format, so one family can produce predict (B2), fill (B3) and fix (B4) items |
| `quiz/generate/kit.py` | A shared generator. A pattern describes its program, plausible wrong outputs, blanks (with wrong lines) and defects (with decoys); the kit samples inputs, builds items and pre-checks them in Python with a step limit |
| `scripts/content/lint_patterns.py` | Pack lint, in CI. Checks the 3 cues, templates in 3 languages (run), 5–7 variants, required atoms (worked, faded, visualizer, micro, classify), micro 60–90 s on the top pitfall, ≥ 12 servable items over ≥ 4 bands, pitfalls used by distractors, quiz wording lengths, and provisional/unreviewed status |

### The 12 pilot packs (tasks 20–23)

| Pattern | Items | Bands | Native problems | Notes |
|---|---|---|---|---|
| `dsa:sliding-window/variable-size` | 68 | 1–6 | longest-unique-substring | |
| `dsa:sliding-window/at-most-k-distinct` | 66 | 1–4, 6 | (external only) | |
| `dsa:binary-search/lower-upper-bound` | 106 | 1, 4–6 | lower-bound-queries | Reuses the M4 boundaries family |
| `dsa:binary-search/answer-monotonic-predicate` | 66 | 1–6 | koko-speed | |
| `dsa:dp-1d/unbounded-coin-change` | 66 | 1–6 | min-coins | Answers from BFS, not the DP shown |
| `dsa:heaps/top-k` | 66 | 1–3, 5–6 | kth-largest-stream, top-k-frequent | No fix items (see decisions) |
| `zero:for-loops/accumulator` | 106 | 1, 3, 5–6 | sum-of-multiples, digit-sum | Reuses the M4 accumulator family |
| `zero:lists/traverse-and-filter` | 66 | 1–6 | above-average | |
| `zero:strings/frequency-count` | 66 | 1–6 | vowel-count, word-frequency | |
| `cp:prefix-difference/difference-array` | 66 | 1–6 | range-add | |
| `cp:modular-arithmetic/fast-power` | 66 | 1–6 | mod-expressions | |
| `cp:complete-search/subset-enumeration` | 66 | 1–6 | apple-split | Answers from recursion, not the bitmask loop |

Each pack has 3 recognition cues; complete templates in Python, C++ and Java (≤ 25 lines,
run against `template_io`); a 6–7 rung variant ladder linked only to existing problem IDs; 3
pitfalls; 5 draft atoms; and a quiz family with 6 static items (B1 recognise, B5 edge, B6
transfer) plus 60 generated items (42 practice, 18 assessment), or 100 for the two M4 families.
**900 generated items** are verified in Python (two hash seeds), C++ and Java; no problem content
was created or edited.

## How to run

```
uv run python scripts/content/validate_quiz.py      # verify generated items, write verified.json (~53 s)
uv run python scripts/content/lint_patterns.py      # lint packs, run templates
uv run pytest services/api/tests/test_quiz_generators.py services/api/tests/test_patterns.py
```

## Acceptance

| Criterion | Result | Evidence |
|---|---|---|
| Schemas valid | Pass | Catalog loads; contracts regenerated (`content-atom-pack`, `content-pattern`), no drift |
| Sandbox verification | Pass | `validate_quiz.py --check`: 900 items, 0 rejected; templates run in 3 languages |
| Lint | Pass | `lint_patterns.py`: 12 patterns, 0 problems |
| Provisional, review null | Pass | Enforced by the lint and `test_repository_patterns_are_provisional_original_and_unreviewed` |
| Misconceptions used (D6) | Pass | `test_new_misconceptions_are_all_used` covers every ID added since M4 |
| CI parity | Pass | Both checks pass from a clean LF `git archive` export |
| Lint, types, tests | Pass | ruff and mypy clean; pytest 361 passed, 24 skipped, 90.3% coverage; atoms 99 adapters; build unchanged |
| e2e | Not run | Still blocked by the local `socrat.e2e.db` (see M3) |

## Findings

1. **"Shrink with `if`" is not a bug for longest-window questions.** I first taught it as the
   top pitfall of variable-size windows. The verifier could not make that defect change the
   answer, because with `if` the window never drops below its best length and just slides (the
   known non-shrinking window). The defect and the misleading micro-lesson were removed. The
   variable-size pitfall is now negative numbers, and two B5 items teach where `if` is harmless
   (longest) and where it is wrong (counting windows).
2. **Hand-computed text is the weak spot.** Two template outputs I wrote by hand were wrong
   (difference array, fast power); the runner would have rejected both. Two walkthroughs had
   errors I found by checking them step by step (variable-size visualizer, answer-search micro).
   **Atom prose (worked, faded, visualizer steps) is not machine-checked**; it needs the human
   review below.
3. **Sampling decides whether a defect is visible.** Uniform random inputs rarely exposed some
   defects (boundary `>=`, missing the last subset element), so generators shape their inputs
   (runs of repeated values, exact sums, targets that use the last element). The kit now picks
   a blank or defect once per item; re-picking per retry had silently favoured the easy ones.
4. **Avoided language divergence.** Options whose meaning differs by language are excluded:
   shifts past 31 bits (undefined in C++, wrapped in Java), map lookups of missing keys
   (`operator[]` versus `KeyError`), and Java's need for explicit booleans.
5. **The taxonomy grew far beyond the D6 estimate.** 93 IDs were added in M5 (110 since M4),
   against about 20 expected. Each is used, but many are fine-grained (`pattern-*` recognition
   confusions, several off-by-one variants). This is worth consolidating before calibration.

## Decisions and assumptions

- **Pattern atoms do not go in the concept packs** (changes M0 §2 "new atoms live in the
  concept's atom pack"). Those packs are `released` under a human review record, the composer
  serves the first atom of each kind from them, and they cap at 20 atoms. Appending
  unreviewed atoms there would ship them. Separate draft packs keep them out of learner
  sessions until M6 reads them behind `pattern_planner`.
- **Static items carry no code**, because nothing would execute it. Code items are always
  generated and verified.
- **Top k has no fix items.** The natural one-line defect (max-heap instead of min-heap) is one
  line in C++ and Java but two in Python, so it would not mean the same in every language.
- **References are independent where it matters**: brute force over subarrays, BFS for coin
  change, recursion for subsets, `pow` for fast power, sorting for top k.
- **Band coverage**: every pack has ≥ 4 bands, as M5 requires. None has B7 (design-and-justify
  needs rubric scoring, out of scope). The three reused or no-fix families lack B2/B3 or B4.
  §3.3's "7 bands × 3+ items" is therefore not met yet.
- **Families attached to patterns**: the M4 boundaries and accumulator families now name their
  pattern. `FRAMEWORK_VERSION` went to 2 (the `Draft.format` field changes every digest), and the
  manifest was regenerated.
- **CI cost**: `validate_quiz.py --check` now takes about 53 s.

## Needs a human

- **Review all 12 packs** before learners see them as reviewed: atom prose and walkthroughs,
  static items, and a sample of generated items (content.md §8.6: 100% of the first 500). To
  mark a pack reviewed, add `review` to the pattern, atom pack and family, then rerun
  `validate_quiz.py`.
- Consolidate the misconception taxonomy (finding 5).
- Earlier items remain open: M1 legal and license verification, and the stale e2e database.
