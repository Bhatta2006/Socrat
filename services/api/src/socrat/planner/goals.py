"""What the learner's goal says about which concepts matter most (B1) and path styles (B4).

Relevance is a 0..1 weight per concept for one goal focus. The planner uses it to order
the concepts that are free to move (prerequisites always come first), and the
goal-focused style sets low-relevance concepts aside as optional. Pure data and functions.
"""

from typing import Literal

Focus = Literal["foundations", "interview", "contest"]
PathStyle = Literal["thorough", "balanced", "fast_track", "goal_focused"]
STYLES: tuple[PathStyle, ...] = ("thorough", "balanced", "fast_track", "goal_focused")
STYLE_WORDS: dict[str, tuple[str, str]] = {
    "thorough": ("Thorough", "Every concept, extra practice, no shortcuts."),
    "balanced": ("Balanced", "The full path at the pace your results set."),
    "fast_track": (
        "Fast track",
        "Skip warm-ups and offer test-outs so you can prove what you know and move on.",
    ),
    "goal_focused": (
        "Goal focused",
        "What your goal needs most comes first; lower-impact topics become optional.",
    ),
}
OPTIONAL_BELOW = 0.35
DEFAULT_RELEVANCE = 0.7

# How often a concept matters for coding interviews (frequency in real loops, roughly).
INTERVIEW = {
    "complexity": 0.8,
    "arrays-hashing": 1.0,
    "prefix-sums": 0.6,
    "two-pointers": 0.9,
    "sliding-window": 0.9,
    "stacks": 0.8,
    "binary-search": 0.9,
    "sorting": 0.6,
    "intervals": 0.7,
    "greedy": 0.6,
    "linked-lists": 0.7,
    "backtracking": 0.6,
    "binary-trees": 0.9,
    "bst": 0.6,
    "heaps": 0.8,
    "tries": 0.4,
    "graph-traversal": 0.9,
    "topological-sort": 0.6,
    "union-find": 0.4,
    "shortest-paths": 0.4,
    "dp-1d": 0.8,
    "dp-2d": 0.6,
    "bit-manipulation": 0.3,
}
# Entry-level loops rarely go deep into these.
JUNIOR_DISCOUNT = {"tries", "union-find", "shortest-paths", "dp-2d", "bit-manipulation"}

# Contest topics by the rating band where they start to pay off.
CONTEST_CORE = {
    "fast-io",
    "simulation",
    "complete-search",
    "number-theory",
    "modular-arithmetic",
    "prefix-difference",
    "binary-search-answer",
    "greedy-cp",
    "bitmasks",
    "dp-classics",
    "graph-techniques",
    "combinatorics",
}
CONTEST_ADVANCED = {
    "bitmask-dp",
    "mst",
    "tree-techniques",
    "lca",
    "fenwick-tree",
    "segment-tree",
    "string-hashing",
    "kmp",
}

FOUNDATIONS_LOW = {"classes-and-objects": 0.4, "recursion": 0.8, "grids": 0.8}


def focus_of(course_id: str, goal: dict) -> Focus:
    if goal.get("target_rating") or course_id == "cp":
        return "contest"
    if goal.get("target_role") or course_id == "dsa":
        return "interview"
    return "foundations"


def relevance(qualified: str, course_id: str, goal: dict) -> float:
    """0..1: how much this concept serves the learner's goal."""
    owner, local = qualified.split(":", 1)
    focus = focus_of(course_id, goal)
    if owner != course_id:
        return DEFAULT_RELEVANCE  # bridge concepts are needed, not optional
    if focus == "interview":
        value = INTERVIEW.get(local, DEFAULT_RELEVANCE)
        if goal.get("target_role") in {"internship", "new-grad"} and local in JUNIOR_DISCOUNT:
            value *= 0.7
        return round(value, 3)
    if focus == "contest":
        target = int(goal.get("target_rating") or 1600)
        if local in CONTEST_CORE:
            return 1.0
        if local in CONTEST_ADVANCED:
            return 1.0 if target >= 1900 else 0.6 if target >= 1500 else 0.3
        return DEFAULT_RELEVANCE
    return FOUNDATIONS_LOW.get(local, 1.0)


def tier(value: float) -> int:
    """Coarse tiers keep ordering stable: only clear differences move a concept."""
    return 2 if value >= 0.85 else 1 if value >= 0.5 else 0
