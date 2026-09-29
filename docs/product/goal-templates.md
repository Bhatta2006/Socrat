# Goal templates

The structured form is authoritative. Free text may be parsed into a proposal, but the learner must confirm all required fields. The product never promises employment, interview success, ranking, or a rating increase.

## Common goal contract

Every accepted goal contains:

| Field | Rule |
|---|---|
| `goal_template_id` | `foundations`, `interview`, or `competitive` |
| `language` | `python`, `cpp`, or `java` |
| `target_outcome` | One outcome released by the selected template |
| `target_date` | ISO date or explicit `no_fixed_date`; never inferred silently |
| `days_per_week` | Integer 3–7 |
| `minutes_per_session` | One of 20, 30, 45, 60, 90 |
| `timezone` | Valid IANA time zone confirmed by the learner |
| `coverage_version` | Released coverage matrix used at confirmation |
| `template_version` | Immutable goal-template version |
| `confirmation_at` | UTC timestamp after the learner reviews the normalized statement |

Optional motivation and free text are presentation context only. They do not alter placement, mastery, or eligibility unless converted to a visible structured field and confirmed.

## Template 1 — Foundations

**Learner intent:** “I am starting from zero or need the programming foundations required for DSA.”

Required selection:

- language;
- target outcome: programming readiness, foundational DSA, or interview-entry readiness;
- schedule and date state;
- self-reported language and DSA experience, used only to select the first diagnostic stage.

Normalized statement:

> Build `{target_outcome}` in `{language}` by `{target_date_or_no_fixed_date}`, practicing `{minutes_per_session}` minutes on `{days_per_week}` days each week. Progress will be judged using independent code, explanation, unseen transfer, and delayed checks.

Qualification behavior:

- No prior coding experience is accepted and must never produce rejection.
- A learner who cannot yet write code receives no-code trace and reasoning items before implementation.
- A very experienced learner selecting Foundations may accelerate only after evidence; self-report alone does not skip proof.

Completion evidence:

- independently trace and explain representative programs;
- implement released foundational structures/algorithms in the chosen language;
- solve unseen problems within the declared foundations band;
- pass a delayed retention check.

## Template 2 — Interview

**Learner intent:** “I want evidence-backed readiness for a software-engineering coding interview.”

Required selection:

- language;
- role level: intern, new graduate, early career, or experienced hire;
- target outcome: screen readiness, interview-loop readiness, or topic repair;
- target date and schedule;
- optional company/pattern context, used only where released coverage maps it to explicit competencies.

Normalized statement:

> Reach `{target_outcome}` for `{role_level}` coding interviews in `{language}` by `{target_date_or_no_fixed_date}`, practicing `{minutes_per_session}` minutes on `{days_per_week}` days each week. Readiness will be judged on unseen independent solving, implementation, complexity analysis, communication, and retention—not company outcomes.

Qualification behavior:

- A learner with no/syntax-only language experience is accepted with a Foundations bridge while the declared goal remains Interview.
- Unknown company-specific requirements resolve to the released generic role blueprint, clearly labeled.
- An impossible date produces a feasibility warning and options to reduce coverage, extend the date, or increase a valid time budget; it never produces a guaranteed plan.

Completion evidence:

- independently clarify, design, implement, test, and analyze unseen items;
- meet the released target band on a parallel assessment form;
- show an acceptable assisted-to-independent trend;
- retain representative competencies after delay.

## Template 3 — Competitive

**Learner intent:** “I want to improve contest problem-solving within a declared platform, division, topic, consistency, or rating target.”

Required selection:

- language;
- platform/format: Codeforces, AtCoder, CodeChef, or other;
- target outcome: rating band, division readiness, topic repair, or contest consistency;
- target value (band/division/topics/consistency definition);
- target date and schedule.

Normalized statement:

> Improve `{target_outcome}:{target_value}` for `{platform_or_format}` using `{language}` by `{target_date_or_no_fixed_date}`, practicing `{minutes_per_session}` minutes on `{days_per_week}` days each week. Progress will be judged using timed unseen solving, upsolve repair, proof/complexity, mixed-topic transfer, and retention; no rating result is guaranteed.

Qualification behavior:

- A novice is accepted. If readiness is insufficient, a Foundations bridge or lower released band is proposed transparently.
- A target outside released difficulty/topic coverage produces a precise waitlist outcome.
- External profile/rating data is optional and never trusted as mastery evidence without product-administered work.

Completion evidence:

- improved timed independent solve rate at the released target band;
- successful upsolve and misconception repair;
- mixed-topic transfer and implementation reliability;
- delayed retention.

## Examples

### Valid

```json
{
  "goal_template_id": "interview",
  "language": "cpp",
  "role_level": "new_grad",
  "target_outcome": "interview_loop_readiness",
  "target_date": "2027-01-15",
  "days_per_week": 5,
  "minutes_per_session": 60,
  "timezone": "Asia/Kolkata"
}
```

### Valid with bridge

```json
{
  "goal_template_id": "competitive",
  "language": "python",
  "platform_or_format": "codeforces",
  "target_outcome": "rating_band",
  "target_value": "released_novice_band",
  "language_experience": "none",
  "days_per_week": 4,
  "minutes_per_session": 30,
  "timezone": "Asia/Kolkata",
  "routing_outcome": "accept_with_foundations_bridge"
}
```

### Invalid

```json
{
  "goal_template_id": "interview",
  "language": "javascript",
  "target_outcome": "get_a_job",
  "days_per_week": 1,
  "minutes_per_session": 10
}
```

This is invalid because the language and promised outcome are unsupported, the minimum commitment is not met, and required fields are missing. The UI must return separate reason codes rather than a generic error.

## Acceptance tests

- A complete beginner can confirm a Foundations goal without lying about experience.
- An interview or competitive learner with low readiness is accepted with a bridge, not relabeled without explanation.
- Every required field appears in the normalized statement or affects a documented decision.
- Unsupported language and unreleased competitive coverage never proceed to diagnosis.
- The same structured inputs and contract version produce the same routing outcome and reason codes.
- Free-text parsing can be fully disabled without blocking goal creation.

