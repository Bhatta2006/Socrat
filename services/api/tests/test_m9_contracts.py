import json
from pathlib import Path

from m9_support import assessment_pack

from socrat.assessment.audit import coverage_audit
from socrat.assessment.contracts import DisputeInput, ResponseInput, ReviewInput, StartInput
from socrat.learnerstate.policy import POLICIES, SPACED_POLICY


def test_exported_m9_contracts_and_inventory_match_runtime():
    for name, contract in (
        ("assessment-start", StartInput),
        ("assessment-response", ResponseInput),
        ("assessment-review", ReviewInput),
        ("assessment-dispute", DisputeInput),
    ):
        assert (
            json.loads(Path(f"contracts/schemas/{name}.schema.json").read_text())
            == contract.model_json_schema()
        )
    policy = json.loads(Path("contracts/product/m9-assessment-policy.json").read_text())
    assert policy["scheduling_policy"] == POLICIES["1.1.0"].model_dump()
    assert all(policy[key] == value for key, value in SPACED_POLICY.items())
    audit = coverage_audit(assessment_pack())
    assert not audit["ready"] and len(audit["cells"]) == 9
    assert all(x["missing_representations"] and not x["missing_kinds"] for x in audit["cells"])
