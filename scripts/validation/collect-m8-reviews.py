"""Collect bounded synthetic proposals and automated checks into a private queue.

Does not populate human judgments, claim expert review or approve release.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services/api/src"))

from socrat.config import Settings  # noqa: E402
from socrat.tutor.contracts import TutorOutput  # noqa: E402
from socrat.tutor.gateway import generate  # noqa: E402
from socrat.tutor.policy import validate_output  # noqa: E402


def check(case, result, *, reference=""):
    error = None
    if result.output is not None:
        try:
            validate_output(
                result.output,
                level=case["context"]["allowed_level"],
                concepts=[x["id"] for x in case["context"]["concepts"]],
                code=case["context"]["code"],
                reasoning=case["context"]["reasoning"],
                reference=reference,
            )
        except ValueError as exc:
            # Emit only known policy codes; Pydantic errors may contain raw inputs.
            known = {
                "unsafe_confidence_or_level",
                "unknown_concept",
                "invalid_code_reference",
                "invalid_reasoning_reference",
                "uncited_diagnosis",
                "solution_or_api_pattern",
                "reference_overlap",
            }
            error = str(exc) if str(exc) in known else "schema_rejected"
    return dict(
        policy_accepted=result.output is not None and error is None,
        policy_failure=error,
        production_deadline_met=result.latency_ms < 4000,
        review_kind="automated_boundary_check",
        reference_checked=bool(reference),
        expert_reviewed=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue", type=Path)
    parser.add_argument("--max-calls", type=int, required=True)
    parser.add_argument("--reservation-budget-microusd", type=int, required=True)
    parser.add_argument("--workers", type=int, choices=[1, 2, 3], default=3)
    parser.add_argument("--diagnostic-timeout-seconds", type=int, choices=range(4, 121), default=30)
    parser.add_argument("--provider-default-output", action="store_true")
    args = parser.parse_args()
    packet = json.loads(args.queue.read_text(encoding="utf-8"))
    if packet["content_state"] != "draft_not_publishable" or packet["release_approved"]:
        parser.error("Collector accepts unapproved synthetic draft queues only")
    values = dotenv_values(".env")
    options = {
        k.removeprefix("SOCRAT_").lower(): v
        for k, v in values.items()
        if k.startswith("SOCRAT_TUTOR_") and v
    }
    options.update(tutor_model_enabled=True, tutor_model_rollout_percent=100)
    try:
        options["tutor_model_allowlist"] = json.loads(options.get("tutor_model_allowlist", "[]"))
        settings = Settings(_env_file=None, environment="test", **options)
    except ValueError:
        parser.error("Invalid private tutor configuration; no request made")
    selected = [x for x in packet["m8_cases"] if x["status"] == "not_executed"][: args.max_calls]
    if (
        args.max_calls < 1
        or len(selected) * settings.tutor_call_reserve_microusd > args.reservation_budget_microusd
    ):
        parser.error("Requested calls exceed the explicit reservation budget")
    settings = settings.model_copy(
        update={"tutor_timeout_seconds": args.diagnostic_timeout_seconds}
    )
    completed = 0
    consecutive_failures = 0

    def run(case):
        return generate(
            settings,
            prompt=packet["prompt_version"],
            context=case["context"],
            schema=TutorOutput.model_json_schema(),
            diagnostic_output_default=args.provider_default_output,
        )

    # One bounded wave at a time permits checkpointing and stops new spending on outages.
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for offset in range(0, len(selected), args.workers):
            batch = selected[offset : offset + args.workers]
            results = list(pool.map(run, batch))
            for case, result in zip(batch, results, strict=True):
                case.update(
                    status="proposal_collected" if result.output else "provider_failed",
                    model_output=result.output,
                    provider_metadata=dict(
                        reason=result.reason,
                        latency_ms=result.latency_ms,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        reserved_microusd=result.reserved_microusd,
                        reasoning_effort=settings.tutor_reasoning_effort,
                        diagnostic_deadline_seconds=args.diagnostic_timeout_seconds,
                        provider_default_output=args.provider_default_output,
                    ),
                    automated_review=check(case, result),
                )
                # Existing human judgments/references remain untouched.
                consecutive_failures = consecutive_failures + 1 if result.output is None else 0
                completed += 1
            packet["collection"] = dict(
                provider=settings.tutor_provider,
                model=settings.tutor_model,
                reservation_budget_microusd=args.reservation_budget_microusd,
                latest_run_calls=completed,
                expert_reviewed=False,
                release_approved=False,
            )
            temporary = args.queue.with_suffix(".checkpoint")
            temporary.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
            temporary.replace(args.queue)
            if completed % 21 == 0 or completed == len(selected) or consecutive_failures >= 3:
                print(
                    json.dumps(
                        dict(
                            completed=completed,
                            planned=len(selected),
                            provider_failures=sum(
                                x["status"] == "provider_failed" for x in selected[:completed]
                            ),
                            release_approved=False,
                        )
                    ),
                    flush=True,
                )
            if consecutive_failures >= 3:
                print(
                    "Stopped after consecutive provider failures; remaining cases untouched.",
                    flush=True,
                )
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
