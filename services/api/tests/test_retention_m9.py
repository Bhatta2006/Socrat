"""Clock-controlled seven-day proof and versioned spaced scheduling."""

import pytest
from test_learner_state import KEY, STAMP, fact

from socrat.learnerstate.projector import replay

DAY = 86400


def history():
    return [
        fact(index, evidence_type=["implement", "trace", "explain"][index % 3])
        for index in range(1, 50)
    ] + [fact(50, mode="assessment", evidence_type="transfer")]


def state(facts, stamp):
    return replay(facts, "1.1.0", stamp)["concepts"][KEY]


def test_two_day_review_is_not_seven_day_mastery_and_practice_does_not_postpone_due():
    facts = history()
    initial = state(facts, STAMP + 1000)
    anchor = initial["first_capable_at"]
    assert initial["band"] == "provisionally_mastered"
    assert initial["due_at"] == anchor + 2 * DAY
    facts.append(fact(51, occurred_at=anchor + DAY))
    assert state(facts, anchor + DAY)["due_at"] == initial["due_at"]
    assert state(facts, initial["due_at"])["band"] == "retention_due"
    facts.append(fact(52, mode="retention", evidence_type="retain", occurred_at=anchor + 2 * DAY))
    early = state(facts, anchor + 2 * DAY)
    assert not early["retention_passed"]
    assert early["band"] == "provisionally_mastered"
    assert early["review_interval_days"] == 7
    facts.append(fact(53, mode="retention", evidence_type="retain", occurred_at=anchor + 9 * DAY))
    late = state(facts, anchor + 9 * DAY)
    assert late["band"] == "mastered" and late["retention_passed"]
    assert late["review_interval_days"] == 14
    assert late["review_representation"] == "mixed_problem"
    assert state(facts, anchor + 10 * DAY)["mastery_mean"] == late["mastery_mean"]


@pytest.mark.parametrize(
    "score,interval,repair", [(0.8, 7, False), (0.79, 2, False), (0.6, 2, False), (0.59, 2, True)]
)
def test_retention_boundary_and_repair_schedule(score, interval, repair):
    facts = history()
    anchor = state(facts, STAMP + 1000)["first_capable_at"]
    facts.append(
        fact(
            51, mode="retention", evidence_type="retain", score=score, occurred_at=anchor + 7 * DAY
        )
    )
    value = state(facts, anchor + 7 * DAY)
    assert value["review_interval_days"] == interval
    assert value["repair_required"] is repair
    if repair:
        assert value["due_at"] is None
        assert value["band"] != "mastered"
        facts.append(fact(52, score=1.0, occurred_at=anchor + 8 * DAY))
        repaired = state(facts, anchor + 8 * DAY)
        assert not repaired["repair_required"]
        assert repaired["due_at"] == anchor + 10 * DAY


def test_replay_correction_removes_retention_and_original_policy_is_preserved():
    facts = history()
    anchor = state(facts, STAMP + 1000)["first_capable_at"]
    delayed = fact(51, mode="retention", evidence_type="retain", occurred_at=anchor + 7 * DAY)
    facts.append(delayed)
    assert state(facts, anchor + 7 * DAY)["retention_passed"]
    facts.append(
        fact(
            52,
            kind="invalidated",
            target_event_id=delayed.event_id,
            source_id=delayed.source_id,
            occurred_at=anchor + 8 * DAY,
        )
    )
    assert not state(facts, anchor + 8 * DAY)["retention_passed"]
    assert state(list(reversed(facts)), anchor + 8 * DAY) == state(facts, anchor + 8 * DAY)
    legacy = replay(history(), "1.0.0", STAMP + 1000)["concepts"][KEY]
    assert "review_interval_days" not in legacy
    assert legacy["due_at"] == STAMP + 50 + 7 * DAY


def test_one_form_expands_once_with_aggregated_concept_score():
    facts = history()
    anchor = state(facts, STAMP + 1000)["first_capable_at"]
    facts.extend(
        [
            fact(
                51,
                mode="retention",
                evidence_type="retain",
                review_group_id="one-form",
                occurred_at=anchor + 7 * DAY,
            ),
            fact(
                52,
                mode="retention",
                evidence_type="retain",
                review_group_id="one-form",
                occurred_at=anchor + 7 * DAY + 20,
            ),
        ]
    )
    value = state(facts, anchor + 7 * DAY + 20)
    assert value["review_interval_days"] == 7
    assert value["due_at"] == anchor + 14 * DAY + 20
