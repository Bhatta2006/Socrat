"""Top k with a min-heap of size k: the k-th largest value of a stream.

No fix items: a one-line max-heap swap exists in C++ and Java but not in Python, so the
defects would not mean the same thing in every language. Predict and fill items only.
"""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, lines

TRIM = lines("if len(heap) > k:", "if ((int)heap.size() > k) {", "if (heap.size() > k) {")
PUSH = lines("heapq.heappush(heap, x)", "heap.push(x);", "heap.add(x);")


def program(v: dict) -> dict[str, str]:
    values, k = ", ".join(map(str, v["a"])), v["k"]
    return {
        "python": (
            "import heapq\n"
            f"a = [{values}]\nk = {k}\n"
            "heap = []  # the k largest values so far; heap[0] is the smallest of them\n"
            "for x in a:\n"
            "    heapq.heappush(heap, x)\n"
            "    if len(heap) > k:\n"
            "        heapq.heappop(heap)\n"
            "print(heap[0])"
        ),
        "cpp": (
            f"vector<int> a = {{{values}}};\nint k = {k};\n"
            "priority_queue<int, vector<int>, greater<int>> heap;  // min-heap of the k largest\n"
            "for (int x : a) {\n"
            "    heap.push(x);\n"
            "    if ((int)heap.size() > k) {\n"
            "        heap.pop();\n"
            "    }\n"
            "}\n"
            'cout << heap.top() << "\\n";'
        ),
        "java": (
            f"int[] a = {{{values}}};\nint k = {k};\n"
            "PriorityQueue<Integer> heap = new PriorityQueue<>();  // min-heap of the k largest\n"
            "for (int x : a) {\n"
            "    heap.add(x);\n"
            "    if (heap.size() > k) {\n"
            "        heap.poll();\n"
            "    }\n"
            "}\n"
            "System.out.println(heap.peek());"
        ),
    }


def kth_largest(a: list[int], k: int) -> int:
    return sorted(a, reverse=True)[k - 1]


def sample(rng, params):
    n = rng.randint(*params["n"])
    a = rng.sample(range(params["value"][0], params["value"][1] + 1), n)  # distinct values
    return {"a": a, "k": rng.randint(2, min(params["k"][1], n - 2))}


def wrong(v):
    a, k = v["a"], v["k"]
    ordered = sorted(a)
    return [
        (str(ordered[k - 1]), "top-k-direction"),
        (str(max(a)), "top-k-returns-max"),
        (str(kth_largest(a, k - 1)), "heap-size-off-by-one"),
        (str(kth_largest(a, k + 1)), "heap-size-off-by-one"),
    ]


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(kth_largest(v["a"], v["k"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print the {v['k']}th largest value. Which line goes in the blank?"
    ),
    fix=lambda v: "",
    explain=lambda v, answer: (
        f"The min-heap keeps the {v['k']} largest values seen so far and drops the smallest "
        f"whenever it grows past {v['k']}; its top is the {v['k']}th largest, {answer}."
    ),
    blanks=[
        Blank(
            TRIM,
            [
                (
                    lines(
                        "if len(heap) >= k:",
                        "if ((int)heap.size() >= k) {",
                        "if (heap.size() >= k) {",
                    ),
                    "heap-size-off-by-one",
                ),
                (
                    lines(
                        "if len(heap) > k + 1:",
                        "if ((int)heap.size() > k + 1) {",
                        "if (heap.size() > k + 1) {",
                    ),
                    "heap-size-off-by-one",
                ),
                (
                    lines(
                        "if len(heap) > 1:", "if ((int)heap.size() > 1) {", "if (heap.size() > 1) {"
                    ),
                    "top-k-returns-max",
                ),
            ],
        ),
        Blank(
            PUSH,
            [
                (
                    lines("heapq.heappush(heap, -x)", "heap.push(-x);", "heap.add(-x);"),
                    "heap-negation-confusion",
                ),
                (
                    lines("heapq.heappush(heap, k)", "heap.push(k);", "heap.add(k);"),
                    "confuse-index-value",
                ),
                (
                    lines("heapq.heappush(heap, a[k])", "heap.push(a[k]);", "heap.add(a[k]);"),
                    "confuse-index-value",
                ),
            ],
        ),
    ],
)
HELPERS = {"kth_largest": kth_largest}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
