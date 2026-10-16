"""Mutation of a correct snippet with one controlled defect (content.md §8.6).

The defect catalogue (``content/quiz/defects.yaml``) names each defect kind and the
misconception it reveals. A generator supplies the concrete edit per language as a pair of
whole lines; ``apply`` replaces exactly one matching line and keeps its indentation, so an
edit can never match by accident inside a longer line.
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field

from socrat.catalog.schema import Model, Slug

Kind = Literal[
    "off-by-one", "wrong-init", "missing-update", "wrong-update", "wrong-comparison", "wrong-output"
]


class Defect(Model):
    id: Slug
    kind: Kind
    misconception: Slug
    description: str = Field(min_length=10, max_length=300)


class Catalogue(Model):
    defects: list[Defect] = Field(min_length=1)

    def get(self, defect_id: str) -> Defect:
        for defect in self.defects:
            if defect.id == defect_id:
                return defect
        raise KeyError(f"unknown defect {defect_id}")


def load(root: Path, taxonomy: set[str]) -> Catalogue:
    catalogue = Catalogue.model_validate(
        yaml.safe_load((root / "defects.yaml").read_text(encoding="utf-8"))
    )
    ids = [d.id for d in catalogue.defects]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate defect id")
    for defect in catalogue.defects:
        if defect.misconception not in taxonomy:
            raise ValueError(f"defect {defect.id}: unknown misconception {defect.misconception}")
    return catalogue


Edit = dict[str, tuple[str, str]]  # language -> (old line, new line), stripped


def applies(code: str, old: str) -> bool:
    return sum(line.strip() == old for line in code.split("\n")) == 1


def apply_line(code: str, old: str, new: str) -> str:
    lines = code.split("\n")
    hits = [i for i, line in enumerate(lines) if line.strip() == old]
    if len(hits) != 1:
        raise ValueError(f"edit needs exactly one line {old!r}, found {len(hits)}")
    i = hits[0]
    indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
    lines[i] = indent + new
    return "\n".join(lines)


def apply(code: dict[str, str], edit: Edit) -> dict[str, str]:
    """The snippet in every language with the edit applied."""
    missing = set(code) - set(edit)
    if missing:
        raise ValueError(f"edit has no rewrite for {sorted(missing)}")
    return {lang: apply_line(snippet, *edit[lang]) for lang, snippet in code.items()}


def reverse(edit: Edit) -> Edit:
    return {lang: (new, old) for lang, (old, new) in edit.items()}


def applicable(code: dict[str, str], edit: Edit) -> bool:
    return all(lang in edit and applies(snippet, edit[lang][0]) for lang, snippet in code.items())
