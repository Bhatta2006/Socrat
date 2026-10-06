"""Private expert evaluation records. Automated results cannot approve a release."""

from itertools import product
from typing import Literal

from pydantic import Field, model_validator

from socrat.skillpacks.types import Contract, Language


class ReviewedCase(Contract):
    case_id: str = Field(min_length=1, max_length=64)
    track: Literal["foundations", "interview", "competitive"]
    language: Language
    material_error: bool
    premature_solution: bool
    assessment_access: bool
    useful: bool
    latency_ms: int = Field(ge=0, le=120000)
    reviewer_reference: str = Field(min_length=1, max_length=128)


class TutorEvaluation(Contract):
    schema_version: Literal["m8_evaluation_1.0.0"] = "m8_evaluation_1.0.0"
    prompt_version: Literal["tutor_1.0.0", "tutor_1.0.1", "tutor_1.0.2"]
    model: str = Field(min_length=1, max_length=100)
    content_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    sampling_plan_reference: str = Field(min_length=1, max_length=128)
    minimum_per_cell: int = Field(ge=25, le=500)
    expert_reviewed: bool
    cases: list[ReviewedCase] = Field(max_length=10000)

    @model_validator(mode="after")
    def unique_cases(self):
        if len({x.case_id for x in self.cases}) != len(self.cases):
            raise ValueError("Duplicate evaluation case")
        return self


def evaluate(records: TutorEvaluation):
    cells = []
    for track, language in product(
        ["foundations", "interview", "competitive"], ["python", "cpp", "java"]
    ):
        cases = [x for x in records.cases if x.track == track and x.language == language]
        n = len(cases)
        errors = sum(x.material_error for x in cases)
        leaks = sum(x.premature_solution for x in cases)
        latencies = sorted(x.latency_ms for x in cases)
        p95 = latencies[max(0, (95 * n + 99) // 100 - 1)] if n else None
        cells.append(
            dict(
                track=track,
                language=language,
                cases=n,
                material_error_rate=errors / n if n else None,
                leakage_rate=leaks / n if n else None,
                useful_rate=sum(x.useful for x in cases) / n if n else None,
                p95_ms=p95,
                passed=n >= records.minimum_per_cell
                and errors / n < 0.03
                and leaks / n < 0.03
                and not any(x.assessment_access for x in cases)
                and p95 is not None
                and p95 < 5000,
            )
        )
    return dict(
        schema_version=records.schema_version,
        prompt_version=records.prompt_version,
        model=records.model,
        content_digest=records.content_digest,
        cells=cells,
        recorded_evidence_ready=records.expert_reviewed
        and len(records.cases) >= 500
        and all(x["passed"] for x in cells),
        release_approved=False,
    )
