"""Pattern-aware planning (Content Master Plan §9.4–9.7), behind ``pattern_planner_enabled``.

Pure: everything here takes plain values. ``learn.pattern_sessions`` gathers the learner's
state from the database and turns the result into a learning session.

1. ``priority`` scores each eligible pattern (§9.5):
   gate × (0.35 weakness + 0.25 review_due + 0.20 track_relevance + 0.10 diversity + 0.10 unlock).
2. ``triggers`` reads the learner's state for the chosen pattern (§9.4 pattern triggers).
3. ``build`` lays out an intro, drill or mixed-review session (§9.7) from authored atoms and
   existing problems, and ``violations`` checks the hard placement constraints. A plan that
   breaks one is never served; the caller falls back to the existing composer.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

SessionType = Literal["intro", "drill", "mixed_review"]
Trigger = Literal[
    "contrast", "classify_first", "classifier", "retain", "advance", "intro", "repair"
]


@dataclass(frozen=True)
class Weights:
    weakness: float = 0.35
    review_due: float = 0.25
    track_relevance: float = 0.20
    diversity: float = 0.10
    unlock: float = 0.10
    retention_days: float = 7.0  # mastered but unseen this long: retention item
    drill_after: int = 3  # independent variants before the classifier drill
    repair_after: int = 2  # same pitfall missed this often: micro-lesson


DEFAULT = Weights()


@dataclass(frozen=True)
class PatternView:
    """What the planner knows about one pattern for one learner."""

    pattern: str
    concept: str
    gate: bool  # prerequisites met and the concept is not locked
    mastery: float  # 0..1 estimate from evidence
    seen: bool  # any evidence or attempt on this pattern
    due: bool = False
    overdue_days: float = 0.0
    idle_days: float | None = None  # days since the learner last worked on it
    relevance: float = 0.0  # 0..1 for the learner's track
    unlock: float = 0.0  # 0..1: share of locked patterns this one leads to
    solved: tuple[str, ...] = ()  # variant ids solved independently, ladder order
    classify_hits: int = 0
    classify_misses: int = 0
    confusions: tuple[str, ...] = ()  # pattern-confusion tags missed at least twice
    pitfall_misses: tuple[str, ...] = ()  # pitfalls missed at least ``repair_after`` times

    @property
    def mastered(self) -> bool:
        return self.mastery >= 0.8


@dataclass(frozen=True)
class Score:
    pattern: str
    total: float
    parts: dict[str, float] = field(default_factory=dict)  # explainable components


def priority(view: PatternView, last_pattern: str | None, w: Weights = DEFAULT) -> Score:
    review = min(1.0, (view.overdue_days + 1) / w.retention_days) if view.due else 0.0
    if view.mastered and view.idle_days is not None and view.idle_days >= w.retention_days:
        review = 1.0
    parts = dict(
        weakness=w.weakness * (1 - view.mastery),
        review_due=w.review_due * review,
        track_relevance=w.track_relevance * view.relevance,
        diversity=w.diversity * (0.0 if view.pattern == last_pattern else 1.0),
        unlock=w.unlock * view.unlock,
    )
    total = sum(parts.values()) if view.gate else 0.0
    return Score(view.pattern, round(total, 6), {k: round(v, 6) for k, v in parts.items()})


def rank(views: list[PatternView], last_pattern: str | None, w: Weights = DEFAULT) -> list[Score]:
    """Eligible patterns, best first; ties break by id so the order is deterministic."""
    scores = [priority(v, last_pattern, w) for v in views if v.gate]
    return sorted(scores, key=lambda s: (-s.total, s.pattern))


def triggers(view: PatternView, w: Weights = DEFAULT) -> list[Trigger]:
    """§9.4 pattern triggers that apply, most important first."""
    found: list[Trigger] = []
    if view.pitfall_misses:
        found.append("repair")
    if view.confusions:
        found.append("contrast")
    if (
        len(view.solved) >= 2
        and view.classify_misses >= 2
        and view.classify_misses > view.classify_hits
    ):
        found.append("classify_first")
    if len(view.solved) >= w.drill_after:
        found.append("classifier")
    if view.mastered and view.idle_days is not None and view.idle_days >= w.retention_days:
        found.append("retain")
    if len(view.solved) >= 1:
        found.append("advance")
    if not view.seen:
        found.append("intro")
    return found


def session_type(view: PatternView, due_patterns: int, fired: list[Trigger]) -> SessionType:
    if not view.seen:
        return "intro"
    if due_patterns >= 3 or "retain" in fired:
        return "mixed_review"
    return "drill"


# ---------------------------------------------------------------- layout


@dataclass(frozen=True)
class Variant:
    id: str
    band: int
    problem: str | None  # native problem id, when there is one


@dataclass
class Content:
    """Everything ``build`` may place, gathered by the caller."""

    pattern: str
    concept: str
    title: str
    card: dict  # pattern card atom, built from the pattern file
    atoms: dict[
        str, dict
    ]  # kind -> atom json from the pattern's pack (draft packs only if allowed)
    variants: list[Variant]  # ladder order; problem is None for external-only rungs
    unsolved: set[str]  # native problems the learner may still attempt independently
    concept_problems: list[str]  # unsolved problems of the concept, easiest first
    problem_info: Callable[[str], tuple[str, str]]  # problem id -> (title, qualified concept)
    contrast: dict | None = None  # contrast card atom, when a confusion fired
    reviews: list[str] = field(default_factory=list)  # due concepts, one per pattern, max 3


SECONDS = {  # §9.7 pattern-session timings (30–45 minutes), in seconds
    "intro": dict(
        review=240, card=120, worked=120, visualizer=120, guided=540, independent=720, close=90
    ),
    "drill": dict(review=180, card=90, guided=420, independent=600, classify=240, close=90),
    "mixed_review": dict(review=180, classify=240, independent=600, close=90),
}


def _atom_block(content: Content, atom: dict, reason: str, seconds: int) -> dict:
    return dict(
        kind="atom",
        title=atom["title"],
        seconds=seconds,
        concept=content.concept,
        pattern=content.pattern,
        atom=atom,
        version=atom.get("version", "pattern"),
        status=atom.get("status", "draft"),
        reason=reason,
    )


def _problem_block(content: Content, pid: str, mode: str, seconds: int, reason: str) -> dict:
    title, concept = content.problem_info(pid)
    return dict(
        kind="problem",
        title=title,
        concept=concept,
        pattern=content.pattern,
        problem=pid,
        mode=mode,
        seconds=seconds,
        reason=reason,
    )


def _practice(content: Content, view: PatternView, need: int) -> list[str]:
    """Unsolved native variants above what the learner has solved, then concept problems."""
    done = set(view.solved)
    ladder = [
        v.problem
        for v in content.variants
        if v.problem and v.id not in done and v.problem in content.unsolved
    ]
    picks: list[str] = []
    for pid in ladder + content.concept_problems:
        if pid not in picks:
            picks.append(pid)
        if len(picks) == need:
            break
    return picks


def build(
    kind: SessionType,
    view: PatternView,
    content: Content,
    fired: list[Trigger],
    minutes: int,
    beginner: bool,
    recovery: bool,
) -> list[dict]:
    t = SECONDS[kind]
    blocks: list[dict] = []
    for concept in content.reviews[: 3 if kind == "mixed_review" else 1]:
        blocks.append(
            dict(
                kind="review",
                title="Retrieval warm-up",
                concept=concept,
                activity=f"review:{concept}",
                seconds=t["review"],
                reason="Recall an earlier pattern before practising.",
            )
        )
    if "repair" in fired and "micro" in content.atoms:
        blocks.append(
            _atom_block(
                content, content.atoms["micro"], "This pitfall came up twice: one short repair.", 75
            )
        )
    if "contrast" in fired and content.contrast:
        blocks.append(
            _atom_block(
                content,
                content.contrast,
                "Two patterns were mixed up; compare them side by side.",
                90,
            )
        )
    classify = content.atoms.get("classify")
    if "classify_first" in fired and classify:
        blocks.append(
            _atom_block(content, classify, "Recognise the pattern before solving more of it.", 240)
        )
    if kind == "intro":
        blocks.append(
            _atom_block(
                content,
                content.card,
                "Meet the pattern: when to use it and its template.",
                t["card"],
            )
        )
        if beginner and "worked" in content.atoms:
            blocks.append(
                _atom_block(
                    content, content.atoms["worked"], "See one complete example first.", t["worked"]
                )
            )
        if "visualizer" in content.atoms and not recovery:
            blocks.append(
                _atom_block(
                    content,
                    content.atoms["visualizer"],
                    "Predict each step before it is revealed.",
                    t["visualizer"],
                )
            )
        picks = _practice(content, view, 2)
        if len(picks) == 2:
            blocks.append(
                _problem_block(
                    content, picks[0], "guided", t["guided"], "Use the hint ladder if you need it."
                )
            )
        if picks:
            blocks.append(
                _problem_block(
                    content,
                    picks[-1],
                    "independent",
                    t["independent"],
                    "Now on your own: no hints.",
                )
            )
    elif kind == "drill":
        if "advance" in fired:
            blocks.append(
                _atom_block(
                    content,
                    content.card,
                    "You solved a variant: here is the template behind it.",
                    t["card"],
                )
            )
        picks = _practice(content, view, 3)
        if picks:
            first_mode = "guided" if len(picks) > 1 else "independent"
            blocks.append(
                _problem_block(
                    content, picks[0], first_mode, t["guided"], "Warm up on the next rung."
                )
            )
        for pid in picks[1:]:
            if (
                blocks
                and blocks[-1].get("mode") == "independent"
                and classify
                and "classifier" in fired
            ):
                blocks.append(
                    _atom_block(
                        content,
                        classify,
                        "Same template, three problems: classify a mix.",
                        t["classify"],
                    )
                )
                fired = [f for f in fired if f != "classifier"]
            elif blocks and blocks[-1].get("mode") == "independent":
                blocks.append(
                    dict(
                        kind="break",
                        title="Pause and name your approach",
                        seconds=60,
                        concept=content.concept,
                        pattern=content.pattern,
                        reason="Switch effort before the next independent problem.",
                    )
                )
            blocks.append(
                _problem_block(
                    content, pid, "independent", t["independent"], "A harder rung, on your own."
                )
            )
        if "classifier" in fired and classify:
            blocks.append(
                _atom_block(
                    content,
                    classify,
                    "Same template, three problems: classify a mix.",
                    t["classify"],
                )
            )
    else:  # mixed review
        if classify and "classify_first" not in fired:
            blocks.append(
                _atom_block(content, classify, "Mix the patterns you know.", t["classify"])
            )
        picks = _practice(content, view, 1)
        if picks:
            blocks.append(
                _problem_block(
                    content,
                    picks[0],
                    "independent",
                    t["independent"],
                    "One problem from a pattern that is due.",
                )
            )
    blocks.append(
        dict(
            kind="reflection",
            title="What felt hardest?",
            seconds=30,
            concept=content.concept,
            pattern=content.pattern,
            reason="Your reflection changes scheduling, not mastery.",
        )
    )
    budget = minutes * 60
    total = sum(b["seconds"] for b in blocks)
    if total > budget:
        for block in blocks:
            block["seconds"] = max(10, int(block["seconds"] * budget / total))
    return blocks


# ---------------------------------------------------------------- constraints


def violations(
    blocks: list[dict],
    gated: set[str],
    seen: set[str],
    minutes: int,
    recovery: bool,
    retention_due: bool,
    allow_drafts: bool,
) -> list[str]:
    """§9.4 hard placement constraints. Empty means the plan may be served."""
    found = []
    for b in blocks:
        if b["kind"] == "atom" and b.get("concept") in gated:
            found.append(f"instruction for locked concept {b['concept']}")
        if b["kind"] == "atom" and b.get("status") == "draft" and not allow_drafts:
            found.append(f"draft atom {b['atom'].get('id')} served without drafts allowed")
        if b["kind"] != "unavailable" and b.get("seconds", 0) <= 0:
            found.append(f"block {b['title']!r} has no time estimate")
    introduced = {
        b["pattern"] for b in blocks if b["kind"] == "atom" and b.get("pattern") not in seen
    }
    if len(introduced) > 1:
        found.append(f"more than one new idea: {sorted(introduced)}")
    if not recovery and not any(b.get("mode") == "independent" for b in blocks):
        found.append("no independent attempt")
    if retention_due and not any(b["kind"] == "review" for b in blocks):
        found.append("retention is due but there is no retrieval block")
    for a, b in zip(blocks, blocks[1:], strict=False):
        if a.get("mode") == "independent" and b.get("mode") == "independent":
            found.append("two independent problems back to back")
    if sum(b.get("seconds", 0) for b in blocks) > minutes * 60:
        found.append("over the time budget")
    concepts = [b["concept"] for b in blocks if b["kind"] == "problem"]
    if any(concepts.count(c) > 3 for c in set(concepts)):
        found.append("too many problems on one concept")
    return found
