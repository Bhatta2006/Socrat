"""Authoring schema for course packs.

A course is a folder of YAML documents. Concepts form a prerequisite DAG that may
reference concepts in other courses with a ``course:concept`` identifier, so a new
skill can reuse an existing foundation without duplicating it.
"""

import random
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

Slug = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")]
Ref = Annotated[str, Field(pattern=r"^([a-z][a-z0-9-]{0,63}:)?[a-z][a-z0-9-]{0,63}$")]
Language = Literal["python", "cpp", "java"]
LANGUAGES: tuple[Language, ...] = ("python", "cpp", "java")


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Resource(Model):
    title: str = Field(min_length=3, max_length=160)
    url: HttpUrl
    kind: Literal["article", "video", "docs", "course", "book", "interactive", "visualizer"]
    source: str = Field(min_length=2, max_length=80)
    minutes: int = Field(ge=1, le=600)
    level: Literal["intro", "core", "deep"] = "core"
    languages: list[Language] = Field(default_factory=list)  # empty = language-neutral


class QuizItem(Model):
    id: Slug
    kind: Literal["mcq", "output", "bug"] = "mcq"
    prompt: str = Field(min_length=5, max_length=4000)
    code: dict[Language, str] = Field(default_factory=dict)
    options: list[str] = Field(min_length=2, max_length=6)
    answer: int = Field(ge=0)
    explanation: str = Field(min_length=5, max_length=2000)
    difficulty: int = Field(ge=1, le=5)

    def snippet(self, language: str) -> str | None:
        """The code shown with this question in the learner's language, if any."""
        for key, value in self.code.items():
            if key == language:
                return value
        return next(iter(self.code.values()), None)

    def order(self, seed: str) -> list[int]:
        """Display position -> authored option index, fixed per (seed, item).

        Authors write the correct option first; the order learners see must not leak it.
        """
        order = list(range(len(self.options)))
        random.Random(f"{seed}:{self.id}").shuffle(order)
        return order

    def shown(self, seed: str) -> dict:
        order = self.order(seed)
        return dict(options=[self.options[i] for i in order], answer=order.index(self.answer))

    def is_correct(self, seed: str, choice: int) -> bool:
        return 0 <= choice < len(self.options) and self.order(seed)[choice] == self.answer

    @model_validator(mode="after")
    def answer_in_range(self):
        if self.answer >= len(self.options):
            raise ValueError(f"quiz {self.id}: answer index out of range")
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"quiz {self.id}: duplicate options")
        return self


class PracticeLink(Model):
    title: str = Field(min_length=2, max_length=160)
    url: HttpUrl
    platform: str = Field(min_length=2, max_length=40)
    difficulty: Literal["easy", "medium", "hard"]


class Concept(Model):
    id: Slug
    title: str = Field(min_length=2, max_length=100)
    summary: str = Field(min_length=10, max_length=300)
    module: Slug
    prerequisites: list[Ref] = Field(default_factory=list)
    difficulty: int = Field(ge=1, le=5)
    estimated_minutes: int = Field(ge=10, le=600)
    lesson: str = Field(min_length=200)
    key_points: list[str] = Field(min_length=2, max_length=8)
    pitfalls: list[str] = Field(default_factory=list, max_length=8)
    resources: list[Resource] = Field(min_length=2, max_length=8)
    quiz: list[QuizItem] = Field(min_length=2, max_length=10)
    problems: list[Slug] = Field(default_factory=list)
    practice_links: list[PracticeLink] = Field(default_factory=list, max_length=10)


class Example(Model):
    input: str
    output: str
    explanation: str = ""


class TestCase(Model):
    input: str = Field(max_length=2_000_000)
    expected: str = Field(max_length=2_000_000)
    public: bool = False


class Problem(Model):
    id: Slug
    title: str = Field(min_length=2, max_length=100)
    concepts: list[Slug] = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    statement: str = Field(min_length=20)
    input_format: str = Field(min_length=3)
    output_format: str = Field(min_length=3)
    constraints: list[str] = Field(default_factory=list)
    examples: list[Example] = Field(min_length=1, max_length=5)
    hints: list[str] = Field(min_length=2, max_length=5)
    approach: str = Field(min_length=20)  # Revealed only at the final Socratic level.
    reference: str = Field(min_length=10)  # Python reference; generates expected output.
    generator: str = ""  # Python: def cases(rng): yield input strings.
    starter: dict[Language, str] = Field(default_factory=dict)
    time_limit_ms: int = Field(default=2000, ge=500, le=10000)
    tests: list[TestCase] = Field(default_factory=list)


class Module(Model):
    id: Slug
    title: str = Field(min_length=2, max_length=100)
    summary: str = Field(min_length=10, max_length=300)
    concepts: list[Slug] = Field(min_length=1)


class LevelStart(Model):
    """Self-reported level → concept at which adaptive placement starts probing."""

    id: Slug
    label: str
    description: str
    start_concept: Slug | None = None  # None = absolute beginner, skip placement.


class Course(Model):
    id: Slug
    title: str = Field(min_length=2, max_length=80)
    tagline: str = Field(min_length=5, max_length=140)
    description: str = Field(min_length=20, max_length=1200)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    languages: list[Language] = Field(min_length=1)
    levels: list[LevelStart] = Field(min_length=2)
    modules: list[Module] = Field(min_length=1)
    concepts: list[Concept] = Field(default_factory=list)
    problems: list[Problem] = Field(default_factory=list)

    def concept(self, concept_id: str) -> Concept:
        return next(item for item in self.concepts if item.id == concept_id)

    def problem(self, problem_id: str) -> Problem:
        return next(item for item in self.problems if item.id == problem_id)
