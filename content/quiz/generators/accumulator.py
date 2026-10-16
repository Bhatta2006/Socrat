"""For-loop accumulator: choose the code for the blank (band 3).

The loop sums lo, lo + step, ... up to n. The blank is the update, the starting value or
the loop bound. Distractors are the classic slips: overwrite instead of add, count instead
of sum, start at 1, stop one early. Distractors that happen to print the right total on
these numbers are dropped, so exactly one option is correct.
"""

from socrat.quiz.generate.framework import BLANK, Draft, Option, run_python


def snippets(lo: int, n: int, step: int, blank: str) -> dict[str, str]:
    init = BLANK if blank == "init" else "0"
    py_range = f"range({lo}, n + 1)" if step == 1 else f"range({lo}, n + 1, {step})"
    py_bound = f"range({lo}, {BLANK})" if step == 1 else f"range({lo}, {BLANK}, {step})"
    c_step = "i++" if step == 1 else f"i += {step}"
    c_cond = BLANK if blank == "bound" else "i <= n"
    py_update = BLANK if blank == "update" else "total += i"
    c_update = BLANK if blank == "update" else "total += i;"
    return {
        "python": (
            f"n = {n}\n"
            f"total = {init}\n"
            f"for i in {py_bound if blank == 'bound' else py_range}:\n"
            f"    {py_update}\n"
            "print(total)"
        ),
        "cpp": (
            f"int n = {n};\n"
            f"int total = {init};\n"
            f"for (int i = {lo}; {c_cond}; {c_step}) {{\n"
            f"    {c_update}\n"
            "}\n"
            'cout << total << "\\n";'
        ),
        "java": (
            f"int n = {n};\n"
            f"int total = {init};\n"
            f"for (int i = {lo}; {c_cond}; {c_step}) {{\n"
            f"    {c_update}\n"
            "}\n"
            "System.out.println(total);"
        ),
    }


def choices(blank: str, lo: int) -> list[tuple[dict[str, str], str | None]]:
    """(fill per language, misconception); the first is correct."""

    def same(py: str, c: str | None = None) -> dict[str, str]:
        return {"python": py, "cpp": c or py, "java": c or py}

    if blank == "update":
        return [
            (same("total += i", "total += i;"), None),
            (same("total = i", "total = i;"), "overwrite-not-accumulate"),
            (same("total += 1", "total += 1;"), "count-not-sum"),
            (same("total += n", "total += n;"), "bound-instead-of-variable"),
            (same("total *= i", "total *= i;"), "product-not-sum"),
        ]
    if blank == "init":
        return [
            (same("0"), None),
            (same("1"), "accumulator-init-one"),
            (same(str(lo)), "accumulator-starts-at-first"),
            (same("n"), "accumulator-starts-at-bound"),
        ]
    return [
        ({"python": "n + 1", "cpp": "i <= n", "java": "i <= n"}, None),
        ({"python": "n", "cpp": "i < n", "java": "i < n"}, "loop-bound-off-by-one"),
        ({"python": "n - 1", "cpp": "i < n - 1", "java": "i < n - 1"}, "loop-bound-off-by-one"),
        ({"python": "n + 2", "cpp": "i <= n + 1", "java": "i <= n + 1"}, "loop-bound-off-by-one"),
    ]


def describe(lo: int, step: int) -> str:
    if step == 1:
        return f"the whole numbers from {lo} to n"
    return f"the numbers {lo}, {lo + step}, {lo + 2 * step}, and so on up to n"


def generate(rng, params):
    low_n, high_n = params["n"]
    while True:
        blank = rng.choice(["update", "init", "bound"])
        lo = rng.randint(*params["start"])
        step = rng.randint(*params["step"])
        n = rng.randint(max(low_n, lo + 2 * step), high_n)
        answer = str(sum(range(lo, n + 1, step)))
        code = snippets(lo, n, step, blank)
        options: list[Option] = []
        for i, (fill, tag) in enumerate(choices(blank, lo)):
            if fill["python"] in {o.text for o in options}:
                continue
            printed = run_python(code["python"].replace(BLANK, fill["python"]))
            if (printed == answer) != (i == 0):
                continue  # a distractor that is right here, or a broken correct option
            options.append(Option(text=fill["python"], misconception=tag, fill=fill))
        if options and options[0].misconception is None and len(options) >= 4:
            break
    distractors = options[1:]
    rng.shuffle(distractors)
    return Draft(
        prompt=f"This code should print the sum of {describe(lo, step)}. "
        "Which code goes in the blank?",
        code=code,
        options=[options[0], *distractors[:3]],
        answer=0,
        explanation=f"The total must start at 0 and add every i the loop visits; it prints {answer}.",
        band=3,
        values={"lo": lo, "n": n, "step": step},
    )
