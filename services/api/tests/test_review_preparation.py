"""Review packets preserve pending decisions and keep provider contexts bounded."""

import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

from socrat.learning.pilot import PilotDraft

ROOT = Path(__file__).resolve().parents[3]


def builder():
    spec = importlib.util.spec_from_file_location(
        "review_preparation", ROOT / "scripts/validation/prepare-m7-m8-reviews.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pending_review_coverage_and_private_context_boundaries():
    draft = PilotDraft.model_validate_json(
        (ROOT / "contracts/content/m7-arrays-pilot-draft.json").read_text(encoding="utf-8")
    )
    packet = builder().prepare(draft)
    assert packet["draft_digest"] == draft.report()["draft_digest"]
    assert not packet["release_approved"]
    assert len(packet["m7_tasks"]) == 210
    assert all(x["status"] == "pending" and x["decision"] is None for x in packet["m7_tasks"])
    cases = packet["m8_cases"]
    assert len({x["case_id"] for x in cases}) == 504
    counts = Counter((x["track"], x["language"]) for x in cases)
    assert len(counts) == 9 and set(counts.values()) == {56}
    for case in cases:
        assert case["status"] == "not_executed" and case["model_output"] is None
        assert set(case["judgments"].values()) == {None}
        context = json.dumps(case["context"])
        assert "reference_solution" not in context and "expected" not in case["context"]
        assert "tests" not in case["context"] and "reviewer" not in context
        assert case["language_reviewer"] == (
            "Ramakrishna" if case["language"] == "cpp" else "Sathish"
        )


def test_generation_preserves_existing_review_work(tmp_path, monkeypatch):
    module = builder()
    output = tmp_path / "reviews"
    monkeypatch.setattr("sys.argv", ["prepare", "--output", str(output)])
    module.main()
    queue = output / "review-queue.json"
    queue.write_text("private review in progress", encoding="utf-8")
    with pytest.raises(SystemExit):
        module.main()
    assert queue.read_text(encoding="utf-8") == "private review in progress"
