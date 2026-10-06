"""Private form definitions and bounded commands. Never expose scoring keys."""

from typing import Literal

from pydantic import Field, model_validator

from socrat.diagnostics.contracts import ResponseSpec
from socrat.skillpacks.types import Contract, Key, Language

AssessmentKind = Literal["baseline", "weekly", "final", "retention"]


class AssessmentItemSpec(Contract):
    exercise_id: Key
    response: ResponseSpec
    rubric_criteria: list[Key] = Field(default_factory=list, max_length=12)
    unfamiliar_representation: bool = False

    @model_validator(mode="after")
    def rubric(self):
        if len(set(self.rubric_criteria)) != len(self.rubric_criteria):
            raise ValueError("Duplicate rubric criterion")
        if bool(self.rubric_criteria) != (self.response.kind == "human_rubric"):
            raise ValueError("Qualitative items require curated 0-4 criteria")
        return self


class AssessmentForm(Contract):
    blueprint_id: Key
    track: Literal["foundations", "interview", "competitive"]
    languages: list[Language] = Field(default_factory=list, max_length=3)
    parallel_group: Key
    maximum_seconds: int = Field(ge=60, le=2700)
    pass_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    boundary_margin: float = Field(default=0.05, ge=0, le=0.1, allow_inf_nan=False)
    allowed_tools: Literal["editor_only"] = "editor_only"
    retention_representation: (
        Literal["recall", "small_implementation", "mixed_problem", "retention_assessment"] | None
    ) = None
    review_reference: str = Field(min_length=1, max_length=512)
    items: list[AssessmentItemSpec] = Field(min_length=1, max_length=100)


class StartInput(Contract):
    kind: AssessmentKind
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")


class ResponseInput(Contract):
    item_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    revision: int = Field(ge=0)
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    answer: str = Field(max_length=2000)
    report_problem: bool = False


class ReviewInput(Contract):
    revision: int = Field(ge=0)
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    decision: Literal["accept", "exclude"]
    criterion_scores: dict[Key, int] = Field(default_factory=dict, max_length=12)
    evidence_reference: str = Field(min_length=1, max_length=512)
    rationale: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def bounded_scores(self):
        if any(not 0 <= value <= 4 for value in self.criterion_scores.values()):
            raise ValueError("Rubric scores must be 0-4")
        return self


class DisputeInput(Contract):
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    rationale: str = Field(min_length=1, max_length=2000)
