"""Server-side scorer boundary. Implementation adapters require M6 verified results."""

from typing import Literal, Protocol

from pydantic import Field, model_validator

from socrat.diagnostics.contracts import ResponseSpec
from socrat.skillpacks.types import Contract, Key


class ScoreResult(Contract):
    status: Literal["scored", "pending_review", "excluded"]
    score: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    quality: float = Field(ge=0, le=1, allow_inf_nan=False)
    scoring_version: str
    reason_code: Key
    misconception_codes: list[Key] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent_result(self):
        if self.status == "scored" and (self.score is None or self.quality <= 0):
            raise ValueError("Scored result requires valid evidence")
        if self.status != "scored" and (self.score is not None or self.quality != 0):
            raise ValueError("Pending/failed evaluation has zero evidence")
        return self


class VerifiedImplementationResult(Contract):
    attempt_id: str
    runtime_digest: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    test_digest: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")
    operational_status: Literal["healthy", "failed"]
    finalized: bool
    signature_verified: bool
    score: float = Field(ge=0, le=1, allow_inf_nan=False)


class ImplementationAdapter(Protocol):
    """M6 broker supplies authenticated results; this interface never executes code."""

    def evaluate(self, attempt_id: str) -> VerifiedImplementationResult: ...


def implementation_score(
    result: VerifiedImplementationResult, attempt_id: str, runtime_digest: str, test_digest: str
) -> ScoreResult:
    if not result.signature_verified or (
        result.attempt_id,
        result.runtime_digest,
        result.test_digest,
    ) != (attempt_id, runtime_digest, test_digest):
        raise ValueError("Untrusted or stale execution result")
    if not result.finalized or result.operational_status != "healthy":
        return ScoreResult(
            status="excluded",
            quality=0.0,
            scoring_version="implementation_1.0.0",
            reason_code="execution_unverified",
        )
    return ScoreResult(
        status="scored",
        score=result.score,
        quality=1.0,
        scoring_version="implementation_1.0.0",
        reason_code="verified_implementation",
    )


def score_response(spec: ResponseSpec, answer: str, withdrawn: bool, reported: bool) -> ScoreResult:
    if withdrawn or reported:
        return ScoreResult(
            status="excluded",
            quality=0.0,
            scoring_version="objective_exact_1.0.0",
            reason_code="content_withdrawn" if withdrawn else "content_report_pending",
        )
    if spec.kind == "human_rubric":
        return ScoreResult(
            status="pending_review",
            quality=0.0,
            scoring_version="human_review_pending_1.0.0",
            reason_code="qualitative_review_pending",
        )
    if spec.kind == "implementation":
        return ScoreResult(
            status="excluded",
            quality=0.0,
            scoring_version="implementation_1.0.0",
            reason_code="runtime_unavailable",
        )
    return ScoreResult(
        status="scored",
        score=float(answer == spec.answer),
        quality=1.0,
        scoring_version="objective_exact_1.0.0",
        reason_code="objective_response_finalized",
        misconception_codes=[spec.misconception_answers[answer]]
        if answer in spec.misconception_answers
        else [],
    )
