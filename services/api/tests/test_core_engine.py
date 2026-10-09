"""Pure engine behaviour: catalog integrity, mastery, placement, planning, Socratic policy."""

import random
from datetime import date

import pytest
from catalog_support import algo, basics, catalog

from socrat.assistant.socratic import (
    Ladder,
    advance,
    genuine,
    leaks,
    parse_level,
    reveal_eligibility,
)
from socrat.catalog.registry import CatalogError, build
from socrat.catalog.schema import Course
from socrat.mastery.model import DAY, ConceptState, apply, band, placed
from socrat.placement import engine as placement
from socrat.planner.engine import build_plan, pace_of

NOW = 1_800_000_000
TODAY = date(2027, 1, 4)  # Monday


def test_catalog_orders_cross_course_prerequisites():
    cat = catalog()
    path = cat.closure(cat.course_concepts("algo"))
    assert path[:3] == ["basics:values", "basics:loops", "basics:functions"]
    assert path.index("algo:arrays") < path.index("algo:two-pointers") < path.index("algo:bfs")
    assert cat.module_of("algo:bfs") == "graphs"
    assert [t.input for t in cat.public_tests("double")] == ["2\n"]


def test_catalog_rejects_cycles_unknown_refs_and_orphans():
    payload = basics().model_dump(mode="json")
    payload["concepts"][0]["prerequisites"] = ["functions"]
    with pytest.raises(CatalogError, match="cycle"):
        build([Course.model_validate(payload)])
    payload = algo().model_dump(mode="json")
    with pytest.raises(CatalogError, match="unknown prerequisite"):
        build([Course.model_validate(payload)])
    payload = basics().model_dump(mode="json")
    payload["modules"][1]["concepts"] = []
    with pytest.raises(ValueError):
        build([Course.model_validate(payload)])
    payload = basics().model_dump(mode="json")
    payload["concepts"][0]["problems"] = ["missing"]
    with pytest.raises(CatalogError, match="unknown problem"):
        build([Course.model_validate(payload)])


def test_mastery_requires_independent_evidence_and_caps_steps():
    state = ConceptState()
    big = apply(state, "checkpoint", 1.0, NOW)
    assert big.mean - state.mean <= 0.15 + 1e-9
    assisted = state
    independent = state
    for i in range(8):
        assisted = apply(assisted, "code", 1.0, NOW + i, assistance=5)
        independent = apply(independent, "code", 1.0, NOW + i)
    assert independent.mastered(NOW + 10)
    assert assisted.mean < independent.mean
    assert assisted.independent_successes == 0 and assisted.assisted_successes == 8
    failing = apply(independent, "review", 0.0, NOW + 20)
    assert failing.review_step == 0 and failing.next_review_at == NOW + 20 + DAY


def test_placement_prior_is_not_verified_mastery():
    known = placed(True, NOW)
    assert known.assumed and not known.mastered(NOW)
    assert band(known, NOW) == "likely_known"
    confirmed = apply(known, "review", 1.0, NOW + DAY)
    assert not confirmed.assumed or confirmed.evidence_count == 1
    assert band(ConceptState(), NOW) == "not_started"


def test_overdue_reviews_decay_effective_mastery():
    state = ConceptState(alpha=9, beta=1, evidence_count=6, next_review_at=NOW)
    assert state.effective(NOW) == state.mean
    assert state.effective(NOW + 20 * DAY) < state.mean


@pytest.mark.parametrize("knows", range(0, 7))
def test_placement_finds_the_frontier(knows):
    cat = catalog()
    path = cat.closure(cat.course_concepts("algo"))
    state = placement.start(cat, path, "algo:arrays", seed=7)
    while not state.done:
        item = placement.question(cat, state)
        assert item is not None
        index = state.pending["index"]
        right = item.shown(placement.seed_of(state))["answer"]
        placement.answer(cat, state, right if index < knows else (right + 1) % len(item.options))
    known = placement.result(state)
    assert [known[c] for c in path] == [i < knows for i in range(len(path))]
    assert len(state.asked) <= placement.MAX_QUESTIONS


def test_absolute_beginner_skips_placement():
    cat = catalog()
    state = placement.start(cat, cat.closure(cat.course_concepts("algo")), None, seed=1)
    assert state.done and not any(placement.result(state).values())


def plan(states=None, completed=(), history=(), weekdays=frozenset({0, 2, 4}), minutes=45):
    cat = catalog()
    return build_plan(
        cat,
        cat.course_concepts("algo"),
        states or {},
        set(completed),
        list(history),
        TODAY,
        NOW,
        set(weekdays),
        minutes,
    )


def test_plan_respects_prerequisites_and_is_deterministic():
    first, second = plan(), plan()
    assert first.to_dict() == second.to_dict()
    order = [a.concept for a in first.queue if a.kind in {"lesson", "quiz", "problem"}]
    positions = {c: order.index(c) for c in dict.fromkeys(order)}
    cat = catalog()
    for concept, index in positions.items():
        for prerequisite in cat.prerequisites[concept]:
            assert positions[prerequisite] < index
    assert first.days[0]["date"] == TODAY.isoformat()
    assert all(day["items"] for day in first.days)


