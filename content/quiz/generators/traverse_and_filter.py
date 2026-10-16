"""Traverse and filter: add up the values in a list that pass a test."""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

TEST = lines("if v > limit:", "if (v > limit) {")
ADD = lines("total += v", "total += v;")
INIT = lines("total = 0", "int total = 0;")
OUTPUT = lines("print(total)", 'cout << total << "\\n";', "System.out.println(total);")


def program(v: dict) -> dict[str, str]:
    values, limit = ", ".join(map(str, v["values"])), v["limit"]
    loop = "    if (v > limit) {\n        total += v;\n    }\n}\n"
    return {
        "python": (
            f"values = [{values}]\nlimit = {limit}\n"
            "total = 0\n"
            "for v in values:\n"
            "    if v > limit:\n"
            "        total += v\n"
            "print(total)"
        ),
        "cpp": (
            f"vector<int> values = {{{values}}};\nint limit = {limit};\n"
            "int total = 0;\n"
            "for (int v : values) {\n" + loop + 'cout << total << "\\n";'
        ),
        "java": (
            f"int[] values = {{{values}}};\nint limit = {limit};\n"
            "int total = 0;\n"
            "for (int v : values) {\n" + loop + "System.out.println(total);"
        ),
    }


def total_above(values: list[int], limit: int) -> int:
    return sum(v for v in values if v > limit)


def sample(rng, params):
    values = [rng.randint(*params["value"]) for _ in range(rng.randint(*params["n"]))]
    # Often a value equals the limit, which is where > and >= part ways.
    limit = rng.choice(values) if rng.random() < 0.6 else rng.randint(*params["value"])
    return {"values": values, "limit": limit}


def wrong(v):
    values, limit = v["values"], v["limit"]
    return [
        (str(sum(x for x in values if x >= limit)), "filter-boundary"),
        (str(sum(1 for x in values if x > limit)), "count-not-sum"),
        (str(sum(values)), "filter-ignored"),
        (str(sum(x for x in values if x < limit)), "filter-inverted"),
    ]


def describe(v):
    return f"the total of the values greater than {v['limit']}"


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(total_above(v["values"], v["limit"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: f"This code should print {describe(v)}. Which line goes in the blank?",
    fix=lambda v: (
        f"This code should print {describe(v)}, but it prints the wrong answer. "
        "Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Visit every value, keep only those greater than {v['limit']}, and add them up: {answer}."
    ),
    blanks=[
        Blank(
            TEST,
            [
                (lines("if v >= limit:", "if (v >= limit) {"), "filter-boundary"),
                (lines("if v < limit:", "if (v < limit) {"), "filter-inverted"),
                (lines("if v != limit:", "if (v != limit) {"), "filter-wrong-test"),
            ],
        ),
        Blank(
            ADD,
            [
                (lines("total += 1", "total += 1;"), "count-not-sum"),
                (lines("total = v", "total = v;"), "overwrite-not-accumulate"),
                (lines("total += limit", "total += limit;"), "bound-instead-of-variable"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "filter-boundary",
            edit(TEST, lines("if v >= limit:", "if (v >= limit) {")),
            "Keep only values strictly greater than the limit (>)",
            "A value equal to the limit is not greater than it.",
        ),
        Fix(
            "filter-count-not-sum",
            edit(ADD, lines("total += 1", "total += 1;")),
            "Add the value v, not 1",
            "Adding 1 counts the values; the task asks for their total.",
        ),
        Fix(
            "filter-overwrite",
            edit(ADD, lines("total = v", "total = v;")),
            "Use += so each value is added",
            "= replaces the total with the latest value instead of adding to it.",
        ),
    ],
    decoys=[
        Decoy(
            edit(INIT, lines("total = 1", "int total = 1;")),
            "Start the total at 1",
            "accumulator-init-one",
        ),
        Decoy(
            edit(TEST, lines("if v < limit:", "if (v < limit) {")),
            "Flip the test to v < limit",
            "filter-inverted",
        ),
        Decoy(
            edit(ADD, lines("total += limit", "total += limit;")),
            "Add the limit each time",
            "bound-instead-of-variable",
        ),
        Decoy(
            edit(
                OUTPUT,
                lines(
                    "print(total - limit)",
                    'cout << total - limit << "\\n";',
                    "System.out.println(total - limit);",
                ),
            ),
            "Subtract the limit before printing",
            "filter-wrong-test",
        ),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"total_above": total_above}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
