"""Validate course content and build each problem's test suite.

1. Load every course without tests: schema, prerequisite DAG and references must pass.
2. For every problem: run its generator (seeded by problem id) for inputs, run the Python
   reference on examples and generated inputs, require examples to match their documented
   output, and write ``.cache/content-tests/<problem>.json``. Unchanged problems are
   skipped using a hash of their YAML.
3. Load the catalog again with tests, exactly as the API does.

Usage: python scripts/content/build.py [--force]
"""

import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "api" / "src"))

from socrat.catalog.registry import CONTENT_ROOT, TESTS_ROOT, load  # noqa: E402

MAX_GENERATED = 14
# Every submission ships its tests in one signed job envelope; keep each test bounded.
MAX_TEST_CHARS = 2_000_000


def run_reference(code: str, stdin: str, timeout: float = 30) -> str:
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        input=stdin.encode(),
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-2000:])
    return result.stdout.decode()


def normalize(text: str) -> str:
    """Mirror the judge (socrat.execution.protocol.same_output): leading spaces matter."""
    lines = text.replace("\r\n", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip("\n")


def generated_inputs(problem: dict) -> list[str]:
    if not problem.get("generator"):
        return []
    namespace: dict = {}
    exec(problem["generator"], namespace)  # Trusted, reviewed authoring code.
    rng = random.Random(problem["id"])
    inputs = []
    for value in namespace["cases"](rng):
        inputs.append(value if value.endswith("\n") else value + "\n")
        if len(inputs) >= MAX_GENERATED:
            break
    return inputs


def build_problem(path: Path) -> list[dict]:
    problem = yaml.safe_load(path.read_text(encoding="utf-8"))
    tests = []
    for example in problem["examples"]:
        stdin = example["input"] if example["input"].endswith("\n") else example["input"] + "\n"
        output = run_reference(problem["reference"], stdin)
        if normalize(output) != normalize(example["output"]):
            raise SystemExit(
                f"{path}: example output mismatch\nexpected:\n{example['output']}\ngot:\n{output}"
            )
        tests.append({"input": stdin, "expected": normalize(output) + "\n", "public": True})
    seen = {t["input"] for t in tests}
    for stdin in generated_inputs(problem):
        if stdin in seen:
            continue
        seen.add(stdin)
        output = run_reference(problem["reference"], stdin)
        tests.append({"input": stdin, "expected": normalize(output) + "\n", "public": False})
    if len(tests) < 4:
        raise SystemExit(f"{path}: needs at least 4 distinct tests (add a generator)")
    largest = max(len(t["input"]) + len(t["expected"]) for t in tests)
    if largest > MAX_TEST_CHARS:
        raise SystemExit(f"{path}: a test is {largest} chars; keep each under {MAX_TEST_CHARS}")
    return tests


def main() -> int:
    force = "--force" in sys.argv
    load(CONTENT_ROOT, tests_root=None)  # Fail fast on authoring errors.
    TESTS_ROOT.mkdir(parents=True, exist_ok=True)
    built = skipped = 0
    failures = []
    for path in sorted(CONTENT_ROOT.glob("*/problems/*.yaml")):
        source = hashlib.sha256(path.read_bytes()).hexdigest()
        target = TESTS_ROOT / f"{path.stem}.json"
        stamp = TESTS_ROOT / f"{path.stem}.sha256"
        if not force and target.exists() and stamp.exists() and stamp.read_text() == source:
            skipped += 1
            continue
        try:
            tests = build_problem(path)
        except (SystemExit, RuntimeError, subprocess.TimeoutExpired) as exc:
            failures.append(f"{path.relative_to(ROOT)}: {exc}")
            continue
        target.write_text(json.dumps(tests, ensure_ascii=False), encoding="utf-8")
        stamp.write_text(source)
        built += 1
    if failures:
        print("\n\n".join(failures))
        print(f"\n{len(failures)} problem(s) failed to build.")
        return 1
    catalog = load(CONTENT_ROOT)
    concepts = sum(len(c.concepts) for c in catalog.courses.values())
    tests = sum(len(p.tests) for _, p in catalog.problems.values())
    print(
        f"{len(catalog.courses)} courses, {concepts} concepts, {len(catalog.problems)} problems "
        f"({built} built, {skipped} unchanged), {tests} tests. Digest {catalog.digest[:12]}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
