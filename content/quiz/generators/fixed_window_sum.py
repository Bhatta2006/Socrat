"""Fixed-size sliding window: predict the largest sum of k consecutive numbers (band 2).

Distractors follow the family's rules: windows of size k - 1 or k + 1, the first window
only, and the largest single element.
"""

from socrat.quiz.generate.framework import Draft, Option

PROMPT = "What does this code print?"


def snippets(a: list[int], k: int) -> dict[str, str]:
    values = ", ".join(map(str, a))
    return {
        "python": (
            f"a = [{values}]\n"
            f"k = {k}\n"
            "window = sum(a[:k])\n"
            "best = window\n"
            "for i in range(k, len(a)):\n"
            "    window += a[i] - a[i - k]\n"
            "    best = max(best, window)\n"
            "print(best)"
        ),
        "cpp": (
            f"vector<int> a = {{{values}}};\n"
            f"int k = {k};\n"
            "int window = 0;\n"
            "for (int i = 0; i < k; i++) window += a[i];\n"
            "int best = window;\n"
            "for (int i = k; i < (int)a.size(); i++) {\n"
            "    window += a[i] - a[i - k];\n"
            "    best = max(best, window);\n"
            "}\n"
            'cout << best << "\\n";'
        ),
        "java": (
            f"int[] a = {{{values}}};\n"
            f"int k = {k};\n"
            "int window = 0;\n"
            "for (int i = 0; i < k; i++) window += a[i];\n"
            "int best = window;\n"
            "for (int i = k; i < a.length; i++) {\n"
            "    window += a[i] - a[i - k];\n"
            "    best = Math.max(best, window);\n"
            "}\n"
            "System.out.println(best);"
        ),
    }


def best(a: list[int], size: int) -> int:
    return max(sum(a[i : i + size]) for i in range(len(a) - size + 1))


def generate(rng, params):
    low_n, high_n = params["n"]
    low_v, high_v = params["value"]
    low_k, high_k = params["k"]
    while True:
        a = [rng.randint(low_v, high_v) for _ in range(rng.randint(low_n, high_n))]
        k = rng.randint(low_k, high_k)
        answer = best(a, k)
        rules = [
            (best(a, k - 1), "window-off-by-one"),
            (sum(a[:k]), "stop-after-first"),
            (max(a), "confuse-index-value"),
            (best(a, k + 1), "window-off-by-one"),
        ]
        distractors: list[tuple[int, str]] = []
        for value, tag in rules:
            if value != answer and value not in [v for v, _ in distractors]:
                distractors.append((value, tag))
        if len(distractors) >= 3:
            break
    options = [Option(text=str(answer))] + [
        Option(text=str(v), misconception=tag) for v, tag in distractors[:3]
    ]
    sums = [sum(a[i : i + k]) for i in range(len(a) - k + 1)]
    return Draft(
        prompt=PROMPT,
        code=snippets(a, k),
        options=options,
        answer=0,
        explanation=(
            f"The windows of {k} numbers sum to {', '.join(map(str, sums))}; "
            f"the largest is {answer}."
        ),
        band=2,
        values={"a": a, "k": k},
    )
