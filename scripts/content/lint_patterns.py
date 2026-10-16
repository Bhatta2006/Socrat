"""Lint every pattern pack (Content Master Plan §3.3) and run its templates.

    uv run python scripts/content/lint_patterns.py

For each pattern: the three recognition cues, a complete template in Python, C++ and Java
(each run against ``template_io``), 5–7 variants, a draft atom pack with worked, faded,
visualizer, pitfall micro-lesson and classify atoms, and a quiz family with at least 12
servable items over at least 4 bands. Everything stays provisional with no review record;
tooling never writes one. Lengths follow the Playbook (atom limits are enforced by the
atom model; quiz wording is checked here).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "services/api/src"), str(ROOT / "services/execution/src")]

from runner.toolchains import toolchains  # noqa: E402

from socrat.catalog.atoms import Adapter  # noqa: E402
from socrat.catalog.registry import CONTENT_ROOT, load  # noqa: E402
from socrat.catalog.validate_atoms import check_adapter  # noqa: E402
from socrat.quiz import pools  # noqa: E402

LANGUAGES = ("python", "cpp", "java")
REQUIRED_ATOMS = ("worked", "faded", "visualizer", "micro", "classify")
MIN_ITEMS, MIN_BANDS = 12, 4
PROMPT_WORDS, OPTION_WORDS, EXPLANATION_WORDS = 70, 16, 70
MICRO_SECONDS = (60, 90)  # Content Master Plan §3.3: pitfall micro-lesson 60-90 s


def words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def lint_pattern(catalog, pattern, items, tools) -> list[str]:
    problems = []
    if pattern.status != "provisional" or pattern.provenance.review is not None:
        problems.append("must stay provisional with no review record")
    if pattern.provenance.origin != "original":
        problems.append("pilot content must be original")
    if not 5 <= len(pattern.variants) <= 7:
        problems.append(f"{len(pattern.variants)} variants; a ladder needs 5-7")
    missing = [lang for lang in LANGUAGES if lang not in pattern.template]
    if missing:
        problems.append(f"template missing for {missing}")
    if pattern.template_io is None:
        problems.append("template_io is required to run the templates")
    else:
        for lang in LANGUAGES:
            if lang not in pattern.template:
                continue
            adapter = Adapter(
                code=pattern.template[lang],
                stdin=pattern.template_io.stdin,
                expected=pattern.template_io.expected,
            )
            try:
                check_adapter(lang, adapter, tools)
            except (ValueError, OSError, subprocess.SubprocessError) as exc:
                problems.append(f"template {exc}")

    pack = catalog.pattern_atoms.get(pattern.id)
    if pack is None:
        problems.append("no pattern atom pack")
    else:
        if pack.status != "draft" or pack.review is not None:
            problems.append("pattern atom pack must be a draft without review")
        kinds = {a.kind: a for a in pack.atoms}
        for kind in REQUIRED_ATOMS:
            if kind not in kinds:
                problems.append(f"atom pack has no {kind} atom")
        if "classify" in kinds and len(kinds["classify"].steps) != 3:
            problems.append("the classify drill has exactly 3 problems")
        if (
            "micro" in kinds
            and pattern.pitfalls
            and kinds["micro"].misconception != pattern.pitfalls[0]
        ):
            problems.append("the micro-lesson must target the top pitfall")
        if "micro" in kinds and not MICRO_SECONDS[0] <= kinds["micro"].seconds <= MICRO_SECONDS[1]:
            problems.append(f"the micro-lesson should take {MICRO_SECONDS[0]}-{MICRO_SECONDS[1]} s")
        listed = set(pattern.atoms)
        unlisted = [a.id for a in pack.atoms if a.id not in listed]
        if unlisted:
            problems.append(f"atoms not listed on the pattern: {unlisted}")

    family = catalog.quiz_families.get(pattern.quiz_family or "")
    if family is None:
        problems.append("no quiz family")
        return problems
    served = [i for i in items if i.family == family.id]
    bands = {i.band for i in served}
    if len(served) < MIN_ITEMS or len(bands) < MIN_BANDS:
        problems.append(f"quiz family serves {len(served)} items over bands {sorted(bands)}")
    tags = {r.misconception for r in family.distractors} | {
        t for i in served for t in i.misconceptions if t
    }
    for pitfall in pattern.pitfalls:
        if pitfall not in tags:
            problems.append(f"pitfall {pitfall} is not used by any distractor")
    for item in family.items:
        if not item.misconceptions:
            problems.append(f"static item {item.id}: distractors need misconceptions")
        elif any(t is None for i, t in enumerate(item.misconceptions) if i != item.answer):
            problems.append(f"static item {item.id}: a distractor has no misconception")
        if words(item.prompt) > PROMPT_WORDS or words(item.explanation) > EXPLANATION_WORDS:
            problems.append(f"static item {item.id}: prompt or explanation too long")
        if any(words(o) > OPTION_WORDS for o in item.options):
            problems.append(f"static item {item.id}: an option is too long")
    return problems


def main() -> int:
    catalog = load(CONTENT_ROOT, tests_root=None)
    tools = toolchains()
    missing = sorted(set(LANGUAGES) - set(tools))
    if missing:
        print(f"Toolchains missing: {', '.join(missing)}")
        return 2
    items = pools.bank(catalog)
    report, problems = [], []
    for pattern_id in sorted(catalog.patterns):
        pattern = catalog.patterns[pattern_id]
        found = lint_pattern(catalog, pattern, items, tools)
        family = catalog.quiz_families.get(pattern.quiz_family or "")
        served = [i for i in items if family and i.family == family.id]
        report.append(
            dict(
                pattern=pattern_id,
                items=len(served),
                bands=sorted({i.band for i in served}),
                atoms=len(catalog.pattern_atoms[pattern_id].atoms)
                if pattern_id in catalog.pattern_atoms
                else 0,
                ok=not found,
            )
        )
        problems += [f"{pattern_id}: {p}" for p in found]
    print(json.dumps(dict(patterns=report, problems=problems), indent=2))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
