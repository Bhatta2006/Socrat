# Content placement implementation and UI handoff

Implemented against the [owner-supplied playbook](content-placement-playbook.md) on `redefined`.
The owner approved the content rollout in chat on 13 October 2026 and assigned frontend
work to the co-founder. This implementation changes content, backend APIs, validation,
tests and runtime packaging. It does not change frontend components or styling.

## Content supplied

- The first ten concepts in each course's declared curriculum order: 30 versioned packs.
- 279 original atoms: hooks, bounded concept cards, worked and faded examples,
  prediction-before-reveal visualizers, pattern cards, structured exit explanations,
  30 concept-specific misconception repairs, and a shared syntax repair in every pack.
- One additional trace, output-prediction and minimal-debug exercise per track.
- Binary search has four pointer-state predictions; binary search on the answer has six.
- 99 distinct executable adapters across Python, C++20 and Java, including intentionally
  defective debug programs whose documented baseline output is verified.
- Two scaffolded original problems: `echo-reading` and `next-counter`. Input parsing is
  supplied in the starter so the first problem tests output, and the second tests an
  assignment update. Both have genuine varied hidden inputs, a simple oracle and three
  reference implementations.

The approved packs record the scope of the owner's chat approval. That record is not a
claim that a learner pilot, independent expert review or measured learning improvement
has occurred. Code correctness is validated separately.

## Authoring and publication

Packs are `content/atoms/<course>/<concept>.yaml`. The schema is
`contracts/schemas/content-atom-pack.schema.json`; the controlled misconception IDs are
in `content/atoms/misconceptions.yaml`. Each pack declares the concept version, atom-pack
version, owner, rights, changelog, review and rollback reference.

An atom introduces one idea and is limited to 120 words (80 for patterns), 25 code lines
(15 for trace/debug, 10 for output prediction), 120 seconds and at most 12 steps.
The language variants are independently authored, with reviewed expected output.
Missing variants are explicitly unavailable; the server never substitutes another
language or invokes an automatic translation.

`released` requires a review record. `draft` is usable only in development/test sessions.
Set a pack to `quarantined` to block its atoms, including pinned in-flight sessions.
The first release's rollback ID quarantines the pack; subsequent releases can restore
an earlier Git version, retaining the version and review history.
After editing or quarantining a pack, restart the API to reload its cached catalogue.
This is a file-based authoring workflow; no live filesystem-editing endpoint was added.

Run from the repository root:

```powershell
uv run python scripts/content/build.py
uv run python scripts/content/validate_atoms.py
uv run python scripts/content/validate_problems.py echo-reading next-counter
```

The atom validator fails if a required toolchain is missing, code fails to compile, or
an output differs. It writes `.cache/atom-validation.json`. CI runs the same validation.
The API image now includes course/atom content and builds its generated judge tests;
`requirements.lock.txt` is re-exported from the existing frozen `uv.lock`.

## Session and evidence rules

Sessions are unique per enrollment and learner-local day, resume on reload and pin their
blocks, language and versions. Writes use row locking and optimistic revision checks.
Stale writes return `409 concurrent_update_retry`; clients should reload the session.
Unfinished sessions expire at the local day boundary. Switching enrollments must start
the new enrollment's session.

- The composer starts with due retrieval, introduces at most one new concept, and uses
  one targeted repair detour for two unresolved misconception failures or syntax friction.
- Beginners see an example and a faded reasoning step. Learners with a baseline attempt
  first. Strong or slow-correct learners receive strategy recognition instead of generic
  remediation. Two diverse independent successes support moving to a harder variant.
- A non-recovery session must include independent practice. Previously accepted or
  tutor-assisted problems are excluded. A lack of fresh content produces an honest
  `409 fresh_independent_problem_unavailable`, not invented progress.
- An unfinished session cannot continue after switching enrollments. A reported tiring
  session shortens the next default block; a failed independent attempt or a request for
  another example brings worked support back into the next session.
- Sixty-minute sessions can add independent transfer practice from a previously mastered
  concept, separated by a lighter block. Ninety-minute sessions include a break prompt.
  Missing transfer inventory is not replaced with longer lectures.
- Reading, worked examples, prediction visualizers, reflections and breaks do not create
  mastery evidence. Faded reasoning is marked guided. Trace, retrieval, debugging and
  structured explanation are distinct evidence kinds; only judged Submit results are
  code-solve evidence. Run results never count as independent solves.
  "Without hints" is reserved for assistance level zero; levels 1–2 are still recorded
  as assisted, so the copy never overstates independence.
- Instructional content, quizzes and tutoring are restricted during an independent
  challenge or weekly assessment. A reserved independent problem cannot be submitted
  before its block. The learner must make a real server-verified attempt to continue;
  acceptance is not required to move on after an honest failed attempt.
- Atom reading and the exit check integrate with the existing lesson/check activity
  records, without granting mastery for passive viewing.
- Completion freezes a summary: specific completed work, real evidence IDs and band
  changes, an honest no-change statement when appropriate, and a selected next step.
  Later work cannot rewrite that summary.

Durations, success-zone calibration and evidence weights are initial policies requiring
pilot validation. No guaranteed learning gain or guaranteed successful solve is claimed.

