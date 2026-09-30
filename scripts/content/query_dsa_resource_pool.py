"""Inspect the DSA metadata pool by topic, difficulty, source, or company."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from socrat.dsa_resource_pool import load_resource_pool  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool-dir", type=Path, default=ROOT / "contracts" / "resource-pool")
    parser.add_argument("--topic")
    parser.add_argument("--difficulty", type=int, choices=range(1, 11))
    parser.add_argument("--source")
    parser.add_argument("--company")
    parser.add_argument(
        "--kind", choices=["problem", "solution", "lesson", "roadmap", "implementation"]
    )
    parser.add_argument("--scope", choices=["dsa_candidate", "unknown", "out_of_scope"])
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.limit <= 200:
        parser.error("--limit must be between 1 and 200")

    pool = load_resource_pool(
        args.pool_dir / "dsa-resources.jsonl",
        args.pool_dir / "dsa-resource-summary.json",
    )
    matched = []
    for item in pool.resources:
        if args.topic and args.topic not in item.topics:
            continue
        if args.difficulty and item.difficulty.band != args.difficulty:
            continue
        if args.source and not any(ref.source == args.source for ref in item.references):
            continue
        if args.company and not any(
            signal.company.casefold() == args.company.casefold() for signal in item.company_signals
        ):
            continue
        if args.kind and item.kind != args.kind:
            continue
        if args.scope and item.scope != args.scope:
            continue
        matched.append(item)

    def company_priority(item) -> float:
        if not args.company:
            return 0
        signals = [
            signal
            for signal in item.company_signals
            if signal.company.casefold() == args.company.casefold()
        ]
        all_time = [signal for signal in signals if signal.window == "all_time"]
        return max((signal.frequency or 0 for signal in (all_time or signals)), default=0)

    matched.sort(
        key=lambda item: (
            item.difficulty.band if item.difficulty.band is not None else 99,
            -company_priority(item),
            item.title.casefold(),
            item.id,
        )
    )
    result = {
        "total_matches": len(matched),
        "results": [
            {
                "id": item.id,
                "title": item.title,
                "kind": item.kind,
                "url": item.url,
                "topics": item.topics,
                "difficulty": item.difficulty.model_dump(exclude_none=True),
                "scope": item.scope,
                "release_status": item.release_status,
                "sources": sorted({ref.source for ref in item.references}),
                "company_signals": [
                    signal.model_dump(exclude_none=True)
                    for signal in item.company_signals
                    if not args.company or signal.company.casefold() == args.company.casefold()
                ][:5],
            }
            for item in matched[: args.limit]
        ],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
