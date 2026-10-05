from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from socrat.skillpacks.types import Contract


class PlanCommand(Contract):
    action: Literal["generate", "confirm", "refresh", "lighter", "recover", "pause", "resume"]
    expected_revision: int = Field(ge=0)
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    reviewed_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    weekdays: list[int] | None = Field(default=None, min_length=3, max_length=6)
    minutes: int | None = Field(default=None, ge=20, le=90)
    target_date: str | None = None

    @model_validator(mode="after")
    def valid_schedule(self):
        if self.weekdays is not None and (
            len(set(self.weekdays)) != len(self.weekdays)
            or any(x < 0 or x > 6 for x in self.weekdays)
        ):
            raise ValueError("Choose distinct weekdays from Monday=0 to Sunday=6")
        if self.target_date is not None and self.target_date != "no_fixed_date":
            if date.fromisoformat(self.target_date).isoformat() != self.target_date:
                raise ValueError("Use an ISO date")
        if self.action == "confirm" and not self.reviewed_digest:
            raise ValueError("Review the plan before confirmation")
        if self.action in {"confirm", "pause", "resume"} and any(
            x is not None for x in (self.weekdays, self.minutes, self.target_date)
        ):
            raise ValueError("Schedule changes require a fresh reviewed revision")
        return self
