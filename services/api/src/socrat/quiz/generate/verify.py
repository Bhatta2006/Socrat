"""Verify generated items by executing them (content.md §8.6 pipeline, D7).

For every seed of a family:

- the generator is deterministic (same seed, same item) and keeps the Draft contract;
- every misconception is in the taxonomy and every distractor carries one;
- no two seeds produce the same item (later duplicates are excluded, not errors);
- the shown code prints the reference answer in every language (``output_prediction``,
  ``trace``), or prints something else (``bug_spot``: the defect is observable);
- exactly one option is right: for ``fill_blank`` each option is substituted into the blank,
  for ``bug_spot`` each option's fixed snippet is run, and only the answer may print the
  reference output (anything else is ambiguous);
- output does not depend on unspecified behaviour: Python runs twice with different hash
  seeds and all languages must agree.

Nothing here decides an answer; it only rejects items whose executed code disagrees.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from socrat.catalog.quizbank import Pool, QuizFamily
from socrat.quiz.generate import framework
from socrat.quiz.generate.framework import BLANK, Draft
from socrat.quiz.generate.harness import Result, Runner

HASH_SEEDS = ("1", "2")


@dataclass
class Verdict:
    seed: int
    pool: Pool
    key: str
    digest: str | None = None
    problems: list[str] = field(default_factory=list)
    duplicate_of: int | None = None  # same item as an earlier seed: excluded, not an error

    @property
    def ok(self) -> bool:
        return self.digest is not None and not self.problems and self.duplicate_of is None


def static_problems(family: QuizFamily, item: Draft, answer: str, taxonomy: set[str]) -> list[str]:
    problems = []
    for option in item.options:
        if option.misconception and option.misconception not in taxonomy:
            problems.append(f"unknown misconception {option.misconception}")
    fmt = family.format
    if fmt == "output_prediction":
        if item.options[item.answer].text != answer:
            problems.append(f"answer option {item.options[item.answer].text!r} is not {answer!r}")
        for i, option in enumerate(item.options):
            if i != item.answer and option.text == answer:
                problems.append(f"distractor {option.text!r} equals the answer")
    if fmt == "trace" and item.trace_line is None:
        problems.append("trace items need trace_line")
    if fmt == "fill_blank":
        for lang in family.languages:
            if item.code[lang].count(BLANK) != 1:
                problems.append(f"{lang}: code needs exactly one {BLANK}")
        for option in item.options:
            if set(option.fill) != set(family.languages):
                problems.append(f"option {option.text!r} needs a fill for every language")
    if fmt == "bug_spot":
        for option in item.options:
            if set(option.variant) != set(family.languages):
                problems.append(f"option {option.text!r} needs a fixed snippet per language")
    return problems


def snippets_for(family: QuizFamily, item: Draft) -> dict[str, dict[str, str]]:
    """Role ("shown" or "option:<i>") -> language -> code to run."""
    runs: dict[str, dict[str, str]] = {}
    if framework.shown_check(family.format) != "none":
        runs["shown"] = {str(lang): code for lang, code in item.code.items()}
    for i, option in enumerate(item.options):
        if family.format == "fill_blank":
            runs[f"option:{i}"] = framework.fill(dict(item.code), option)
        elif family.format == "bug_spot":
            runs[f"option:{i}"] = {str(lang): code for lang, code in option.variant.items()}
    return runs


def compared(result: Result, item: Draft) -> str | None:
    if result.output is None:
        return None
    if item.trace_line is None:
        return result.output
    lines = result.output.split("\n")
    return lines[item.trace_line - 1] if len(lines) >= item.trace_line else None


def describe(outputs: dict[str, Result]) -> str:
    return ", ".join(
        f"{lang}={r.output!r}" if r.output is not None else f"{lang} failed ({r.error})"
        for lang, r in outputs.items()
    )


def dynamic_problems(
    family: QuizFamily, item: Draft, answer: str, results: dict[str, dict[str, Result]]
) -> list[str]:
    problems = []
    for role, outputs in results.items():
        values = {lang: compared(r, item) for lang, r in outputs.items()}
        if any(v is None for v in values.values()):
            problems.append(f"{role} did not run: {describe(outputs)}")
            continue
        if len(set(values.values())) > 1:
            problems.append(f"{role}: unspecified behaviour, outputs disagree: {describe(outputs)}")
            continue
        value = next(iter(values.values()))
        if role == "shown":
            check = framework.shown_check(family.format)
            if check == "equals" and value != answer:
                problems.append(f"shown code prints {value!r}, reference says {answer!r}")
            if check == "differs" and value == answer:
                problems.append("the defect is not observable: buggy code prints the answer")
            continue
        index = int(role.split(":")[1])
        if index == item.answer and value != answer:
            problems.append(f"the answer option prints {value!r}, reference says {answer!r}")
        if index != item.answer and value == answer:
            problems.append(
                f"ambiguous: option {item.options[index].text!r} also prints {answer!r}"
            )
    return problems


def verify_family(
    root: Path, family: QuizFamily, runner: Runner, taxonomy: set[str]
) -> list[Verdict]:
    verdicts: list[Verdict] = []
    drafts: dict[int, tuple[Draft, str]] = {}
    seen: dict[str, int] = {}
    for seed, pool in framework.seeds(family):
        verdict = Verdict(seed, pool, framework.item_key(family, seed))
        verdicts.append(verdict)
        try:
            item = framework.draft(root, family, seed)
            again = framework.draft(root, family, seed)
            answer = framework.expected(family, item)
        except Exception as exc:  # noqa: BLE001 - any generator failure rejects the seed
            verdict.problems.append(f"generator failed: {type(exc).__name__}: {exc}")
            continue
        if again.digest() != item.digest():
            verdict.problems.append("generator is not deterministic for this seed")
        digest, face = item.digest(), item.face()
        if face in seen:
            verdict.duplicate_of = seen[face]
        seen.setdefault(face, seed)
        verdict.problems += static_problems(family, item, answer, taxonomy)
        verdict.digest = digest
        drafts[seed] = (item, answer)

    # One batch per language (Python twice) across the whole family.
    jobs: dict[str, list[tuple[int, str]]] = defaultdict(list)
    sources: dict[str, list[str]] = defaultdict(list)
    for seed, (item, _) in drafts.items():
        for role, by_lang in snippets_for(family, item).items():
            for language in family.languages:
                if language in by_lang:
                    jobs[language].append((seed, role))
                    sources[language].append(by_lang[language])
    results: dict[int, dict[str, dict[str, Result]]] = defaultdict(lambda: defaultdict(dict))
    for lang, snippets in sources.items():
        if lang == "python":
            first, second = (runner.run(lang, snippets, h) for h in HASH_SEEDS)
            for (seed, role), a, b in zip(jobs[lang], first, second, strict=True):
                results[seed][role]["python"] = a
                if a.output != b.output:
                    results[seed][role]["python(hash 2)"] = b
        else:
            for (seed, role), r in zip(jobs[lang], runner.run(lang, snippets), strict=True):
                results[seed][role][lang] = r
    for verdict in verdicts:
        if verdict.seed in drafts:
            item, answer = drafts[verdict.seed]
            verdict.problems += dynamic_problems(family, item, answer, results[verdict.seed])
    return verdicts


def manifest_entry(root: Path, family: QuizFamily, verdicts: list[Verdict]) -> dict:
    return dict(
        source=framework.source_digest(root, family),
        items={str(v.seed): v.digest for v in verdicts if v.ok},
        duplicates={str(v.seed): v.duplicate_of for v in verdicts if v.duplicate_of is not None},
        rejected={str(v.seed): v.problems for v in verdicts if v.problems},
    )
