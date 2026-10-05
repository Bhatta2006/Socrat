"""Gold transitions and generated histories for learning evidence invariants."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from socrat.learnerstate.policy import POLICIES, canonical, digest
from socrat.learnerstate.projector import EvidenceFact, replay, state_key

STAMP = 1_790_899_200
KEY = state_key("pack", "python", "loops")


def fact(index=1, **changes):
    value = dict(
        event_id=f"event-{index}",
        user_id="learner",
        goal_id="goal",
        track="foundations",
        sequence=index,
        source_id=f"attempt-{index}",
        pack_id="pack",
        pack_digest="a" * 64,
        language="python",
        concept_ids=["loops"],
        mode="practice",
        evidence_type="implement",
        family_id=f"family_{index}",
        score=1.0,
        quality=1.0,
        hint_level=0,
        valid=True,
        unseen=True,
        finalized=True,
        occurred_at=STAMP + index,
        scoring_version="fixture-1.0.0",
        policy_version="1.0.0",
        policy_digest=digest(POLICIES["1.0.0"].model_dump()),
        reason_code="fixture_scored",
    )
    return EvidenceFact.model_validate({**value, **changes})


def state(facts, as_of=STAMP + 1000, requirements=None):
    return replay(facts, "1.0.0", as_of, requirements)["concepts"][KEY]


def test_weighted_beta_gold_and_assistance_contract():
    expected = [1.0, 0.85, 0.65, 0.35, 0.0, 0.0]
    for level, multiplier in enumerate(expected):
        result = state([fact(hint_level=level)])
        assert result["alpha"] == pytest.approx(2 + 1.2 * multiplier)
        assert result["beta"] == 2
        assert result["mastery_mean"] == pytest.approx(
            (2 + 1.2 * multiplier) / (4 + 1.2 * multiplier)
        )
        assert result["independent_count"] == int(level == 0)
        assert result["assisted_count"] == int(level in {1, 2, 3})
        assert result["band"] not in {"mastered", "provisionally_mastered"}
    failed = state([fact(score=0.0)])
    assert failed["beta"] == 3.2 and failed["alpha"] == 2


@pytest.mark.parametrize(
    "changes",
    [
        dict(mode="passive"),
        dict(valid=False),
        dict(quality=0.0),
        dict(finalized=False),
        dict(hint_level=4),
        dict(hint_level=5),
    ],
)
def test_non_evidence_never_changes_capability(changes):
    result = state([fact(**changes)])
    assert (result["alpha"], result["beta"], result["confidence"], result["evidence_count"]) == (
        2,
        2,
        0,
        0,
    )
    assert result["band"] == "insufficient_evidence"


@settings(max_examples=35, deadline=None)
@given(
    st.lists(
        st.tuples(st.floats(min_value=0, max_value=1, allow_nan=False), st.integers(0, 5)),
        min_size=1,
        max_size=35,
    )
)
def test_generated_history_replay_dedup_bounds_and_event_cap(history):
    facts = [
        fact(index, score=score, hint_level=level)
        for index, (score, level) in enumerate(history, 1)
    ]
    expected = replay(facts, "1.0.0", STAMP + 1000)
    assert canonical(replay(list(reversed(facts)) + facts, "1.0.0", STAMP + 1000)) == canonical(
        expected
    )
    result = expected["concepts"][KEY]
    for field in ("mastery_mean", "confidence", "retention_factor", "effective_mastery"):
        assert 0 <= result[field] <= 1
    previous = 0.5
    for end in range(1, len(facts) + 1):
        current = state(facts[:end])["mastery_mean"]
        assert abs(current - previous) <= 0.150000000001
        previous = current


def test_gaps_conflicting_duplicates_sources_and_corrections_rejected():
    with pytest.raises(ValueError, match="gap"):
        state([fact(2)])
    with pytest.raises(ValueError, match="duplicate"):
        state([fact(), fact(score=0.0)])
    with pytest.raises(ValueError, match="source"):
        state([fact(), fact(2, source_id="attempt-1")])
    with pytest.raises(ValueError, match="clock"):
        state([fact()], as_of=0)
    with pytest.raises(ValueError, match="target"):
        state([fact(kind="invalidated", target_event_id="missing")])
    with pytest.raises(ValueError, match="scope"):
        state(
            [
                fact(),
                fact(
                    2,
                    kind="invalidated",
                    source_id="attempt-1",
                    target_event_id="event-1",
                    language="java",
                ),
            ]
        )


def test_family_caps_independent_diversity_and_attribution():
    repeated = [fact(index, family_id="same_family") for index in range(1, 30)]
    result = state(repeated)
    assert result["alpha"] == 3.8
    assert result["independent_successes"] == 1
    assert result["confidence"] < 0.1
    split = state([fact(concept_ids=["loops", "arrays"])])
    assert split["alpha"] == 2.6
    assisted_forms = [
        fact(index, hint_level=1, evidence_type="trace" if index % 2 else "explain")
        for index in range(1, 45)
    ]
    result = state(assisted_forms)
    assert result["independent_forms"] == []
    assert result["band"] not in {"mastered", "provisionally_mastered"}


def test_mastery_requires_unseen_assessment_prerequisite_and_delayed_check():
    facts = [
        fact(index, evidence_type=["implement", "trace", "explain"][index % 3])
        for index in range(1, 50)
    ]
    assert state(facts)["band"] == "capable"
    facts.append(fact(50, mode="assessment", evidence_type="transfer"))
    assert state(facts)["band"] == "provisionally_mastered"
    requirements = {KEY: {"prerequisites": {state_key("pack", "python", "arrays"): 0.75}}}
    assert state(facts, requirements=requirements)["band"] == "capable"
    facts.append(fact(51, mode="retention", evidence_type="retain", occurred_at=STAMP + 8 * 86400))
    assert state(facts, as_of=STAMP + 8 * 86400)["band"] == "mastered"
    later = state(facts, as_of=STAMP + 80 * 86400)
    assert later["band"] == "retention_due" and later["retention_factor"] == 0.65
    assert later["mastery_mean"] == state(facts, as_of=STAMP + 8 * 86400)["mastery_mean"]
    facts.append(
        fact(
            52, mode="retention", evidence_type="retain", score=0.0, occurred_at=STAMP + 81 * 86400
        )
    )
    assert state(facts, as_of=STAMP + 81 * 86400)["band"] == "capable"


def test_misconception_needs_two_distinct_counterexamples_and_delayed_success():
    facts = [
        fact(score=0.0, misconception_codes=["boundary"]),
        fact(2),
        fact(3, family_id="family_2"),
    ]
    assert state(facts)["misconceptions"]["boundary"]["resolved"] is False
    facts.append(fact(4))
    assert state(facts)["misconceptions"]["boundary"]["counterexamples"] == 2
    facts.append(fact(5, mode="retention", evidence_type="retain", occurred_at=STAMP + 8 * 86400))
    assert state(facts, as_of=STAMP + 8 * 86400)["misconceptions"]["boundary"]["resolved"] is True


def test_invalidation_preserves_history_and_removes_evidence_effect():
    original = fact()
    correction = fact(
        2,
        kind="invalidated",
        source_id=original.source_id,
        target_event_id=original.event_id,
        quality=0.0,
        valid=False,
    )
    result = state([original, correction])
    assert result["alpha"] == 2 and result["evidence_count"] == 0
    assert original.score == 1.0 and original.valid is True


@pytest.mark.parametrize(
    "changes",
    [
        dict(score=float("nan")),
        dict(quality=float("inf")),
        dict(score=-0.01),
        dict(mode="assessment", hint_level=1),
        dict(concept_ids=["loops", "loops"]),
    ],
)
def test_malformed_evidence_fails_closed(changes):
    with pytest.raises(ValidationError):
        fact(**changes)
