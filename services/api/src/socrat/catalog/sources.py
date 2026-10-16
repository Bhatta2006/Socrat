"""Source registry and the license gate for adapted content.

Selection policy (Content Master Plan §2): original text is the default. A record marked
``origin: adapted`` may only cite registry entries whose license was verified and whose
action allows adaptation, under one of the entry's SPDX identifiers.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, HttpUrl, model_validator

from socrat.catalog.schema import Model, Provenance, Slug

REGISTRY_PATH = Path(__file__).resolve().parents[5] / "content" / "sources" / "registry.yaml"
LicenseClass = Literal[
    "permissive",
    "share-alike",
    "non-commercial",
    "no-derivatives",
    "all-rights-reserved",
    "mixed",
    "unknown",
]
ADAPTABLE = {"adapt", "share-alike-lane"}
LINK_ONLY_CLASSES = {"non-commercial", "no-derivatives", "all-rights-reserved"}


class SourceEntry(Model):
    id: Slug
    name: str = Field(min_length=2, max_length=200)
    url: HttpUrl
    content: str = Field(min_length=1, max_length=200)
    license: str = Field(min_length=2, max_length=200)
    spdx: list[str] = Field(default_factory=list)
    license_class: LicenseClass
    license_status: Literal["verified", "unverified"]
    action: Literal["adapt", "share-alike-lane", "link-only", "per-item", "verify"]
    last_verified_at: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    verified_from: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def action_fits_license(self):
        if self.license_class in LINK_ONLY_CLASSES and self.action != "link-only":
            raise ValueError(f"{self.id}: {self.license_class} sources must be link-only")
        if self.license_class == "unknown" and self.action not in {"link-only", "verify"}:
            raise ValueError(f"{self.id}: a source with an unknown license is link-only or verify")
        if self.action == "adapt" and self.license_class != "permissive":
            raise ValueError(f"{self.id}: only permissive sources can be adapted directly")
        if self.action == "share-alike-lane" and self.license_class != "share-alike":
            raise ValueError(f"{self.id}: the share-alike lane is for share-alike sources")
        if self.action in ADAPTABLE and (self.license_status != "verified" or not self.spdx):
            raise ValueError(f"{self.id}: adaptation needs a verified SPDX license")
        if self.license_status == "verified" and not (self.last_verified_at and self.verified_from):
            raise ValueError(f"{self.id}: verified entries record when and where")
        return self


class SourceRegistry(Model):
    version: int = Field(ge=1)
    sources: list[SourceEntry]

    @model_validator(mode="after")
    def unique(self):
        ids = [entry.id for entry in self.sources]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate source id")
        return self

    def get(self, source_id: str) -> SourceEntry:
        return next(entry for entry in self.sources if entry.id == source_id)

    def find(self, source_id: str) -> SourceEntry | None:
        return next((entry for entry in self.sources if entry.id == source_id), None)


def load_registry(path: Path = REGISTRY_PATH) -> SourceRegistry:
    return SourceRegistry.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def provenances(catalog) -> Iterator[tuple[str, Provenance]]:
    """Every provenance record in the catalog, with where it was declared."""
    for key, concept in catalog.concepts.items():
        if concept.provenance:
            yield key, concept.provenance
        for item in concept.quiz:
            if item.provenance:
                yield f"{key} quiz {item.id}", item.provenance
    for problem_id, (_, problem) in catalog.problems.items():
        if problem.provenance:
            yield f"problem {problem_id}", problem.provenance
    for key, pack in catalog.atom_packs.items():
        if pack.provenance:
            yield f"atoms {key}", pack.provenance
    for key, pattern in getattr(catalog, "patterns", {}).items():
        yield f"pattern {key}", pattern.provenance
    for key, family in getattr(catalog, "quiz_families", {}).items():
        yield f"quiz family {key}", family.provenance


def violations(records, registry: SourceRegistry) -> list[str]:
    found = []
    for where, provenance in records:
        if provenance.origin != "adapted":
            continue
        for ref in provenance.authors_adapted_from:
            entry = registry.find(ref.source_id)
            if entry is None:
                found.append(f"{where}: unknown source {ref.source_id}")
            elif entry.license_status != "verified":
                found.append(f"{where}: source {entry.id} is unverified; adaptation not allowed")
            elif entry.action not in ADAPTABLE:
                found.append(
                    f"{where}: source {entry.id} is {entry.action}; adaptation not allowed"
                )
            elif ref.license_spdx not in entry.spdx:
                found.append(
                    f"{where}: license {ref.license_spdx} does not match {entry.id} "
                    f"({', '.join(entry.spdx)})"
                )
    return found


def check_catalog(catalog, registry: SourceRegistry | None = None) -> None:
    from socrat.catalog.registry import CatalogError

    problems = violations(provenances(catalog), registry or load_registry())
    if problems:
        raise CatalogError("license gate: " + "; ".join(problems))
