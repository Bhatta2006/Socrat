"""Course projects (Content Master Plan §5.5, §10.3).

``content/projects/<course>/<project>.yaml``: milestones, a rubric whose weights total 100,
a self-review checklist and provenance. A project is evidence of integration; it never
changes mastery bands by itself (PRD: only independent solves do).
"""

from pathlib import Path

import yaml
from pydantic import Field, HttpUrl, model_validator

from socrat.catalog.patterns import Qualified, Status
from socrat.catalog.schema import Model, Provenance, Slug


class Milestone(Model):
    id: Slug
    title: str = Field(min_length=2, max_length=120)
    checklist: list[str] = Field(min_length=1, max_length=10)


class RubricCriterion(Model):
    criterion: str = Field(min_length=2, max_length=60)
    weight: int = Field(ge=1, le=100)
    full_marks: str = Field(min_length=2, max_length=300)  # what a 4/4 looks like


class Project(Model):
    id: Slug
    course: Slug
    title: str = Field(min_length=2, max_length=120)
    summary: str = Field(min_length=10, max_length=600)
    skills: list[str] = Field(min_length=1, max_length=12)
    concepts: list[Qualified] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list, max_length=12)
    milestones: list[Milestone] = Field(min_length=1, max_length=5)
    rubric: list[RubricCriterion] = Field(min_length=1, max_length=8)
    self_review: list[str] = Field(default_factory=list, max_length=12)
    starter_repo: HttpUrl | None = None
    status: Status = "provisional"
    provenance: Provenance

    @model_validator(mode="after")
    def contract(self):
        if sum(c.weight for c in self.rubric) != 100:
            raise ValueError("rubric weights must total 100")
        if len({m.id for m in self.milestones}) != len(self.milestones):
            raise ValueError("duplicate milestone id")
        if self.status == "calibrated" and self.provenance.review is None:
            raise ValueError("a calibrated project needs a human review record")
        return self


def load(root: Path, catalog) -> dict[str, Project]:
    """Projects keyed ``course:project``; raises CatalogError on the first problem."""
    from socrat.catalog.registry import CatalogError

    found: dict[str, Project] = {}
    if not root.exists():
        return found
    for path in sorted(root.glob("*/*.yaml")):
        try:
            project = Project.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        except ValueError as exc:
            raise CatalogError(f"{path}: {exc}") from exc
        course, name = path.relative_to(root).with_suffix("").parts
        if (project.course, project.id) != (course, name):
            raise CatalogError(
                f"{path}: file path must match project {project.course}:{project.id}"
            )
        if project.course not in catalog.courses:
            raise CatalogError(f"{path}: unknown course {project.course}")
        for concept in project.concepts:
            if concept not in catalog.concepts:
                raise CatalogError(f"{path}: unknown concept {concept}")
        found[f"{project.course}:{project.id}"] = project
    return found
