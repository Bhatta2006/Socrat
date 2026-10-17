"""Difference array: many range additions, then one prefix-sum pass."""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

START = lines("diff[l] += x", "diff[l] += x;")
END = lines("diff[r + 1] -= x", "diff[r + 1] -= x;")
RUN = lines("running += diff[i]", "running += diff[i];")
RUN_INIT = lines("running = 0", "int running = 0;")


def program(v: dict) -> dict[str, str]:
    n, updates = v["n"], v["updates"]
    py_updates = ", ".join(f"({lo}, {hi}, {x})" for lo, hi, x in updates)
    c_updates = ", ".join(f"{{{lo}, {hi}, {x}}}" for lo, hi, x in updates)
    loop = (
        "    int l = u[0], r = u[1], x = u[2];\n"
        "    diff[l] += x;\n"
        "    diff[r + 1] -= x;\n"
        "}\n"
        "int running = 0;\n"
        "for (int i = 0; i < n; i++) {\n"
        "    running += diff[i];\n"
    )
    return {
        "python": (
            f"n = {n}\nupdates = [{py_updates}]  # (l, r, x): add x to positions l..r\n"
            "diff = [0] * (n + 1)\n"
            "for l, r, x in updates:\n"
            "    diff[l] += x\n"
            "    diff[r + 1] -= x\n"
            "running = 0\n"
            "result = []\n"
            "for i in range(n):\n"
            "    running += diff[i]\n"
            "    result.append(running)\n"
            "print(*result)"
        ),
        "cpp": (
            f"int n = {n};\nvector<array<int, 3>> updates = {{{c_updates}}};  // add x to l..r\n"
            "vector<int> diff(n + 1, 0);\n"
            "for (auto& u : updates) {\n" + loop + '    cout << (i ? " " : "") << running;\n}\n'
            'cout << "\\n";'
        ),
        "java": (
            f"int n = {n};\nint[][] updates = {{{c_updates}}};  // add x to l..r\n"
            "int[] diff = new int[n + 1];\n"
            "for (int[] u : updates) {\n"
            + loop
            + '    System.out.print((i > 0 ? " " : "") + running);\n}\n'
            "System.out.println();"
        ),
    }


def apply(n: int, updates: list, end_shift: int = 1, sign: int = -1, prefix: bool = True) -> str:
    """Brute force (and the classic slips, for distractors)."""
    if prefix and end_shift == 1 and sign == -1:
        values = [0] * n
        for lo, hi, x in updates:
            for i in range(lo, hi + 1):
                values[i] += x
        return " ".join(map(str, values))
    diff = [0] * (n + 1)
    for lo, hi, x in updates:
        diff[lo] += x
        diff[min(hi + end_shift, n)] += sign * x
    if not prefix:
        return " ".join(map(str, diff[:n]))
    out, running = [], 0
    for i in range(n):
        running += diff[i]
        out.append(running)
    return " ".join(map(str, out))


def sample(rng, params):
    n = rng.randint(*params["n"])
    updates = []
    for _ in range(rng.randint(*params["updates"])):
        lo = rng.randrange(n)
        updates.append((lo, rng.randrange(lo, n), rng.randint(*params["value"])))
    return {"n": n, "updates": updates}


def wrong(v):
    n, updates = v["n"], v["updates"]
    return [
        (apply(n, updates, prefix=False), "missing-prefix-sum"),
        (apply(n, updates, end_shift=0), "diff-end-off-by-one"),
        (apply(n, updates, sign=1), "diff-sign-error"),
        (apply(n, updates, end_shift=n), "diff-missing-end"),
    ]


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: apply(v["n"], v["updates"]),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        "This code should add x to every position from l to r for each update, then print the "
        "array. Which line goes in the blank?"
    ),
    fix=lambda v: (
        "This code should add x to every position from l to r for each update, then print the "
        "array, but the output is wrong. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Mark +x at l and −x just after r, then a running total turns the marks into values: {answer}."
    ),
    blanks=[
        Blank(
            END,
            [
                (lines("diff[r] -= x", "diff[r] -= x;"), "diff-end-off-by-one"),
                (lines("diff[r + 1] += x", "diff[r + 1] += x;"), "diff-sign-error"),
                (lines("diff[l + 1] -= x", "diff[l + 1] -= x;"), "diff-wrong-endpoint"),
            ],
        ),
        Blank(
            START,
            [
                (lines("diff[l] = x", "diff[l] = x;"), "overwrite-not-accumulate"),
                (lines("diff[l] += 1", "diff[l] += 1;"), "count-not-sum"),
                (lines("diff[r] += x", "diff[r] += x;"), "diff-wrong-endpoint"),
            ],
        ),
        Blank(
            RUN,
            [
                (lines("running = diff[i]", "running = diff[i];"), "missing-prefix-sum"),
                (lines("running += diff[i + 1]", "running += diff[i + 1];"), "diff-end-off-by-one"),
                (lines("running += i", "running += i;"), "confuse-index-value"),
            ],
        ),
    ],
    fixes=[
        Fix(
            "diff-end-off-by-one",
            edit(END, lines("diff[r] -= x", "diff[r] -= x;")),
            "Cancel x just after the range, at r + 1",
            "Position r is still inside the range, so the cancel mark goes at r + 1.",
        ),
        Fix(
            "diff-sign-error",
            edit(END, lines("diff[r + 1] += x", "diff[r + 1] += x;")),
            "Subtract x at r + 1",
            "The mark after the range must cancel the addition, so it is −x.",
        ),
        Fix(
            "diff-missing-prefix",
            edit(RUN, lines("running = diff[i]", "running = diff[i];")),
            "Add diff[i] to the running total",
            "The marks only become values through a running (prefix) sum.",
        ),
    ],
    decoys=[
        Decoy(
            edit(START, lines("diff[l] += 1", "diff[l] += 1;")),
            "Add 1 at l instead of x",
            "count-not-sum",
        ),
        Decoy(
            edit(RUN, lines("running += i", "running += i;")),
            "Add the index to the running total",
            "confuse-index-value",
        ),
        Decoy(
            edit(END, lines("diff[l + 1] -= x", "diff[l + 1] -= x;")),
            "Cancel x at l + 1",
            "diff-wrong-endpoint",
        ),
        Decoy(
            edit(RUN_INIT, lines("running = 1", "int running = 1;")),
            "Start the running total at 1",
            "accumulator-init-one",
        ),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"apply_updates": apply}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
