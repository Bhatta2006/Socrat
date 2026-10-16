"""Binary search boundary bugs: find the one-line fix (band 4, mutation generator).

A correct lower-bound search gets one defect from the catalogue. The options are one-line
edits to the buggy code: the fix that undoes the defect, and other plausible edits that do
not fix it on this input. The generator checks this in Python; the verifier re-checks in
every language and rejects the item if any other option also fixes it.
"""

from socrat.quiz.generate import mutate
from socrat.quiz.generate.framework import Draft, Option, run_python

PROMPT = (
    "This code should print the first index whose value is at least x, or the array "
    "length if there is none. For these values it prints the wrong answer. "
    "Which one-line change fixes it?"
)

COMPARE = {
    "python": ("if a[mid] < x:", "if a[mid] <= x:"),
    "cpp": ("if (a[mid] < x) {", "if (a[mid] <= x) {"),
    "java": ("if (a[mid] < x) {", "if (a[mid] <= x) {"),
}
HIGH = {
    "python": ("lo, hi = 0, len(a)", "lo, hi = 0, len(a) - 1"),
    "cpp": ("int lo = 0, hi = (int)a.size();", "int lo = 0, hi = (int)a.size() - 1;"),
    "java": ("int lo = 0, hi = a.length;", "int lo = 0, hi = a.length - 1;"),
}
LEFT = {
    "python": ("hi = mid", "hi = mid - 1"),
    "cpp": ("hi = mid;", "hi = mid - 1;"),
    "java": ("hi = mid;", "hi = mid - 1;"),
}
PLUS_ONE = {
    "python": ("print(lo)", "print(lo + 1)"),
    "cpp": ('cout << lo << "\\n";', 'cout << lo + 1 << "\\n";'),
    "java": ("System.out.println(lo);", "System.out.println(lo + 1);"),
}
PRINT_HI = {
    "python": ("print(lo)", "print(hi)"),
    "cpp": ('cout << lo << "\\n";', 'cout << hi << "\\n";'),
    "java": ("System.out.println(lo);", "System.out.println(hi);"),
}

# Defect id -> (edit, text of the fix that undoes it, explanation).
DEFECTS = {
    "bs-inclusive-compare": (
        COMPARE,
        "Compare with a[mid] < x",
        "With <= the search also moves past values equal to x and finds the upper bound.",
    ),
    "bs-closed-hi": (
        HIGH,
        "Start hi at the array length",
        "The search is half-open: hi must start one past the last index so the length "
        "can be returned when every value is smaller than x.",
    ),
    "bs-skip-mid": (
        LEFT,
        "Move left with hi = mid",
        "When a[mid] >= x, mid may be the answer, so hi = mid keeps it in range.",
    ),
}
# Edits that look like fixes but are not: (edit, text, misconception).
DECOYS = [
    (COMPARE, "Compare with a[mid] <= x", "lower-vs-upper-bound"),
    (HIGH, "Start hi at the last index", "half-open-bound"),
    (LEFT, "Move left with hi = mid - 1", "exclude-candidate-mid"),
    (PLUS_ONE, "Print lo + 1 instead of lo", "off-by-one-output"),
    (PRINT_HI, "Print hi instead of lo", "lo-hi-confusion"),
]


def snippets(a: list[int], x: int) -> dict[str, str]:
    values = ", ".join(map(str, a))
    return {
        "python": (
            f"a = [{values}]\n"
            f"x = {x}\n"
            "lo, hi = 0, len(a)\n"
            "while lo < hi:\n"
            "    mid = (lo + hi) // 2\n"
            "    if a[mid] < x:\n"
            "        lo = mid + 1\n"
            "    else:\n"
            "        hi = mid\n"
            "print(lo)"
        ),
        "cpp": (
            f"vector<int> a = {{{values}}};\n"
            f"int x = {x};\n"
            "int lo = 0, hi = (int)a.size();\n"
            "while (lo < hi) {\n"
            "    int mid = (lo + hi) / 2;\n"
            "    if (a[mid] < x) {\n"
            "        lo = mid + 1;\n"
            "    } else {\n"
            "        hi = mid;\n"
            "    }\n"
            "}\n"
            'cout << lo << "\\n";'
        ),
        "java": (
            f"int[] a = {{{values}}};\n"
            f"int x = {x};\n"
            "int lo = 0, hi = a.length;\n"
            "while (lo < hi) {\n"
            "    int mid = (lo + hi) / 2;\n"
            "    if (a[mid] < x) {\n"
            "        lo = mid + 1;\n"
            "    } else {\n"
            "        hi = mid;\n"
            "    }\n"
            "}\n"
            "System.out.println(lo);"
        ),
    }


def generate(rng, params):
    low_n, high_n = params["n"]
    low_v, high_v = params["value"]
    names = sorted(DEFECTS)
    while True:
        a = sorted(rng.randint(low_v, high_v) for _ in range(rng.randint(low_n, high_n)))
        x = rng.choice([*a, *a, rng.randint(low_v, high_v + 2)])
        answer = str(sum(1 for v in a if v < x))
        defect = rng.choice(names)
        edit, fix_text, why = DEFECTS[defect]
        correct = snippets(a, x)
        buggy = mutate.apply(correct, edit)
        if run_python(buggy["python"]) == answer:
            continue  # the defect must be visible on this input
        decoys = []
        for decoy, text, tag in DECOYS:
            if not mutate.applicable(buggy, decoy):
                continue
            changed = mutate.apply(buggy, decoy)
            if run_python(changed["python"]) != answer:
                decoys.append(Option(text=text, misconception=tag, variant=changed))
        if len(decoys) >= 3:
            break
    rng.shuffle(decoys)
    fix = Option(text=fix_text, variant=mutate.apply(buggy, mutate.reverse(edit)))
    return Draft(
        prompt=PROMPT,
        code=buggy,
        options=[fix, *decoys[:3]],
        answer=0,
        explanation=f"{why} The correct answer here is {answer}.",
        band=4,
        values={"a": a, "x": x},
    )
