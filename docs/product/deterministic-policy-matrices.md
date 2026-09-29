# Deterministic policy matrices

These matrices define authority and the minimum total routing behavior for V1. Exact numeric thresholds belong to versioned configuration; changes require replay against gold fixtures before release.

## 1. Eligibility and routing

Rules run in priority order and return stable reason codes. Multiple errors may be displayed, but no lower-priority acceptance overrides a higher-priority exclusion.

| Priority | Condition | Outcome | Reason code |
|---:|---|---|---|
| 10 | Adult confirmation absent | Ineligible until confirmed | `adult_confirmation_required` |
| 20 | Language not Python/C++/Java | Waitlist | `unsupported_language` |
| 30 | Fewer than 3 days/week or less than 20 minutes/session | Not eligible for beta program; offer informational preview | `minimum_practice_commitment_not_met` |
| 40 | Competitive target coverage is not released | Waitlist with exact gap | `competitive_target_not_released` |
| 50 | Interview/Competitive intent and language experience is none/syntax-only | Accept declared goal with Foundations bridge | `foundation_prerequisites_required` |
| 60 | Foundations intent | Foundations diagnostic | `foundations_goal_selected` |
| 70 | Interview intent | Interview diagnostic | `interview_goal_selected` |
| 80 | Competitive intent | Competitive diagnostic | `competitive_goal_selected` |

Unknown or malformed required inputs return `input_confirmation_required`; they never fall through to an accepted route.

## 2. Diagnostic start and stop

| Track/policy | Start evidence | Initial stage | Stop condition | Maximum duration |
|---|---|---|---|---:|
| Foundations | None/self-report only | No-code reasoning and language readiness | Placement and prerequisite decisions stable within configured uncertainty | 15 min |
| Interview | Verified prior product evidence exists | Goal-relevant prerequisite frontier | Same as above, with target-band coverage | 45 min |
| Interview | No verified evidence | Broad staged screen | Same as above | 45 min |
| Competitive | Verified recent product contest-like evidence | Released target-band frontier | Topic/difficulty placement stable | 45 min |
| Competitive | No verified evidence | Mixed prerequisites and speed baseline | Topic/difficulty placement stable | 45 min |

Self-report chooses only the first item. Correctness, latency, explanation, implementation, and hint use update evidence. Operational failures and invalid items contribute zero evidence and cause replacement.

## 3. Prerequisite eligibility

| State | New dependent instruction | Review dependent | Assessment dependent |
|---|---|---|---|
| Required prerequisite locked | Prohibited | Prohibited unless review targets prerequisite itself | Prohibited |
| Prerequisite learning/low confidence | Prohibited | Allowed for prerequisite | Diagnostic probe only if blueprint permits |
| Prerequisite ready but retention due | Allowed with bounded concurrent prerequisite review | Required review allowed | Allowed only if assessment blueprint treats prerequisite as ready |
| Prerequisite mastered/retained | Allowed | Allowed by due schedule | Allowed |
| Content/graph version inconsistent | Prohibited | Prohibited | Prohibited; operator review |

The LLM advisor receives only already eligible candidates. It cannot reinterpret this matrix.

## 4. Exercise candidate filtering and ranking

Hard filters run before scoring:

1. released and not quarantined;
2. supports selected language/runtime;
3. maps to an eligible concept and required mode;
4. respects practice/diagnostic/assessment separation;
5. respects exposure and cooldown limits;
6. fits remaining time budget;
7. has a healthy immutable test/runtime version.

Eligible candidates receive deterministic scores:

`priority = need + due_review + goal_relevance + misconception_match + diversity + difficulty_fit - recent_exposure - abandonment_risk - duration_mismatch`

Tie order is stable: higher priority, lower exposure count, older last exposure, stable content ID. Randomization is permitted only through an explicitly stored experiment seed after structural eligibility is fixed.

## 5. Track policy

