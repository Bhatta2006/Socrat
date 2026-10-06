"""Evaluate supplied M7 acceptance records without inventing human evidence."""

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Annotated, Literal

from pydantic import Field, ValidationError, model_validator

from socrat.learning.audit import planning_audit
from socrat.skillpacks.schema import SkillPack
from socrat.skillpacks.types import Contract, Key, Language, Text

Track = Literal["foundations", "interview", "competitive"]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
OpaqueId = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")]
Exclusion = Literal["test", "staff", "synthetic", "deleted_before_eligibility", "known_corrupt"]


class AcceptanceReview(Contract):
    reviewer_id: Key
    decision: Literal["pending", "approved", "rejected"] = "pending"
    evidence_reference: Text | None = None

    @model_validator(mode="after")
    def referenced_decision(self):
        if self.decision != "pending" and not self.evidence_reference:
            raise ValueError("Review decisions require an evidence reference")
        return self


class DurationObservation(Contract):
    session_id: OpaqueId
    planned_minutes: float = Field(gt=0, le=180, allow_inf_nan=False)
    actual_seconds: float = Field(ge=0, allow_inf_nan=False)
    completed: bool
    normal: bool
    valid: bool
    exclusion: Exclusion | None = None


class CellAcceptance(Contract):
    track: Track
    language: Language
    golden_environment: Literal["local", "staging"]
    golden_review: AcceptanceReview
    accessibility_review: AcceptanceReview
    language_review: AcceptanceReview
    duration_reference: Text | None = None
    durations: list[DurationObservation] = Field(default_factory=list, max_length=10000)
    dogfood_reference: Text | None = None
    attempted_exercise_ids: list[Key] = Field(default_factory=list, max_length=5000)
    confirmed_material_defect_ids: list[Key] = Field(default_factory=list, max_length=5000)

    @model_validator(mode="after")
    def distinct_inventory(self):
        for values in (self.attempted_exercise_ids, self.confirmed_material_defect_ids):
            if len(values) != len(set(values)):
                raise ValueError("Count each exercised artifact once per cell")
        if not set(self.confirmed_material_defect_ids) <= set(self.attempted_exercise_ids):
            raise ValueError("Defect numerator must belong to attempted inventory")
        if self.durations and not self.duration_reference:
            raise ValueError("Duration measurements require a source reference")
        if self.attempted_exercise_ids and not self.dogfood_reference:
            raise ValueError("Dogfood records require a source reference")
        return self


class AcceptanceEvidence(Contract):
    version: Literal["m7_acceptance_1.0.0"] = "m7_acceptance_1.0.0"
    pack_digest: Digest
    author_id: Key
    # Sample sizes must come from an approved validation plan, not this evaluator.
    minimum_duration_samples_per_cell: int = Field(ge=1, le=10000)
    minimum_dogfood_exercises_per_cell: int = Field(ge=1, le=5000)
    activation_definition: Literal["independent_submit", "first_plan_start", "unresolved"]
    content_review: AcceptanceReview
    penalty_review: AcceptanceReview
    metric_review: AcceptanceReview
    release_review: AcceptanceReview
    cells: list[CellAcceptance] = Field(max_length=9)

    @model_validator(mode="after")
    def distinct_records(self):
        keys = [(x.track, x.language) for x in self.cells]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate acceptance cell")
        ids = [x.session_id for cell in self.cells for x in cell.durations]
        if len(ids) != len(set(ids)):
            raise ValueError("A duration observation cannot count in multiple cells")
        return self


