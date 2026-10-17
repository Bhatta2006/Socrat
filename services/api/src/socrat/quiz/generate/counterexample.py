"""Counterexample items (content.md §8.6): an input where a candidate disagrees with brute force.

Both functions are trusted authoring code. ``breaks`` grades one input; ``find`` searches a
space of small inputs so a generator can prove a counterexample exists before it asks for
one, and pick multiple-choice options where exactly one input breaks the candidate.
"""

from collections.abc import Callable, Iterable
from typing import Any


def breaks(candidate: Callable[..., Any], brute: Callable[..., Any], args: tuple) -> bool:
    """True when the candidate's answer differs from brute force (or the candidate fails)."""
    try:
        got = candidate(*args)
    except Exception:  # noqa: BLE001 - a crashing candidate is broken by this input
        return True
    return got != brute(*args)


def find(
    candidate: Callable[..., Any], brute: Callable[..., Any], inputs: Iterable[tuple]
) -> tuple | None:
    """The first input that breaks the candidate, or None if it agrees on all of them."""
    for args in inputs:
        if breaks(candidate, brute, args):
            return args
    return None


def split(
    candidate: Callable[..., Any], brute: Callable[..., Any], inputs: Iterable[tuple]
) -> tuple[list[tuple], list[tuple]]:
    """Inputs that break the candidate, and inputs where it is right."""
    bad: list[tuple] = []
    good: list[tuple] = []
    for args in inputs:
        (bad if breaks(candidate, brute, args) else good).append(args)
    return bad, good
