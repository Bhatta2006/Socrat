from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st
from m5_support import planner_pack

from socrat.planning.engine import adapt, build_plan, ready
from socrat.planning.policy import POLICY

PACK = planner_pack()
TODAY = date(2026, 10, 5)


def plan(**changes):
    values = dict(
        pack=PACK,
        track="foundations",
        language="python",
        states={},
        today=TODAY,
        as_of=1791158400,
        weekdays=[0, 1, 2, 3],
        minutes=30,
        target_date="no_fixed_date",
        history=[],
        exposures={},
    )
    return build_plan(**{**values, **changes})


@settings(max_examples=2000, deadline=None, derandomize=True)
@given(
    track=st.sampled_from(["foundations", "interview", "competitive"]),
    language=st.sampled_from(["python", "cpp", "java"]),
    minutes=st.integers(20, 90),
    missed=st.integers(0, 10),
    mastery=st.lists(
        st.floats(0, 1, allow_nan=False, allow_infinity=False),
        min_size=len(PACK.concepts),
        max_size=len(PACK.concepts),
    ),
    confidence=st.floats(0, 1, allow_nan=False, allow_infinity=False),
    scores=st.lists(st.floats(0, 1, allow_nan=False, allow_infinity=False), max_size=20),
)
def test_two_thousand_histories_reproduce_and_preserve_prerequisites_capacity(
    track, language, minutes, missed, mastery, confidence, scores
):
    states = {
        concept.id: dict(
            effective_mastery=value,
            confidence=confidence,
            independent_successes=2,
            due_at=0,
            missing_gates=["unseen_assessment_required"],
        )
        for concept, value in zip(PACK.concepts, mastery, strict=True)
    }
    history = [
        dict(
            sequence=index + 1,
            mode=["practice", "assessment", "retention"][index % 3],
            valid=index % 7 != 0,
            finalized=True,
            hint_level=0 if index % 3 else 4,
            family_id=f"family_{index % 6}",
            concept_ids=[PACK.concepts[index % len(PACK.concepts)].id],
            score=score,
            difficulty=1,
            unseen=True,
            evidence_type="explain" if index % 2 else "implement",
            elapsed_seconds=30 + index * 10,
            expected_seconds=60,
            misconception_codes=["synthetic_boundary"] if score < 0.4 else [],
        )
        for index, score in enumerate(scores)
    ]
    values = dict(
        track=track,
        language=language,
        minutes=minutes,
        states=states,
        missed_days=missed,
        history=history,
        previous=dict(difficulty=1, changed_on="2026-10-01", watermark=0),
    )
    actual = plan(**values)
    assert actual == plan(**values)
    for day in actual["days"]:
        assert sum(x["minutes"] for x in day["blocks"]) <= day["capacity_minutes"] <= minutes
        if not day["blocks"]:
            continue
        assert sum(x["mode"] == "independent" for x in day["blocks"]) == 1
        assert all(x["minutes"] > 0 for x in day["blocks"])
        assert sum(x["minutes"] for x in day["blocks"] if x["mode"] == "retrieval") <= int(
            day["capacity_minutes"] * POLICY.review_fraction
        )
        for block in day["blocks"]:
            for key in block["concept_ids"]:
                for edge in PACK.edges:
                    if edge.concept == key:
                        assert ready(
                            states[edge.prerequisite], max(POLICY.readiness, edge.minimum_mastery)
                        )
            for key in block["exercise_ids"]:
                item = next(x for x in PACK.exercises if x.id == key)
                assert item.inventory == "practice" and item.modality == "text"


def test_unknown_prior_does_not_unlock_and_equal_candidates_do_not_starve():
    actual = plan()
    selected = [
        key for day in actual["days"] for block in day["blocks"] for key in block["exercise_ids"]
    ]
    assert len(set(selected)) >= 6
    assert any(node["blocked_by"] for node in actual["nodes"])
    assert all(
        "protected_inventory" in x["rejected_by"]
        for x in actual["decisions"]
        if next(item for item in PACK.exercises if item.id == x["exercise_id"]).inventory
        == "assessment"
    )


def test_impossible_date_and_operational_gap_are_explicit():
    assert plan(target_date="2026-10-04")["feasibility"] == "date_unfeasible"
    exposure = {x.id: {"count": 3, "last_date": TODAY.isoformat()} for x in PACK.exercises}
    actual = plan(exposures=exposure)
    assert all(not x["blocks"] for x in actual["days"])
    assert any(x["status"] == "content_gap" for x in actual["days"])


def test_difficulty_dwell_and_evidence_consumption_prevent_oscillation():
    history = [
        dict(
            valid=True,
            finalized=True,
            sequence=i,
            hint_level=0,
            mode="practice",
            family_id=f"f{i}",
            score=0.9,
            difficulty=1,
        )
        for i in range(1, 4)
    ]
    prior = dict(difficulty=1, changed_on="2026-10-01", watermark=0)
    raised = adapt(history, prior, TODAY, "foundations")
    assert raised["difficulty"] == 2
    assert adapt(history, raised, TODAY, "foundations")["difficulty"] == 2
    failures = history + [
        dict(
            valid=True,
            finalized=True,
            sequence=i,
            hint_level=0,
            mode="practice",
            family_id=f"f{i}",
            score=0.1,
            difficulty=2,
        )
        for i in range(4, 6)
    ]
    assert adapt(failures, raised, date(2026, 10, 6), "foundations")["difficulty"] == 2
    assert adapt(failures, raised, date(2026, 10, 8), "foundations")["difficulty"] == 1
    invalid = [{**x, "valid": False} for x in failures[3:]]
    assert adapt(invalid, raised, date(2026, 10, 8), "foundations")["difficulty"] == 2
