"""Frequency count: count each letter with an array of 26 counters, then use the counts."""

import string

from socrat.quiz.generate import kit
from socrat.quiz.generate.kit import Blank, Decoy, Fix, edit, lines

BUMP = lines("counts[ord(ch) - ord('a')] += 1", "counts[ch - 'a'] += 1;")
OUTPUT = lines(
    "print(max(counts))",
    'cout << *max_element(counts.begin(), counts.end()) << "\\n";',
    "System.out.println(Arrays.stream(counts).max().getAsInt());",
)


def program(v: dict) -> dict[str, str]:
    text = v["text"]
    return {
        "python": (
            f'text = "{text}"\n'
            "counts = [0] * 26  # one counter per letter a..z\n"
            "for ch in text:\n"
            "    counts[ord(ch) - ord('a')] += 1\n"
            "print(max(counts))"
        ),
        "cpp": (
            f'string text = "{text}";\n'
            "vector<int> counts(26, 0);  // one counter per letter a..z\n"
            "for (char ch : text) {\n"
            "    counts[ch - 'a'] += 1;\n"
            "}\n"
            'cout << *max_element(counts.begin(), counts.end()) << "\\n";'
        ),
        "java": (
            f'String text = "{text}";\n'
            "int[] counts = new int[26];  // one counter per letter a..z\n"
            "for (char ch : text.toCharArray()) {\n"
            "    counts[ch - 'a'] += 1;\n"
            "}\n"
            "System.out.println(Arrays.stream(counts).max().getAsInt());"
        ),
    }


def most_common(text: str) -> int:
    return max(text.count(c) for c in set(text))


def sample(rng, params):
    letters = string.ascii_lowercase[: rng.randint(*params["alphabet"])]
    while True:
        text = "".join(rng.choice(letters) for _ in range(rng.randint(*params["length"])))
        if text[0] != "a" and most_common(text) > 1:
            return {"text": text}


def wrong(v):
    text = v["text"]
    return [
        (str(len(set(text))), "distinct-vs-frequency"),
        (str(len(text)), "count-all-not-each"),
        (str(text.count(text[0])), "first-char-only"),
        (str(most_common(text) - 1), "off-by-one-output"),
        (str(most_common(text) + 1), "off-by-one-output"),
    ]


SPEC = kit.Spec(
    sample=sample,
    program=program,
    answer=lambda v: str(most_common(v["text"])),
    wrong=wrong,
    predict="What does this code print?",
    fill=lambda v: (
        f'This code should print how many times the most common letter appears in "{v["text"]}". '
        "Which line goes in the blank?"
    ),
    fix=lambda v: (
        f'This code should print how many times the most common letter appears in "{v["text"]}", '
        "but it prints the wrong answer. Which one-line change fixes it?"
    ),
    explain=lambda v, answer: (
        f"Each letter has its own counter; after the loop the largest counter is {answer}."
    ),
    blanks=[
        Blank(
            BUMP,
            [
                (
                    lines("counts[ord(ch) - ord('a')] = 1", "counts[ch - 'a'] = 1;"),
                    "overwrite-not-accumulate",
                ),
                (lines("counts[0] += 1", "counts[0] += 1;"), "frequency-single-bucket"),
                (
                    lines("counts[ord(ch) - ord('a')] += 2", "counts[ch - 'a'] += 2;"),
                    "double-count",
                ),
            ],
        ),
    ],
    fixes=[
        Fix(
            "freq-overwrite",
            edit(BUMP, lines("counts[ord(ch) - ord('a')] = 1", "counts[ch - 'a'] = 1;")),
            "Add 1 to the letter's counter instead of setting it to 1",
            "Setting the counter to 1 forgets earlier copies of the letter.",
        ),
        Fix(
            "freq-single-bucket",
            edit(BUMP, lines("counts[0] += 1", "counts[0] += 1;")),
            "Use the letter's own counter, not counts[0]",
            "counts[0] belongs to 'a'; every letter needs its own slot.",
        ),
    ],
    decoys=[
        Decoy(
            edit(
                OUTPUT,
                lines(
                    "print(len(text))",
                    'cout << text.size() << "\\n";',
                    "System.out.println(text.length());",
                ),
            ),
            "Print the length of the text",
            "count-all-not-each",
        ),
        Decoy(
            edit(
                OUTPUT,
                lines(
                    "print(counts[0])",
                    'cout << counts[0] << "\\n";',
                    "System.out.println(counts[0]);",
                ),
            ),
            "Print the counter for 'a'",
            "frequency-single-bucket",
        ),
        Decoy(
            edit(
                OUTPUT,
                lines(
                    "print(max(counts) - 1)",
                    'cout << *max_element(counts.begin(), counts.end()) - 1 << "\\n";',
                    "System.out.println(Arrays.stream(counts).max().getAsInt() - 1);",
                ),
            ),
            "Print one less than the largest counter",
            "off-by-one-output",
        ),
    ],
)
DEFECTS = SPEC.defects
HELPERS = {"most_common": most_common}


def generate(rng, params):
    return kit.generate(SPEC, rng, params)
