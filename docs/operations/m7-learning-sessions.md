# M7 learning sessions

Enable `SOCRAT_LEARNING_SESSIONS_ENABLED=true` to expose the Today session API/UI. It defaults off; local Compose enables it and staging defaults off. This does not enable execution. Code sessions require the existing M6 execution configuration and healthy worker capabilities. M7 adds no executable learner-code path in the API.

Apply Alembic revision `0007` before starting the new application. Backup/restore defaults now expect `0007`; use an explicit expected revision for older archives. To roll back exposure, disable the session feature and retain the database records. Do not downgrade a populated session schema as a routine rollback.

Endpoints:

- `GET /api/v1/goals/{goal_id}/learning-session`: current learner-local day's session or `null`.
- `POST /api/v1/goals/{goal_id}/learning-session`: start with `curriculum_revision` and optional `timing` (`standard` or `untimed`). Retries return that day's existing session; a conflicting timing choice fails. Rest/content-gap days and stale/unconfirmed plans cannot start.
- `POST /api/v1/learning-sessions/{session_id}/commands`: `advance`, `pause`, `resume`, `abandon`, `start_timed`, or `upsolve`, with `expected_revision` and `idempotency_key`. Text blocks require a response except instruction. Exit requires a controlled reflection code. Independent/upsolve coding requires the phase's signed, healthy, completed Submit `run_id`. Upsolve requires `error_classification`.

Authentication, ownership, and CSRF match other learner APIs. Mutations lock the learner row on PostgreSQL. A repeated command with the same body returns its original receipt; reusing a key with different input fails. Content withdrawal also blocks receipt replay from exposing content. The browser reload button retrieves the latest progress after a revision conflict.

Blocks unlock sequentially. Only unlocked blocks expose prompts, explanation, or examples; reference solutions and hidden tests never appear in session views. Code drafts remain in M6 autosave storage. Operational failure preserves the draft and leaves independent work available for retry. Normal and upsolve blocks may advance after a healthy incorrect submission; a timed unsuccessful submission goes through error classification and upsolve first.

Text responses are retained in session progress and receipts, under the same learner-data access boundary. They are ungraded and never appended as learning evidence. Reflection codes are controlled signals only. Session start/completion/block/command events enter the existing transactional audit/outbox without answer text. No activation or meaningful-session aggregate is claimed by this increment.

`active_seconds` sums saved active intervals, excluding explicit pauses. It is not an inactivity detector or a calibrated duration metric. Session-bound implementation evidence measures solve duration using the command receipt at broker admission, excluding worker/queue latency and later session changes. Sessions cannot accept new commands after their local date ends; historical state remains stored.

## Timed practice and upsolve

The planner decides which independent blocks are timed from verified readiness. Their window starts only with `start_timed`; its deadline is `start + block.minutes * 60`. Browser countdowns use server time for display. Broker admission is authoritative: `issued_at` must be before the deadline, and refreshing the page or repeating start commands cannot extend it. A timed block cannot pause after starting. Before it starts, normal pause is available.

Submissions admitted before the deadline retain eligibility while waiting for their worker result. The learner cannot start upsolve while that Submit is pending. A passing on-time result advances to reflection. An unsuccessful result can enter upsolve; a timeout with no Submit can enter upsolve after the deadline. Worker failures are labelled `unscored_operational_failure`, with no fabricated score. Timed text responses stay ungraded and cannot establish timed solving ability.

`upsolve` records a controlled category (`wrong_answer`, `implementation_bug`, `complexity`, `time_pressure`, `concept_gap`, or `unclear_prompt`). The browser first saves the latest editor source. The API copies that saved source into a fresh, pinned practice attempt for the same item. That attempt is explicitly seen (`unseen=false`); the old attempt and original timed outcome are retained. Samples and Submit from the old phase cannot be admitted again. Quotas, runtime capability, signatures, withdrawal, ownership, and kill switches remain enforced. Untimed upsolve supports normal pause/resume. A healthy finalized upsolve submission can advance even if incorrect; it is a learning attempt rather than a new contest result.

Choosing `timing=untimed` at session start removes practice timing and records the choice visibly. It provides a low-stakes access path; it neither approves an assessment accommodation nor proves timed performance. M9 owns assessment accommodation decisions. Upsolve can take additional learner-selected time; a separate planned upsolve budget and alternative repair variants remain pending.

Machine-readable input contracts: [`learning-session-start.schema.json`](../../contracts/schemas/learning-session-start.schema.json) and [`learning-session-command.schema.json`](../../contracts/schemas/learning-session-command.schema.json).
