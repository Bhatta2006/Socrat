"""Judge-problem quality gates."""

from socrat.catalog import validate

REFERENCE = "n = int(input())\nprint(n * (n + 1) // 2)\n"
BRUTE = "n = int(input())\nprint(sum(range(n + 1)))\n"
GENERATOR = "def cases(rng):\n    for n in (10**5, 10**6, 7, 3):\n        yield str(n)\n"
SMALL = "def cases(rng):\n    for _ in range(50):\n        yield str(rng.randint(0, 40))\n"


def problem(**overrides) -> dict:
    raw = dict(
        id="triangle-total",
        title="Triangle total",
        concepts=["loops"],
        difficulty="easy",
        statement="Read a whole number n and print the sum of all integers from 0 to n inclusive.",
        input_format="One integer n.",
        output_format="The sum.",
        constraints=["0 ≤ n ≤ 10^6"],
        examples=[dict(input="3", output="6"), dict(input="0", output="0")],
        hints=["Add them up.", "There is a formula."],
        approach="Use n(n+1)/2 or a loop; both fit the limits comfortably.",
        reference=REFERENCE,
        generator=GENERATOR,
        brute=BRUTE,
        small_generator=SMALL,
    )
    raw.update(overrides)
    return raw


def gates(raw: dict, strict: bool = True, statements: dict | None = None) -> dict[str, dict]:
    result = validate.validate(
        raw,
        strict=strict,
        library_titles=["Two Sum", "Climbing Stairs"],
        statements=statements or {},
        concept_difficulty={"loops": 1},
    )
    return {g.name: {"status": g.status, "detail": g.detail} for g in result}


def test_a_sound_problem_passes_every_gate():
    result = gates(problem())
    assert {name: g["status"] for name, g in result.items()} == {
        "schema": "pass",
        "examples": "pass",
        "brute": "pass",
        "timing": "pass",
        "languages": "skip",
        "originality": "pass",
        "difficulty": "pass",
    }


def test_wrong_reference_is_caught_by_examples_and_brute_force():
    wrong = "n = int(input())\nprint(n * n // 2)\n"
    result = gates(problem(reference=wrong, examples=[dict(input="0", output="0")]))
    assert result["brute"]["status"] == "fail" and "disagree" in result["brute"]["detail"]
    result = gates(problem(reference=wrong))
    assert result["examples"]["status"] == "fail"


def test_drafts_need_a_brute_force_but_authored_problems_only_warn():
    assert gates(problem(brute=""))["brute"]["status"] == "fail"
    assert gates(problem(brute=""), strict=False)["brute"]["status"] == "warn"


def test_crashes_and_schema_errors_fail_cleanly():
    assert gates(problem(brute="raise ValueError('boom')"))["brute"]["status"] == "fail"
    result = gates(problem(difficulty="impossible"))
    assert list(result) == ["schema"] and result["schema"]["status"] == "fail"


def test_copies_are_flagged():
    twin = {"other": problem()["statement"]}
    assert gates(problem(), statements=twin)["originality"]["status"] == "fail"
    assert gates(problem(), strict=False, statements=twin)["originality"]["status"] == "warn"
    assert gates(problem(title="Two Sum"))["originality"]["status"] == "warn"


def test_difficulty_reads_size_bounds_not_value_bounds():
    assert validate.max_constraint(["1 ≤ n ≤ 2·10^5", "|a_i| ≤ 10^9"]) == 200_000
    assert validate.max_constraint(["Each value is at most 10^9"]) == 0
    assert gates(problem(difficulty="hard"))["difficulty"]["status"] == "warn"


def test_harness_supports_binary_stdin_and_exit():
    code = "import sys\ndata = sys.stdin.buffer.read().split()\nprint(len(data))\nraise SystemExit(0)\n"
    assert validate.run_many(code, ["a b c\n"]) == [(True, "3\n")]
