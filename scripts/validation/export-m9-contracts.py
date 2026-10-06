"""Export additive M9 contracts without changing historic policy defaults or pack digests."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api/src"))

from socrat.assessment.contracts import DisputeInput, ResponseInput, ReviewInput, StartInput  # noqa: E402
from socrat.learnerstate.policy import POLICIES, SPACED_POLICY  # noqa: E402
from socrat.skillpacks.schema import SkillPack  # noqa: E402

for name, contract in (
    ("assessment-start", StartInput),
    ("assessment-response", ResponseInput),
    ("assessment-review", ReviewInput),
    ("assessment-dispute", DisputeInput),
    ("skill-pack", SkillPack),
):
    (ROOT / "contracts/schemas" / f"{name}.schema.json").write_text(
        json.dumps(contract.model_json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
(ROOT / "contracts/product/m9-assessment-policy.json").write_text(
    json.dumps(dict(schema_version=1, scoring_version="objective_exact_1.0.0",
                    qualitative_scoring_version="human_rubric_1.0.0",
                    scheduling_policy=POLICIES["1.1.0"].model_dump(),
                    default_learning_policy="1.0.0", scheduling_requires_reviewed_promotion=True,
                    **SPACED_POLICY),
               indent=2) + "\n", encoding="utf-8"
)
