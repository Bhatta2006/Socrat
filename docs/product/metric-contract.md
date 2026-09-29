# Metric contract

**Status:** Candidate for M0 sign-off  
**Reporting rule:** Every metric is segmented by goal track and language. Aggregate success cannot hide a failing launch cell.

## Unit conventions

- Calendar windows use the learner’s confirmed IANA time zone; storage timestamps remain UTC.
- A “day” is a learner-local calendar day unless a duration is explicitly stated in hours.
- Users are deduplicated by canonical account after confirmed account merges.
- Test, staff, synthetic, deleted-before-eligibility, and known-corrupt records are excluded with reason codes.
- Metric queries and event schemas are versioned. Backfills never overwrite the prior published result.

## Primary outcome

### Independent solve-rate delta

For each eligible learner:

`final independent correct items / final eligible items - baseline independent correct items / baseline eligible items`

Use parallel unseen forms matched by blueprint and calibrated difficulty. Exclude assisted attempts, invalid/quarantined items, and operational failures. Report the median learner delta, confidence interval, completion sensitivity, and track/language segments. Do not compare raw counts across unequal forms.

### Incremental efficacy

`median adaptive-cohort delta - median fixed-plan-cohort delta`

The control receives the same content inventory, assessment schedule, runtime, and support availability; only sequencing/adaptation differs. Assignment is stable before first plan exposure. The initial go threshold is ≥10 percentage points with completion non-inferior by more than five points.

## Funnel and retention

| Metric | Numerator | Denominator | Window | Target |
|---|---|---|---|---:|
| Qualification completion | Users receiving accepted/waitlist/ineligible reasoned result | Eligibility flow starters | 24 h | Observe in pilot |
| Activation | Qualified users confirming goal, completing diagnostic, and starting first plan | Qualified created users | 48 h | ≥55% |
| Week-one practice | Activated users completing ≥4 meaningful sessions | Activated users | First 7 local days | ≥35% |
| D1/D7/D30 retention | Activated users with a meaningful session on the named local-day window | Activated users eligible to reach window | Defined window | D7 ≥35%, D30 ≥20% |
| Program completion | Activated users finalizing and viewing final assessment | Activated users | Program window + grace | ≥30% |

A meaningful session contains a finalized valid action: independent/assisted exercise submission, completed diagnostic/assessment item, or completed retention check. Login, passive content view, reminder open, or tutor-only chat does not qualify.

## Quality and safety

| Metric | Definition | Gate |
|---|---|---:|
| Material exercise defect rate | Released attempted exercises with confirmed correctness, ambiguity, test, or runtime defect / released attempted exercises | <2% after closed beta |
| Premature solution leakage | Audited tutor outputs semantically revealing the solution before allowed escalation / audited tutor outputs | <3% |
| Material tutor factual error | Audited tutor outputs with a learning-relevant factual error / audited outputs | <3% |
| Runner success | Valid jobs completing expected platform outcome / accepted valid jobs, segmented by runtime | ≥99.5% |
| False mastery | Concepts labeled Mastered that fail the next eligible independent check / Mastered concepts receiving a check | <15% |
| Plan duration error | `abs(actual - planned) / planned` for completed normal sessions | Median ≤20% after calibration |

## Guardrails

- No increase in tutor usage can compensate for worse independent outcomes.
- No engagement metric may change mastery.
- Dropout is not silently scored as failure; report bounds and completion sensitivity.
- Learners affected by material item/scoring incidents are identified, repaired, and included/excluded according to a versioned incident decision.
- Any experiment stops for a critical privacy/security issue, material assessment contamination, >5% confirmed content defects, or a segment-level severe regression.

## Event minimums

Every decision-bearing event carries:

- `event_id`, `event_name`, `event_schema_version`;
- `occurred_at_utc`, `received_at_utc`, `learner_timezone` where applicable;
- pseudonymous `user_id`, `goal_id`, `track`, `language`;
- relevant content, graph, policy, model, experiment, runtime, and prompt versions;
- attempt/session/assessment identifiers;
- assistance and independence classification;
- operational validity and exclusion reason;
- deterministic reason code for material decisions.

Raw code, free text, email, tutor transcript, and provider payloads are not copied into general analytics events. Store sensitive artifacts in access-controlled purpose-specific systems and link through opaque identifiers.

## Pilot decision metrics

M0 uses comprehension and problem proof rather than efficacy:

- ≥12/15 demonstrate the problem without prompted agreement;
- ≥10/15 prefer the proposed daily-loop concept over their current planning workflow;
- ≥12/15 can restate their confirmed goal and next action;
- ≥11/15 correctly distinguish assisted practice from independent proof;
- no track has a recurring critical misunderstanding without an accepted remediation.

These thresholds are product decisions for this pilot, not statistical evidence of market size or learning efficacy.