| Dimension | Foundations | Interview | Competitive |
|---|---|---|---|
| Primary objective | Correct reasoning then implementation | Unseen pattern transfer and communication | Speed, accuracy, proof, mixed-topic transfer |
| Default new:review | 60:40 | 50:50 | 40:60 |
| Timing | No pressure until readiness | Add after clean untimed solve | Default for validated concepts |
| First help | Elicit trace/next step, allow high scaffolding | Elicit plan/invariant | Locked during contest simulation; post-attempt repair |
| Difficulty increase | Two clean independent successes with confidence | Clean unseen solution plus explanation | Timed success at current band across diverse topics |
| Difficulty decrease | Repeated prerequisite error/abandonment | Two independent failures with same prerequisite signal | Repeated timeout/wrong-answer pattern, then focused upsolve |
| Daily non-negotiable | One independent action | One unseen independent action | Timed set or independent upsolve |
| Progress proof | Trace, implement, explain, retain | Clarify, design, implement, analyze, retain | Recognize, prove, implement, optimize, recover |

Ratios are initial targets, not exact daily quotas. Capacity and due retention work can adjust them while preserving one independent action.

## 6. Help and evidence weight

| Highest assistance | Allowed behavior | Evidence classification | Mastery multiplier |
|---:|---|---|---:|
| 0 | No tutor help | Independent | 1.00 |
| 1 | Ask learner to restate/trace; point to failing observation | Lightly assisted | 0.85 |
| 2 | Conceptual cue or relevant invariant, no target-specific plan | Assisted | 0.65 |
| 3 | Target-specific decomposition/next-step guidance | Heavily assisted | 0.35 |
| 4 | Pseudocode or solution skeleton after gate | Learning-only | 0.00 |
| 5 | Full reviewed explanation after gate | Learning-only | 0.00 |

These are candidate thresholds for pilot comprehension and later calibration. They never turn assisted work into independent evidence. Assessment mode allows level 0 only.

## 7. Mastery transition

| Input | Effect |
|---|---|
| Passive view, scroll, video completion | No mastery change |
| Valid independent practice | Update mastery and confidence with practice evidence class |
| Assisted practice levels 1–3 | Update separate assisted evidence and bounded estimate; cannot satisfy independent gate alone |
| Assistance levels 4–5 | Learning record only; schedule fresh parallel item |
| Valid unseen assessment | Update assessment evidence after finalization |
| Runner/content failure | Zero evidence; preserve attempt and schedule replacement |
| Delayed successful check | Restore retention factor and lengthen interval |
| Delayed failed check | Reopen concept/repair path; preserve historical evidence |
| Scoring-policy change | Shadow/replay first; versioned migration only after approval |

`Mastered` requires estimate ≥0.80, confidence ≥0.65, independent and diverse evidence, unseen assessment, prerequisite readiness, and retention/provisional compliance. The UI must show limited evidence instead of manufacturing precision.

## 8. Workload and recovery

| Situation | Deterministic response |
|---|---|
| Normal day | Fill selected capacity without exceeding it; include one independent action |
| Missed day | Recalculate from remaining calendar capacity; never add backlog on top of today |
| Repeated abandonment | Reduce novelty/difficulty or workload; check one prerequisite; offer target-date change |
| Repeated easy clean success | Skip redundant practice but retain delayed verification |
| Operational outage | Preserve work; no negative evidence; offer retry/replacement |
| Impossible goal/date | Present feasible alternatives and tradeoffs; require learner confirmation |
| Retention due exceeds capacity | Prioritize goal-critical due checks, defer others visibly |

## 9. LLM advisor envelope

| Stage | Authority | Failure response |
|---|---|---|
| Candidate generation | Deterministic engine only | No plan if no safe candidate; operator/content gap event |
| Optional ranking advice | LLM may rank 3–8 supplied IDs and cite supplied evidence | Timeout/invalid output selects deterministic baseline |
| Validation | Deterministic engine rejects unknown IDs, policy violations, stale versions, or unsupported rationale | Baseline choice |
| State write | Deterministic service only | Idempotent retry or no change |
| Rollout | Shadow mode first; then small canary only after approved learning-effect evaluation | Global/per-capability kill switch |

## 10. Safety fallbacks

| Failure | Required behavior |
|---|---|
| LLM unavailable or budget exhausted | Curated/deterministic help; core learning remains usable |
| LLM output leaks solution or fails schema | Suppress output, log safe diagnostic metadata, serve curated hint |
| Item reported broken | Pause scoring; two credible reports quarantine automatically |
| Test/runtime mismatch | Mark operational failure and unscore affected attempts |
| Analytics unavailable | Continue core transaction; durable outbox retries telemetry |
| Queue unavailable | Preserve accepted request exactly once; display delayed state; never double-score |
| Assessment integrity uncertain | Hold evidence and enter human review; never accuse automatically |

