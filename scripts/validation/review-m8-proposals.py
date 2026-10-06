"""Generate explicitly provisional model-assisted reviews of synthetic proposals.

Uses the same model as the generator; correlated errors and human review remain.
Never edits the human judgment fields or creates expert acceptance evidence.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import dotenv_values
from pydantic import Field

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services/api/src"))

from socrat.config import Settings  # noqa: E402
from socrat.learnerstate.policy import digest  # noqa: E402
from socrat.skillpacks.types import Contract  # noqa: E402
from socrat.tutor.gateway import generate  # noqa: E402


class Opinion(Contract):
    case_id: str = Field(min_length=1, max_length=100)
    material_error: bool
    premature_solution: bool
    unsupported_diagnosis: bool
    useful: bool
    uncertain: bool
    explanation: str = Field(min_length=1, max_length=350)


class Opinions(Contract):
    reviews: list[Opinion] = Field(min_length=1, max_length=7)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queue", type=Path)
    parser.add_argument("--reservation-budget-microusd", type=int, required=True)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--provider-default-output", action="store_true")
    parser.add_argument("--diagnostic-timeout-seconds", type=int, choices=range(4, 121), default=30)
    args = parser.parse_args()
    packet = json.loads(args.queue.read_text(encoding="utf-8"))
    output = args.queue.parent / "ai-hint-reviews.json"
    existing = (
        json.loads(output.read_text(encoding="utf-8"))
        if output.exists()
        else dict(
            draft_digest=packet["draft_digest"],
            actual_reviewer="model-assisted evaluator",
            reviewer_model="zai-org/GLM-5.3-Flash",
            prompt_version="pilot_review_1.0.0",
            independent=False,
            expert_reviewed=False,
            release_approved=False,
            reviews=[],
            limitation="Same generator/reviewer model can share errors; Codex findings and human sign-off are separate.",
        )
    )
    previous_prompt = existing["prompt_version"]
    for review in existing["reviews"]:
        review.setdefault("review_prompt_version", previous_prompt)
    existing["prompt_version"] = "pilot_review_1.0.1"
    completed = {
        x["case_id"]
        for x in existing["reviews"]
        if not args.retry_failed
        or x["review_status"] == "provisional_ai_opinion"
        or x["provider_reason"] != "model_proposal"
    }
    selected = [
        x
        for x in packet["m8_cases"]
        if x["status"] != "not_executed" and x["case_id"] not in completed
    ]
    values = dotenv_values(".env")
    options = {
        k.removeprefix("SOCRAT_").lower(): v
        for k, v in values.items()
        if k.startswith("SOCRAT_TUTOR_") and v
    }
    options.update(
        tutor_model_enabled=True, tutor_model_rollout_percent=100, tutor_output_tokens=2000
    )
    try:
        options["tutor_model_allowlist"] = json.loads(options.get("tutor_model_allowlist", "[]"))
        settings = Settings(_env_file=None, environment="test", **options)
    except ValueError:
        parser.error("Invalid private settings; no calls made")
    selected_ids = {x["case_id"] for x in selected}
    if args.retry_failed:
        superseded = [x for x in existing["reviews"] if x["case_id"] in selected_ids]
        existing.setdefault("superseded_reviews", []).extend(superseded)
        existing["reviews"] = [x for x in existing["reviews"] if x["case_id"] not in selected_ids]
    batches = [selected[i : i + 2] for i in range(0, len(selected), 2)]
    if len(batches) * settings.tutor_call_reserve_microusd > args.reservation_budget_microusd:
        parser.error("Proposed review batches exceed the explicit reservation budget")
    settings = settings.model_copy(
        update={"tutor_timeout_seconds": args.diagnostic_timeout_seconds}
    )
    failures = 0

    def run(batch):
        context = dict(
            cases=[
                dict(
                    case_id=x["case_id"],
                    problem=x["context"]["statement"],
                    allowed_level=x["context"]["allowed_level"],
                    language=x["language"],
                    code=x["context"]["code"],
                    learner_reasoning=x["context"]["reasoning"],
                    proposal=x["model_output"],
                )
                for x in batch
            ]
        )
        return generate(
            settings,
            prompt="pilot_review_1.0.1",
            context=context,
            schema=Opinions.model_json_schema(),
            diagnostic_output_default=args.provider_default_output,
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        for offset in range(0, len(batches), 3):
            wave = batches[offset : offset + 3]
            for batch, result in zip(wave, pool.map(run, wave), strict=True):
                by_id = {}
                if result.output is not None:
                    try:
                        values = Opinions.model_validate(result.output)
                        by_id = {x.case_id: x.model_dump() for x in values.reviews}
                        if len(by_id) != len(batch) or set(by_id) != {x["case_id"] for x in batch}:
                            by_id = {}
                    except ValueError:
                        pass
                failures = 0 if by_id else failures + 1
                for case in batch:
                    record = dict(
                        case_id=case["case_id"],
                        context_digest=digest(case["context"]),
                        proposal_digest=digest(case["model_output"]),
                        review_status="provisional_ai_opinion"
                        if case["model_output"] and by_id
                        else "not_reviewable",
                        opinion=by_id.get(case["case_id"]) if case["model_output"] else None,
                        provider_reason=case["provider_metadata"]["reason"],
                        automated_review=case["automated_review"],
                        reviewer_call_reason=result.reason,
                        reviewer_metadata=dict(
                            latency_ms=result.latency_ms,
                            input_tokens=result.input_tokens,
                            output_tokens=result.output_tokens,
                            diagnostic_deadline_seconds=args.diagnostic_timeout_seconds,
                            provider_default_output=args.provider_default_output,
                        ),
                        expert_reviewed=False,
                        review_prompt_version="pilot_review_1.0.1",
                    )
                    existing["reviews"].append(record)
            temporary = output.with_suffix(".checkpoint")
            temporary.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
            temporary.replace(output)
            print(
                json.dumps(
                    dict(
                        review_records=len(existing["reviews"]),
                        expert_reviewed=False,
                        release_approved=False,
                    )
                ),
                flush=True,
            )
            if failures >= 3:
                print("Repeated evaluator failures; further calls stopped.", flush=True)
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
