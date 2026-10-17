"""Write the JSON contracts in contracts/schemas from the content models.

A test fails when a committed contract differs from its model, so run this after changing
an authoring schema: python scripts/content/export_contracts.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from socrat.catalog.atoms import AtomPack  # noqa: E402
from socrat.catalog.patterns import Pattern  # noqa: E402
from socrat.catalog.projects import Project  # noqa: E402
from socrat.catalog.quizbank import QuizFamily  # noqa: E402

CONTRACTS = {
    "content-atom-pack.schema.json": AtomPack,
    "content-pattern.schema.json": Pattern,
    "content-quiz-family.schema.json": QuizFamily,
    "content-project.schema.json": Project,
}


def main() -> int:
    for name, model in CONTRACTS.items():
        path = ROOT / "contracts" / "schemas" / name
        path.write_text(
            json.dumps(model.model_json_schema(), indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"wrote {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
