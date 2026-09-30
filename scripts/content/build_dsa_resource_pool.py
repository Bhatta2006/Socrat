"""Build a metadata-only DSA resource pool from pinned local source snapshots."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from socrat.dsa_resource_pool import TOPIC_PARENTS, build_resource_pool  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--cses-html", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "contracts" / "resource-pool")
    args = parser.parse_args()

    pool = build_resource_pool(
        args.source_root, cses_html=args.cses_html.read_text(encoding="utf-8")
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    draft_pack = json.loads(
        (ROOT / "contracts" / "skill-packs" / "dsa-sample.json").read_text(encoding="utf-8")
    )
    draft_concepts = {concept["key"] for concept in draft_pack["concepts"]}
    (args.output_dir / "dsa-resources.jsonl").write_text(
        "\n".join(item.model_dump_json(exclude_none=True) for item in pool.resources) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "dsa-topic-taxonomy.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "topics": {
                    topic: {
                        "prerequisites": prerequisites,
                        "m2_draft_concept_key": topic if topic in draft_concepts else None,
                    }
                    for topic, prerequisites in TOPIC_PARENTS.items()
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    topic_difficulty: dict[str, Counter[str]] = {topic: Counter() for topic in TOPIC_PARENTS}
    for item in pool.resources:
        if item.kind != "problem" or item.scope != "dsa_candidate":
            continue
        band = str(item.difficulty.band) if item.difficulty.band is not None else "unclassified"
        for topic in item.topics:
            topic_difficulty[topic][band] += 1
    (args.output_dir / "dsa-topic-difficulty-matrix.json").write_text(
        json.dumps(
            {topic: dict(sorted(counts.items())) for topic, counts in topic_difficulty.items()},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    kinds = Counter(item.kind for item in pool.resources)
    providers = Counter(item.provider for item in pool.resources)
    difficulty = Counter(str(item.difficulty.band or "unclassified") for item in pool.resources)
    topic_counts = Counter(topic for item in pool.resources for topic in item.topics)
    source_references = Counter(
        reference.source for item in pool.resources for reference in item.references
    )
    summary = {
        "schema_version": 1,
        "resource_count": len(pool.resources),
        "company_signal_count": sum(len(item.company_signals) for item in pool.resources),
        "source_reference_count": sum(len(item.references) for item in pool.resources),
        "company_count": len(
            {signal.company for item in pool.resources for signal in item.company_signals}
        ),
        "kind_counts": dict(sorted(kinds.items())),
        "provider_counts": dict(sorted(providers.items())),
        "source_reference_counts": dict(sorted(source_references.items())),
        "difficulty_band_counts": dict(sorted(difficulty.items())),
        "topic_counts": dict(sorted(topic_counts.items())),
        "scope_counts": dict(sorted(Counter(item.scope for item in pool.resources).items())),
        "unclassified_topic_count": sum(not item.topics for item in pool.resources),
        "unclassified_difficulty_count": sum(
            item.difficulty.band is None for item in pool.resources
        ),
        "taxonomy_topic_count": len(TOPIC_PARENTS),
        "m2_draft_concept_match_count": len(TOPIC_PARENTS.keys() & draft_concepts),
        "snapshots": [source.model_dump(exclude_none=True) for source in pool.sources],
        "release_status": "review_required",
    }
    (args.output_dir / "dsa-resource-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "resource_count",
                    "company_signal_count",
                    "source_reference_count",
                    "company_count",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
