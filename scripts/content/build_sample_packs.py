"""Regenerate M2 draft fixtures. They are structural samples, not release content."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "contracts" / "skill-packs"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "api" / "src"))

from socrat.skill_packs import PackManifest  # noqa: E402

MODES = ["recognize", "trace", "explain", "implement", "analyze", "transfer", "retain"]


def concept(key: str, name: str, prerequisites: list[str], modes: list[str]) -> dict:
    return {
        "key": key,
        "name": name,
        "competency": f"Demonstrate {name.lower()} on an unfamiliar task",
        "scope": f"Foundational {name.lower()} tasks",
        "exclusions": ["Unreleased advanced variants"],
        "objectives": [f"Apply {name.lower()} and explain the result"],
        "evidence_modes": modes,
        "prerequisites": [
            {
                "key": dependency,
                "threshold": 0.65,
                "strength": "required",
                "rationale": f"{dependency} supports {key}",
            }
            for dependency in prerequisites
        ],
        "misconceptions": [],
        "mastery": {
            "min_independent": 2,
            "min_diverse_modes": 2,
            "assessment_required": True,
            "retention_days": 7,
        },
        "expected_minutes": 45,
        "accessibility_notes": "Provide a text equivalent for every trace or diagram",
        "author": "Socrat learning design",
        "provenance": "Original Socrat M2 draft concept map",
    }


def dsa_pack() -> dict:
    graph = [
        ("language-readiness", "Language readiness", [], ["trace", "implement"]),
        ("debugging", "Debugging and testing", ["language-readiness"], ["trace", "implement"]),
        ("complexity", "Complexity analysis", ["language-readiness"], ["explain", "analyze"]),
        ("arrays", "Arrays and strings", ["language-readiness"], ["trace", "implement"]),
        ("hash-maps", "Hash maps and sets", ["arrays"], ["trace", "implement"]),
        ("binary-search", "Binary search", ["complexity", "arrays"], ["trace", "implement"]),
        ("two-pointers", "Two pointers", ["arrays", "hash-maps"], ["explain", "implement"]),
        ("recursion", "Recursion and call stack", ["language-readiness"], ["trace", "implement"]),
        ("trees", "Tree traversal", ["recursion"], ["trace", "implement"]),
        ("graphs", "Graph traversal", ["trees"], ["trace", "implement"]),
        (
            "interview-tradeoffs",
            "Interview strategy tradeoffs",
            ["binary-search", "two-pointers"],
            ["explain", "analyze"],
        ),
        ("number-theory", "Number theory basics", ["complexity"], ["explain", "implement"]),
        ("prefix-sums", "Prefix sums", ["arrays"], ["trace", "implement"]),
        ("greedy", "Greedy reasoning", ["complexity"], ["explain", "implement"]),
        ("dsu", "Disjoint set union", ["graphs"], ["trace", "implement"]),
        ("shortest-paths", "Shortest paths", ["graphs", "greedy"], ["trace", "implement"]),
        (
            "dynamic-programming",
            "Dynamic programming",
            ["recursion", "arrays"],
            ["explain", "implement"],
        ),
        ("contest-strategy", "Contest strategy", ["greedy", "prefix-sums"], ["explain", "analyze"]),
    ]
    foundations = [
        "language-readiness",
        "debugging",
        "complexity",
        "arrays",
        "hash-maps",
        "binary-search",
        "two-pointers",
        "recursion",
    ]
    interview = foundations + ["trees", "graphs", "interview-tradeoffs"]
    competitive = interview + [
        "number-theory",
        "prefix-sums",
        "greedy",
        "dsu",
        "shortest-paths",
        "dynamic-programming",
        "contest-strategy",
    ]
    tracks = {
        "foundations": foundations,
        "interview": interview,
        "competitive": competitive,
    }
    return {
        "contract_version": 2,
        "release_stage": "draft",
        "key": "dsa",
        "version": "0.1.0",
        "name": "Data structures and algorithms",
        "domain": "computer-science",
        "evidence_modalities": MODES,
        "language_adapters": [
            {
                "language": language,
                "tool": "code_execution",
                "runtime_key": f"{language}-pending-m6",
            }
            for language in ("python", "cpp", "java")
        ],
        "concepts": [concept(*row) for row in graph],
        "goal_templates": [
            {
                "key": f"{track}-goal",
                "track": track,
                "outcome": f"Demonstrate independent {track} DSA capability",
                "required_concepts": nodes,
            }
            for track, nodes in tracks.items()
        ],
        "track_policies": [
            {
                "key": track,
                "goal_keys": [f"{track}-goal"],
                "required_concepts": nodes,
                "optional_concepts": [],
                "languages": ["python", "cpp", "java"],
                "difficulty_ceiling": ceiling,
            }
            for (track, nodes), ceiling in zip(tracks.items(), (2, 5, 8), strict=True)
        ],
        "coverage": [
            {"track": track, "language": language, "status": "draft"}
            for track in tracks
            for language in ("python", "cpp", "java")
        ],
        "content": [
            {
                "key": "readiness-lesson",
                "kind": "lesson",
                "concept_keys": ["language-readiness"],
                "evidence_modes": ["trace"],
                "language_variants": ["python", "cpp", "java"],
                "title": "Trace a simple loop",
                "source": {
                    "author": "Socrat learning design",
                    "license": "original",
                    "rights_checked_at": "2026-09-30",
                },
                "accessibility_notes": "Trace table has a text equivalent",
            }
        ],
        "assessment_blueprints": [
            {
                "key": f"{track}-baseline",
                "track": track,
                "concept_keys": nodes,
                "evidence_modes": ["trace", "explain", "implement"],
            }
            for track, nodes in tracks.items()
        ],
    }


def non_dsa_pack() -> dict:
    return {
        "contract_version": 2,
        "release_stage": "draft",
        "key": "argument-reasoning",
        "version": "0.1.0",
        "name": "Argument reasoning test fixture",
        "domain": "critical-thinking",
        "evidence_modalities": ["explain", "trace"],
        "language_adapters": [],
        "concepts": [
            concept("premises", "Identifying premises", [], ["explain", "trace"]),
            concept("conclusions", "Identifying conclusions", ["premises"], ["explain", "trace"]),
        ],
        "goal_templates": [
            {
                "key": "reasoning-goal",
                "track": "foundations",
                "outcome": "Identify premises and conclusions independently",
                "required_concepts": ["premises", "conclusions"],
            }
        ],
        "track_policies": [
            {
                "key": "foundations",
                "goal_keys": ["reasoning-goal"],
                "required_concepts": ["premises", "conclusions"],
                "optional_concepts": [],
                "languages": [],
                "difficulty_ceiling": 1,
            }
        ],
        "coverage": [{"track": "foundations", "language": None, "status": "draft"}],
        "content": [],
        "assessment_blueprints": [
            {
                "key": "reasoning-check",
                "track": "foundations",
                "concept_keys": ["premises", "conclusions"],
                "evidence_modes": ["explain", "trace"],
            }
        ],
    }


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for filename, data in (
        ("dsa-sample.json", dsa_pack()),
        ("non-dsa-fixture.json", non_dsa_pack()),
    ):
        PackManifest.model_validate(data)
        (ROOT / filename).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    schema = (
        Path(__file__).resolve().parents[2] / "contracts" / "schemas" / "skill-pack.schema.json"
    )
    schema.write_text(
        json.dumps(PackManifest.model_json_schema(), indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
