"""The skill ladder every course quietly climbs.

Concepts are grouped into tiers roughly aligned with Codeforces rating bands. A learner's
mastery across the tiers gives an estimated problem-solving rating, which sets how hard
recommended problems are. Learners see "your level" and "a step up", never the ladder.
"""

from socrat.mastery.model import ConceptState

TIERS: list[tuple[int, tuple[str, ...]]] = [
    (
        800,
        (
            "zero:programs-and-output",
            "zero:variables-and-types",
            "zero:input-and-arithmetic",
            "zero:conditionals",
            "zero:boolean-logic",
            "zero:while-loops",
            "zero:for-loops",
            "zero:debugging",
            "cp:fast-io",
            "cp:simulation",
        ),
    ),
    (
        1000,
        (
            "zero:strings",
            "zero:lists",
            "zero:functions",
            "zero:nested-loops",
            "zero:grids",
            "zero:maps",
            "zero:scope-and-mutation",
            "zero:problem-solving",
            "dsa:complexity",
            "dsa:arrays-hashing",
            "dsa:sorting",
            "cp:complete-search",
        ),
    ),
    (
        1200,
        (
            "zero:recursion",
            "zero:classes-and-objects",
            "dsa:two-pointers",
            "dsa:prefix-sums",
            "dsa:sliding-window",
            "dsa:binary-search",
            "dsa:stacks",
            "dsa:linked-lists",
            "dsa:intervals",
            "dsa:bit-manipulation",
            "dsa:greedy",
            "dsa:dp-1d",
            "cp:prefix-difference",
            "cp:greedy-cp",
        ),
    ),
    (
        1400,
        (
            "dsa:binary-trees",
            "dsa:bst",
            "dsa:heaps",
            "dsa:backtracking",
            "dsa:graph-traversal",
            "dsa:dp-2d",
            "cp:binary-search-answer",
            "cp:number-theory",
            "cp:modular-arithmetic",
            "cp:bitmasks",
            "cp:dp-classics",
        ),
    ),
    (
        1600,
        (
            "dsa:shortest-paths",
            "dsa:union-find",
            "dsa:topological-sort",
            "dsa:tries",
            "cp:combinatorics",
            "cp:tree-techniques",
            "cp:mst",
            "cp:string-hashing",
        ),
    ),
    (
        1800,
        (
            "cp:segment-tree",
            "cp:fenwick-tree",
            "cp:lca",
            "cp:kmp",
            "cp:bitmask-dp",
            "cp:graph-techniques",
        ),
    ),
]
TIER_OF = {concept: rating for rating, concepts in TIERS for concept in concepts}
COVERED = 0.75  # average mastery at which a tier counts as climbed
STEP = 200
FLOOR = 800


def tier_of(concept: str) -> int:
    return TIER_OF.get(concept, 1200)


def _score(state: ConceptState | None, now: int) -> float:
    if state is None or (state.evidence_count == 0 and not state.assumed):
        return 0.0
    return state.effective(now)


def estimate_rating(states: dict[str, ConceptState], now: int, linked: int | None = None) -> int:
    """Mastery-based rating; a linked contest rating, when present, is weighted in."""
    rating = FLOOR
    for base, concepts in TIERS:
        average = sum(_score(states.get(c), now) for c in concepts) / len(concepts)
        covered = min(1.0, average / COVERED)
        rating = base + round(STEP * covered)
        if covered < 1.0:
            break
    if linked:
        rating = round(0.6 * linked + 0.4 * rating)
    return max(FLOOR, min(3000, rating // 50 * 50))


def frontier(states: dict[str, ConceptState], now: int, rating: int, limit: int = 4) -> list[str]:
    """Concepts just above the learner's level that are not yet solid, in ladder order."""
    picked = []
    for base, concepts in TIERS:
        if base > rating + STEP:
            break
        for concept in concepts:
            if _score(states.get(concept), now) < 0.6:
                picked.append(concept)
    return picked[:limit]