## API contract for the co-founder

All endpoints use the existing session cookie, Origin and CSRF protections. Each write
carries `X-CSRF-Token`. Paths below are relative to `/api/v1`.

| Endpoint | Purpose / request |
|---|---|
| `GET /learning-sessions/current` | `{session: null}` or the current session view |
| `POST /learning-sessions` | Start/resume; optional `{minutes: 10|15|20|30|45|60|90|120}` |
| `GET /learning-sessions/{id}` | Owned session view |
| `POST /learning-sessions/{id}/answer` | `{block, step, choice}`; commit a displayed prediction |
| `POST /learning-sessions/{id}/advance` | `{block, reflection?}`; next step/block after validation |
| `POST /learning-sessions/{id}/summary-viewed` | Idempotent closure-view event after completion |
| `POST /learning-sessions/{id}/issues` | `{block, reason, note?}`; report a current/earlier atom |
| `GET /admin/learning-quality` | Admin-only learning guardrails, closure counts and issue reports |

The view contains `id`, `day`, `minutes`, `language`, `concept`, `recovery`, `index`,
`blocks`, `current`, `feedback`, `finished` and `summary`. `blocks` contains navigation
metadata only. Only `current` includes an atom body and the selected language's code.
Never render future blocks as instructional content.

`current.kind` is `atom`, `problem`, `review`, `reflection`, `break` or `unavailable`.
An interactive atom has `current.atom.check` with `state`, `prompt`, shuffled `options`,
`step` and `total`. No answer key, expected output, future state or grading explanation
is sent before a committed answer. After `/answer`, announce `feedback` with a live
region; `/advance` moves to the next prediction or block. Keep options keyboard operable,
focus visible and state understandable without colour.

Problem blocks carry `problem` and `mode` (`guided` or `independent`). Use the existing
problem workspace; return to the session after Run/Submit. Review blocks carry an
existing quiz `activity` ID. The server refuses `/advance` until the corresponding
server-side evidence exists. Display `409 independent_attempt_required` as an invitation
to submit, not as failure. Reflections are one of `clear`, `syntax`, `strategy`,
`boundaries`, `tired`, `need-example`; they are scheduling information only.

Issue reasons: `incorrect`, `unclear`, `language`, `accessibility`. Each report includes
the pinned atom version and appears in the owner's quality endpoint. Its note is limited
to 1,000 characters. Reports, session outcomes, submitted checks and evidence provenance
are included in account export and removed by account deletion.

Existing `GET /concepts/{id}` now returns `423 concept_locked` for locked instruction,
and instruction requests during independent work return `423 independent_work_in_progress`.
The co-founder should provide a checkpoint/return-to-challenge action for those states.
The judge's existing response gains additive `learning_feedback`: explicit wording for
visible-only tests, independent Submit, assisted work, syntax errors and runner failure.

## UI work deliberately left to the co-founder

- Bounded atom blocks, expandable reasoning and accessible prediction steppers.
- A session entry point, recovery time choice, block estimates and workspace return path.
- The frozen session summary and short textual skill-state-change treatment.
- Issue reporting on every atom and admin presentation of the quality endpoint.
- Remove the current badge collection, time/lesson-click celebrations and routine confetti.
  Preserve only evidence-backed rare milestone treatment, reduced-motion support and
  neutral copy for planned study/rest/rescheduled days.
- Apply the playbook's copy standards rather than streak pressure or upsells at struggle.

No frontend edits, screenshots or browser acceptance of these new UI flows are claimed.
The shared running demo was not restarted during the co-founder's UI work. Activate the
new backend with the existing demo startup after stopping the old stack; startup applies
migration `0007_learning_sessions`. Fresh SQLite migration and API paths were tested;
PostgreSQL and container/gVisor deployment acceptance remain pending.

Validation record: the full local backend run passed 198 tests, with 24 environment-gated
sandbox tests skipped and 88.97% coverage. After adding content/concurrency/progression
checks, the focused content suite passed all 17 tests. All 99 distinct adapters passed;
both new problems passed every quality gate. No paid model generation was used.

## First-week validation and experiments

Use the supplied playbook's Day 0–7 script in a real pilot. Observe first independent
success within the initial session, first recall after a delay, use of hints, a fresh
transfer attempt, the weekly assessment and whether the learner can explain progress.
When a first session fails to produce an independent success, inspect the task/scaffold
and re-sequence; do not blame the learner or artificially advance their mastery.

The API records `learning.session_started`, `learning.prediction_committed`,
`learning.independent_solve` and `learning.band_changed` (with evidence resource IDs),
`learning.session_completed`, `learning.summary_viewed`, and `content.issue_reported`.
The admin endpoint exposes independent success, high-hint evidence, retention checks,
closure and content issues. Existing D1/D7/D30 retention remains in `/admin/overview`.

The six A/B hypotheses in playbook section 13 remain pending sufficient traffic and
a working UI. Establish a control/baseline and evaluate independent transfer and delayed
retention; reject a treatment that worsens independent success, hint dependence,
abandonment, anxiety feedback or defects. No traffic allocation, paid media generation,
video content, learner contact or unobserved pilot results have been manufactured.
