"""The resource pool must preserve provenance and never let metadata bypass policy."""

import json

import pytest
from pydantic import ValidationError

from socrat.dsa_resource_pool import (
    AdvisorChoice,
    LearnerSnapshot,
    ResourcePool,
    build_resource_pool,
    choose_next,
    load_resource_pool,
    topics_for,
    validate_advisor_choice,
)


def test_import_deduplicates_company_windows_and_solution_appearances(tmp_path):
    companies = tmp_path / "companies" / "Acme"
    companies.mkdir(parents=True)
    header = "Difficulty,Title,Frequency,Acceptance Rate,Link,Topics\n"
    row = 'EASY,Two Sum,91,0.48,https://leetcode.com/problems/two-sum/,"Array, Hash Table"\n'
    (companies / "1. Thirty Days.csv").write_text(header + row, encoding="utf-8")
    (companies / "5. All.csv").write_text(header + row, encoding="utf-8")
    solution = tmp_path / "striver" / "01.Arrays" / "1.Easy"
    solution.mkdir(parents=True)
    (solution / "01. Two Sum.cpp").write_text("// reference only", encoding="utf-8")
    pool = build_resource_pool(tmp_path, cses_html="")

    item = next(item for item in pool.resources if item.id == "leetcode:two-sum")
    assert item.kind == "problem"
    assert item.difficulty.band == 2
    assert item.difficulty.basis == "provider_label"
    assert {"arrays", "hash-maps"} <= set(item.topics)
    assert len(item.company_signals) == 2
    assert len([ref for ref in item.references if ref.role == "solution"]) == 1
    assert (
        next(ref for ref in item.references if ref.role == "solution").match_basis
        == "exact_title_unverified"
    )
    assert item.release_status == "review_required"


def test_cses_index_keeps_problem_ids_and_marks_difficulty_provisional(tmp_path):
    html = (
        '<h2>Introductory Problems</h2><ul class="task-list">'
        '<li class="task"><a href="/problemset/task/1068">Weird Algorithm</a></li>'
        '</ul><h2>Dynamic Programming</h2><ul class="task-list">'
        '<li class="task"><a href="/problemset/task/1634">Minimizing Coins</a></li>'
        "</ul>"
    )
    pool = build_resource_pool(tmp_path, cses_html=html)
    intro = next(item for item in pool.resources if item.id == "cses:1068")
    dp = next(item for item in pool.resources if item.id == "cses:1634")

    assert intro.url == "https://cses.fi/problemset/task/1068"
    assert intro.difficulty.status == "provisional"
    assert dp.topics == ["dynamic-programming"]
    assert dp.difficulty.band > intro.difficulty.band


def test_cses_advanced_categories_have_priors_but_interactive_is_excluded(tmp_path):
    html = (
        '<h2>Advanced Graph Problems</h2><ul class="task-list">'
        '<li class="task"><a href="/problemset/task/4001">Hard Route</a></li></ul>'
        '<h2>Sliding Window Problems</h2><ul class="task-list">'
        '<li class="task"><a href="/problemset/task/4002">Window Task</a></li></ul>'
        '<h2>Interactive Problems</h2><ul class="task-list">'
        '<li class="task"><a href="/problemset/task/4003">Secret Task</a></li></ul>'
    )
    pool = build_resource_pool(tmp_path, cses_html=html)
    by_id = {item.id: item for item in pool.resources}
    assert "graphs" in by_id["cses:4001"].topics
    assert by_id["cses:4001"].difficulty.band == 8
    assert "sliding-window" in by_id["cses:4002"].topics
    assert by_id["cses:4002"].difficulty.band == 5
    assert by_id["cses:4003"].scope == "out_of_scope"


def test_selector_enforces_release_prerequisites_exposure_and_language():
    pool = ResourcePool.model_validate(
        {
            "schema_version": 1,
            "sources": [],
            "resources": [
                candidate("leetcode:arrays", "arrays", 2),
                candidate("leetcode:graphs", "graphs", 5),
                candidate("leetcode:wrong-language", "arrays", 2, languages=["cpp"]),
                candidate("leetcode:already-solved", "arrays", 2),
                candidate("leetcode:unreviewed", "arrays", 2, status="review_required"),
                candidate("leetcode:solution", "arrays", 2, kind="solution"),
            ],
        }
    )
    learner = LearnerSnapshot(
        track="interview",
        language="python",
        ready_topics=["language-readiness", "arrays"],
        released_topics=["arrays"],
        target_topics=["arrays", "graphs"],
        target_difficulty=2,
        time_budget_minutes=30,
        solved_ids=["leetcode:already-solved"],
    )

    decision = choose_next(pool, learner)
    assert [item.id for item in decision.candidates] == ["leetcode:arrays"]
    assert decision.baseline_id == "leetcode:arrays"
    assert decision.policy_version


