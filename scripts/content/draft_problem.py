"""Draft an original judge problem with Claude, check it, and file it for human review.

Pipeline (backlog item 5):
1. Build a brief from the concept (title, summary, key points, tier) and a short idea seed
   written by a person. External statements are never pasted in.
2. Claude drafts the whole problem as structured output: statement, formats, constraints,
   examples, four Socratic hints, approach, Python reference, brute force, generators
   and starter code.
3. The quality gates run (schema, examples, brute-force agreement, timing, originality,
   difficulty). Failures go back to Claude once per attempt as feedback.
4. A second, independent call solves the problem from the statement and examples alone;
   its answers must match the reference on every test, or the statement is ambiguous.
5. The draft lands in content/drafts/<course>/<id>.yaml for the review queue in /admin.

Needs SOCRAT_ANTHROPIC_API_KEY (or ANTHROPIC_API_KEY). Each problem costs a few model
calls; --dry-run prints the brief without calling the API.

Usage:
  python scripts/content/draft_problem.py --course dsa --concept two-pointers \\
      --difficulty medium --idea "pair up guests by height difference"
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from socrat.catalog import validate  # noqa: E402
from socrat.catalog.registry import CONTENT_ROOT, Catalog, load  # noqa: E402
from socrat.library import ladder  # noqa: E402

DRAFTS = ROOT / "content" / "drafts"
MODEL = os.environ.get("SOCRAT_DRAFT_MODEL", "claude-opus-5-5")


class Example(BaseModel):
    input: str
    output: str
    explanation: str = ""


class Draft(BaseModel):
    """Exactly the authoring fields of catalog.schema.Problem (ids and links added later)."""

    title: str = Field(description="Short, original title (2-6 words); not a known problem's name")
    statement: str = Field(description="Markdown story and task; self-contained and unambiguous")
    input_format: str
    output_format: str
    constraints: list[str] = Field(description="One bound per line, e.g. '1 ≤ n ≤ 2·10^5'")
    examples: list[Example] = Field(description="2-3 examples, outputs exactly as printed")
    hints: list[str] = Field(description="Exactly 4 Socratic hints, each more specific, no code")
    approach: str = Field(description="Explanation of the intended solution and its complexity")
    reference: str = Field(description="Efficient Python 3 solution reading stdin, writing stdout")
    brute: str = Field(description="Obviously-correct slow Python 3 solution for small inputs")
    generator: str = Field(
        description="Python: def cases(rng): yield 10-14 input strings incl. max size"
    )
    small_generator: str = Field(
        description="Python: def cases(rng): yield ~300 tiny random inputs"
    )
    starter_python: str
    starter_cpp: str
    starter_java: str = Field(description="Public class Main with main()")
    time_limit_ms: int = Field(ge=1000, le=5000)


class Solution(BaseModel):
    reasoning: str
    code: str = Field(description="Python 3 program reading stdin, writing stdout")


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]


def brief(catalog: Catalog, course: str, concept: str, difficulty: str, idea: str) -> str:
    qualified = f"{course}:{concept}"
    item = catalog.concept(qualified)
    existing = sorted(
        problem.title for _, problem in catalog.problems.values() if concept in problem.concepts
    )
    tier = ladder.tier_of(qualified)
    points = "\n".join(f"- {p}" for p in item.key_points)
    return f"""You are writing an ORIGINAL programming problem for Socrat, a learning platform.

Concept: {item.title} (course "{course}", concept tier {item.difficulty} of 5, ladder rating ~{tier})
What the concept teaches: {item.summary}
Key points:
{points}

Target difficulty: {difficulty}. Idea seed from the author: {idea}

Problems that already exist for this concept (do not repeat them): {", ".join(existing) or "none"}

Rules:
- The story, title and task must be original. Never reproduce or paraphrase a statement from
  LeetCode, Codeforces, CSES, AtCoder, HackerRank or any book. Plain technical names are fine.
- The statement must be unambiguous: specify ties, output formatting, and edge cases.
- The intended solution should exercise the concept above at the target difficulty.
- `reference` must be efficient enough for the largest constraints in Python within
  time_limit_ms. `brute` must be simple and obviously correct, used only on tiny inputs.
- `generator` yields 10-14 inputs covering edge cases and the maximum sizes (each input under
  1.5 MB); `small_generator` yields about 300 tiny inputs the brute force handles instantly.
  Both are `def cases(rng):` using the given random.Random; no imports besides what you need.
