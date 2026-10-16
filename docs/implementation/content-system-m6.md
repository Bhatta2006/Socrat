# Content system M6: pattern planner

Status: **complete, awaiting review.** Branch `content-system`. Plan: [M0](content-system-m0.md),
previous milestone: [M5](content-system-m5.md).

## What was built

Behind `pattern_planner_enabled` (default `False`, reported as `pattern_planner` in
`/api/v1/features`):

| Module | Responsibility |
|---|---|
| `planner/patterns.py` (pure) | `Weights` (§9.5 starting values: 0.35 weakness, 0.25 review due, 0.20 track relevance, 0.10 diversity, 0.10 unlock); `priority` with an explainable breakdown; `rank`; the §9.4 pattern `triggers`; `session_type`; `build` for intro, drill and mixed-review sessions (§9.7); `violations` for the hard placement constraints |
| `learn/pattern_sessions.py` | Builds one `PatternView` per pilot pattern from concept mastery, pattern θ, solved variants, classify quiz responses and adaptive-quiz misconception steps; track relevance from the practice index (company frequency for Interview, contest problems for Competitive, course order for Foundations); assembles content from the pattern pack, a pattern card built from the pattern file, and contrast cards |
| `content/patterns/contrasts.yaml` | One original contrast card per `pattern-*` confusion tag (8) |
| `learn/sessions.py` | With the flag on, tries the pattern planner first; with no valid plan it runs the existing composer unchanged. Pattern sessions record `pattern_plan` (pattern, type, triggers, top-3 scores) in the payload |

**Triggers**: repair (a pitfall missed twice) → the pattern's micro-lesson; confusion → contrast
card; variants solved but classification failing → classifier first; 3 variants solved →
classifier drill; mastered and idle 7 days → mixed review; first variant solved → pattern card
and the next rung; unseen → intro.

**Hard constraints** (`violations`; any violation discards the plan): no instruction for a
locked concept or one with a locked prerequisite (variant problems in other concepts are
checked too), at most one new idea per session, at least one independent attempt outside
recovery, a retrieval block whenever retention is due, never two independent problems back to
back, every block has a time estimate, the total fits the budget, draft atoms only where drafts
are allowed, and at most three problems on one concept.

**Unreviewed content stays unreviewed**: pattern atoms (draft packs) write no mastery evidence
and do not complete the concept's lesson or quiz activity until their pack is `released`;
quarantining a pattern pack blocks its atoms (423).

## How to run

```
uv run pytest services/api/tests/test_pattern_planner.py
SOCRAT_PATTERN_PLANNER_ENABLED=true     # to try it locally (drafts show outside secure deployments)
```

## Acceptance

| Criterion | Result | Evidence |
|---|---|---|
| Flag off = unchanged | Pass | `test_session_start_uses_the_pattern_planner_only_with_the_flag[False]` (no `pattern_plan`, no pattern blocks); every existing session and learner test passes unchanged |
| Priority scoring with weights config | Pass | `test_priority_follows_the_weighted_formula`, `test_gate_diversity_and_retention`, `test_rank_drops_gated_patterns_and_is_deterministic`, `test_relevance_is_scaled_per_track` |
| Pattern triggers in the composer path | Pass | `test_triggers_follow_section_9_4`; end-to-end test with the flag on (intro session, payload explains the scores) |
| Session templates + hard-constraint properties | Pass | `test_built_sessions_never_break_a_hard_constraint` (hypothesis, 150 states × content availability × budgets); `test_constraint_checker_catches_each_rule` |
| Golden tests, three learner states | Pass | New Foundations learner → intro; Interview learner after a first variant → drill; returning learner with three due patterns and a confusion → mixed review with a contrast card |
| Lint, types, tests | Pass | ruff and mypy clean; pytest 375 passed, 24 skipped, 90.68% coverage; content checks green |
| e2e | Not run | Still blocked by the local `socrat.e2e.db` (see M3) |

## Findings

1. **Synthesized cards must match the atom shape.** The session view reads every atom field
   (`adapters` and others), so the first end-to-end run crashed on the generated pattern card.
   Cards now carry the full `Atom` field set.
2. **Variant problems cross concepts.** `digit-sum` is an accumulator variant but belongs to
   `zero:while-loops`. Gating only the pattern's own concept would have offered it to a learner
   who has not unlocked while loops; problems are now gated by their own concept.
3. **Native variants are scarce.** Most rungs are external IDs, which sessions cannot run, so
   sessions fall back to the concept's unsolved problems. A drill rarely reaches three rungs
   until more native problems exist.

## Decisions and assumptions

- **"Block" in §9.5** ("at most two blocks on the same concept") is read as practice problems:
  at most three per concept per session (a drill's guided plus two independent rungs).
- **Mastery estimate** = concept Beta mean, averaged with P(correct at band 4) from the
  pattern's θ once the learner has adaptive-quiz answers on it. θ still never changes mastery (D4).
- **"Seen"** = a solved variant, adaptive-quiz answers on the pattern, or an earlier pattern
  session for it.
- **Exit explanation**: pattern packs have no explanation atom, so sessions end with the
  existing reflection block.
- **Company mode** is not a separate switch: Interview relevance already uses company counts
  from the practice index (log-scaled).
- **Contrast cards and pattern cards** are built from authored text (`contrasts.yaml`, the
  pattern file) and inherit the pack's draft status.
- **Weights are starting values** (§9.5) in one frozen object; tuning needs the A/B data of §9.16.

## Needs a human

- Review the contrast cards (with the M5 pack review).
- Decide whether pattern sessions should ship before the packs are reviewed (with the flag on
  in a secure deployment, draft pattern atoms are not allowed, so no pattern session forms and
  the composer runs).
- Earlier items remain open: M1 legal and license verification, the stale e2e database.
