"""Versioned, domain-neutral authoring contract and semantic validation."""

import hashlib
import heapq
import json
from collections.abc import Iterable, Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Key = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]
Version = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")]
Text = Annotated[str, Field(min_length=1, max_length=8000)]
CodeText = Annotated[str, StringConstraints(strip_whitespace=False, min_length=1, max_length=8000)]
IOText = Annotated[str, StringConstraints(strip_whitespace=False, min_length=0, max_length=8000)]
EvidenceMode = Literal[
    "recognize", "trace", "explain", "implement", "analyze", "transfer", "retain"
]
Modality = Literal["text", "code"]
Language = Literal["python", "cpp", "java"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)


class Provenance(Contract):
    author: Text
    source: Text
    license: Text
    rights_reference: Text
    attribution: Text


class Concept(Contract):
    id: Key
    title: Text
    competency: Text
    explanation: Text
    examples: list[Text] = Field(min_length=1, max_length=20)
    misconceptions: list[Text] = Field(max_length=30)
    evidence_modes: list[EvidenceMode] = Field(min_length=1, max_length=7)
    estimated_minutes: int = Field(ge=1, le=600)
    accessibility: Text


class Edge(Contract):
    prerequisite: Key
    concept: Key
    minimum_mastery: float = Field(ge=0, le=1, allow_inf_nan=False)
    rationale: Text


class TrackPolicy(Contract):
    id: Key
    goals: list[Key] = Field(min_length=1, max_length=100)
    concept_ids: list[Key] = Field(min_length=1, max_length=1000)
    prerequisite_rule: Literal["require_all"] = "require_all"
    help_ceiling: int = Field(ge=0, le=3)
    maximum_daily_minutes: int = Field(ge=1, le=180)


class ReleasedTarget(Contract):
    outcome: Key
    value: Text | None = None
    role_level: Key | None = None
    platform_or_format: Key | None = None


class GoalTemplate(Contract):
    id: Key
    title: Text
    outcome: Text
    track_id: Key
    released_targets: list[ReleasedTarget] = Field(default_factory=list, max_length=100)
    required_fields: list[
        Literal["target_date", "days_per_week", "minutes_per_session", "timezone", "language"]
    ] = Field(min_length=1, max_length=5)


class LanguageVariant(Contract):
    language: Language
    adapter_version: Literal["1.0.0"] = "1.0.0"
    starter_code: CodeText
    reference_solution: CodeText
    interface: Text
    runtime_ref: Annotated[str, Field(pattern=r"^[a-z0-9./:_-]+@sha256:[a-f0-9]{64}$")]
    time_limit_ms: int = Field(ge=10, le=30000)
    memory_limit_mb: int = Field(ge=16, le=1024)


class TestCase(Contract):
    input: IOText
    expected: IOText
    visibility: Literal["public", "hidden"]


class Exercise(Contract):
    id: Key
    title: Text
    concept_ids: list[Key] = Field(min_length=1, max_length=100)
    inventory: Literal["practice", "assessment"]
    modality: Modality
    evidence_mode: EvidenceMode
    statement: Text
    rubric: Text
    difficulty: int = Field(ge=1, le=10)
    calibration: Literal["uncalibrated", "reviewed"] = "uncalibrated"
    estimated_minutes: int = Field(ge=1, le=180)
    family_id: Key
    variants: list[LanguageVariant] = Field(default_factory=list, max_length=3)
    tests: list[TestCase] = Field(default_factory=list, max_length=1000)
    provenance: Provenance
    accessibility: Text

    @model_validator(mode="after")
    def validate_modality(self):
        if self.modality == "code":
            if not self.variants or not self.tests:
                raise ValueError("Code exercises require variants and deterministic tests")
            if {test.visibility for test in self.tests} != {"public", "hidden"}:
                raise ValueError("Code exercises require public and hidden tests")
        elif self.variants or self.tests:
            raise ValueError("Text exercises cannot contain code variants or runtime tests")
        unique([variant.language for variant in self.variants], "exercise languages")
        return self


class Blueprint(Contract):
    id: Key
    kind: Literal["diagnostic", "baseline", "weekly", "final"]
    exercise_ids: list[Key] = Field(min_length=1, max_length=1000)
    concept_ids: list[Key] = Field(min_length=1, max_length=1000)
    scoring: Literal["deterministic", "human_rubric"]


class MasteryPolicy(Contract):
    rule: Literal["independent_unseen_and_delayed"] = "independent_unseen_and_delayed"
    minimum_independent: int = Field(ge=2, le=100)
    minimum_families: int = Field(ge=2, le=100)
    retention_days: int = Field(ge=1, le=365)
    passive_weight: Literal[0] = 0


class Migration(Contract):
    from_version: Version
    concept_mapping: dict[Key, Key] = Field(max_length=1000)
    rationale: Text


def unique(values: Iterable[str], label: str):
    values = list(values)
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label}")