- Programs read standard input and write standard output, nothing else.
- Hints guide thinking (questions, observations); none of them contains code.
- Starter code only reads the input and leaves a TODO; it must not solve the problem."""


def feedback(gates: list[validate.Gate]) -> str:
    problems = [f"- {g.name}: {g.detail}" for g in gates if g.status == "fail"]
    return (
        "The draft failed these automatic checks. Fix them and return the full problem:\n"
        + "\n".join(problems)
    )


def to_problem(draft: Draft, problem_id: str, concept: str, difficulty: str) -> dict:
    return dict(
        id=problem_id,
        title=draft.title,
        concepts=[concept],
        difficulty=difficulty,
        statement=draft.statement,
        input_format=draft.input_format,
        output_format=draft.output_format,
        constraints=draft.constraints,
        examples=[e.model_dump(exclude_defaults=True) for e in draft.examples],
        hints=draft.hints,
        approach=draft.approach,
        reference=draft.reference,
        generator=draft.generator,
        starter=dict(python=draft.starter_python, cpp=draft.starter_cpp, java=draft.starter_java),
        brute=draft.brute,
        small_generator=draft.small_generator,
        time_limit_ms=draft.time_limit_ms,
    )


def ask(client, messages: list[dict], output_format: type[BaseModel]):
    with client.messages.stream(
        model=MODEL,
        max_tokens=32000,
        output_config={"effort": "high"},
        output_format=output_format,
        messages=messages,
    ) as stream:
        message = stream.get_final_message()
    if message.stop_reason in {"refusal", "max_tokens"} or message.parsed_output is None:
        raise RuntimeError(f"Model stopped early ({message.stop_reason}); try another idea seed.")
    return message


def solver_check(client, raw: dict) -> validate.Gate:
    """A fresh call sees only what learners see; its answers must match the reference."""
    shown = {
        k: raw[k] for k in ("statement", "input_format", "output_format", "constraints", "examples")
    }
    prompt = (
        "Solve this programming problem in Python 3. Read stdin, write stdout.\n\n"
        + json.dumps(shown, indent=2, ensure_ascii=False)
    )
    message = ask(client, [{"role": "user", "content": prompt}], Solution)
    code = message.parsed_output.code
    inputs = [
        e["input"] if e["input"].endswith("\n") else e["input"] + "\n" for e in raw["examples"]
    ]
    inputs += validate.cases(raw["generator"], raw["id"], validate.MAX_GENERATED)
    inputs = [i for i in inputs if len(i) < 200_000]  # keep the solver run quick
    expected = validate.run_many(raw["reference"], inputs)
    actual = validate.run_many(code, inputs)
    for text, (_, want), (ok, got) in zip(inputs, expected, actual, strict=True):
        if not ok or validate.normalize(want) != validate.normalize(got):
            return validate.Gate(
                "statement", "fail", f"An independent solver read it differently on {text[:80]!r}."
            )
    return validate.Gate(
        "statement", "pass", f"An independent solver matched the reference on {len(inputs)} tests."
    )


def draft_problem(
    client,
    catalog: Catalog,
    *,
    course: str,
    concept: str,
    difficulty: Literal["easy", "medium", "hard"],
    idea: str,
    attempts: int = 3,
) -> tuple[dict, list[validate.Gate], dict]:
    messages: list[dict] = [
        {"role": "user", "content": brief(catalog, course, concept, difficulty, idea)}
    ]
    usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
    titles = validate.library_titles()
    statements = validate.statements_of(catalog)
    tiers = validate.concept_tiers(catalog, course)
    raw: dict = {}
    gates: list[validate.Gate] = []
    for _ in range(attempts):
        message = ask(client, messages, Draft)
        usage["calls"] += 1
        usage["input_tokens"] += message.usage.input_tokens
        usage["output_tokens"] += message.usage.output_tokens
        draft: Draft = message.parsed_output
        raw = to_problem(draft, slugify(draft.title), concept, difficulty)
        gates = validate.validate(
            raw, strict=True, library_titles=titles, statements=statements, concept_difficulty=tiers
        )
        if validate.verdict(gates) != "fail":
            gates.append(solver_check(client, raw))
            usage["calls"] += 1
            if validate.verdict(gates) != "fail":
                break
        messages += [
            {"role": "assistant", "content": message.content},
            {"role": "user", "content": feedback(gates)},
        ]
    return raw, gates, usage


def write_draft(
    raw: dict, course: str, gates: list[validate.Gate], meta: dict, root: Path = DRAFTS
) -> Path:
    folder = root / course
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{raw['id']}.yaml"
    path.write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8"
    )
    record = dict(meta, gates=validate.as_dicts(gates), verdict=validate.verdict(gates))
    path.with_name(f"{raw['id']}.draft.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    return path


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    parser = argparse.ArgumentParser()
    parser.add_argument("--course", required=True)
    parser.add_argument("--concept", required=True, help="concept id within the course")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], required=True)
    parser.add_argument("--idea", required=True, help="one-line original idea seed")
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true", help="print the brief; no API call")
    args = parser.parse_args()

    catalog = load(CONTENT_ROOT, tests_root=None)
    if f"{args.course}:{args.concept}" not in catalog.concepts:
        parser.error(f"unknown concept {args.course}:{args.concept}")
    if args.dry_run:
        print(brief(catalog, args.course, args.concept, args.difficulty, args.idea))
        return 0
    key = os.environ.get("SOCRAT_ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        parser.error("set SOCRAT_ANTHROPIC_API_KEY (or ANTHROPIC_API_KEY) to draft problems")

    import anthropic

    client = anthropic.Anthropic(api_key=key)
    raw, gates, usage = draft_problem(
        client,
        catalog,
        course=args.course,
        concept=args.concept,
        difficulty=args.difficulty,
        idea=args.idea,
        attempts=args.attempts,
    )
    path = write_draft(raw, args.course, gates, dict(model=MODEL, idea=args.idea, usage=usage))
    for gate in gates:
        print(f"{gate.status:>5}  {gate.name}: {gate.detail}")
    print(
        f"\nDraft written to {path.relative_to(ROOT)} ({usage['calls']} calls, "
        f"{usage['input_tokens']:,} in / {usage['output_tokens']:,} out tokens)."
    )
    print(
        "Review it in /admin → Review queue."
        if validate.verdict(gates) != "fail"
        else "Gates still fail; fix the YAML by hand or redraft."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
