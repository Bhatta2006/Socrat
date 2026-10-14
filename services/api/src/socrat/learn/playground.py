"""Progress-based topic suggestions for the visual playground."""

from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.learn import service as learn
from socrat.mastery.model import ConceptState, band
from socrat.models import Enrollment, User


def overview(db: Session, catalog: Catalog, user: User, enrollment: Enrollment, stamp: int) -> dict:
    scope = learn.curriculum(catalog, enrollment)
    locked = learn.locked_concepts(db, catalog, enrollment, stamp)
    states = learn.states_for(db, enrollment)
    completed = learn.completed_for(db, enrollment)
    concepts, suggestions = [], []
    for qualified in catalog.order:
        if qualified not in scope or qualified in locked:
            continue
        concept = catalog.concept(qualified)
        state = states.get(qualified, ConceptState())
        label = band(state, stamp)
        item = dict(id=qualified, title=concept.title, band=label)
        concepts.append(item)
        studied = state.evidence_count or f"lesson:{qualified}" in completed
        if studied and (state.failures or label in {"needs_practice", "developing"} or state.due(stamp)):
            reason = "Recent mistakes: slow down and trace each step." if state.failures else (
                "Due for review: test what you remember." if state.due(stamp) else
                "Build confidence with a worked explanation and predictions."
            )
            suggestions.append((state.effective(stamp), dict(item, reason=reason)))
    if not suggestions:
        plan = learn.plan_for(db, catalog, user, enrollment, stamp, record=False)
        current = next((r["concept"] for r in plan.roadmap if r["status"] in {"in_progress", "upcoming"}), None)
        suggestions = [(0, dict(c, reason="Explore the next topic in your plan.")) for c in concepts if c["id"] == current]
    suggestions.sort(key=lambda pair: pair[0])
    return dict(concepts=concepts, suggestions=[item for _, item in suggestions[:4]])
