"""Export M8 structured request/output contracts and additive skill-pack authoring schema."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api/src"))

from socrat.skillpacks.schema import SkillPack  # noqa: E402
from socrat.tutor.contracts import HintRequest, ShadowOutput, TutorOutput  # noqa: E402
from socrat.tutor.evaluation import TutorEvaluation  # noqa: E402

for name, contract in (
    ("tutor-request", HintRequest),
    ("tutor-output", TutorOutput),
    ("advisor-shadow-output", ShadowOutput),
    ("skill-pack", SkillPack),
    ("m8-evaluation", TutorEvaluation),
):
    (ROOT / "contracts/schemas" / f"{name}.schema.json").write_text(
        json.dumps(contract.model_json_schema(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
