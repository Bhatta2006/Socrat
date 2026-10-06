from typing import Literal

from pydantic import Field

from socrat.skillpacks.types import Contract, Key, Language


class HintRequest(Contract):
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    draft_revision: int = Field(ge=0)
    reasoning: str = Field(min_length=1, max_length=2000)
    requested_level: int = Field(default=1, ge=1, le=5)
    action: Literal["hint", "accessibility", "exit"] = "hint"


class AuthoredHint(Contract):
    exercise_id: Key
    language: Language
    level: int = Field(ge=1, le=4)
    message: str = Field(min_length=1, max_length=2000)
    question: str = Field(min_length=1, max_length=500)


class TutorOutput(Contract):
    diagnosis: str = Field(max_length=500)
    hint_level: int = Field(ge=1, le=3)
    message: str = Field(min_length=1, max_length=1200)
    question: str = Field(min_length=1, max_length=500)
    concept_refs: list[Key] = Field(min_length=1, max_length=10)
    code_lines: list[int] = Field(default_factory=list, max_length=10)
    reasoning_quote: str = Field(default="", max_length=300)
    leakage_risk: Literal["low", "medium", "high"]
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)


class GatewayResponse(Contract):
    output: dict
    input_tokens: int = Field(ge=0, le=20000)
    # Actual application output authority remains bounded by the request cap in generate.
    # Diagnostic provider-default runs may receive larger usage counts.
    output_tokens: int = Field(ge=0, le=1000000)


class ShadowOutput(Contract):
    candidate_ids: list[Key] = Field(min_length=3, max_length=8)
    reason_code: Literal["prerequisite_fit", "practice_need", "review_need", "baseline_preferred"]


class ShadowRequest(Contract):
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    expected_revision: int = Field(ge=1)
