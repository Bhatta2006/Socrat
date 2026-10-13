"""Validate every atom pack and each distinct runnable Python/C++/Java adapter."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "services/api/src"), str(ROOT / "services/execution/src")]

from runner.toolchains import toolchains  # noqa: E402

from socrat.catalog.registry import CONTENT_ROOT, load  # noqa: E402
from socrat.catalog.validate_atoms import check_adapter  # noqa: E402


def main() -> int:
    catalog = load(CONTENT_ROOT, tests_root=None)
    tools = toolchains()
    checked = set()
    failures = []
    for concept, pack in catalog.atom_packs.items():
        for atom in pack.atoms:
            for language, adapter in atom.adapters.items():
                key = (language, adapter.code, adapter.stdin, adapter.expected)
                if key in checked:
                    continue
                try:
                    check_adapter(language, adapter, tools)
                except (ValueError, OSError, subprocess.SubprocessError) as exc:
                    failures.append(f"{concept}/{atom.id}: {exc}")
                else:
                    checked.add(key)
    report = dict(
        packs=len(catalog.atom_packs),
        atoms=sum(len(p.atoms) for p in catalog.atom_packs.values()),
        validated_adapters=len(checked),
        failures=failures,
    )
    (ROOT / ".cache").mkdir(exist_ok=True)
    (ROOT / ".cache" / "atom-validation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