def evaluate_acceptance(pack: SkillPack, evidence: AcceptanceEvidence) -> dict:
    """A reproducible summary of supplied records, not an independent approval.

    Review owners must verify the referenced records and choose sample sizes.
    M6 acceptance is explicitly outside this report's scope.
    """
    gaps = []
    if evidence.pack_digest != pack.digest():
        gaps.append("acceptance_pack_digest_mismatch")
    if pack.purpose != "launch" or not pack.session_content_version:
        gaps.append("launch_session_content_required")
    inventory = planning_audit(pack)
    if not inventory["ready"]:
        gaps.append("learning_plan_coverage_incomplete")
    for name in ("content", "penalty", "metric", "release"):
        review = getattr(evidence, f"{name}_review")
        if review.decision != "approved":
            gaps.append(f"{name}_review_not_approved")
        if review.reviewer_id == evidence.author_id:
            gaps.append(f"{name}_review_not_independent")
    if evidence.activation_definition == "unresolved":
        gaps.append("activation_definition_unresolved")
    exercises = {x.id: x for x in pack.exercises}
    records = {(x.track, x.language): x for x in evidence.cells}
    cells = []
    for track in ("foundations", "interview", "competitive"):
        for language in ("python", "cpp", "java"):
            record = records.get((track, language))
            cell_gaps = []
            errors = []
            attempted, defects, excluded = 0, 0, 0
            if record is None:
                cell_gaps.append("missing_acceptance_cell")
            else:
                for name in ("golden", "accessibility", "language"):
                    review = getattr(record, f"{name}_review")
                    if review.decision != "approved":
                        cell_gaps.append(f"{name}_review_not_approved")
                    if review.reviewer_id == evidence.author_id:
                        cell_gaps.append(f"{name}_review_not_independent")
                if record.golden_environment != "staging":
                    cell_gaps.append("deployed_golden_journey_required")
                overlay = next((x for x in pack.tracks if x.id == track), None)
                if any(
                    key not in exercises
                    or exercises[key].inventory != "practice"
                    or overlay is None
                    or not set(exercises[key].concept_ids) <= set(overlay.concept_ids)
                    or pack.variant_for(key, language) is None
                    for key in record.attempted_exercise_ids
                ):
                    cell_gaps.append("dogfood_inventory_outside_launch_cell")
                for sample in record.durations:
                    if (
                        sample.completed
                        and sample.normal
                        and sample.valid
                        and sample.exclusion is None
                    ):
                        errors.append(
                            abs(sample.actual_seconds / 60 - sample.planned_minutes)
                            / sample.planned_minutes
                        )
                    else:
                        excluded += 1
                attempted = len(record.attempted_exercise_ids)
                defects = len(record.confirmed_material_defect_ids)
                if len(errors) < evidence.minimum_duration_samples_per_cell:
                    cell_gaps.append("insufficient_duration_samples")
                if errors and median(errors) > 0.20:
                    cell_gaps.append("duration_error_above_target")
                if attempted < evidence.minimum_dogfood_exercises_per_cell:
                    cell_gaps.append("insufficient_dogfood_inventory")
                if attempted and defects / attempted >= 0.02:
                    cell_gaps.append("material_defect_rate_above_target")
            cells.append(
                dict(
                    track=track,
                    language=language,
                    ready=not cell_gaps,
                    gaps=cell_gaps,
                    duration_samples=len(errors),
                    excluded_duration_samples=excluded,
                    median_duration_error=median(errors) if errors else None,
                    attempted_exercises=attempted,
                    confirmed_material_defects=defects,
                    material_defect_rate=defects / attempted if attempted else None,
                )
            )
    return dict(
        version=evidence.version,
        scope="supplied_m7_evidence_without_m6_acceptance",
        pack_digest=pack.digest(),
        recorded_evidence_ready=not gaps and all(x["ready"] for x in cells),
        runtime_acceptance="deferred",
        activation_definition=evidence.activation_definition,
        gaps=gaps,
        cells=cells,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize private M7 acceptance records; M6 remains deferred"
    )
    parser.add_argument("pack", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    if any(
        not path.is_file() or path.stat().st_size > 10_000_000
        for path in (args.pack, args.evidence)
    ):
        parser.error("Require pack and evidence JSON files of at most 10 MB each")
    try:
        pack = SkillPack.model_validate_json(args.pack.read_text(encoding="utf-8"))
        evidence = AcceptanceEvidence.model_validate_json(args.evidence.read_text(encoding="utf-8"))
    except (ValidationError, ValueError):
        print(
            "Invalid acceptance contract; inspect records privately (input values are not echoed)."
        )
        return 1
    report = evaluate_acceptance(pack, evidence)
    print(json.dumps(report))
    return 0 if report["recorded_evidence_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
