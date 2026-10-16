"""At most k distinct: longest run of neighbours holding at most k different values."""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

WHILE = lines(
    "while len(count) > k:", "while ((int)count.size() > k) {", "while (count.size() > k) {"
)
BEST = lines(
    "best = max(best, right - left + 1)",
    "best = max(best, right - left + 1);",
    "best = Math.max(best, right - left + 1);",
)
INIT = lines("left = best = 0", "int left = 0, best = 0;")
LOOP = lines(
    "for right in range(len(a)):",
    "for (int right = 0; right < (int)a.size(); right++) {",
    "for (int right = 0; right < a.length; right++) {",
)


def program(v: dict) -> dict[str, str]:
    values, k = ", ".join(map(str, v["a"])), v["k"]
    return {
        "python": (
            f"a = [{values}]\nk = {k}\n"
            "count = {}\n"
            "left = best = 0\n"
            "for right in range(len(a)):\n"
            "    count[a[right]] = count.get(a[right], 0) + 1\n"
            "    while len(count) > k:\n"
            "        count[a[left]] -= 1\n"
            "        if count[a[left]] == 0:\n"
            "            del count[a[left]]\n"
            "        left += 1\n"
            "    best = max(best, right - left + 1)\n"
            "print(best)"
        ),
        "cpp": (
            f"vector<int> a = {{{values}}};\nint k = {k};\n"
            "map<int, int> count;\n"
            "int left = 0, best = 0;\n"
            "for (int right = 0; right < (int)a.size(); right++) {\n"
            "    count[a[right]]++;\n"
            "    while ((int)count.size() > k) {\n"
            "        count[a[left]]--;\n"
            "        if (count[a[left]] == 0) count.erase(a[left]);\n"
            "        left++;\n"
            "    }\n"
            "    best = max(best, right - left + 1);\n"
            "}\n"
            'cout << best << "\\n";'
        ),
        "java": (
            f"int[] a = {{{values}}};\nint k = {k};\n"
            "Map<Integer, Integer> count = new HashMap<>();\n"
            "int left = 0, best = 0;\n"
            "for (int right = 0; right < a.length; right++) {\n"
            "    count.merge(a[right], 1, Integer::sum);\n"
            "    while (count.size() > k) {\n"
            "        count.merge(a[left], -1, Integer::sum);\n"
            "        if (count.get(a[left]) == 0) count.remove(a[left]);\n"
            "        left++;\n"
            "    }\n"
            "    best = Math.max(best, right - left + 1);\n"
            "}\n"
            "System.out.println(best);"
        ),
    }


def longest(a: list[int], k: int) -> int:
    """Brute force over every subarray."""
    best = 0
    for i in range(len(a)):
        for j in range(i, len(a)):
            if len(set(a[i : j + 1])) <= k:
                best = max(best, j - i + 1)
    return best


def sample(rng, params):
    while True:
        # Runs of repeated values: a new value then forces several removals in a row.
        n = rng.randint(*params["n"])
        a: list[int] = []
        while len(a) < n:
            a += [rng.randint(*params["value"])] * rng.randint(1, 3)
        a = a[:n]
        k = rng.randint(*params["k"])
        if len(set(a)) > k + 1:
            return {"a": a, "k": k}


def wrong(v):
    a, k = v["a"], v["k"]
    best = longest(a, k)
    return [
        (str(longest(a, k - 1) if k > 1 else longest(a, k + 1)), "k-distinct-boundary"),
        (str(best - 1), "window-length-off-by-one"),
        (str(len(set(a))), "distinct-count-not-length"),
        (str(best + 1), "window-length-off-by-one"),
    ]


def describe(v):
    return f"the longest run of neighbours with at most {v['k']} different values"


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(longest(v["a"], v["k"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print the length of {describe(v)}. Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should print the length of {describe(v)}, but it prints the wrong answer. "
        "Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Count each value inside the window and shrink while more than {v['k']} different values "
        f"are inside; the longest valid window has {answer} numbers."
    ),
    blanks=[
        Blank(
            WHILE,
            [
                (
                    lines(
                        "while len(count) >= k:",
                        "while ((int)count.size() >= k) {",
                        "while (count.size() >= k) {",
                    ),
                    "k-distinct-boundary",
                ),
                (
                    lines("while right - left + 1 > k:", "while (right - left + 1 > k) {"),
                    "distinct-count-not-length",
                ),
                (lines("while left < right:", "while (left < right) {"), "reset-instead-of-shrink"),
            ],
        ),
        Blank(
            BEST,
            [
                (
                    lines(
                        "best = max(best, right - left)",
                        "best = max(best, right - left);",
                        "best = Math.max(best, right - left);",
                    ),
                    "window-length-off-by-one",
                ),
                (
                    lines(
                        "best = max(best, len(count))",
                        "best = max(best, (int)count.size());",
                        "best = Math.max(best, count.size());",
                    ),
                    "distinct-count-not-length",
                ),
                (lines("best = right - left + 1", "best = right - left + 1;"), "overwrite-best"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "akd-boundary",
            edit(
                WHILE,
                lines(
                    "while len(count) >= k:",
                    "while ((int)count.size() >= k) {",
                    "while (count.size() >= k) {",
                ),
            ),
            "Shrink only while more than k values are inside",
            "Exactly k different values is allowed; >= k forces the window down to k - 1.",
        ),
        Fix(
            "sw-length-off-by-one",
            edit(
                BEST,
                lines(
                    "best = max(best, right - left)",
                    "best = max(best, right - left);",
                    "best = Math.max(best, right - left);",
                ),
            ),
            "Measure the window as right - left + 1",
            "A window from left to right holds right - left + 1 numbers.",
        ),
    ],
    decoys=[
        Decoy(
            edit(
                BEST,
                lines(
                    "best = max(best, right - left)",
                    "best = max(best, right - left);",
                    "best = Math.max(best, right - left);",
                ),
            ),
            "Measure the window as right - left",
            "window-length-off-by-one",
        ),
        Decoy(
            edit(
                BEST,
                lines(
                    "best = max(best, len(count))",
                    "best = max(best, (int)count.size());",
                    "best = Math.max(best, count.size());",
                ),
            ),
            "Track the number of different values instead",
            "distinct-count-not-length",
        ),
        Decoy(
            edit(
                WHILE,
                lines(
                    "while len(count) > k + 1:",
                    "while ((int)count.size() > k + 1) {",
                    "while (count.size() > k + 1) {",
                ),
            ),
            "Allow k + 1 different values",
            "k-distinct-boundary",
        ),
        Decoy(
            edit(
                LOOP,
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
            edit(INIT, lines("left, best = 0, 1", "int left = 0, best = 1;")),
            "Start best at 1",
            "accumulator-init-one",
        ),
        Decoy(
            edit(lines("left += 1", "left++;"), lines("left += 2", "left += 2;")),
            "Move left two places at a time",
            "shrink-too-far",
        ),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"longest": longest}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