class SkillPack(Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    key: Key
    version: Version
    domain: Key
    title: Text
    purpose: Literal["fixture", "launch"]
    change_log: Text
    modalities: list[Modality] = Field(min_length=1, max_length=2)
    languages: list[Language] = Field(max_length=3)
    provenance: Provenance
    concepts: list[Concept] = Field(min_length=1, max_length=1000)
    edges: list[Edge] = Field(max_length=5000)
    goals: list[GoalTemplate] = Field(min_length=1, max_length=100)
    tracks: list[TrackPolicy] = Field(min_length=1, max_length=100)
    exercises: list[Exercise] = Field(min_length=1, max_length=5000)
    blueprints: list[Blueprint] = Field(min_length=1, max_length=100)
    mastery_policy: MasteryPolicy
    migration: Migration | None = None

    @model_validator(mode="after")
    def validate_references(self):
        groups: dict[str, Sequence[Concept | GoalTemplate | TrackPolicy | Exercise | Blueprint]] = {
            "concepts": self.concepts,
            "goals": self.goals,
            "tracks": self.tracks,
            "exercises": self.exercises,
            "blueprints": self.blueprints,
        }
        for label, items in groups.items():
            unique([item.id for item in items], label)
        unique(self.languages, "pack languages")
        unique(self.modalities, "pack modalities")
        if ("code" in self.modalities) != bool(self.languages):
            raise ValueError("Code modality and declared runtime languages must agree")
        concepts = {concept.id: concept for concept in self.concepts}
        goals = {goal.id: goal for goal in self.goals}
        tracks = {track.id: track for track in self.tracks}
        exercises = {exercise.id: exercise for exercise in self.exercises}
        for edge in self.edges:
            if edge.prerequisite not in concepts or edge.concept not in concepts:
                raise ValueError("Unknown prerequisite concept")
        if len({(edge.prerequisite, edge.concept) for edge in self.edges}) != len(self.edges):
            raise ValueError("Duplicate prerequisite edge")
        self.topological_order()
        for goal in self.goals:
            unique(goal.required_fields, "goal fields")
            if goal.track_id not in tracks or goal.id not in tracks[goal.track_id].goals:
                raise ValueError("Goal and track overlay mismatch")
        for track in self.tracks:
            unique(track.goals, "track goals")
            unique(track.concept_ids, "track concepts")
            if not set(track.concept_ids) <= concepts.keys():
                raise ValueError("Unknown track concept")
            if any(goal not in goals or goals[goal].track_id != track.id for goal in track.goals):
                raise ValueError("Unknown or mismatched track goal")
            selected = set(track.concept_ids)
            if any(
                edge.concept in selected and edge.prerequisite not in selected
                for edge in self.edges
            ):
                raise ValueError("Track overlay omits a required prerequisite")
        for exercise in self.exercises:
            unique(exercise.concept_ids, "exercise concepts")
            if not set(exercise.concept_ids) <= concepts.keys():
                raise ValueError("Unknown exercise concept")
            if exercise.modality not in self.modalities:
                raise ValueError("Unsupported exercise modality")
            if any(
                exercise.evidence_mode not in concepts[key].evidence_modes
                for key in exercise.concept_ids
            ):
                raise ValueError("Unsupported concept evidence mode")
            if not {variant.language for variant in exercise.variants} <= set(self.languages):
                raise ValueError("Undeclared language variant")
        practice_families = {
            item.family_id for item in self.exercises if item.inventory == "practice"
        }
        assessment_families = {
            item.family_id for item in self.exercises if item.inventory == "assessment"
        }
        if practice_families & assessment_families:
            raise ValueError("Practice and assessment families must be separate")
        for blueprint in self.blueprints:
            unique(blueprint.exercise_ids, "blueprint exercises")
            unique(blueprint.concept_ids, "blueprint concepts")
            if (
                not set(blueprint.exercise_ids) <= exercises.keys()
                or not set(blueprint.concept_ids) <= concepts.keys()
            ):
                raise ValueError("Unknown blueprint reference")
            covered = set()
            for key in blueprint.exercise_ids:
                item = exercises[key]
                if item.inventory != "assessment":
                    raise ValueError("Blueprints cannot reuse practice inventory")
                covered.update(item.concept_ids)
            if not set(blueprint.concept_ids) <= covered:
                raise ValueError("Blueprint competency coverage is incomplete")
        baseline_families = {
            exercises[key].family_id
            for blueprint in self.blueprints
            if blueprint.kind == "baseline"
            for key in blueprint.exercise_ids
        }
        final_families = {
            exercises[key].family_id
            for blueprint in self.blueprints
            if blueprint.kind == "final"
            for key in blueprint.exercise_ids
        }
        if baseline_families & final_families:
            raise ValueError("Baseline and final forms cannot reuse item families")
        if self.migration:
            if tuple(map(int, self.migration.from_version.split("."))) >= tuple(
                map(int, self.version.split("."))
            ):
                raise ValueError("Migration must reference a prior version")
            if not set(self.migration.concept_mapping.values()) <= concepts.keys():
                raise ValueError("Unknown migration target")
        return self

    def topological_order(self) -> list[str]:
        incoming = {concept.id: 0 for concept in self.concepts}
        children: dict[str, list[str]] = {key: [] for key in incoming}
        for edge in self.edges:
            incoming[edge.concept] += 1
            children[edge.prerequisite].append(edge.concept)
        ready = [key for key, count in incoming.items() if count == 0]
        heapq.heapify(ready)
        ordered = []
        while ready:
            key = heapq.heappop(ready)
            ordered.append(key)
            for child in sorted(children[key]):
                incoming[child] -= 1
                if incoming[child] == 0:
                    heapq.heappush(ready, child)
        if len(ordered) != len(incoming):
            raise ValueError("Prerequisite graph contains a cycle")
        return ordered

    def canonical_json(self) -> str:
        payload = self.model_dump(mode="json")
        # Preserve pre-M3 immutable release digests. Empty target declarations add no coverage.
        for goal in payload["goals"]:
            if not goal["released_targets"]:
                del goal["released_targets"]
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def variant_for(self, exercise_id: str, language: str) -> LanguageVariant | None:
        """Missing variants remain explicitly unavailable; never translate or execute."""
        for item in self.exercises:
            if item.id == exercise_id:
                return next(
                    (variant for variant in item.variants if variant.language == language), None
                )
        return None

    def coverage(self) -> dict[str, dict[str, bool]]:
        return {
            item.id: {
                language: self.variant_for(item.id, language) is not None
                for language in self.languages
            }
            for item in self.exercises
            if item.modality == "code"
        }