def test_company_affinity_only_reranks_eligible_items():
    first = candidate("leetcode:first", "arrays", 2)
    second = candidate("leetcode:second", "arrays", 2)
    second["company_signals"] = [{"company": "Acme", "window": "thirty_days", "frequency": 90.0}]
    pool = ResourcePool.model_validate(
        {"schema_version": 1, "sources": [], "resources": [first, second]}
    )
    learner = LearnerSnapshot(
        track="interview",
        language="python",
        ready_topics=["language-readiness", "arrays"],
        released_topics=["arrays"],
        target_topics=["arrays"],
        target_difficulty=2,
        time_budget_minutes=30,
        target_company="Acme",
    )

    decision = choose_next(pool, learner)
    assert decision.baseline_id == "leetcode:second"


def test_advisor_can_only_rerank_current_candidate_snapshot():
    pool = ResourcePool.model_validate(
        {
            "schema_version": 1,
            "sources": [],
            "resources": [
                candidate("leetcode:first", "arrays", 2),
                candidate("leetcode:second", "arrays", 2),
            ],
        }
    )
    learner = LearnerSnapshot(
        track="interview",
        language="python",
        ready_topics=["language-readiness", "arrays"],
        released_topics=["arrays"],
        target_topics=["arrays"],
        target_difficulty=2,
        time_budget_minutes=30,
    )
    decision = choose_next(pool, learner)
    invalid = AdvisorChoice(
        policy_version=decision.policy_version,
        input_snapshot_hash=decision.input_snapshot_hash,
        recommended_candidate_ids=["leetcode:invented"],
        evidence_refs=["recent_attempt:1"],
        reason_codes=["difficulty_fit"],
        confidence=0.9,
    )
    assert (
        validate_advisor_choice(decision, invalid, allowed_evidence_refs={"recent_attempt:1"})
        == "leetcode:first"
    )
    valid = AdvisorChoice(
        policy_version=decision.policy_version,
        input_snapshot_hash=decision.input_snapshot_hash,
        recommended_candidate_ids=["leetcode:second"],
        evidence_refs=["recent_attempt:1"],
        reason_codes=["difficulty_fit"],
        confidence=0.9,
    )
    assert (
        validate_advisor_choice(decision, valid, allowed_evidence_refs={"recent_attempt:1"})
        == "leetcode:second"
    )
    stale = valid.model_copy(update={"input_snapshot_hash": "0" * 64})
    assert (
        validate_advisor_choice(decision, stale, allowed_evidence_refs={"recent_attempt:1"})
        == "leetcode:first"
    )
    assert json.loads(decision.model_dump_json())["candidates"][0]["id"] == "leetcode:first"


def test_released_item_requires_reviewed_primary_topic_and_rights():
    item = candidate("leetcode:unverified", "arrays", 2)
    item.pop("primary_topic")
    with pytest.raises(ValidationError):
        ResourcePool.model_validate({"schema_version": 1, "sources": [], "resources": [item]})


def test_performance_moves_one_band_and_prioritizes_due_topic():
    pool = ResourcePool.model_validate(
        {
            "schema_version": 1,
            "sources": [],
            "resources": [
                candidate("leetcode:easy", "arrays", 2),
                candidate("leetcode:next", "arrays", 3),
            ],
        }
    )
    learner = LearnerSnapshot(
        track="interview",
        language="python",
        ready_topics=["language-readiness", "arrays"],
        released_topics=["arrays"],
        target_topics=["arrays"],
        target_difficulty=2,
        time_budget_minutes=30,
        recent_performance=[
            {
                "topic": "arrays",
                "difficulty_band": 2,
                "success": True,
                "independent": True,
                "within_expected_time": True,
            }
            for _ in range(3)
        ],
    )
    assert choose_next(pool, learner).baseline_id == "leetcode:next"
    learner = LearnerSnapshot.model_validate(
        {
            **learner.model_dump(),
            "recent_performance": [
                {
                    "topic": "arrays",
                    "difficulty_band": 2,
                    "success": False,
                    "independent": True,
                    "within_expected_time": False,
                }
                for _ in range(2)
            ],
        }
    )
    assert choose_next(pool, learner).baseline_id == "leetcode:easy"


