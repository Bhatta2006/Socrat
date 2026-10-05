"""Shared strict domain-neutral authoring types."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Key = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]
Text = Annotated[str, Field(min_length=1, max_length=8000)]
Language = Literal["python", "cpp", "java"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)
