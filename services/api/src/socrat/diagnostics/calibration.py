"""Versioned placement predictions paired with the next clean independent outcome."""

from socrat.learnerstate.projector import EvidenceFact


def outcome_pairs(
    result: dict, pack_id: str, language: str, facts: list[EvidenceFact]
) -> list[dict]:
    invalidated = {fact.target_event_id for fact in facts if fact.kind == "invalidated"}
    pairs = []
    for concept, prediction in result["concepts"].items():
        if prediction is None or prediction["evidence_count"] == 0:
            continue
        candidate = next(
            (
                fact
                for fact in sorted(facts, key=lambda item: item.sequence)
                if fact.sequence > result["watermark"]
                and fact.kind == "scored"
                and fact.event_id not in invalidated
                and fact.pack_id == pack_id
                and fact.language == language
                and concept in fact.concept_ids
                and fact.valid
                and fact.finalized
                and fact.quality > 0
                and fact.hint_level == 0
                and fact.unseen
                and fact.mode in {"assessment", "retention"}
            ),
            None,
        )
        if candidate:
            pairs.append(
                {
                    "prediction": prediction["mastery_mean"],
                    "outcome": candidate.score,
                    "model_version": result["policy_version"],
                    "concept": concept,
                    "outcome_event_id": candidate.event_id,
                }
            )
    return pairs


def summarize(pairs: list[dict]) -> dict:
    # Multiple goal snapshots may predict the same next outcome. Count it once
    # per concept; the caller supplies newest predictions first.
    seen: set[tuple[str, str]] = set()
    deduplicated: list[dict] = []
    for pair in pairs:
        key = pair["outcome_event_id"], pair["concept"]
        if key not in seen:
            seen.add(key)
            deduplicated.append(pair)
    pairs = deduplicated
    bins = []
    for index in range(5):
        cell = [pair for pair in pairs if min(4, int(pair["prediction"] * 5)) == index]
        bins.append(
            {
                "lower": index / 5,
                "upper": (index + 1) / 5,
                "count": len(cell),
                "predicted_mean": sum(pair["prediction"] for pair in cell) / len(cell)
                if cell
                else None,
                "observed_mean": sum(pair["outcome"] for pair in cell) / len(cell)
                if cell
                else None,
            }
        )
    return {
        "outcome_pairs": len(pairs),
        "calibration": "available" if len(pairs) >= 20 else "insufficient_data",
        "minimum_pairs": 20,
        "bins": bins,
        "brier_score": sum((pair["prediction"] - pair["outcome"]) ** 2 for pair in pairs)
        / len(pairs)
        if len(pairs) >= 20
        else None,
    }
