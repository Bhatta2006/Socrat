"""Synthetic review checks cannot manufacture independent quality judgments."""

import importlib.util
from pathlib import Path

from socrat.tutor.gateway import GatewayResult

ROOT = Path(__file__).resolve().parents[3]


def collector():
    spec = importlib.util.spec_from_file_location(
        "m8_collection", ROOT / "scripts/validation/collect-m8-reviews.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collection_distinguishes_provider_failure_and_unsafe_proposal():
    module = collector()
    case = dict(
        context=dict(allowed_level=1, concepts=[dict(id="scan")], code="", reasoning="trace")
    )
    failure = module.check(case, GatewayResult(None, "provider_timeout", latency_ms=4001))
    assert not failure["policy_accepted"] and not failure["production_deadline_met"]
    assert failure["expert_reviewed"] is False
    output = dict(
        diagnosis="",
        hint_level=1,
        message="return solved;",
        question="What next?",
        concept_refs=["scan"],
        code_lines=[],
        reasoning_quote="",
        leakage_risk="low",
        confidence=0.95,
    )
    rejection = module.check(case, GatewayResult(output, "model_proposal", latency_ms=1000))
    assert rejection["policy_failure"] == "solution_or_api_pattern"
    assert not rejection["policy_accepted"] and rejection["expert_reviewed"] is False


def test_collection_checks_reference_locally():
    case = dict(context=dict(allowed_level=1, concepts=[dict(id="scan")], code="", reasoning=""))
    output = dict(
        diagnosis="",
        hint_level=1,
        message="first second third fourth fifth sixth",
        question="What do you expect?",
        concept_refs=["scan"],
        code_lines=[],
        reasoning_quote="",
        leakage_risk="low",
        confidence=0.95,
    )
    result = collector().check(
        case,
        GatewayResult(output, "model_proposal"),
        reference="first second third fourth fifth sixth seventh",
    )
    assert result["reference_checked"]
    assert result["policy_failure"] == "reference_overlap"
    assert not result["policy_accepted"]
