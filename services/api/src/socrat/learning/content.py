"""Declarative learning content. Answer keys never belong in learner views."""

from typing import Literal

from pydantic import Field, model_validator

from socrat.diagnostics.contracts import ResponseSpec
from socrat.skillpacks.types import Contract, Key, Language, Text


class LearningCheck(Contract):
    id: Key
    prompt: Text
    response: ResponseSpec
    validator_version: Literal["objective_exact_1.0.0"] = "objective_exact_1.0.0"

    @model_validator(mode="after")
    def objective_only(self):
        if self.response.kind not in {"choice", "trace"}:
            raise ValueError("Learning checks require a deterministic choice or exact trace")
        if self.response.misconception_answers:
            raise ValueError("Learning checks do not produce diagnostic misconception evidence")
        return self

    def public(self):
        return dict(
            id=self.id,
            prompt=self.prompt,
            kind=self.response.kind,
            choices=[x.model_dump() for x in self.response.choices],
        )


class LearningLesson(Contract):
    id: Key
    track: Literal["foundations", "interview", "competitive"]
    language: Language
    concept_ids: list[Key] = Field(min_length=1, max_length=100)
    title: Text
    instruction: Text
    examples: list[Text] = Field(min_length=1, max_length=20)
    language_notes: Text
    pattern_recognition: Text | None = None
    correctness: Text | None = None
    complexity: Text | None = None
    retrieval_check: LearningCheck
    exit_check: LearningCheck
    calibration: Literal["uncalibrated", "reviewed"] = "uncalibrated"
    accessibility: Text
    source_reference: Text

    @model_validator(mode="after")
    def complete_lesson(self):
        if len(set(self.concept_ids)) != len(self.concept_ids):
            raise ValueError("Duplicate lesson concepts")
        if self.retrieval_check.id == self.exit_check.id:
            raise ValueError("Retrieval and exit checks must be distinct")
        if self.track == "interview" and not all(
            (self.pattern_recognition, self.correctness, self.complexity)
        ):
            raise ValueError("Interview lessons require recognition, correctness and complexity")
        return self


class StructuralRepair(Contract):
    exercise_id: Key
    variant_id: Key
    structural_change: Text
    review_reference: Text
    calibration: Literal["uncalibrated", "reviewed"] = "uncalibrated"


class CompetitivePenalty(Contract):
    version: Literal["1.0.0"] = "1.0.0"
    basis: Literal["healthy_incorrect_submit"] = "healthy_incorrect_submit"
    wrong_submit_seconds: int = Field(ge=0, le=3600)
    calibration: Literal["uncalibrated", "reviewed"] = "uncalibrated"
    review_reference: Text


def lesson_for(pack, track, language, concept_ids, allowed_concepts=None):
    """Prefer the narrowest reviewed lesson, then a stable authoring identifier."""
    return next(
        iter(
            sorted(
                (
                    x
                    for x in pack.learning_lessons
                    if x.track == track
                    and x.language == language
                    and x.calibration == "reviewed"
                    and set(concept_ids) <= set(x.concept_ids)
                    and set(x.concept_ids) <= set(allowed_concepts or concept_ids)
                ),
                key=lambda x: (len(x.concept_ids), x.id),
            )
        ),
        None,
    )


def coverage_audit(pack):
    """Inventory audit, not a claim of human review or runtime attestation."""
    cells = []
    for track in ("foundations", "interview", "competitive"):
        overlay = next((x for x in pack.tracks if x.id == track), None)
        for language in ("python", "cpp", "java"):
            gaps = []
            if overlay is None or language not in pack.languages:
                gaps.append(dict(code="missing_cell"))
            else:
                selected = set(overlay.concept_ids)
                if track == "competitive" and (
                    pack.competitive_penalty is None
                    or pack.competitive_penalty.calibration != "reviewed"
                ):
                    gaps.append(dict(code="missing_reviewed_penalty_policy"))
                if track == "competitive":
                    mixed = [
                        x
                        for x in pack.exercises
                        if x.inventory == "practice"
                        and x.calibration == "reviewed"
                        and x.modality == "code"
                        and set(x.concept_ids) <= selected
                        and x.difficulty == 1
                        and x.estimated_minutes <= 15
                        and pack.variant_for(x.id, language) is not None
                    ]
                    if overlay.maximum_daily_minutes < 60 or not any(
                        x.family_id != y.family_id and set(x.concept_ids) != set(y.concept_ids)
                        for x in mixed
                        for y in mixed
                    ):
                        gaps.append(dict(code="missing_mixed_set"))
                for concept in sorted(selected):
                    practice = [
                        x
                        for x in pack.exercises
                        if x.inventory == "practice"
                        and x.calibration == "reviewed"
                        and x.modality == "code"
                        and concept in x.concept_ids
                        and set(x.concept_ids) <= selected
                        and pack.variant_for(x.id, language) is not None
                    ]
                    if len({x.family_id for x in practice}) < 2:
                        gaps.append(dict(code="insufficient_practice_families", concept_id=concept))
                    if not lesson_for(pack, track, language, [concept]):
                        gaps.append(dict(code="missing_reviewed_lesson", concept_id=concept))
                    if track == "competitive":
                        ids = {x.id for x in practice}
                        if not any(
                            x.calibration == "reviewed"
                            and x.exercise_id in ids
                            and x.variant_id in ids
                            for x in pack.structural_repairs
                        ):
                            gaps.append(dict(code="missing_structural_repair", concept_id=concept))
                roots = selected - {x.concept for x in pack.edges if x.concept in selected}
                if not any(
                    x.inventory == "practice"
                    and x.calibration == "reviewed"
                    and x.modality == "code"
                    and x.difficulty == 1
                    and x.estimated_minutes <= 8
                    and set(x.concept_ids) <= roots
                    and pack.variant_for(x.id, language) is not None
                    for x in pack.exercises
                ):
                    gaps.append(dict(code="no_beginner_entry"))
            cells.append(dict(track=track, language=language, ready=not gaps, gaps=gaps))
    return dict(version="1.0.0", ready=all(x["ready"] for x in cells), cells=cells)
