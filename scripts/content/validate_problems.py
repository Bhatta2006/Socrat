"""Run the judge-problem quality gates over course problems and drafts.

Drafts (content/drafts/<course>/<id>.yaml) run in strict mode: a brute force is required.
Writes .cache/content-validation.json and exits 1 if any problem fails a gate.

Usage: python scripts/content/validate_problems.py [--drafts-only] [--strict] [ids...]
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from socrat.catalog import validate  # noqa: E402
from socrat.catalog.registry import CONTENT_ROOT, load  # noqa: E402

DRAFTS = ROOT / "content" / "drafts"
REPORT = ROOT / ".cache" / "content-validation.json"
MARK = {"pass": "ok  ", "warn": "warn", "fail": "FAIL", "skip": "skip"}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="*")
    parser.add_argument("--drafts-only", action="store_true")
    parser.add_argument("--strict", action="store_true", help="require a brute force everywhere")
    args = parser.parse_args()

    catalog = load(CONTENT_ROOT, tests_root=None)
    drafts = sorted(DRAFTS.glob("*/*.yaml")) if DRAFTS.exists() else []
    authored = [] if args.drafts_only else sorted(CONTENT_ROOT.glob("*/problems/*.yaml"))
    paths = [(p, True) for p in drafts] + [(p, args.strict) for p in authored]
    if args.ids:
        paths = [(p, s) for p, s in paths if p.stem in set(args.ids)]
    draft_statements = {}
    for path in drafts:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(raw, dict) and raw.get("statement"):
            draft_statements[raw.get("id", path.stem)] = raw["statement"]
    titles = validate.library_titles()
    statements = validate.statements_of(catalog, draft_statements)

    report, counts = {}, {"pass": 0, "warn": 0, "fail": 0}
    for path, strict in paths:
        result = validate.validate_file(
            path, catalog, strict=strict, titles=titles, statements=statements
        )
        result["draft"] = path.is_relative_to(DRAFTS)
        report[result["id"]] = result
        counts[result["verdict"]] += 1
        if result["verdict"] != "pass":
            print(f"{MARK[result['verdict']]} {result['course']}/{result['id']}")
            for gate in result["gates"]:
                if gate["status"] in {"warn", "fail"}:
                    print(f"       {MARK[gate['status']]} {gate['name']}: {gate['detail']}")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    per_concept: dict[str, int] = {}
    for _, problem in catalog.problems.values():
        for concept in problem.concepts:
            per_concept[concept] = per_concept.get(concept, 0) + 1
    thin = sum(1 for c in catalog.concepts if per_concept.get(c.split(":", 1)[1], 0) < 8)
    print(
        f"\n{len(paths)} problems: {counts['pass']} pass, {counts['warn']} with warnings, "
        f"{counts['fail']} failing. {thin} of {len(catalog.concepts)} concepts have fewer "
        f"than 8 judge problems. Report: {REPORT.relative_to(ROOT)}"
    )
    return 1 if counts["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
