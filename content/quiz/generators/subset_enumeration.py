"""Subset enumeration with bitmasks: count subsets whose sum hits a target exactly."""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

MASKS = lines(
    "for mask in range(1 << n):",
    "for (int mask = 0; mask < (1 << n); mask++) {",
)
BIT = lines("if mask >> i & 1:", "if (mask >> i & 1) {", "if ((mask >> i & 1) == 1) {")
ADD = lines("total += a[i]", "total += a[i];")
MATCH = lines("if total == target:", "if (total == target) {")
COUNT = lines("count += 1", "count += 1;")
START = lines("count = 0", "int count = 0;")


def c_like(bit: str) -> str:
    """The C++/Java loop; only the bit test differs (Java needs an explicit boolean)."""
    return (
        "for (int mask = 0; mask < (1 << n); mask++) {\n"
        "    int total = 0;\n"
        "    for (int i = 0; i < n; i++) {\n"
        f"        {bit}\n"
        "            total += a[i];\n"
        "        }\n"
        "    }\n"
        "    if (total == target) {\n"
        "        count += 1;\n"
        "    }\n"
        "}\n"
    )


def program(v: dict) -> dict[str, str]:
    values, target = ", ".join(map(str, v["a"])), v["target"]
    return {
        "python": (
            f"a = [{values}]\ntarget = {target}\n"
            "n = len(a)\n"
            "count = 0\n"
            "# every mask is one subset: bit i says whether a[i] is chosen\n"
            "for mask in range(1 << n):\n"
            "    total = 0\n"
            "    for i in range(n):\n"
            "        if mask >> i & 1:\n"
            "            total += a[i]\n"
            "    if total == target:\n"
            "        count += 1\n"
            "print(count)"
        ),
        "cpp": (
            f"vector<int> a = {{{values}}};\nint target = {target};\n"
            "int n = a.size();\n"
            "int count = 0;\n" + c_like("if (mask >> i & 1) {") + 'cout << count << "\\n";'
        ),
        "java": (
            f"int[] a = {{{values}}};\nint target = {target};\n"
            "int n = a.length;\n"
            "int count = 0;\n"
            + c_like("if ((mask >> i & 1) == 1) {")
            + "System.out.println(count);"
        ),
    }


def subsets_with_sum(a: list[int], target: int) -> int:
    """Recursion over include/exclude: an independent check of the bitmask loop."""

    def go(i: int, left: int) -> int:
        if i == len(a):
            return int(left == 0)
        return go(i + 1, left) + go(i + 1, left - a[i])

    return go(0, target)


def sample(rng, params):
    while True:
        a = [rng.randint(*params["value"]) for _ in range(rng.randint(*params["n"]))]
        # The target is the sum of a subset that uses the last element, so a matching mask
        # always has the top bit set: too few masks (1 << (n - 1), n, 2n) then miss it.
        chosen = [x for x in a[:-1] if rng.random() < 0.5] + [a[-1]]
        target = sum(chosen)
        if target >= 3:
            return {"a": a, "target": target}


def wrong(v):
    a, target = v["a"], v["target"]
    at_most = sum(subsets_with_sum(a, t) for t in range(target + 1))
    return [
        (str(at_most), "exact-vs-at-least"),
        (str(subsets_with_sum(a[:-1], target)), "subset-count-off-by-one"),
        (str(2 ** len(a)), "subsets-vs-elements"),
        (str(subsets_with_sum(a, target) + 1), "skip-empty-subset"),
    ]


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(subsets_with_sum(v["a"], v["target"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should count the subsets of the values whose sum is exactly {v['target']}. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should count the subsets whose sum is exactly {v['target']}, but it prints "
        "the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Each mask from 0 to 2^{len(v['a'])} − 1 is one subset: bit i says whether a[i] is in it. "
        f"{answer} of them sum to {v['target']}."
    ),
    blanks=[
        Blank(
            MASKS,
            [
                (
                    lines(
                        "for mask in range(1 << (n - 1)):",
                        "for (int mask = 0; mask < (1 << (n - 1)); mask++) {",
                    ),
                    "subset-count-off-by-one",
                ),
                (
                    lines("for mask in range(n):", "for (int mask = 0; mask < n; mask++) {"),
                    "subsets-vs-elements",
                ),
                (
                    lines(
                        "for mask in range(2 * n):", "for (int mask = 0; mask < 2 * n; mask++) {"
                    ),
                    "subsets-vs-elements",
                ),
            ],
        ),
        Blank(
            BIT,
            [
                (lines("if mask & i:", "if ((mask & i) != 0) {"), "bit-test-wrong"),
                (
                    lines(
                        "if mask >> (i + 1) & 1:",
                        "if (mask >> (i + 1) & 1) {",
                        "if ((mask >> (i + 1) & 1) == 1) {",
                    ),
                    "bit-test-wrong",
                ),
                (lines("if mask >> i:", "if ((mask >> i) != 0) {"), "bit-test-missing-and"),
            ],
        ),
        Blank(
            ADD,
            [
                (lines("total += i", "total += i;"), "confuse-index-value"),
                (lines("total = a[i]", "total = a[i];"), "overwrite-not-accumulate"),
                (lines("total += 1", "total += 1;"), "count-not-sum"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "subset-too-few-masks",
            edit(
                MASKS,
                lines(
                    "for mask in range(1 << (n - 1)):",
                    "for (int mask = 0; mask < (1 << (n - 1)); mask++) {",
                ),
            ),
            "Loop over all 2^n masks: 1 << n",
            "With n elements there are 2^n subsets; 1 << (n − 1) never includes the last element.",
        ),
        Fix(
            "subset-wrong-bit-test",
            edit(BIT, lines("if mask & i:", "if ((mask & i) != 0) {")),
            "Test bit i with (mask >> i) & 1",
            "mask & i tests the bits of the number i, not bit number i.",
        ),
        Fix(
            "subset-add-index",
            edit(ADD, lines("total += i", "total += i;")),
            "Add the value a[i], not the index i",
            "The subset's sum is made of the chosen values.",
        ),
    ],
    decoys=[
        Decoy(
            edit(COUNT, lines("count += total", "count += total;")),
            "Add the subset's total to count",
            "count-vs-sum",
        ),
        Decoy(
            edit(MATCH, lines("if total >= target:", "if (total >= target) {")),
            "Count subsets with total >= target",
            "exact-vs-at-least",
        ),
        Decoy(
            edit(
                MASKS,
                lines(
                    "for mask in range(1, 1 << n):", "for (int mask = 1; mask < (1 << n); mask++) {"
                ),
            ),
            "Skip the empty subset (start at mask 1)",
            "skip-empty-subset",
        ),
        Decoy(
            edit(START, lines("count = 1", "int count = 1;")),
            "Start count at 1",
            "accumulator-init-one",
        ),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"subsets_with_sum": subsets_with_sum}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
