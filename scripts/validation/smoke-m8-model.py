"""Bounded live provider smoke test using synthetic data; never release evidence."""

import argparse
import itertools
import json
import sys
from pathlib import Path

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services/api/src"))

from socrat.config import Settings  # noqa: E402
from socrat.tutor.contracts import TutorOutput  # noqa: E402
from socrat.tutor.gateway import generate  # noqa: E402
from socrat.tutor.policy import validate_output  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument(
        "--gateway-url", help="Explicit HTTPS endpoint override for isolated testing"
    )
    parser.add_argument(
        "--provider", choices=["openai_responses", "openai_chat", "structured_gateway"]
    )
    parser.add_argument("--max-calls", type=int, choices=range(1, 10), default=1)
    parser.add_argument("--prompt-version", choices=["tutor_1.0.0", "tutor_1.0.1", "tutor_1.0.2"])
    parser.add_argument("--reservation-budget-microusd", type=int, default=10000)
    parser.add_argument("--diagnostic-timeout-seconds", type=int, choices=range(4, 31), default=4)
    args = parser.parse_args()
    values = dotenv_values(args.env_file)
    # Read tutor configuration only; do not load deployment auth/database settings.
    options = {
        key.removeprefix("SOCRAT_").lower(): value
        for key, value in values.items()
        if key.startswith("SOCRAT_TUTOR_") and value
    }
    options.update(tutor_model_enabled=True, tutor_model_rollout_percent=100)
    if args.gateway_url:
        options["tutor_gateway_url"] = args.gateway_url
    if args.provider:
        options["tutor_provider"] = args.provider
    if args.prompt_version:
        options["tutor_prompt_version"] = args.prompt_version
    if not options.get("tutor_gateway_secret") and not options.get("tutor_gateway_secret_file"):
        import os

        options["tutor_gateway_secret"] = os.environ.get("NEBIUS_API_KEY") or values.get(
            "NEBIUS_API_KEY", ""
        )
    try:
        if "tutor_model_allowlist" in options:
            options["tutor_model_allowlist"] = json.loads(options["tutor_model_allowlist"])
        settings = Settings(_env_file=None, environment="test", **options)
    except ValueError:
        print("Live smoke configuration incomplete or invalid; no provider call made.")
        return 2
    if args.max_calls * settings.tutor_call_reserve_microusd > args.reservation_budget_microusd:
        print("Requested calls exceed the smoke reservation budget; no provider call made.")
        return 2
    # Diagnostic runs can inspect a slow provider, without changing the application's
    # validated four-second deadline or claiming latency acceptance.
    settings = settings.model_copy(
        update={"tutor_timeout_seconds": args.diagnostic_timeout_seconds}
    )
    passed = True
    cells = itertools.product(
        ["foundations", "interview", "competitive"], ["python", "cpp", "java"]
    )
    for track, language in list(cells)[: args.max_calls]:
        context = dict(
            statement="Read an integer and print twice its value. Public example: input 3, output 6.",
            language=language,
            track=track,
            allowed_level=1,
            concepts=[
                dict(
                    id="input_output",
                    title="Input and output",
                    excerpt="Trace a small input before choosing a transformation.",
                )
            ],
            code="",
            reasoning="I will trace the given sample first",
            public_results=[],
            misconception_labels=[],
            prior_hints=[],
        )
        result = generate(
            settings,
            prompt=settings.tutor_prompt_version,
            context=context,
            schema=TutorOutput.model_json_schema(),
        )
        accepted = False
        if result.output is not None:
            try:
                validate_output(
                    result.output,
                    level=1,
                    concepts=["input_output"],
                    code="",
                    reasoning=context["reasoning"],
                    reference="",
                )
                accepted = True
            except ValueError:
                pass
        passed &= accepted
        print(
            json.dumps(
                dict(
                    track=track,
                    language=language,
                    reason=result.reason,
                    policy_accepted=accepted,
                    latency_ms=result.latency_ms,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    reserved_microusd=result.reserved_microusd,
                    release_approved=False,
                    production_deadline_met=result.latency_ms < 4000,
                )
            )
        )
        if not accepted:
            break  # Stop spending immediately on protocol/policy failure.
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
