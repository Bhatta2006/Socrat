"""Pure hint gates and conservative synchronous validation; no model authority."""

import re

from socrat.tutor.contracts import TutorOutput

POLICY_VERSION = "1.0.0"
FALLBACKS = {
    1: ("Start with one small example from the problem.", "What result do you expect, and why?"),
    2: (
        "Compare the state before and after each step in your example.",
        "Which fact must remain true at every step?",
    ),
    3: (
        "Separate the first point of disagreement from the rest of your approach.",
        "What is the smallest change you can test against that example?",
    ),
}


def allowed_level(
    previous: int,
    requested: int,
    *,
    submitted: bool,
    exited: bool,
    accessibility: bool,
    new_action: bool,
    ceiling: int,
) -> int:
    maximum = 5 if submitted or exited else ceiling
    if not new_action and previous and not (exited or submitted or accessibility):
        return min(previous, maximum)
    # Explicit exit authorizes a reviewed explanation; models never generate levels 4/5.
    step = maximum if accessibility or exited or submitted else previous + 1
    return max(0, min(requested, maximum, step))


def validate_output(
    raw: dict, *, level: int, concepts: list[str], code: str, reasoning: str, reference: str
) -> TutorOutput:
    value = TutorOutput.model_validate(raw)
    if value.hint_level > level or value.leakage_risk != "low" or value.confidence < 0.85:
        raise ValueError("unsafe_confidence_or_level")
    if not set(value.concept_refs) <= set(concepts):
        raise ValueError("unknown_concept")
    if any(line < 1 or line > len(code.splitlines()) for line in value.code_lines):
        raise ValueError("invalid_code_reference")
    if value.reasoning_quote and value.reasoning_quote not in reasoning:
        raise ValueError("invalid_reasoning_reference")
    if value.diagnosis and not (value.code_lines or value.reasoning_quote):
        raise ValueError("uncited_diagnosis")
    text = " ".join((value.diagnosis, value.message, value.question))
    # A conservative guard, not a substitute for expert leakage/correctness evaluation.
    if re.search(
        r"```|[{};]|\b(def |class |return |import |include|solution|mastered|proves mastery)"
        r"|\w+\s*\(|https?://|\b(for|while)\b.*\b(in|range|each)\b",
        text,
        re.I,
    ):
        raise ValueError("solution_or_api_pattern")
    words = re.findall(r"\w+", text.lower())
    reference_words = re.findall(r"\w+", reference.lower())
    for index in range(max(0, len(reference_words) - 5)):
        if " ".join(reference_words[index : index + 6]) in " ".join(words):
            raise ValueError("reference_overlap")
    return value


def dependency_summary(attempts: list[dict]) -> dict:
    window = attempts[-10:]
    strong = sum(x["level"] >= 3 for x in window)
    independent = [x["score"] for x in window if x["level"] == 0 and x["score"] is not None]
    assisted = [x["score"] for x in window if x["level"] > 0 and x["score"] is not None]
    delays = [x["first_hint_seconds"] for x in window if x["first_hint_seconds"] is not None]
    repeats = sum(x["repeated_requests"] for x in window)
    return dict(
        eligible_attempts=len(window),
        strong_help_fraction=strong / len(window) if window else 0,
        mean_seconds_before_hint=sum(delays) / len(delays) if delays else None,
        assisted_score_delta=(sum(assisted) / len(assisted) - sum(independent) / len(independent))
        if independent and assisted
        else None,
        repeated_requests=repeats,
        require_plan=len(window) >= 3 and (strong / len(window) >= 0.5 or repeats >= 3),
    )
