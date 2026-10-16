"""Binary search on the answer: the slowest eating speed that finishes all piles in time."""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

CHECK = lines("if need <= hours:", "if (need <= hours) {")
NEED = lines(
    "need = sum((p + mid - 1) // mid for p in piles)",
    "for (int p : piles) need += (p + mid - 1) / mid;",
)
SHRINK = lines("hi = mid", "hi = mid;")
RANGE = lines(
    "lo, hi = 1, max(piles)",
    "int lo = 1, hi = *max_element(piles.begin(), piles.end());",
    "int lo = 1, hi = Arrays.stream(piles).max().getAsInt();",
)
OUTPUT = lines("print(lo)", 'cout << lo << "\\n";', "System.out.println(lo);")


def program(v: dict) -> dict[str, str]:
    values, hours = ", ".join(map(str, v["piles"])), v["hours"]
    body = (
        "while (lo < hi) {\n"
        "    int mid = (lo + hi) / 2;\n"
        "    int need = 0;\n"
        "    for (int p : piles) need += (p + mid - 1) / mid;\n"
        "    if (need <= hours) {\n"
        "        hi = mid;\n"
        "    } else {\n"
        "        lo = mid + 1;\n"
        "    }\n"
        "}\n"
    )
    return {
        "python": (
            f"piles = [{values}]\nhours = {hours}\n"
            "lo, hi = 1, max(piles)\n"
            "while lo < hi:\n"
            "    mid = (lo + hi) // 2\n"
            "    need = sum((p + mid - 1) // mid for p in piles)\n"
            "    if need <= hours:\n"
            "        hi = mid\n"
            "    else:\n"
            "        lo = mid + 1\n"
            "print(lo)"
        ),
        "cpp": (
            f"vector<int> piles = {{{values}}};\nint hours = {hours};\n"
            "int lo = 1, hi = *max_element(piles.begin(), piles.end());\n"
            + body
            + 'cout << lo << "\\n";'
        ),
        "java": (
            f"int[] piles = {{{values}}};\nint hours = {hours};\n"
            "int lo = 1, hi = Arrays.stream(piles).max().getAsInt();\n"
            + body
            + "System.out.println(lo);"
        ),
    }


def hours_at(piles: list[int], speed: int) -> int:
    return sum(-(-p // speed) for p in piles)


def slowest(piles: list[int], hours: int) -> int:
    """Brute force: try every speed from 1 up."""
    speed = 1
    while hours_at(piles, speed) > hours:
        speed += 1
    return speed


def sample(rng, params):
    piles = [rng.randint(*params["pile"]) for _ in range(rng.randint(*params["n"]))]
    # Hours that some speed needs exactly: the answer then sits on the boundary of the rule.
    hours = hours_at(piles, rng.randint(2, max(piles)))
    return {"piles": piles, "hours": hours}


def wrong(v):
    piles, hours = v["piles"], v["hours"]
    best = slowest(piles, hours)
    strict = slowest(piles, hours - 1) if hours > len(piles) else max(piles)
    return [
        (str(strict), "predicate-boundary"),
        (str(best - 1), "exclude-candidate-mid"),
        (str(max(piles)), "answer-max-not-min"),
        (str(-(-sum(piles) // hours)), "predicate-average-shortcut"),
        (str(best + 1), "off-by-one-output"),
    ]


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(slowest(v["piles"], v["hours"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print the slowest whole-number speed that eats every pile within "
        f"{v['hours']} hours (a pile of p takes ceil(p / speed) hours). Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should print the slowest speed that eats every pile within {v['hours']} "
        "hours, but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Faster speeds never need more hours, so the rule is monotone; the first speed that "
        f"fits within {v['hours']} hours is {answer}."
    ),
    blanks=[
        Blank(
            CHECK,
            [
                (lines("if need < hours:", "if (need < hours) {"), "predicate-boundary"),
                (lines("if need >= hours:", "if (need >= hours) {"), "predicate-inverted"),
                (lines("if need <= mid:", "if (need <= mid) {"), "predicate-wrong-variable"),
            ],
        ),
        Blank(
            NEED,
            [
                (
                    lines(
                        "need = sum(p // mid for p in piles)",
                        "for (int p : piles) need += p / mid;",
                    ),
                    "ceil-vs-floor",
                ),
                (
                    lines(
                        "need = sum((p + mid) // mid for p in piles)",
                        "for (int p : piles) need += (p + mid) / mid;",
                    ),
                    "ceil-vs-floor",
                ),
                (
                    lines(
                        "need = sum(mid // p for p in piles)",
                        "for (int p : piles) need += mid / p;",
                    ),
                    "rate-inverted",
                ),
            ],
        ),
    ],
    fixes=[
        Fix(
            "ap-strict-predicate",
            edit(CHECK, lines("if need < hours:", "if (need < hours) {")),
            "Accept a speed when need <= hours",
            "Finishing in exactly the allowed hours is fine, so the rule must include equality.",
        ),
        Fix(
            "ap-skip-mid",
            edit(SHRINK, lines("hi = mid - 1", "hi = mid - 1;")),
            "Keep mid with hi = mid",
            "A speed that fits may be the slowest one, so it must stay in the range.",
        ),
    ],
    decoys=[
        Decoy(
            edit(CHECK, lines("if need >= hours:", "if (need >= hours) {")),
            "Accept a speed when need >= hours",
            "predicate-inverted",
        ),
        Decoy(
            edit(
                OUTPUT,
                lines("print(lo - 1)", 'cout << lo - 1 << "\\n";', "System.out.println(lo - 1);"),
            ),
            "Print lo - 1",
            "off-by-one-output",
        ),
        Decoy(
            edit(
                RANGE,
                lines(
                    "lo, hi = 1, sum(piles)",
                    "int lo = 1, hi = accumulate(piles.begin(), piles.end(), 0);",
                    "int lo = 1, hi = Arrays.stream(piles).sum();",
                ),
            ),
            "Search up to the total of all piles",
            "search-range-confusion",
        ),
        Decoy(
            edit(
                NEED,
                lines(
                    "need = sum(p // mid for p in piles)", "for (int p : piles) need += p / mid;"
                ),
            ),
            "Round the hours per pile down",
            "ceil-vs-floor",
        ),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"slowest": slowest}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
