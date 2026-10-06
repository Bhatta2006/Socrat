"""Pilot drafts must stay unreviewed, complete, deterministic and non-executable."""

import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from socrat.learning.pilot import PilotDraft
from socrat.skillpacks.schema import SkillPack

ROOT = Path(__file__).resolve().parents[3]
DRAFT = ROOT / "contracts/content/m7-arrays-pilot-draft.json"


def draft():
    return PilotDraft.model_validate_json(DRAFT.read_text(encoding="utf-8"))


def test_original_draft_covers_cells_without_claiming_release_or_review():
    bank = draft()
    assert len(bank.concepts) == 6
    assert len(bank.lessons) == 54
    assert len(bank.exercises) == 24
    assert bank.report()["publishable"] is False
    assert all(x.calibration == "uncalibrated" for x in bank.lessons + bank.exercises)
    assert all(x.reuse == "link_only" for x in bank.resources)
    assert bank.competitive_penalty.calibration == "uncalibrated"
    assert len(bank.structural_repairs) == 6
    with pytest.raises(ValidationError):
        SkillPack.model_validate(bank.model_dump())
    report = json.dumps(bank.report())
    for private in ("reference_solution", "starter_code", "expected", "prompt", "answer"):
        assert private not in report
    schema = ROOT / "contracts/schemas/m7-pilot-draft.schema.json"
    assert json.loads(schema.read_text()) == PilotDraft.model_json_schema()


@pytest.mark.parametrize(
    "change",
    [
        "reviewed",
        "missing_lesson",
        "unknown_concept",
        "duplicate_id",
        "cycle",
        "missing_java",
        "wrong_target",
        "runtime_pin",
        "same_family_repair",
    ],
)
def test_draft_rejects_incomplete_or_misrepresented_authoring(change):
    data = draft().model_dump()
    if change == "reviewed":
        data["lessons"][0]["calibration"] = "reviewed"
    elif change == "missing_lesson":
        data["lessons"].pop()
    elif change == "unknown_concept":
        data["exercises"][0]["concept_ids"] = ["not_in_pilot"]
    elif change == "duplicate_id":
        data["exercises"][1]["id"] = data["exercises"][0]["id"]
    elif change == "cycle":
        data["edges"].append(
            dict(
                prerequisite="linear_search",
                concept="sequence_iteration",
                minimum_mastery=0.65,
                rationale="Invalid reverse edge",
            )
        )
    elif change == "missing_java":
        data["exercises"][0]["variants"].pop()
    elif change == "wrong_target":
        data["exercises"][0]["variants"][0]["target"] = "Java 21"
    elif change == "same_family_repair":
        data["structural_repairs"][0]["variant_id"] = data["structural_repairs"][0]["exercise_id"]
    else:
        data["exercises"][0]["variants"][0]["runtime_ref"] = "fake@sha256:" + "a" * 64
    with pytest.raises(ValidationError):
        PilotDraft.model_validate(data)


def test_committed_draft_matches_original_authoring_and_critical_oracle_edges():
    path = ROOT / "scripts/content/build-m7-pilot.py"
    spec = importlib.util.spec_from_file_location("pilot_builder", path)
    assert spec is not None and spec.loader is not None
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    assert builder.build().model_dump() == draft().model_dump()
    assert builder.oracle("window_max", [-4, -2, -7], 2) == [-6]
    assert builder.oracle("sorted_pair", [4], 8) == [0]
    assert builder.oracle("equal_pairs", [8, 8, 8], 0) == [3]
    assert builder.oracle("prefix_target", [], 0) == [-1]
    assert builder.oracle("balanced_cut", [], 0) == [0]
    assert builder.oracle("window_changes", [2, 2, 3], 1) == [0, 0, 0]


def test_proposed_policy_matches_existing_candidate_and_stays_unapproved():
    policy = json.loads((ROOT / "contracts/product/m7-pilot-policy.json").read_text())
    assert policy["status"] == "proposed_pending_review"
    assert policy["activation"]["window_seconds"] == 48 * 3600
    assert policy["activation"]["correct_answer_required"] is False
    assert policy["reporting"]["global_reporting"].startswith("deferred_")
    assert (
        policy["competitive_penalty"]["wrong_submit_seconds"]
        == draft().competitive_penalty.wrong_submit_seconds
    )


def test_original_python_stdin_stdout_references_match_all_vectors(monkeypatch):
    # Trusted committed authoring only; never execute learner-submitted source here.
    for exercise in draft().exercises:
        source = next(x.reference_solution for x in exercise.variants if x.language == "python")
        code = compile(source, exercise.id, "exec")
        for index, case in enumerate(exercise.tests):
            monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(case.input.encode())))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(code, {})
            assert output.getvalue().split() == case.expected.split(), (exercise.id, index)
