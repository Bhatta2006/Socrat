"""Export deterministic planning contracts; checked for drift by API tests."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api/src"))

from socrat.planning.contracts import PlanCommand  # noqa: E402
from socrat.planning.policy import POLICY_DOCUMENT  # noqa: E402

for relative, payload in (
    ("contracts/product/m5-planning-policy.json", POLICY_DOCUMENT),
    ("contracts/schemas/planning-command.schema.json", PlanCommand.model_json_schema()),
):
    (ROOT / relative).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
