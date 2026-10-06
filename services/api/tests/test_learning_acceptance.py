"""Synthetic acceptance records exercise the evaluator, not real M7 approvals."""

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_learning_audit import stocked_pack

from socrat.learning.acceptance import AcceptanceEvidence, evaluate_acceptance, main
from socrat.skillpacks.schema import SkillPack


def evidence_pack():
    payload = stocked_pack().model_dump()
    payload["purpose"] = "launch"
    return SkillPack.model_validate(payload)


def evidence(pack):
    review = dict(
        reviewer_id="synthetic_reviewer",
        decision="approved",
        evidence_reference="Synthetic fixture; never a real approval",
    )
    cells = []
    for track in ("foundations", "interview", "competitive"):
        for language in pack.languages:
            cells.append(
                dict(
                    track=track,
                    language=language,
                    golden_environment="staging",
                    golden_review=review,
                    accessibility_review=review,
                    language_review=review,
                    duration_reference="Synthetic measurements only",
                    durations=[
                        dict(
                            session_id=f"{track}_{language}",
                            planned_minutes=20,
                            actual_seconds=1440,
                            completed=True,
                            normal=True,
                            valid=True,
                        )
                    ],
                    dogfood_reference="Synthetic inventory only",
                    attempted_exercise_ids=["a_runtime_probe"],
                    confirmed_material_defect_ids=[],
                )
            )
    return dict(
        pack_digest=pack.digest(),
        author_id="synthetic_author",
        minimum_duration_samples_per_cell=1,
        minimum_dogfood_exercises_per_cell=1,
        activation_definition="independent_submit",
        content_review=review,
        penalty_review=review,
        metric_review=review,
        release_review=review,
        cells=cells,
    )


def test_acceptance_summary_is_bound_to_pack_and_never_includes_private_records():
    pack = evidence_pack()
    records = AcceptanceEvidence.model_validate(evidence(pack))
    report = evaluate_acceptance(pack, records)
    assert report["recorded_evidence_ready"]
    assert report["runtime_acceptance"] == "deferred"
    assert len(report["cells"]) == 9
    assert all(x["median_duration_error"] == 0.2 for x in report["cells"])
    assert evaluate_acceptance(pack, records) == report
    rendered = json.dumps(report)
    assert "Synthetic fixture" not in rendered
    assert "synthetic_reviewer" not in rendered
    assert "synthetic_author" not in rendered
    assert "session_id" not in rendered
    assert "reference_solution" not in rendered
    payload = evidence(pack)
    payload["pack_digest"] = "0" * 64
    assert (
        "acceptance_pack_digest_mismatch"
        in evaluate_acceptance(pack, AcceptanceEvidence.model_validate(payload))["gaps"]
    )


@pytest.mark.parametrize(
    "exclusion", ["test", "staff", "synthetic", "deleted_before_eligibility", "known_corrupt"]
)
def test_excluded_cohorts_cannot_calibrate_duration(exclusion):
    pack = evidence_pack()
    payload = evidence(pack)
    payload["cells"][0]["durations"][0]["exclusion"] = exclusion
    report = evaluate_acceptance(pack, AcceptanceEvidence.model_validate(payload))
    assert not report["recorded_evidence_ready"]
    assert report["cells"][0]["duration_samples"] == 0
    assert report["cells"][0]["excluded_duration_samples"] == 1
    assert "insufficient_duration_samples" in report["cells"][0]["gaps"]


@pytest.mark.parametrize("flag", ["completed", "normal", "valid"])
def test_ineligible_sessions_cannot_calibrate_duration(flag):
    pack = evidence_pack()
    payload = evidence(pack)
    payload["cells"][0]["durations"][0][flag] = False
    assert not evaluate_acceptance(pack, AcceptanceEvidence.model_validate(payload))[
        "recorded_evidence_ready"
    ]


def test_one_failing_cell_cannot_be_hidden_by_global_success():
    pack = evidence_pack()
    payload = evidence(pack)
    payload["cells"][-1]["durations"][0]["actual_seconds"] = 1441
    report = evaluate_acceptance(pack, AcceptanceEvidence.model_validate(payload))
    assert not report["recorded_evidence_ready"]
    assert "duration_error_above_target" in report["cells"][-1]["gaps"]
    assert all(x["ready"] for x in report["cells"][:-1])


