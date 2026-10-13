"""Summarise how a re-imported practice index differs from the committed one.

Compares content/practice/problems.jsonl in the working tree with the version at a git
revision (default HEAD) and prints a Markdown report: problems added, removed, and
changed (title, rating, difficulty or concepts). Used by the monthly import job.

Usage: python scripts/content/practice_diff.py [--base REV] [--limit N]
"""

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = "content/practice/problems.jsonl"
FIELDS = ("title", "rating", "difficulty", "concepts")


def parse(text: str) -> dict[str, dict]:
    rows = (json.loads(line) for line in text.splitlines() if line.strip())
    return {row["id"]: row for row in rows}


def committed(rev: str) -> dict[str, dict]:
    result = subprocess.run(
        ["git", "show", f"{rev}:{INDEX}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return parse(result.stdout) if result.returncode == 0 else {}


def diff(old: dict[str, dict], new: dict[str, dict]) -> dict:
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = {}
    for pid in sorted(set(old) & set(new)):
        fields = [f for f in FIELDS if old[pid].get(f) != new[pid].get(f)]
        if fields:
            changed[pid] = fields
    return dict(added=added, removed=removed, changed=changed)


def report(old: dict[str, dict], new: dict[str, dict], result: dict, limit: int) -> str:
    by_platform = Counter(new[p]["platform"] for p in result["added"])
    fields = Counter(f for fs in result["changed"].values() for f in fs)
    lines = [
        "## Practice index refresh",
        "",
        f"{len(old):,} problems before, {len(new):,} after.",
        "",
        "| Change | Count |",
        "|---|---:|",
        f"| Added | {len(result['added']):,} |",
        f"| Removed | {len(result['removed']):,} |",
        f"| Changed | {len(result['changed']):,} |",
        "",
    ]
    if by_platform:
        added = ", ".join(f"{p} {n:,}" for p, n in by_platform.most_common())
        lines += [f"Added by platform: {added}.", ""]
    if fields:
        lines += [
            f"Changed fields: {', '.join(f'{f} {n:,}' for f, n in fields.most_common())}.",
            "",
        ]
    if result["removed"]:
        lines += ["### Removed (check learners' saved lists)", ""]
        lines += [f"- `{pid}` {old[pid]['title']}" for pid in result["removed"][:limit]]
        lines += [""]
    if result["added"]:
        lines += ["### Added (first few)", ""]
        lines += [f"- `{pid}` {new[pid]['title']}" for pid in result["added"][:limit]]
        lines += [""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()
    old = committed(args.base)
    new = parse((ROOT / INDEX).read_text(encoding="utf-8"))
    print(report(old, new, diff(old, new), args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
