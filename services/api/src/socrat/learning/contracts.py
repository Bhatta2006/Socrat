from typing import Literal

from pydantic import Field

from socrat.skillpacks.types import Contract


class StartSession(Contract):
    curriculum_revision: int = Field(ge=1)
    timing: Literal["standard", "untimed"] = "standard"


class SessionAction(Contract):
    action: Literal["advance", "pause", "resume", "abandon", "start_timed", "upsolve"]
    expected_revision: int = Field(ge=0)
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    answer: str | None = Field(default=None, min_length=1, max_length=8000)
    run_id: str | None = Field(default=None, pattern=r"^[a-f0-9-]{36}$")
    error_classification: (
        Literal[
            "wrong_answer",
            "implementation_bug",
            "complexity",
            "time_pressure",
            "concept_gap",
            "unclear_prompt",
        ]
        | None
    ) = None
    reflection: (
        Literal[
            "concept_gap",
            "pattern_recognition",
            "implementation_bug",
            "complexity",
            "unclear_prompt",
            "time_pressure",
            "none",
        ]
        | None
    ) = None
