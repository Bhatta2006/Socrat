"""Trace items: state after each step of an instrumented reference (content.md §8.6).

A generator's shown snippet prints one line of state per step in every language; the
verifier compares line ``trace_line`` with the reference. ``states`` records the same
states from a Python callable so the generator can build options from neighbouring steps.
"""

from collections.abc import Callable, Iterable


def states(steps: Callable[[], Iterable[tuple]]) -> list[str]:
    """Each yielded state tuple as a line, formatted as the snippets print it."""
    return [" ".join(str(v) for v in state) for state in steps()]


def options(
    lines: list[str], step: int, extra: list[tuple[str, str]]
) -> list[tuple[str, str | None]]:
    """The state at ``step`` (1-based) first, then neighbouring steps and extra distractors.

    ``extra`` holds (text, misconception) pairs. Neighbouring steps carry ``trace-step-slip``.
    Duplicates of the answer are dropped.
    """
    answer = lines[step - 1]
    found: list[tuple[str, str | None]] = [(answer, None)]
    for neighbour in (step - 2, step):
        if 0 <= neighbour < len(lines) and lines[neighbour] not in {t for t, _ in found}:
            found.append((lines[neighbour], "trace-step-slip"))
    for text, tag in extra:
        if text not in {t for t, _ in found}:
            found.append((text, tag))
    return found
