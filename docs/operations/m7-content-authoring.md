# Session content authoring

M7 content is declarative JSON inside an immutable skill-pack version. It never contains executable validators or plugins. Read the [content standard](../product/content-standard.md) and use the existing independent technical, learning, language-verification, staging and publication workflow. The [authoring example pack](../../contracts/fixtures/skill-packs/dsa-m7-authoring-1.2.0.json) supplies eighteen unreviewed lessons across the nine cells for traversal and linear search. It includes language-specific fragments, state traces, recognition/invariant/complexity notes, and objective checks. All lessons are uncalibrated; the pack is synthetic fixture inventory with no runtime or launch approval. Synthetic reviewed metadata in `services/api/tests/m7_support.py` exercises selection and publication guards, and is not a human review record.

Add `session_content_version: "1.0.0"`, `learning_lessons`, `structural_repairs` and, for Competitive, `competitive_penalty`. Empty fields are omitted from canonical legacy JSON, preserving released digests. Existing versions cannot be edited; author a new version and retain the required migration metadata when concept identities change.

Each lesson declares a unique `id`, `track`, `language`, `concept_ids`, `title`, `instruction`, `examples`, `language_notes`, `accessibility`, `source_reference`, `calibration`, `retrieval_check` and `exit_check`. Interview lessons additionally require `pattern_recognition`, `correctness` and `complexity`. Concept/language references must belong to the declared track. Session start chooses the narrowest reviewed matching lesson, with a stable identifier tie-break, and pins its identifiers. Mixed instruction/guided blocks combine their concept lessons; the first pinned lesson supplies that block's objective check. This is sampling, not a comprehensive assessment of every concept.

Author Foundations notes for the selected language's syntax, data representation, control flow and common mistakes. Interview content should teach observable pattern triggers, a trace, a correctness argument and resource complexity. Competitive content should support concise retrieval and independent practice. Plain text remains safely rendered text rather than executable HTML. An `uncalibrated` lesson cannot be selected for a declared session-content release.

An objective check contains a distinct identifier, prompt and a server-private `response`, using `validator_version: "objective_exact_1.0.0"`. Choice checks require two to twelve uniquely identified choices and an answer referencing one choice. Trace checks use an exact private answer; equivalent alternative representations are not silently accepted. Pydantic's contract trims surrounding whitespace. Qualitative explanation and implementation validator kinds are rejected here. Reflection remains separate and ungraded; M9 owns qualitative assessment. For example, this is an authoring fragment with an answer key and must never be sent directly to a learner:

```json
{
  "id": "accumulator_trace",
  "prompt": "Start total at zero. Add 2, then 3. Write the final value as one digit.",
  "validator_version": "objective_exact_1.0.0",
  "response": {"kind": "trace", "answer": "5"}
}
```

Structural repair declarations contain `exercise_id`, `variant_id`, `structural_change`, `review_reference` and `calibration`. Both exercises must be practice inventory with matching concepts and modality, different families, and a target difficulty no higher than the source. Review must explain the actual structural change, not merely renamed variables or different input values. Runtime selection still verifies language, readiness, cooldown, exposure, difficulty and repair budget. A declaration cannot override those filters or expose protected assessment families.

Competitive penalty declarations contain `version: "1.0.0"`, `basis: "healthy_incorrect_submit"`, a bounded integer `wrong_submit_seconds`, `review_reference` and `calibration`. Choose and review the actual launch value; the synthetic sixty-second test value is not a product default. Unreviewed policies are not pinned, and cannot satisfy the Competitive publication audit. The result is a practice ledger, not a contest ranking or approved assessment rule.

The nine-cell audit requires a reviewed lesson and at least two reviewed practice families per track concept and language, a beginner entry task at difficulty one estimated at eight minutes or less, a reviewed Competitive penalty policy, structural repair coverage, and two distinct Competitive concept/family sets fitting fifteen minutes each with at least sixty-minute track capacity. These static minimums do not prove adequate inventory for every schedule, mastery state, exposure history or difficulty band. Review full planner golden journeys for published targets and watch the existing explicit content-gap decisions.

With the API package on `PYTHONPATH`, run:

```text
python -m socrat.skillpacks.cli validate path/to/draft.json
python -m socrat.skillpacks.cli learning-audit path/to/draft.json
```

Audit output contains gap codes and concept identifiers, without answer keys or hidden tests. A launch pack declaring session content cannot publish until the audit passes. Human review and real language/runtime semantic verification are still required; setting `calibration` or a review reference in JSON does not provide that evidence.
