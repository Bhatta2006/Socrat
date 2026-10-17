"""Unbounded coin change: fewest coins that make an amount, or -1 when impossible."""

from collections import deque

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

TAKE = lines("dp[a] = dp[a - c] + 1", "dp[a] = dp[a - c] + 1;")
CHECK = lines(
    "if c <= a and dp[a - c] + 1 < dp[a]:",
    "if (c <= a && dp[a - c] + 1 < dp[a]) {",
)
LOOP = lines(
    "for a in range(1, amount + 1):",
    "for (int a = 1; a <= amount; a++) {",
)
OUTPUT = lines(
    "print(dp[amount] if dp[amount] < INF else -1)",
    'cout << (dp[amount] < INF ? dp[amount] : -1) << "\\n";',
    "System.out.println(dp[amount] < INF ? dp[amount] : -1);",
)


def program(v: dict) -> dict[str, str]:
    coins, amount = ", ".join(map(str, v["coins"])), v["amount"]
    loops = (
        "for (int a = 1; a <= amount; a++) {\n"
        "    for (int c : coins) {\n"
        "        if (c <= a && dp[a - c] + 1 < dp[a]) {\n"
        "            dp[a] = dp[a - c] + 1;\n"
        "        }\n"
        "    }\n"
        "}\n"
    )
    return {
        "python": (
            f"coins = [{coins}]\namount = {amount}\n"
            "INF = 10**9\n"
            "dp = [0] + [INF] * amount  # dp[a] = fewest coins that make a\n"
            "for a in range(1, amount + 1):\n"
            "    for c in coins:\n"
            "        if c <= a and dp[a - c] + 1 < dp[a]:\n"
            "            dp[a] = dp[a - c] + 1\n"
            "print(dp[amount] if dp[amount] < INF else -1)"
        ),
        "cpp": (
            f"vector<int> coins = {{{coins}}};\nint amount = {amount};\n"
            "const int INF = 1000000000;\n"
            "vector<int> dp(amount + 1, INF);  // dp[a] = fewest coins that make a\n"
            "dp[0] = 0;\n" + loops + 'cout << (dp[amount] < INF ? dp[amount] : -1) << "\\n";'
        ),
        "java": (
            f"int[] coins = {{{coins}}};\nint amount = {amount};\n"
            "final int INF = 1000000000;\n"
            "int[] dp = new int[amount + 1];  // dp[a] = fewest coins that make a\n"
            "Arrays.fill(dp, INF);\n"
            "dp[0] = 0;\n" + loops + "System.out.println(dp[amount] < INF ? dp[amount] : -1);"
        ),
    }


def fewest(coins: list[int], amount: int) -> int:
    """Breadth-first search over amounts: an independent check of the DP."""
    seen = {0}
    queue = deque([(0, 0)])
    while queue:
        total, used = queue.popleft()
        if total == amount:
            return used
        for c in coins:
            if total + c <= amount and total + c not in seen:
                seen.add(total + c)
                queue.append((total + c, used + 1))
    return -1


def greedy(coins: list[int], amount: int) -> int:
    used = 0
    for c in sorted(coins, reverse=True):
        used += amount // c
        amount %= c
    return used if amount == 0 else -1


def ways(coins: list[int], amount: int) -> int:
    count = [1] + [0] * amount
    for c in coins:
        for a in range(c, amount + 1):
            count[a] += count[a - c]
    return count[amount]


def sample(rng, params):
    while True:
        coins = sorted(rng.sample(range(1, params["coin"][1] + 1), rng.randint(*params["kinds"])))
        amount = rng.randint(*params["amount"])
        if fewest(coins, amount) != -1 or rng.random() < 0.2:
            return {"coins": coins, "amount": amount}


def wrong(v):
    coins, amount = v["coins"], v["amount"]
    best = fewest(coins, amount)
    found = [
        (str(greedy(coins, amount)), "greedy-coin-change"),
        (str(ways(coins, amount)), "count-vs-min"),
        (str(best + 1), "off-by-one-output"),
    ]
    if best == -1:
        found.append((str(10**9), "missing-unreachable-check"))  # the raw sentinel
    else:
        found.append((str(best - 1), "off-by-one-output"))
    return found


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(fewest(v["coins"], v["amount"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print the fewest coins (any coin may repeat) that make {v['amount']}, "
        "or -1 if no mix works. Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should print the fewest coins that make {v['amount']}, or -1, but it prints "
        "the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"dp[a] is the fewest coins for amount a: try each coin c as the last coin, dp[a - c] + 1. "
        f"For {v['amount']} that gives {answer}."
    ),
    blanks=[
        Blank(
            TAKE,
            [
                (lines("dp[a] = dp[a - c]", "dp[a] = dp[a - c];"), "dp-missing-plus-one"),
                (lines("dp[a] = dp[a - 1] + 1", "dp[a] = dp[a - 1] + 1;"), "dp-wrong-subproblem"),
                (lines("dp[a] = dp[a - c] + c", "dp[a] = dp[a - c] + c;"), "count-vs-sum"),
            ],
        ),
        Blank(
            CHECK,
            [
                (
                    lines(
                        "if c < a and dp[a - c] + 1 < dp[a]:",
                        "if (c < a && dp[a - c] + 1 < dp[a]) {",
                    ),
                    "coin-equals-amount",
                ),
                (lines("if c <= a:", "if (c <= a) {"), "dp-overwrite-min"),
                (
                    lines(
                        "if c <= a and dp[a - c] + 1 > dp[a]:",
                        "if (c <= a && dp[a - c] + 1 > dp[a]) {",
                    ),
                    "min-vs-max",
                ),
            ],
        ),
    ],
    fixes=[
        Fix(
            "dp-missing-plus-one",
            edit(TAKE, lines("dp[a] = dp[a - c]", "dp[a] = dp[a - c];")),
            "Add 1 for the coin just used",
            "Taking coin c costs one coin on top of the best way to make a - c.",
        ),
        Fix(
            "dp-coin-boundary",
            edit(
                CHECK,
                lines(
                    "if c < a and dp[a - c] + 1 < dp[a]:", "if (c < a && dp[a - c] + 1 < dp[a]) {"
                ),
            ),
            "Allow a coin equal to the amount (c <= a)",
            "A coin worth exactly a makes a with one coin, from dp[0] = 0.",
        ),
        Fix(
            "dp-wrong-subproblem",
            edit(TAKE, lines("dp[a] = dp[a - 1] + 1", "dp[a] = dp[a - 1] + 1;")),
            "Build on dp[a - c], the amount left after coin c",
            "After using coin c, what remains to make is a - c, not a - 1.",
        ),
    ],
    decoys=[
        Decoy(
            edit(
                OUTPUT,
                lines(
                    "print(dp[amount])",
                    'cout << dp[amount] << "\\n";',
                    "System.out.println(dp[amount]);",
                ),
            ),
            "Print dp[amount] without the -1 check",
            "missing-unreachable-check",
        ),
        Decoy(
            edit(LOOP, lines("for a in range(1, amount):", "for (int a = 1; a < amount; a++) {")),
            "Stop the amount loop before amount",
            "loop-bound-off-by-one",
        ),
        Decoy(
            edit(TAKE, lines("dp[a] = dp[a - c] + c", "dp[a] = dp[a - c] + c;")),
            "Add the coin's value instead of 1",
            "count-vs-sum",
        ),
        Decoy(
            edit(CHECK, lines("if c <= a:", "if (c <= a) {")),
            "Take every coin that fits",
            "dp-overwrite-min",
        ),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"fewest": fewest}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
