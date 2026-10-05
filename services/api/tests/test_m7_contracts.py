import json
from pathlib import Path

from socrat.learning.contracts import SessionAction, StartSession


def test_session_contracts_match_exported_schemas():
    for name, contract in (("start", StartSession), ("command", SessionAction)):
        exported = Path(f"contracts/schemas/learning-session-{name}.schema.json")
        assert json.loads(exported.read_text(encoding="utf-8")) == contract.model_json_schema()
