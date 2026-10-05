"""Export the versioned execution boundary from its authoritative runtime contracts."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/api/src"))
from socrat.execution.protocol import JobEnvelope, ResultEnvelope, RuntimeProfile  # noqa: E402

for name, contract in (("execution-job", JobEnvelope), ("execution-result", ResultEnvelope),
                       ("execution-runtime", RuntimeProfile)):
    (ROOT / "contracts/schemas" / f"{name}.schema.json").write_text(
        json.dumps(contract.model_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
