# Adaptive roadmap

Socrat keeps one personalised roadmap per learner, watches how they progress, and adapts it.
The rule that shapes everything here: **Socrat asks before it changes the roadmap.**

## What adapts on its own, and what needs a yes

| Adapts automatically (how a concept is taught) | Proposed, applied only after the learner accepts (the roadmap itself) |
|---|---|
| Pace and problem difficulty, overall and per concept | Refresh a weak prerequisite first |
| Spaced reviews, spaced to the learner's own forgetting rate | Quick check of a concept's foundations (probe) |
| Support steps when stuck: worked example, another explanation, tutor check-in | Test out of a concept or a whole module |
| Learner's own choices: path style, "too easy / too hard / I know this", undo | Set a concept aside, drop optional topics, focus a topic |
| | Study minutes or days, path style or goal, a new target date |
| | Weekly stretch problem, ease-back-in plan after a long break |

Proposals come from three sources (`planner`, `tutor`, `review`) and live in `plan_proposals`.
Accepting one writes the enrollment's `adaptive.overrides` (or schedule/goal), logs a plan
revision whose first reason is "You approved: …", and retires the alternatives in its group.
A declined proposal is not re-offered for 14 days. Planner proposals that no longer apply expire.

## Pieces

- `adaptive/profile.py` — one skill profile per concept: mastery, Elo rating, speed, hint
  dependence, trend, plateau, unresolved misconceptions, failure modes; forgetting rate,
  adherence and a unified practice level.
- `adaptive/stuck.py` — stuck needs two or more signals (long time, plateau, many attempts,
  hint-heavy, slow, repeated mistake) or repeated failure; names the likely cause and walks an
  intervention ladder one rung at a time.
- `planner/goals.py` — goal relevance (interview, contest, foundations) and path styles.
- `planner/engine.py` — orders free concepts by relevance (prerequisites always first; a pinned
  concept pulls its foundations forward; a deferred one takes its dependents back), applies
  approved overrides, adds support steps, milestones and an adherence-aware forecast. Pure.
- `adaptive/suggest.py` — pure drafts: deadline alternatives, test-outs, stretch, stuck ladder,
  comeback. `adaptive/proposals.py` stores, validates, applies and undoes them.
- `adaptive/views.py`, `adaptive/routes.py` — `/api/v1/adaptive/*`: proposals, decide, undo,
  path options and style, feel, weekly review, nudges, profile.
- Tutor: `get_learner_profile`, `propose_plan_change`, `propose_goal`, `record_observation`
  tools; an `<adaptive>` context section; the `plan` scope for planning conversations. Tutor
  observations are `tutor` evidence that can only lower confidence (score ≤ 0.5).
- Evaluation: `uv run python scripts/evals/tutor_eval.py` runs scripted learners (stuck,
  cruising, behind, asks to change the plan, planning chat, demands the answer) against the
  configured provider and grades the replies.

## Flags

`adaptive_quiz_enabled` and `pattern_planner_enabled` now default to on. Set
`SOCRAT_ADAPTIVE_QUIZ_ENABLED=false` or `SOCRAT_PATTERN_PLANNER_ENABLED=false` to switch them
off. Pattern-plan outcomes are logged as `learning.pattern_plan_served` / `_fallback` events, and
nudges as `nudge.<kind>` outbox events (at most once a day per kind) for a mailer or push service.
