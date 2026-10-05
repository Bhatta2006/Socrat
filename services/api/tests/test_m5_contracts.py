import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from socrat.planning.contracts import PlanCommand
from socrat.planning.policy import POLICY_DOCUMENT


def test_exported_policy_and_command_contract_do_not_drift():
    assert (
        json.loads(Path("contracts/product/m5-planning-policy.json").read_text()) == POLICY_DOCUMENT
    )
    assert (
        json.loads(Path("contracts/schemas/planning-command.schema.json").read_text())
        == PlanCommand.model_json_schema()
    )


@pytest.mark.parametrize(
    "changes",
    [
        dict(weekdays=[0, 0, 2]),
        dict(weekdays=[0, 1, 7]),
        dict(target_date="next-week"),
        dict(action="confirm"),
        dict(action="pause", minutes=20),
    ],
)
def test_unsafe_or_unreviewed_schedule_commands_fail(changes):
    with pytest.raises(ValidationError):
        PlanCommand.model_validate(
            dict(
                action="generate",
                expected_revision=0,
                idempotency_key="test",
                **{k: v for k, v in changes.items() if k != "action"},
            )
            | ({"action": changes["action"]} if "action" in changes else {})
        )
