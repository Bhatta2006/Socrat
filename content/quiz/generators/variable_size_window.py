"""Variable-size window: longest run of positive numbers whose sum stays within a limit."""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

WHILE = lines("while total > limit:", "while (total > limit) {")
DROP = lines("total -= a[left]", "total -= a[left];")
GROW = lines("total += a[right]", "total += a[right];")
BEST = lines(
    "best = max(best, right - left + 1)",
    "best = max(best, right - left + 1);",
    "best = Math.max(best, right - left + 1);",
)


def program(v: dict) -> dict[str, str]:
    a, limit = v["a"], v["limit"]
    values = ", ".join(map(str, a))
    loop = (
        "    total += a[right];\n"
        "    while (total > limit) {\n"
        "        total -= a[left];\n"
        "        left++;\n"
        "    }\n"
    )
    return {
        "python": (
            f"a = [{values}]\nlimit = {limit}\n"
            "total = left = best = 0\n"
            "for right in range(len(a)):\n"
            "    total += a[right]\n"
            "    while total > limit:\n"
            "        total -= a[left]\n"
            "        left += 1\n"
            "    best = max(best, right - left + 1)\n"
            "print(best)"
        ),
        "cpp": (
            f"vector<int> a = {{{values}}};\nint limit = {limit};\n"
            "int total = 0, left = 0, best = 0;\n"
            "for (int right = 0; right < (int)a.size(); right++) {\n"
            + loop
            + "    best = max(best, right - left + 1);\n}\n"
            'cout << best << "\\n";'
        ),
        "java": (
            f"int[] a = {{{values}}};\nint limit = {limit};\n"
            "int total = 0, left = 0, best = 0;\n"
            "for (int right = 0; right < a.length; right++) {\n"
            + loop
            + "    best = Math.max(best, right - left + 1);\n}\n"
            "System.out.println(best);"
        ),
    }


def longest(a: list[int], limit: int) -> int:
    """Brute force over every subarray."""
    best = 0
    for i in range(len(a)):
        for j in range(i, len(a)):
            if sum(a[i : j + 1]) <= limit:
                best = max(best, j - i + 1)
    return best


def overwrite_best(a: list[int], limit: int) -> int:
    """best = right - left + 1: the length of the last window, not the longest."""
    total = left = best = 0
    for right in range(len(a)):
        total += a[right]
        while total > limit:
            total -= a[left]
            left += 1
        best = right - left + 1
    return best


def largest_sum(a: list[int], limit: int) -> int:
    sums = [sum(a[i : j + 1]) for i in range(len(a)) for j in range(i, len(a))]
    return max([s for s in sums if s <= limit], default=0)


def sample(rng, params):
    n = rng.randint(*params["n"])
    low, high = params["value"]
    a = [rng.randint(low, high) for _ in range(n)]
    if rng.random() < 0.5:
        # An exact window sum: a run may hit the limit exactly.
        i = rng.randrange(n - 1)
        j = rng.randrange(i + 1, min(n, i + 4))
        limit = max(sum(a[i : j + 1]), max(a))
    else:
        # Between the largest number and half the total: never the whole array, never empty.
        limit = rng.randint(max(a), max(max(a), sum(a) // 2))
    return {"a": a, "limit": limit}


def wrong(v):
    a, limit = v["a"], v["limit"]
    best = longest(a, limit)
    return [
        (str(best - 1), "window-length-off-by-one"),
        (str(largest_sum(a, limit)), "window-sum-not-length"),
        (str(overwrite_best(a, limit)), "overwrite-best"),
        (str(best + 1), "window-length-off-by-one"),
    ]


BEST_SHORT = lines(
    "best = max(best, right - left)",
    "best = max(best, right - left);",
    "best = Math.max(best, right - left);",
)
BEST_SUM = lines(
    "best = max(best, total)", "best = max(best, total);", "best = Math.max(best, total);"
)
BEST_LAST = lines("best = right - left + 1", "best = right - left + 1;")

SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(longest(v["a"], v["limit"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print the length of the longest run of neighbours whose sum is "
        f"at most {v['limit']}. Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should print the length of the longest run of neighbours whose sum is "
        f"at most {v['limit']}, but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Grow the window one number at a time and shrink it while the sum is over "
        f"{v['limit']}; the longest valid window has {answer} numbers."
    ),
    blanks=[
        Blank(
            GROW,
            [
                (lines("total += a[left]", "total += a[left];"), "drop-wrong-end"),
                (lines("total += right", "total += right;"), "confuse-index-value"),
                (lines("total = a[right]", "total = a[right];"), "reset-instead-of-shrink"),
            ],
        ),
        Blank(
            DROP,
            [
                (lines("total -= a[right]", "total -= a[right];"), "drop-wrong-end"),
                (lines("total = 0", "total = 0;"), "reset-instead-of-shrink"),
                (lines("total -= left", "total -= left;"), "confuse-index-value"),
            ],
        ),
        Blank(
            BEST,
            [
                (BEST_SHORT, "window-length-off-by-one"),
                (BEST_LAST, "overwrite-best"),
                (BEST_SUM, "window-sum-not-length"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "sw-length-off-by-one",
            edit(BEST, BEST_SHORT),
            "Measure the window as right - left + 1",
            "A window from left to right holds right - left + 1 numbers.",
        ),
        Fix(
            "sw-drop-wrong-end",
            edit(DROP, lines("total -= a[right]", "total -= a[right];")),
            "Subtract a[left], the number that leaves",
            "Shrinking removes the leftmost number, so the sum must lose a[left].",
        ),
        Fix(
            "sw-overwrite-best",
            edit(BEST, BEST_LAST),
            "Keep the larger of best and the current length",
            "best must remember the longest window seen so far, not the latest one.",
        ),
    ],
    decoys=[
        Decoy(
            edit(BEST, BEST_SUM),
            "Track the largest sum instead of the length",
            "window-sum-not-length",
        ),
        Decoy(
            edit(WHILE, lines("while total >= limit:", "while (total >= limit) {")),
            "Shrink while the sum is at least the limit",
            "window-rule-boundary",
        ),
        Decoy(
            edit(GROW, lines("total += a[left]", "total += a[left];")),
            "Add a[left] when the window grows",
            "drop-wrong-end",
        ),
        Decoy(
            edit(lines("left += 1", "left++;"), lines("left += 2", "left += 2;")),
            "Move left two places at a time",
            "shrink-too-far",
        ),
        Decoy(
            edit(
                lines(
                    "for right in range(len(a)):",
                    "for (int right = 0; right < (int)a.size(); right++) {",
                    "for (int right = 0; right < a.length; right++) {",
                ),
                lines(
                    "for right in range(1, len(a)):",
                    "for (int right = 1; right < (int)a.size(); right++) {",
                    "for (int right = 1; right < a.length; right++) {",
                ),
            ),
            "Start right at index 1",
            "skip-first-element",
        ),
        Decoy(
            edit(
                lines("total = left = best = 0", "int total = 0, left = 0, best = 0;"),
                lines("total, left, best = 0, 0, 1", "int total = 0, left = 0, best = 1;"),
            ),
            "Start best at 1",
            "accumulator-init-one",
        ),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"longest": longest}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