def test_known_concepts_are_skipped_and_reviewed():
    known = {c: placed(True, NOW) for c in ("basics:values", "basics:loops", "basics:functions")}
    result = plan(states=known)
    assert all(a.concept.startswith("algo:") for a in result.queue if a.kind != "checkpoint")
    assert any("Skipped 3" in r for r in result.reasons)
    reviews = [i for d in result.days for i in d["items"] if i["kind"] == "review"]
    assert {r["concept"] for r in reviews} == set(known)


def test_fast_learner_accelerates_and_struggling_learner_gets_support():
    fast = [
        dict(kind="code", score=1.0, assistance=0, elapsed_seconds=300, expected_seconds=600)
    ] * 3
    slow = [
        dict(kind="code", score=0.2),
        dict(kind="quiz", score=1.0),
        dict(kind="code", score=0.3),
    ]
    assert pace_of(fast)[0] == "fast" and pace_of(slow)[0] == "support"
    assert pace_of(fast[:2])[0] == "steady"
    steady, quick = plan(), plan(history=fast)
    assert quick.remaining_minutes < steady.remaining_minutes
    assert quick.projected_finish < steady.projected_finish
    assert "problem:arr-easy" not in {a.id for a in quick.queue}
    assert "problem:arr-easy" in {a.id for a in steady.queue}


def test_repeated_failure_inserts_one_prerequisite_refresher():
    struggling = ConceptState(alpha=1, beta=4, evidence_count=3, failures=3)
    weak_prerequisite = ConceptState(alpha=1, beta=2, evidence_count=1)
    result = plan(states={"algo:two-pointers": struggling, "algo:arrays": weak_prerequisite})
    remedial = [a for a in result.queue if a.kind == "remedial"]
    assert [a.concept for a in remedial] == ["algo:arrays"]
    assert any("refresher" in r for r in result.reasons)


def test_missed_days_never_create_backlog():
    later = build_plan(
        catalog(),
        catalog().course_concepts("algo"),
        {},
        set(),
        [],
        date(2027, 2, 1),
        NOW + 28 * DAY,
        {0, 2, 4},
        45,
    )
    # Missed days are never stacked: each day stays within budget plus <40% of one activity.
    for day in later.days:
        largest = max(item["minutes"] for item in day["items"])
        assert day["minutes"] < 45 + 0.4 * largest or len(day["items"]) == 1
    assert later.days[0]["date"] == "2027-02-01"


def test_simulated_learners_never_violate_prerequisites():
    cat = catalog()
    rng = random.Random(3)
    for _ in range(200):
        states = {
            c: ConceptState(
                alpha=rng.uniform(1, 9), beta=rng.uniform(1, 9), evidence_count=rng.randint(0, 6)
            )
            for c in cat.order
            if rng.random() < 0.6
        }
        result = plan(states=states, weekdays={rng.randint(0, 6)}, minutes=rng.choice([20, 45, 90]))
        seen: set[str] = set()
        for activity in result.queue:
            if activity.kind in {"lesson", "quiz", "problem"}:
                for prerequisite in cat.prerequisites[activity.concept]:
                    assert prerequisite in seen or prerequisite not in {
                        a.concept for a in result.queue
                    }
                seen.add(activity.concept)


def test_socratic_ladder_needs_real_work_to_escalate():
    ladder = Ladder()
    for _ in range(5):
        ladder = advance(ladder, "help", new_attempt=False)
    assert ladder.ceiling == 0
    assert genuine("I tried a loop but it prints the wrong total for the second test", False)
    for _ in range(10):
        ladder = advance(ladder, "", new_attempt=True)
    assert ladder.ceiling == 4 and ladder.turns_at_ceiling == 6


def test_full_answer_requires_struggle():
    assert not reveal_eligibility(Ladder(ceiling=1), failed_submits=0)[0]
    assert not reveal_eligibility(Ladder(ceiling=2), failed_submits=5)[0]
    assert reveal_eligibility(Ladder(ceiling=3), failed_submits=2)[0]
    assert reveal_eligibility(Ladder(ceiling=4, turns_at_ceiling=3), failed_submits=0)[0]


def test_leak_detection():
    reference = "n = int(input())\nprint(sum(x * x for x in range(1, n + 1)))\n"
    code = "```python\nn = int(input())\nprint(n)\n```"
    assert leaks(code, 3) and leaks(code, 4) and not leaks(code, 5)
    assert not leaks("What happens to the total after each step?", 1)
    pseudo = "```text\nfor each value\n  add its square\nprint the total\n```"
    assert leaks(pseudo, 3) and not leaks(pseudo, 4)
    copied = "Try this: print(sum(x * x for x in range(1, n + 1))) and n = int(input())"
    assert leaks(copied, 4, reference)
    assert parse_level("<level>2</level>\nThink about it.") == (2, "Think about it.")
    assert parse_level("No tag") == (None, "No tag")


def test_options_are_shuffled_so_position_never_gives_the_answer_away():
    cat = catalog()
    items = [q for c in cat.concepts.values() for q in c.quiz]
    positions = [q.shown("session-1")["answer"] for q in items]
    # Authors put the right option first; learners must not see it there every time.
    assert positions.count(0) < len(items) * 0.6
    for q in items[:20]:
        shown = q.shown("session-1")
        assert sorted(shown["options"]) == sorted(q.options)
        assert shown["options"][shown["answer"]] == q.options[q.answer]
        assert q.is_correct("session-1", shown["answer"])
        assert not q.is_correct("session-1", -1)
        assert q.shown("session-1") == shown  # stable for the same session