def test_non_dsa_company_rows_remain_out_of_scope(tmp_path):
    folder = tmp_path / "companies" / "Acme"
    folder.mkdir(parents=True)
    (folder / "5. All.csv").write_text(
        "Difficulty,Title,Frequency,Acceptance Rate,Link,Topics\n"
        "EASY,Big Countries,30,0.5,https://leetcode.com/problems/big-countries/,Database\n",
        encoding="utf-8",
    )
    pool = build_resource_pool(tmp_path, cses_html="")
    assert pool.resources[0].scope == "out_of_scope"


def test_unreleased_taxonomy_topic_cannot_be_assigned():
    pool = ResourcePool.model_validate(
        {
            "schema_version": 1,
            "sources": [],
            "resources": [candidate("leetcode:graphs", "graphs", 2)],
        }
    )
    learner = LearnerSnapshot(
        track="interview",
        language="python",
        ready_topics=["language-readiness", "arrays", "recursion", "trees"],
        released_topics=["arrays"],
        target_topics=["graphs"],
        target_difficulty=2,
        time_budget_minutes=30,
    )
    assert choose_next(pool, learner).baseline_id is None


def test_weak_concept_outranks_strong_concept_after_prerequisites():
    pool = ResourcePool.model_validate(
        {
            "schema_version": 1,
            "sources": [],
            "resources": [
                candidate("leetcode:arrays", "arrays", 2),
                candidate("leetcode:hash-maps", "hash-maps", 2),
            ],
        }
    )
    learner = LearnerSnapshot(
        track="interview",
        language="python",
        ready_topics=["language-readiness", "arrays"],
        released_topics=["arrays", "hash-maps"],
        target_topics=["arrays", "hash-maps"],
        target_difficulty=2,
        time_budget_minutes=30,
        topic_mastery={"arrays": 0.9, "hash-maps": 0.2},
        misconception_topics=["hash-maps"],
    )
    assert choose_next(pool, learner).baseline_id == "leetcode:hash-maps"


def test_repo_section_names_map_to_stable_topics():
    assert "trees" in topics_for("11. Binary Trees")
    assert "heaps" in topics_for("09. Heaps")
    assert "graphs" in topics_for("Graph Algorithms")
    assert "number-theory" in topics_for("Mathematics")


def test_roadmap_week_supplies_topic_when_filename_is_generic(tmp_path):
    folder = tmp_path / "roadmap" / "Week1" / "Day1"
    folder.mkdir(parents=True)
    (folder / "brute_force.py").write_text("pass", encoding="utf-8")
    pool = build_resource_pool(tmp_path, cses_html="")
    item = next(item for item in pool.resources if item.provider == "roadmap")
    assert "arrays" in item.topics


def test_generated_pool_round_trips_from_line_index(tmp_path):
    resources_path = tmp_path / "dsa-resources.jsonl"
    summary_path = tmp_path / "dsa-resource-summary.json"
    resources_path.write_text(
        json.dumps(candidate("leetcode:two-sum", "arrays", 2)) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(json.dumps({"schema_version": 1, "snapshots": []}), encoding="utf-8")
    loaded = load_resource_pool(resources_path, summary_path)
    assert loaded.resources[0].id == "leetcode:two-sum"


def candidate(
    item_id: str,
    topic: str,
    difficulty: int,
    *,
    languages: list[str] | None = None,
    status: str = "released",
    kind: str = "problem",
) -> dict:
    return {
        "id": item_id,
        "kind": kind,
        "title": item_id,
        "url": "https://leetcode.com/problems/example/",
        "provider": "leetcode",
        "topics": [topic],
        "primary_topic": topic,
        "difficulty": {"band": difficulty, "status": "calibrated", "basis": "reviewed"},
        "languages": languages or ["python", "cpp", "java"],
        "tracks": ["foundations", "interview", "competitive"],
        "expected_minutes": 20,
        "release_status": status,
        "scope": "dsa_candidate",
        "rights_reviewed_at": "2026-09-30" if status == "released" else None,
        "delivery": "external_link",
        "references": [],
        "company_signals": [],
    }