def test_dogfood_rate_counts_distinct_attempted_items_and_rejects_exact_two_percent():
    pack = evidence_pack()
    payload = evidence(pack)
    # The stocked bank contains exactly 52 reviewed code practice artifacts.
    ids = [x.id for x in pack.exercises if x.inventory == "practice" and x.modality == "code"]
    assert len(ids) >= 51
    payload["cells"][0]["attempted_exercise_ids"] = ids[:50]
    payload["cells"][0]["confirmed_material_defect_ids"] = ids[:1]
    report = evaluate_acceptance(pack, AcceptanceEvidence.model_validate(payload))
    assert report["cells"][0]["material_defect_rate"] == 0.02
    assert not report["recorded_evidence_ready"]
    payload["cells"][0]["attempted_exercise_ids"] = ids[:51]
    assert evaluate_acceptance(pack, AcceptanceEvidence.model_validate(payload))[
        "recorded_evidence_ready"
    ]


@pytest.mark.parametrize(
    "corruption",
    [
        "author_review",
        "pending_review",
        "unresolved_metrics",
        "local_golden",
        "missing_cell",
        "protected_inventory",
    ],
)
def test_acceptance_fails_closed_without_release_evidence(corruption):
    pack = evidence_pack()
    payload = evidence(pack)
    if corruption == "author_review":
        payload["author_id"] = "synthetic_reviewer"
    elif corruption == "pending_review":
        payload["content_review"] = dict(reviewer_id="synthetic_reviewer")
    elif corruption == "unresolved_metrics":
        payload["activation_definition"] = "unresolved"
    elif corruption == "local_golden":
        payload["cells"][0]["golden_environment"] = "local"
    elif corruption == "missing_cell":
        payload["cells"].pop()
    else:
        payload["cells"][0]["attempted_exercise_ids"] = [
            next(x.id for x in pack.exercises if x.inventory == "assessment")
        ]
    assert not evaluate_acceptance(pack, AcceptanceEvidence.model_validate(payload))[
        "recorded_evidence_ready"
    ]


@pytest.mark.parametrize(
    "corruption",
    [
        "duplicate_cell",
        "duplicate_session",
        "duplicate_exercise",
        "unattempted_defect",
        "missing_reference",
        "nonfinite_duration",
    ],
)
def test_malformed_or_duplicate_acceptance_records_are_rejected(corruption):
    pack = evidence_pack()
    payload = evidence(pack)
    if corruption == "duplicate_cell":
        payload["cells"][1] = payload["cells"][0]
    elif corruption == "duplicate_session":
        payload["cells"][1]["durations"][0]["session_id"] = payload["cells"][0]["durations"][0][
            "session_id"
        ]
    elif corruption == "duplicate_exercise":
        payload["cells"][0]["attempted_exercise_ids"] *= 2
    elif corruption == "unattempted_defect":
        payload["cells"][0]["confirmed_material_defect_ids"] = ["missing"]
    elif corruption == "missing_reference":
        payload["release_review"]["evidence_reference"] = None
    else:
        payload["cells"][0]["durations"][0]["actual_seconds"] = float("inf")
    with pytest.raises(ValidationError):
        AcceptanceEvidence.model_validate(payload)


def test_acceptance_cli_prints_only_safe_summary(tmp_path, monkeypatch, capsys):
    pack = evidence_pack()
    pack_path, records_path = tmp_path / "pack.json", tmp_path / "evidence.json"
    pack_path.write_text(pack.canonical_json(), encoding="utf-8")
    records_path.write_text(json.dumps(evidence(pack)), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["acceptance", str(pack_path), str(records_path)])
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["recorded_evidence_ready"]
    records_path.write_text('{"private":"do-not-echo"}', encoding="utf-8")
    assert main() == 1
    assert "do-not-echo" not in capsys.readouterr().out


def test_exported_acceptance_contract_does_not_drift():
    path = Path("contracts/schemas/m7-acceptance-evidence.schema.json")
    assert json.loads(path.read_text(encoding="utf-8")) == AcceptanceEvidence.model_json_schema()
