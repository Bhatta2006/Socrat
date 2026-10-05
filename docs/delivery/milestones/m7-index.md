# M7 track-complete learning experience

**Status: implementation started, 5 October 2026. M7 is not complete.** The owner authorized proceeding after M6 repository implementation while deferring dedicated-host gVisor tests. The [M6 gate](m6-gate.md) remains open and execution remains disabled without its configured, attested runtime capabilities.

The first increment connects M5 reviewed plans to durable normal learning sessions and M6 signed Submit results. Schema `0007` stores one session per goal/local day, immutable content/curriculum pins, revisioned block progress, and append-only idempotent command receipts. The Today panel renders retrieval, concept instruction, guided examples, independent practice, and exit reflection, with pause/resume and server-backed reload. Each code session allocates its own fresh attempt; browser history cannot substitute a previous exercise attempt.

Reading, acknowledgments, text responses, and reflection create no mastery evidence. Text responses are explicitly ungraded. A coding block advances only from its own completed, healthy, signed Submit result; Run and operational failures cannot advance it. M6 remains the sole producer of implementation evidence. Session completion means learning participation, not independently verified mastery or a graded explanation.

New sessions require today's confirmed, current-evidence plan and released pinned content. A session may finish after its own Submit changes the evidence watermark. Plan refresh does not rewrite an existing session. Plan pause and content withdrawal block further transitions; saved work remains. Sessions close to further commands at the end of their learner-local date.

The second increment implements Competitive timed independent practice and post-timeout/unsuccessful-result upsolve. `start_timed` establishes a server deadline that cannot be paused or reset. Session-bound broker admission rejects execution from a locked/inactive phase or outside that window. A Submit admitted before the deadline may finish scoring afterward. Pending Submit results must resolve before upsolve, and operational failures remain unscored. Upsolve records a controlled error classification, copies the saved learner source into a separate attempt, and marks it seen; the original timed outcome is preserved. The editor saves before the handoff. Work duration is calculated from the immutable session receipt at submission, excluding explicit pauses and worker/queue delay.

Learners may choose `timing=untimed` when starting low-stakes practice. That choice is immutable and visibly labelled; it does not create timed-performance evidence or claim an approved assessment accommodation. Existing JSON storage at schema `0007` supports this increment without another migration.

The third increment adds session planning policy `1.0.0`, pinned in new plans when learning sessions are enabled. Competitive sessions with at least 60 minutes of effective capacity select two different concept sets and problem families when safe reviewed inventory fits. Shorter sessions keep one primary problem. Verified sessions reserve 20% of their working budget for optional upsolve, within the existing weekly reserve. Every code block owns a separate attempt. Concept-gap, wrong-answer, and complexity repair can select a pinned reviewed task with matching concepts, no higher difficulty, a different family, and an estimate that fits the repair allocation. Other categories, or missing eligible inventory, retain the saved solution. Repair attempts are conservatively marked seen; family metadata does not prove structural novelty. Original drafts and timed outcomes remain preserved. Historical M5 plans replay with their original algorithm.

## Remaining implementation

1. Reviewed language-foundation lessons and Interview pattern-specific session content, rather than relying solely on existing concept explanations/examples.
2. Competitive penalty policy, reviewed structural-variant mappings, and mixed-set content coverage. Basic concept-matched repair selection and upsolve allocation are implemented; allocations are planning guides rather than hard repair deadlines. Approved assessment accommodations remain with M9; low-stakes practice offers a labelled untimed choice.
3. Deterministic objective learning checks and their reviewed validators; qualitative explanation grading stays with M9.
4. Historical-session resume/expiry policy and recovery integration; current-day session retrieval is implemented.
5. Reviewed content-bank coverage audit and publication checks for all nine cells, with no dead ends and sufficient structural variants. Existing synthetic fixtures are not launch content.
6. Session telemetry exports, meaningful-session/activation evaluation, calibrated duration error, accessibility review, staff dogfood, and deployed golden journeys. Local PostgreSQL persistence/concurrent-start/concurrent-command checks pass.

See the [gate](m7-gate.md), [operations](../../operations/m7-learning-sessions.md), and [validation record](../validation/m7-validation-report.md).
