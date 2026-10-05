"""Export reviewed runtime schemas/policy, without modifying released pack payloads."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api/src"))

from socrat.learnerstate.policy import POLICIES  # noqa: E402
from socrat.learnerstate.projector import EvidenceFact  # noqa: E402
from socrat.skillpacks.schema import SkillPack  # noqa: E402

for path, value in {
    "contracts/schemas/skill-pack.schema.json": SkillPack.model_json_schema(),
    "contracts/schemas/learning-evidence.schema.json": EvidenceFact.model_json_schema(),
    "contracts/product/m4-learning-policies.json": {
        "default_version": "1.0.0", "candidate_version": "1.0.1",
        "policies": {version: policy.model_dump() for version, policy in POLICIES.items()},
    },
}.items():
    (ROOT / path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
