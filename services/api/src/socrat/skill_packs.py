"""Versioned, domain-neutral skill-pack contract and runtime loading."""

import hashlib
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.models import PackItemQuarantine, PackVersion

EvidenceMode = Literal[
    "recognize", "trace", "explain", "implement", "analyze", "transfer", "retain"
]
Strength = Literal["required", "recommended"]
ContentKind = Literal["lesson", "exercise", "assessment"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Prerequisite(StrictModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    threshold: float = Field(ge=0, le=1)
    strength: Strength
    rationale: str = Field(min_length=3, max_length=500)


class Misconception(StrictModel):
    code: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    signal: str = Field(min_length=3, max_length=500)
    repair_concept: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")


class MasteryPolicy(StrictModel):
    min_independent: int = Field(ge=1, le=20)
    min_diverse_modes: int = Field(ge=1, le=7)
    assessment_required: bool
    retention_days: int = Field(ge=1, le=365)


class Concept(StrictModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    name: str = Field(min_length=2, max_length=120)
    competency: str = Field(min_length=10, max_length=500)
    scope: str = Field(min_length=3, max_length=500)
    exclusions: list[str]
    objectives: list[str] = Field(min_length=1)
    evidence_modes: list[EvidenceMode] = Field(min_length=1)
    prerequisites: list[Prerequisite]
    misconceptions: list[Misconception]
    mastery: MasteryPolicy
    expected_minutes: int = Field(ge=1, le=600)
    accessibility_notes: str = Field(min_length=3, max_length=1000)
    author: str = Field(min_length=2, max_length=120)
    provenance: str = Field(min_length=3, max_length=1000)


class LanguageAdapter(StrictModel):
    language: str = Field(pattern=r"^[a-z][a-z0-9_+]{1,31}$")
    tool: Literal["code_execution", "manual"]
    runtime_key: str = Field(min_length=2, max_length=120)


class GoalTemplate(StrictModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    track: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    outcome: str = Field(min_length=10, max_length=500)
    required_concepts: list[str] = Field(min_length=1)


class TrackPolicy(StrictModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    goal_keys: list[str] = Field(min_length=1)
    required_concepts: list[str] = Field(min_length=1)
    optional_concepts: list[str]
    languages: list[str]
    difficulty_ceiling: int = Field(ge=1, le=10)


class CoverageCell(StrictModel):
    track: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    language: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_+]{1,31}$")
    status: Literal["draft", "released", "unavailable"]
    reason: str | None = Field(default=None, min_length=10, max_length=500)


class ConceptMapping(StrictModel):
    old_key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    new_keys: list[str]
    disposition: Literal["replaced", "retired"]
    rationale: str = Field(min_length=10, max_length=500)


class EvidenceReference(StrictModel):
    uri: str = Field(min_length=3, max_length=500)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    summary: str = Field(min_length=20, max_length=1000)


class ReleaseEvidence(StrictModel):
    rights: EvidenceReference
    accessibility: EvidenceReference
    concept_quality: EvidenceReference
    exercise_quality: EvidenceReference
    assessment_separation: EvidenceReference
    canary: EvidenceReference
    language_coverage: EvidenceReference | None = None


class Source(StrictModel):
    author: str = Field(min_length=2, max_length=120)
    license: str = Field(min_length=2, max_length=120)
    rights_checked_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class ContentItem(StrictModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    kind: ContentKind
    concept_keys: list[str] = Field(min_length=1)
    evidence_modes: list[EvidenceMode] = Field(min_length=1)
    language_variants: list[str]
    title: str = Field(min_length=3, max_length=160)
    source: Source
    accessibility_notes: str = Field(min_length=3, max_length=1000)


class AssessmentBlueprint(StrictModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    track: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    concept_keys: list[str] = Field(min_length=1)
    evidence_modes: list[EvidenceMode] = Field(min_length=1)


def unique_keys(values: Sequence[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label}")


def coverage_languages(track: TrackPolicy) -> list[str | None]:
    return list(track.languages) if track.languages else [None]


def verify_dag(concepts: list[Concept]) -> None:
    edges = {item.key: [edge.key for edge in item.prerequisites] for item in concepts}
    visited: set[str] = set()
    active: set[str] = set()

    def visit(key: str) -> None:
        if key in active:
            raise ValueError("prerequisite cycle")
        if key in visited:
            return
        active.add(key)
        for prerequisite in edges[key]:
            visit(prerequisite)
        active.remove(key)
        visited.add(key)

    for key in edges:
        visit(key)


class PackManifest(StrictModel):
    contract_version: Literal[1, 2]
    release_stage: Literal["draft", "candidate"]
    key: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    name: str = Field(min_length=3, max_length=120)
    domain: str = Field(min_length=3, max_length=120)
    evidence_modalities: list[EvidenceMode] = Field(min_length=1)
    language_adapters: list[LanguageAdapter]
    concepts: list[Concept] = Field(min_length=1)
    goal_templates: list[GoalTemplate] = Field(min_length=1)
    track_policies: list[TrackPolicy] = Field(min_length=1)
    coverage: list[CoverageCell] = Field(default_factory=list)
    migration_from_version: str | None = Field(default=None, pattern=r"^\d+\.\d+\.\d+$")
    concept_mappings: list[ConceptMapping] = Field(default_factory=list)
    release_evidence: ReleaseEvidence | None = None
    content: list[ContentItem]
    assessment_blueprints: list[AssessmentBlueprint] = Field(min_length=1)

    @model_validator(mode="after")
    def references_and_graph(self) -> "PackManifest":
        concepts = {item.key: item for item in self.concepts}
        goals = {item.key: item for item in self.goal_templates}
        tracks = {item.key: item for item in self.track_policies}
        adapters = {item.language for item in self.language_adapters}
        unique_keys([item.key for item in self.concepts], "concept")
        unique_keys([item.key for item in self.goal_templates], "goal")
        unique_keys([item.key for item in self.track_policies], "track")
        unique_keys([item.key for item in self.content], "content item")
        unique_keys([item.key for item in self.assessment_blueprints], "assessment blueprint")
        unique_keys([item.language for item in self.language_adapters], "language adapter")
        if self.contract_version == 2:
            expected_cells = {
                (track.key, language)
                for track in self.track_policies
                for language in coverage_languages(track)
            }
            actual_cells = [(cell.track, cell.language) for cell in self.coverage]
            if len(actual_cells) != len(set(actual_cells)) or set(actual_cells) != expected_cells:
                raise ValueError("coverage must declare every track/language cell exactly once")
            for cell in self.coverage:
                if cell.status == "draft" and self.release_stage != "draft":
                    raise ValueError("release candidate has draft coverage")
                if cell.status == "unavailable" and not cell.reason:
                    raise ValueError("unavailable coverage needs a reason")
                if cell.status != "unavailable" and cell.reason:
                    raise ValueError("coverage reason is only for unavailable cells")
            if self.release_stage == "candidate":
                if self.release_evidence is None:
                    raise ValueError("release candidate needs an evidence bundle")
                if any(cell.status == "released" and cell.language for cell in self.coverage):
                    if self.release_evidence.language_coverage is None:
                        raise ValueError("released language coverage needs verification evidence")
            elif self.release_evidence is not None:
                raise ValueError("draft cannot claim release evidence")
            unique_keys([mapping.old_key for mapping in self.concept_mappings], "concept mapping")
            if self.concept_mappings and self.migration_from_version is None:
                raise ValueError("concept mappings need a source version")
            if self.migration_from_version == self.version:
                raise ValueError("migration source cannot be the current version")
            for mapping in self.concept_mappings:
                unique_keys(mapping.new_keys, "mapped concept")
                if mapping.disposition == "replaced" and not mapping.new_keys:
                    raise ValueError("replacement must name a current concept")
                if mapping.disposition == "retired" and mapping.new_keys:
                    raise ValueError("retired concept cannot have replacements")
                if not set(mapping.new_keys) <= concepts.keys():
                    raise ValueError("mapping references unknown current concept")
        supported_modes = set(self.evidence_modalities)
        for concept in self.concepts:
            if not set(concept.evidence_modes) <= supported_modes:
                raise ValueError("concept uses unsupported modality")
            if concept.mastery.min_diverse_modes > len(set(concept.evidence_modes)):
                raise ValueError("mastery diversity exceeds concept modalities")
            unique_keys([edge.key for edge in concept.prerequisites], "prerequisite")
            for edge in concept.prerequisites:
                if edge.key not in concepts:
                    raise ValueError("unknown prerequisite")
            for misconception in concept.misconceptions:
                if misconception.repair_concept not in concepts:
                    raise ValueError("unknown misconception repair concept")
        verify_dag(self.concepts)
        for track in self.track_policies:
            unique_keys(track.goal_keys, "track goal")
            unique_keys(track.required_concepts, "required concept")
            unique_keys(track.optional_concepts, "optional concept")
            unique_keys(track.languages, "track language")
            if set(track.required_concepts) & set(track.optional_concepts):
                raise ValueError("required/optional concept overlap")
            if not set(track.languages) <= adapters:
                raise ValueError("track uses unknown language adapter")
            selected = set(track.required_concepts + track.optional_concepts)
            if not selected <= concepts.keys():
                raise ValueError("track references unknown concept")
            for key in selected:
                prerequisites = {
                    edge.key for edge in concepts[key].prerequisites if edge.strength == "required"
                }
                if not prerequisites <= selected:
                    raise ValueError("track missing prerequisite closure")
            if not set(track.goal_keys) <= goals.keys():
                raise ValueError("track references unknown goal")
        for goal in self.goal_templates:
            unique_keys(goal.required_concepts, "goal concept")
            if goal.track not in tracks or goal.key not in tracks[goal.track].goal_keys:
                raise ValueError("goal/track overlay mismatch")
            if not set(goal.required_concepts) <= set(tracks[goal.track].required_concepts):
                raise ValueError("goal outside track coverage")
        for item in self.content:
            unique_keys(item.concept_keys, "content concept")
            unique_keys(item.evidence_modes, "content mode")
            unique_keys(item.language_variants, "content language")
            if not set(item.concept_keys) <= concepts.keys():
                raise ValueError("content references unknown concept")
            if not set(item.evidence_modes) <= supported_modes:
                raise ValueError("content uses unsupported modality")
            concept_modes = set().union(
                *(set(concepts[key].evidence_modes) for key in item.concept_keys)
            )
            if not set(item.evidence_modes) <= concept_modes:
                raise ValueError("content mode outside concept contract")
            if not set(item.language_variants) <= adapters:
                raise ValueError("content uses unknown language adapter")
        for blueprint in self.assessment_blueprints:
            unique_keys(blueprint.concept_keys, "assessment concept")
            unique_keys(blueprint.evidence_modes, "assessment mode")
            if blueprint.track not in tracks:
                raise ValueError("assessment references unknown track")
            if not set(blueprint.concept_keys) <= set(tracks[blueprint.track].required_concepts):
                raise ValueError("assessment outside track coverage")
            if not set(blueprint.evidence_modes) <= supported_modes:
                raise ValueError("assessment uses unsupported modality")
            concept_modes = set().union(
                *(set(concepts[key].evidence_modes) for key in blueprint.concept_keys)
            )
            if not set(blueprint.evidence_modes) <= concept_modes:
                raise ValueError("assessment mode outside concept contract")
        return self


def verify_concept_migration(previous: PackManifest, current: PackManifest) -> None:
    """Stable keys carry forward; every removed key needs an explicit disposition."""
    removed = {concept.key for concept in previous.concepts} - {
        concept.key for concept in current.concepts
    }
    mappings = {mapping.old_key: mapping for mapping in current.concept_mappings}
    if removed != mappings.keys():
        raise ValueError("concept migration must account for every removed key")
    if current.migration_from_version is not None and current.migration_from_version != previous.version:
        raise ValueError("concept migration source does not match active version")
    if removed and current.migration_from_version is None:
        raise ValueError("concept migration source does not match active version")
    if not removed and current.concept_mappings:
        raise ValueError("concept mappings have no removed keys")


def manifest_digest(manifest: PackManifest) -> str:
    excluded = (
        {"coverage", "migration_from_version", "concept_mappings", "release_evidence"}
        if manifest.contract_version == 1
        else None
    )
    return hashlib.sha256(
        manifest.model_dump_json(exclude_none=True, exclude=excluded).encode()
    ).hexdigest()


def verified_manifest(version: PackVersion) -> PackManifest:
    manifest = PackManifest.model_validate(version.manifest)
    if manifest_digest(manifest) != version.digest:
        raise ValueError("skill-pack integrity check failed")
    return manifest


def available_manifest(db: Session, version: PackVersion) -> PackManifest:
    manifest = verified_manifest(version)
    blocked = set(
        db.scalars(
            select(PackItemQuarantine.item_key).where(PackItemQuarantine.version_id == version.id)
        ).all()
    )
    return manifest.model_copy(
        update={
            "content": [
                item
                for item in manifest.content
                if item.key not in blocked and item.kind != "assessment"
            ]
        }
    )


def load_active_pack(db: Session, key: str) -> PackManifest | None:
    version = db.scalar(
        select(PackVersion).where(
            PackVersion.pack_key == key,
            PackVersion.is_active.is_(True),
            PackVersion.status == "released",
        )
    )
    return available_manifest(db, version) if version is not None else None


def load_eligible_pack(
    db: Session, key: str, track_key: str, language: str | None
) -> PackManifest | None:
    """Return only released content for an explicit track/language cell."""
    manifest = load_active_pack(db, key)
    if manifest is None or manifest.contract_version != 2:
        return None
    eligible = any(
        cell.track == track_key and cell.language == language and cell.status == "released"
        for cell in manifest.coverage
    )
    if not eligible:
        return None
    track = next(item for item in manifest.track_policies if item.key == track_key)
    selected_concepts = set(track.required_concepts + track.optional_concepts)
    return manifest.model_copy(
        update={
            "content": [
                item
                for item in manifest.content
                if set(item.concept_keys) <= selected_concepts
                and (not item.language_variants or language in item.language_variants)
            ]
        }
    )


def load_pack_version(db: Session, key: str, version_name: str) -> PackManifest | None:
    version = db.scalar(
        select(PackVersion).where(
            PackVersion.pack_key == key,
            PackVersion.version == version_name,
            PackVersion.status == "released",
        )
    )
    return available_manifest(db, version) if version is not None else None
