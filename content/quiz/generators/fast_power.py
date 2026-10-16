"""Fast power: base^exp mod m by repeated squaring."""

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

ODD = lines("if e % 2 == 1:", "if (e % 2 == 1) {")
MULTIPLY = lines("result = result * b % mod", "result = result * b % mod;")
SQUARE = lines("b = b * b % mod", "b = b * b % mod;")
START = lines("result = 1", "long long result = 1;", "long result = 1;")
HALVE = lines("e //= 2", "e /= 2;")
OUTPUT = lines("print(result)", 'cout << result << "\\n";', "System.out.println(result);")


def program(v: dict) -> dict[str, str]:
    base, exp, mod = v["base"], v["exp"], v["mod"]
    loop = (
        "while (e > 0) {\n"
        "    if (e % 2 == 1) {\n"
        "        result = result * b % mod;\n"
        "    }\n"
        "    b = b * b % mod;\n"
        "    e /= 2;\n"
        "}\n"
    )
    return {
        "python": (
            f"base, exp, mod = {base}, {exp}, {mod}\n"
            "result = 1\n"
            "b = base % mod  # base^1, then base^2, base^4, ...\n"
            "e = exp\n"
            "while e > 0:\n"
            "    if e % 2 == 1:\n"
            "        result = result * b % mod\n"
            "    b = b * b % mod\n"
            "    e //= 2\n"
            "print(result)"
        ),
        "cpp": (
            f"long long base = {base}, exp = {exp}, mod = {mod};\n"
            "long long result = 1;\n"
            "long long b = base % mod;  // base^1, then base^2, base^4, ...\n"
            "long long e = exp;\n" + loop + 'cout << result << "\\n";'
        ),
        "java": (
            f"long base = {base}, exp = {exp}, mod = {mod};\n"
            "long result = 1;\n"
            "long b = base % mod;  // base^1, then base^2, base^4, ...\n"
            "long e = exp;\n" + loop + "System.out.println(result);"
        ),
    }


def sample(rng, params):
    return {
        "base": rng.randint(*params["base"]),
        "exp": rng.randint(*params["exp"]),
        "mod": rng.choice(params["mod"]),
    }


def wrong(v):
    base, exp, mod = v["base"], v["exp"], v["mod"]
    return [
        (str(pow(base, exp - 1, mod)), "off-by-one-output"),
        (str(base * exp % mod), "power-as-multiply"),
        (str(pow(base, exp // 2, mod)), "fast-power-step"),
        (str(pow(base, exp + 1, mod)), "off-by-one-output"),
        (str(pow(base, exp, mod + 1)), "mod-wrong-modulus"),
    ]


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(pow(v["base"], v["exp"], v["mod"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f"This code should print {v['base']}^{v['exp']} mod {v['mod']} using repeated squaring. "
        "Which line goes in the blank?"
    ),
    fix=lambda v: (
        f"This code should print {v['base']}^{v['exp']} mod {v['mod']}, but it prints the wrong "
        "answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Write {v['exp']} in binary; multiply in base^(2^k) for every 1 bit, squaring b each "
        f"step and reducing mod {v['mod']}: {answer}."
    ),
    blanks=[
        Blank(
            ODD,
            [
                (lines("if e % 2 == 0:", "if (e % 2 == 0) {"), "fast-power-parity"),
                (lines("if b % 2 == 1:", "if (b % 2 == 1) {"), "fast-power-wrong-variable"),
                (
                    lines("if result % 2 == 1:", "if (result % 2 == 1) {"),
                    "fast-power-wrong-variable",
                ),
            ],
        ),
        Blank(
            MULTIPLY,
            [
                (
                    lines("result = result * base % mod", "result = result * base % mod;"),
                    "fast-power-base-not-square",
                ),
                (lines("result = b % mod", "result = b % mod;"), "overwrite-not-accumulate"),
                (
                    lines("result = (result + b) % mod", "result = (result + b) % mod;"),
                    "sum-not-product",
                ),
            ],
        ),
        Blank(
            SQUARE,
            [
                (lines("b = b * 2 % mod", "b = b * 2 % mod;"), "square-vs-double"),
                (lines("b = b * base % mod", "b = b * base % mod;"), "fast-power-base-not-square"),
                (
                    lines("b = result * result % mod", "b = result * result % mod;"),
                    "fast-power-wrong-variable",
                ),
            ],
        ),
    ],
    fixes=[
        Fix(
            "pow-parity",
            edit(ODD, lines("if e % 2 == 0:", "if (e % 2 == 0) {")),
            "Multiply in b when the lowest bit of e is 1",
            "Only the 1 bits of the exponent contribute a factor.",
        ),
        Fix(
            "pow-base-not-square",
            edit(MULTIPLY, lines("result = result * base % mod", "result = result * base % mod;")),
            "Multiply result by b, the current power, not by base",
            "b holds base^(2^k) for the bit being read; base is only right for the lowest bit.",
        ),
        Fix(
            "pow-double-not-square",
            edit(SQUARE, lines("b = b * 2 % mod", "b = b * 2 % mod;")),
            "Square b each step (b * b)",
            "Moving to the next bit squares the power: base^(2^k) becomes base^(2^(k+1)).",
        ),
    ],
    decoys=[
        Decoy(
            edit(START, lines("result = 0", "long long result = 0;", "long result = 0;")),
            "Start result at 0",
            "product-init-zero",
        ),
        Decoy(
            edit(
                OUTPUT,
                lines(
                    "print(result % mod)",
                    'cout << result % mod << "\\n";',
                    "System.out.println(result % mod);",
                ),
            ),
            "Reduce mod once more before printing",
            "mod-only-at-end",
        ),
        Decoy(
            edit(HALVE, lines("e -= 1", "e -= 1;")), "Decrease e by 1 each step", "fast-power-step"
        ),
        Decoy(
            edit(SQUARE, lines("b = b * base % mod", "b = b * base % mod;")),
            "Multiply b by base each step",
            "fast-power-base-not-square",
        ),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"pow": pow}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
