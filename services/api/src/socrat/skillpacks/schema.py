"""Versioned, domain-neutral authoring contract and semantic validation."""

import hashlib
import heapq
import json
from collections.abc import Iterable, Sequence
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from socrat.diagnostics.contracts import DiagnosticDefinition, MisconceptionDefinition
from socrat.learning.content import CompetitivePenalty, LearningLesson, StructuralRepair
from socrat.skillpacks.types import Contract as Contract
from socrat.skillpacks.types import Key as Key
from socrat.skillpacks.types import Language as Language
from socrat.skillpacks.types import Text as Text
from socrat.tutor.contracts import AuthoredHint

Version = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")]
CodeText = Annotated[str, StringConstraints(strip_whitespace=False, min_length=1, max_length=8000)]
IOText = Annotated[str, StringConstraints(strip_whitespace=False, min_length=0, max_length=8000)]
EvidenceMode = Literal[
    "recognize", "trace", "explain", "implement", "analyze", "transfer", "retain"
]
Modality = Literal["text", "code"]


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
    diagnostics: list[DiagnosticDefinition] = Field(default_factory=list, max_length=100)
    misconception_taxonomy: list[MisconceptionDefinition] = Field(
        default_factory=list, max_length=1000
    )
    session_content_version: Literal["1.0.0"] | None = None
    learning_lessons: list[LearningLesson] = Field(default_factory=list, max_length=3000)
    structural_repairs: list[StructuralRepair] = Field(default_factory=list, max_length=5000)
    competitive_penalty: CompetitivePenalty | None = None
    tutor_hints: list[AuthoredHint] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def validate_references(self):
        unique([f"{x.exercise_id}:{x.language}:{x.level}" for x in self.tutor_hints], "tutor hints")
        for hint in self.tutor_hints:
            exercise = next((x for x in self.exercises if x.id == hint.exercise_id), None)
            if (
                exercise is None
                or exercise.inventory != "practice"
                or hint.language not in {x.language for x in exercise.variants}
            ):
                raise ValueError("Tutor hints require a practice language variant")
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
        unique([x.id for x in self.learning_lessons], "learning lessons")
        unique(
            [f"{x.exercise_id}/{x.variant_id}" for x in self.structural_repairs],
            "structural repairs",
        )
        for lesson in self.learning_lessons:
            overlay = tracks.get(lesson.track)
            if (
                overlay is None
                or lesson.language not in self.languages
                or not set(lesson.concept_ids) <= set(overlay.concept_ids)
            ):
                raise ValueError("Lesson exceeds track/language coverage")
        for repair in self.structural_repairs:
            source, target = exercises.get(repair.exercise_id), exercises.get(repair.variant_id)
            if (
                source is None
                or target is None
                or source.inventory != "practice"
                or target.inventory != "practice"
                or source.family_id == target.family_id
                or set(source.concept_ids) != set(target.concept_ids)
                or source.modality != target.modality
                or target.difficulty > source.difficulty
            ):
                raise ValueError("Invalid structural repair mapping")
        if (
            self.learning_lessons or self.structural_repairs or self.competitive_penalty
        ) and not self.session_content_version:
            raise ValueError("Learning content requires an explicit session content version")
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
        unique([item.id for item in self.misconception_taxonomy], "misconception codes")
        taxonomy = {item.id: item for item in self.misconception_taxonomy}
        for misconception in taxonomy.values():
            if (
                misconception.concept_id not in concepts
                or misconception.repair_concept_id not in concepts
            ):
                raise ValueError("Unknown misconception concept")
        unique([item.blueprint_id for item in self.diagnostics], "diagnostic definitions")
        blueprints = {item.id: item for item in self.blueprints}
        for definition in self.diagnostics:
            diagnostic_blueprint = blueprints.get(definition.blueprint_id)
            if diagnostic_blueprint is None or diagnostic_blueprint.kind != "diagnostic":
                raise ValueError("Unknown diagnostic blueprint")
            if definition.track not in goals:
                raise ValueError("Unknown diagnostic track")
            diagnostic_track = tracks[goals[definition.track].track_id]
            if not set(diagnostic_blueprint.concept_ids) <= set(diagnostic_track.concept_ids):
                raise ValueError("Diagnostic exceeds released track overlay")
            if self.languages and not definition.languages:
                raise ValueError("Language packs require explicit diagnostic coverage")
            unique(definition.languages, "diagnostic languages")
            if not set(definition.languages) <= set(self.languages):
                raise ValueError("Undeclared diagnostic language")
            if {item.exercise_id for item in definition.items} != set(
                diagnostic_blueprint.exercise_ids
            ):
                raise ValueError("Diagnostic items do not match blueprint")
            for diagnostic_item in definition.items:
                exercise = exercises[diagnostic_item.exercise_id]
                if not set(exercise.concept_ids) <= set(diagnostic_blueprint.concept_ids):
                    raise ValueError("Diagnostic item exceeds blueprint scope")
                unique(diagnostic_item.languages, "diagnostic item languages")
                if not set(diagnostic_item.languages) <= set(definition.languages):
                    raise ValueError("Undeclared item language")
                if (exercise.modality == "code") != (
                    diagnostic_item.response.kind == "implementation"
                ):
                    raise ValueError("Diagnostic response modality mismatch")
                if (
                    diagnostic_item.response.kind == "human_rubric"
                    and diagnostic_blueprint.scoring != "human_rubric"
                ):
                    raise ValueError("Qualitative diagnostic requires a human-rubric blueprint")
                if diagnostic_item.response.kind == "implementation" and not set(
                    diagnostic_item.languages
                ) <= {variant.language for variant in exercise.variants}:
                    raise ValueError("Missing diagnostic implementation variant")
                if (
                    diagnostic_item.response.kind == "implementation"
                    and not diagnostic_item.languages
                ):
                    raise ValueError("Implementation items require explicit language coverage")
                if any(
                    code not in taxonomy or taxonomy[code].concept_id not in exercise.concept_ids
                    for code in diagnostic_item.response.misconception_answers.values()
                ):
                    raise ValueError("Unknown or mismatched misconception signature")
            # A diagnostic must not consume a protected future assessment form.
            other_families = {
                exercises[key].family_id
                for form in self.blueprints
                if form.kind != "diagnostic"
                for key in form.exercise_ids
            }
            if any(
                exercises[item.exercise_id].family_id in other_families for item in definition.items
            ):
                raise ValueError("Diagnostic overlaps protected assessment families")
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
        for key in (
            "diagnostics",
            "misconception_taxonomy",
            "learning_lessons",
            "structural_repairs",
            "session_content_version",
            "competitive_penalty",
            "tutor_hints",
        ):
            if not payload[key]:
                del payload[key]
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
