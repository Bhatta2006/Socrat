"""Export M7 session commands and the private acceptance-record contract."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api/src"))

from socrat.learning.acceptance import AcceptanceEvidence  # noqa: E402
from socrat.learning.contracts import SessionAction, StartSession  # noqa: E402
from socrat.learning.pilot import PilotDraft  # noqa: E402

for name, contract in (
    ("learning-session-start", StartSession),
    ("learning-session-command", SessionAction),
    ("m7-acceptance-evidence", AcceptanceEvidence),
    ("m7-pilot-draft", PilotDraft),
):
    (ROOT / "contracts/schemas" / f"{name}.schema.json").write_text(
        json.dumps(contract.model_json_schema(), indent=2) + "\n",
        encoding="utf-8",
    )
