"""Offline original pilot drafts; deliberately not an executable/released SkillPack."""

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from socrat.learning.content import CompetitivePenalty, LearningLesson, StructuralRepair
from socrat.skillpacks.schema import CodeText, Concept, Edge, Provenance, TestCase
from socrat.skillpacks.types import Contract, Key, Language, Text


class PilotResource(Contract):
    id: Key
    title: Text
    url: str = Field(pattern=r"^https://[^\s]+$")
    role: Text
    access_note: Text
    checked_on: Literal["2026-10-06"]
    reuse: Literal["link_only"] = "link_only"


class DraftVariant(Contract):
    language: Language
    starter_code: CodeText
    reference_solution: CodeText
    target: Literal["Python 3.12", "C++20", "Java 21"]

    @model_validator(mode="after")
    def matching_target(self):
        targets = {"python": "Python 3.12", "cpp": "C++20", "java": "Java 21"}
        if self.target != targets[self.language]:
            raise ValueError("Language/target mismatch")
        return self


class DraftExercise(Contract):
    id: Key
    title: Text
    concept_ids: list[Key] = Field(min_length=1)
    family_id: Key
    statement: Text
    rubric: Text
    difficulty: int = Field(ge=1, le=10)
    estimated_minutes: int = Field(ge=1, le=180)
    calibration: Literal["uncalibrated"] = "uncalibrated"
    variants: list[DraftVariant] = Field(min_length=3, max_length=3)
    tests: list[TestCase] = Field(min_length=2, max_length=1000)
    provenance: Provenance
    accessibility: Text

    @model_validator(mode="after")
    def all_languages(self):
        if {x.language for x in self.variants} != {"python", "cpp", "java"}:
            raise ValueError("Pilot exercises require all three languages")
        if {x.visibility for x in self.tests} != {"public", "hidden"}:
            raise ValueError("Draft requires public and hidden checks")
        if len(set(self.concept_ids)) != len(self.concept_ids):
            raise ValueError("Duplicate exercise concept")
        return self


class PilotDraft(Contract):
    version: Literal["m7_pilot_draft_1.0.0"]
    status: Literal["draft_not_publishable"]
    scope: Text
    resources: list[PilotResource] = Field(min_length=1)
    concepts: list[Concept] = Field(min_length=1)
    edges: list[Edge]
    lessons: list[LearningLesson] = Field(min_length=9)
    exercises: list[DraftExercise] = Field(min_length=1)
    structural_repairs: list[StructuralRepair] = Field(min_length=1)
    competitive_penalty: CompetitivePenalty
    promotion_requirements: list[Text] = Field(min_length=1)

    @model_validator(mode="after")
    def draft_integrity(self):
        for rows in (self.resources, self.concepts, self.lessons, self.exercises):
            ids = [x.id for x in rows]
            if len(set(ids)) != len(ids):
                raise ValueError("Duplicate draft identifier")
        concepts = {x.id for x in self.concepts}
        cells = set()
        for lesson in self.lessons:
            if lesson.calibration != "uncalibrated" or not set(lesson.concept_ids) <= concepts:
                raise ValueError("Draft lessons must be unreviewed and concept-scoped")
            for concept in lesson.concept_ids:
                cell = (concept, lesson.track, lesson.language)
                if cell in cells:
                    raise ValueError("Duplicate concept/track/language lesson")
                cells.add(cell)
        expected = {
            (concept, track, language)
            for concept in concepts
            for track in ("foundations", "interview", "competitive")
            for language in ("python", "cpp", "java")
        }
        if cells != expected:
            raise ValueError("Every pilot concept requires all nine lesson cells")
        for exercise in self.exercises:
            if not set(exercise.concept_ids) <= concepts:
                raise ValueError("Unknown exercise concept")
        inventory = {x.id: x for x in self.exercises}
        mappings = set()
        for repair in self.structural_repairs:
            pair = (repair.exercise_id, repair.variant_id)
            if repair.calibration != "uncalibrated" or pair in mappings:
                raise ValueError("Repair proposals require unique unreviewed mappings")
            mappings.add(pair)
            if not set(pair) <= inventory.keys():
                raise ValueError("Repair proposal references unknown exercise")
            source, target = (inventory[key] for key in pair)
            if (
                set(source.concept_ids) != set(target.concept_ids)
                or source.family_id == target.family_id
                or target.difficulty > source.difficulty
            ):
                raise ValueError(
                    "Repair proposal must preserve concepts and change candidate family"
                )
        # Unknown/self/duplicate edges and cycles must not survive offline authoring.
        pending: dict[str, set[str]] = {concept: set() for concept in concepts}
        seen = set()
        for edge in self.edges:
            key = (edge.prerequisite, edge.concept)
            if not set(key) <= concepts or len(set(key)) != 2 or key in seen:
                raise ValueError("Invalid pilot prerequisite")
            seen.add(key)
            pending[edge.concept].add(edge.prerequisite)
        while pending:
            roots = {key for key, dependencies in pending.items() if not dependencies}
            if not roots:
                raise ValueError("Cyclic pilot prerequisites")
            pending = {key: value - roots for key, value in pending.items() if key not in roots}
        if self.competitive_penalty.calibration != "uncalibrated":
            raise ValueError("Pilot penalty remains a proposal")
        return self

    def report(self):
        canonical = json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":"))
        return dict(
            version=self.version,
            status=self.status,
            draft_digest=hashlib.sha256(canonical.encode()).hexdigest(),
            concepts=len(self.concepts),
            lessons=len(self.lessons),
            exercises=len(self.exercises),
            candidate_families=len({x.family_id for x in self.exercises}),
            repair_proposals=len(self.structural_repairs),
            language_variants=sum(len(x.variants) for x in self.exercises),
            test_cases=sum(len(x.tests) for x in self.exercises),
            publishable=False,
            promotion_requirements=self.promotion_requirements,
        )
