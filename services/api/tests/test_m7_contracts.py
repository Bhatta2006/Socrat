import json
from pathlib import Path

from socrat.learning.contracts import SessionAction, StartSession
from socrat.planning.sessions import SESSION_POLICY


def test_session_contracts_match_exported_schemas():
    for name, contract in (("start", StartSession), ("command", SessionAction)):
        exported = Path(f"contracts/schemas/learning-session-{name}.schema.json")
        assert json.loads(exported.read_text(encoding="utf-8")) == contract.model_json_schema()


def test_session_planning_policy_matches_export():
    assert (
        json.loads(Path("contracts/product/m7-session-planning-policy.json").read_text())
        == SESSION_POLICY
    )
