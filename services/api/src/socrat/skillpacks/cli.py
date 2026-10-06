"""Offline validate/schema tools; editorial mutations use authenticated HTTP."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from socrat.learning.audit import planning_audit
from socrat.learning.content import coverage_audit
from socrat.skillpacks.schema import SkillPack


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate declarative skill packs without executing content"
    )
    parser.add_argument(
        "command", choices=["validate", "schema", "learning-audit", "learning-plan-audit"]
    )
    parser.add_argument("path", type=Path, nargs="?")
    args = parser.parse_args()
    if args.command == "schema":
        value = SkillPack.model_json_schema()
        rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        if args.path:
            args.path.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    if not args.path or not args.path.is_file() or args.path.stat().st_size > 2_000_000:
        parser.error("validate requires a skill-pack JSON file of at most 2 MB")
    try:
        pack = SkillPack.model_validate_json(args.path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError):
        print("Invalid skill-pack contract; inspect it privately (input values are not echoed).")
        return 1
    if args.command in {"learning-audit", "learning-plan-audit"}:
        audit = (
            planning_audit(pack) if args.command == "learning-plan-audit" else coverage_audit(pack)
        )
        print(json.dumps(audit))
        return 0 if audit["ready"] else 1
    print(
        json.dumps(
            {
                "key": pack.key,
                "version": pack.version,
                "digest": pack.digest(),
                "topological_order": pack.topological_order(),
                "coverage": pack.coverage(),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
