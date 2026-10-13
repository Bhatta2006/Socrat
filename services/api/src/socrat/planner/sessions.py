"""Evidence-triggered session composition; one new concept, bounded reading, real practice."""

from socrat.catalog.registry import Catalog
from socrat.mastery.model import ConceptState


def compose(
    catalog: Catalog,
    concept: str,
    states: dict[str, ConceptState],
    problems: list[str],
    minutes: int,
    beginner: bool,
    recovery: bool,
    due: str | None,
    failures: dict[str, int],
    syntax_friction: bool,
    slow_correct: bool,
    now: int,
    language: str,
    diverse_successes: bool = False,
    allow_drafts: bool = False,
    transfer: str | None = None,
) -> list[dict]:
    pack = catalog.atom_packs.get(concept)
    atoms = (
        list(pack.atoms)
        if pack and (pack.status == "released" or (pack.status == "draft" and allow_drafts))
        else []
    )
    blocks: list[dict] = []

    def atom(kind: str, reason: str, misconception: str | None = None):
        match = next(
            (
                a
                for a in atoms
                if a.kind == kind and (not misconception or a.misconception == misconception)
            ),
            None,
        )
        if match:
            assert pack is not None
            if match.adapters and language not in match.adapters:
                blocks.append(
                    dict(
                        kind="unavailable",
                        title=match.title,
                        concept=concept,
                        seconds=0,
                        reason=f"The {language} adapter is unavailable; no automatic translation is used.",
                    )
                )
                return
            blocks.append(
                dict(
                    kind="atom",
                    title=match.title,
                    seconds=match.seconds,
                    concept=concept,
                    atom=match.model_dump(mode="json"),
                    version=pack.version,
                    status=pack.status,
                    reason=reason,
                )
            )

    def practice(pid: str, mode: str, seconds: int):
        course_id, problem = catalog.problems[pid]
        blocks.append(
            dict(
                kind="problem",
                title=catalog.problem(pid).title,
                concept=f"{course_id}:{problem.concepts[0]}",
                problem=pid,
                mode=mode,
                seconds=seconds,
                reason="Try it without hints; an honest attempt is enough to continue."
                if mode == "independent"
                else "Use the hint ladder if you need it.",
            )
        )

    if due:
        blocks.append(
            dict(
                kind="review",
                title="Retrieval warm-up",
                concept=due,
                activity=f"review:{due}",
                seconds=min(240, minutes * 12),
                reason="Recall a previous idea before introducing another.",
            )
        )
    atom("hook", "Start with the situation this idea helps solve.")
    misconception = next((key for key, count in failures.items() if count >= 2), None)
    if misconception:
        atom(
            "micro",
            "This misconception appeared twice; take one short repair detour.",
            misconception,
        )
    elif syntax_friction:
        atom(
            "micro",
            "Three compile errors suggest language friction, not a gap in the algorithm.",
            "syntax-delimiters",
        )
    strong = states.get(concept, ConceptState()).mastered(now)
    if strong:
        atom("pattern", "Your existing evidence supports moving straight to transfer practice.")
    elif slow_correct or diverse_successes:
        atom("pattern", "Your solution was correct; practise recognising the strategy sooner.")
    elif beginner:
        atom("worked", "See one concrete example before trying it yourself.")
        atom("faded", "Complete a small step with support.")
    elif problems:
        practice(
            problems[0], "guided" if len(problems) > 1 else "independent", max(180, minutes * 6)
        )
        atom("concept", "Use your first attempt to decide what the explanation needs to answer.")
    else:
        atom("concept", "A short explanation while new original practice is prepared.")
    if not strong and not recovery and minutes >= 30:
        atom("visualizer", "Predict the next state before it is revealed.")
    independent = (
        problems[-1]
        if problems and not any(b.get("mode") == "independent" for b in blocks)
        else None
    )
    if independent:
        practice(independent, "independent", max(180, minutes * (25 if minutes <= 20 else 20)))
    elif not problems:
        blocks.append(
            dict(
                kind="unavailable",
                title="Fresh independent practice is unavailable",
                concept=concept,
                seconds=0,
                reason="We will not relabel a familiar or assisted solve as independent evidence.",
            )
        )
    if minutes >= 60 and transfer:
        blocks.append(
            dict(
                kind="break",
                title="Pause and name your approach",
                seconds=60,
                concept=concept,
                reason="Switch effort before the second independent problem.",
            )
        )
        practice(transfer, "independent", 12 * 60)
    atom("explanation", "Explain the idea through one structured reasoning check.")
    blocks.append(
        dict(
            kind="reflection",
            title="What felt hardest?",
            seconds=30,
            concept=concept,
            reason="Your reflection changes scheduling, not mastery.",
        )
    )
    # Timings are estimates; do not fill unused minutes with extra reading.
    total = sum(b["seconds"] for b in blocks)
    block_budget = minutes * 60 - (300 if minutes >= 90 else 0)
    if total > block_budget:
        for block in blocks:
            block["seconds"] = (
                max(10, int(block["seconds"] * block_budget / total)) if block["seconds"] else 0
            )
    if minutes >= 90:
        position = next(
            (i for i, b in enumerate(blocks) if b.get("mode") == "independent"), len(blocks) - 1
        )
        blocks.insert(
            position,
            dict(
                kind="break",
                title="Take a five-minute break",
                seconds=300,
                concept=concept,
                reason="Step away; continue when you are ready.",
            ),
        )
    return blocks
