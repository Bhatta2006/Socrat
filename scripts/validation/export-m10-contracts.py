"""Export the M10 command contracts from runtime validation."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api/src"))

from socrat.accountability.preferences import PreferencesUpdate  # noqa: E402
from socrat.accountability.routes import CleanupInput, DeferInput, DeleteInput  # noqa: E402

for name, contract in (
    ("preferences-update", PreferencesUpdate), ("privacy-delete", DeleteInput),
    ("privacy-cleanup", CleanupInput), ("assessment-deferral", DeferInput),
):
    (ROOT / "contracts/schemas" / f"{name}.schema.json").write_text(
        json.dumps(contract.model_json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
