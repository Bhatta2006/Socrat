"""Declarative diagnostic authoring. Scoring specifications are server-private."""

from typing import Literal

from pydantic import Field, model_validator

from socrat.skillpacks.types import Contract, Key, Language, Text

Stage = Literal[
    "no_code_trace_and_reasoning", "dsa_trace_and_reasoning", "implementation_diagnostic"
]


class Choice(Contract):
    id: Key
    label: Text


class ResponseSpec(Contract):
    kind: Literal["choice", "trace", "human_rubric", "implementation"]
    choices: list[Choice] = Field(default_factory=list, max_length=12)
    answer: str | None = Field(default=None, min_length=1, max_length=2000)
    misconception_answers: dict[str, Key] = Field(default_factory=dict, max_length=12)

    @model_validator(mode="after")
    def valid_spec(self):
        ids = [choice.id for choice in self.choices]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate choice")
        if self.kind == "choice":
            if len(ids) < 2 or self.answer not in ids:
                raise ValueError("Choice items require a valid private answer")
        elif self.choices:
            raise ValueError("Only choice items contain choices")
        if self.kind == "trace" and self.answer is None:
            raise ValueError("Trace items require an exact private answer")
        if self.kind in {"human_rubric", "implementation"} and self.answer is not None:
            raise ValueError("Unimplemented scoring cannot contain an objective key")
        if self.kind == "choice" and not set(self.misconception_answers) <= set(ids):
            raise ValueError("Unknown misconception choice")
        return self


class DiagnosticItem(Contract):
    exercise_id: Key
    stage: Stage
    languages: list[Language] = Field(default_factory=list, max_length=3)
    response: ResponseSpec


class MisconceptionDefinition(Contract):
    id: Key
    concept_id: Key
    description: Text
    repair_concept_id: Key


class DiagnosticDefinition(Contract):
    blueprint_id: Key
    track: Literal["foundations", "interview", "competitive"]
    languages: list[Language] = Field(default_factory=list, max_length=3)
    scope: Literal["objective_readiness", "full_placement"]
    minimum_per_concept: int = Field(ge=2, le=20)
    maximum_items: int = Field(ge=2, le=100)
    maximum_seconds: int = Field(ge=60, le=2700)
    uncertainty_margin: float = Field(ge=0, le=0.25, allow_inf_nan=False)
    items: list[DiagnosticItem] = Field(min_length=2, max_length=1000)

    @model_validator(mode="after")
    def valid_definition(self):
        ids = [item.exercise_id for item in self.items]
        if len(ids) != len(set(ids)) or len(self.languages) != len(set(self.languages)):
            raise ValueError("Duplicate diagnostic item/language")
        if self.track == "foundations" and self.maximum_seconds > 900:
            raise ValueError("Foundations diagnostic exceeds 15 minutes")
        if self.maximum_items < self.minimum_per_concept:
            raise ValueError("Insufficient item budget")
        return self
