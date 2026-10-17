"""Try Socrat before signing up: one judged problem with the Socratic tutor, no account.

The landing page runs the visitor's code in the browser against the tests below and talks
to the same tutor learners get, with the same server-side help ladder and leak guard. The
conversation lives only in the visitor's browser: the server keeps nothing but metered
usage. Help is capped below the full walkthrough, so the demo can never hand out the answer.

Limits, in order: the feature switch, per-visitor and all-visitor hourly message caps (in
memory, per API process: with several processes the caps multiply, the budgets do not), a
per-conversation turn cap, this feature's own daily budget, then the global AI budgets
every model call already goes through. The tutor's context never holds the intended
approach or the reference solution, so neither prompt injection nor a forged history can
make it reveal them.
"""

import hashlib
import time
from collections import defaultdict, deque
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.assistant import budget, socratic
from socrat.assistant import service as assistant
from socrat.assistant.gateway import OfflineProvider, Turn, make_provider
from socrat.assistant.prompts import render_context
from socrat.catalog.registry import Catalog
from socrat.learn.routes import catalog, engine
from socrat.models import AIUsage, now

router = APIRouter(prefix="/api/v1/try")

PROBLEM_ID = "max-window-sum"
FEATURE = "try"
MAX_TURNS = 8  # visitor messages per conversation
MAX_LEVEL = 3  # approach at most: never pseudocode or code
MAX_TEST_BYTES = 4000  # big stress tests stay on the judge
GLOBAL_FACTOR = 100  # all visitors together, per API process, per hour
LEARNER = (
    "A visitor trying Socrat on the landing page before signing up. This is their first "
    "minute with you: keep every reply under 80 words, warm and specific to their code."
)

_recent: dict[str, deque[float]] = defaultdict(deque)


class TryTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class TryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    history: list[TryTurn] = Field(default_factory=list, max_length=2 * MAX_TURNS)
    message: str = Field(default="", max_length=1000)
    intent: Literal["chat", "hint"] = "chat"
    code: str = Field(default="", max_length=8000)
    result: str = Field(default="", max_length=1500)
    new_attempt: bool = False


def visitor(request: Request) -> str:
    """A salted hash of the address our own proxy saw; never stored.

    The rightmost X-Forwarded-For entry is the one the web server appended, so a client
    cannot pick it by sending its own header (earlier entries are client-controlled).
    """
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[-1].strip()
    address = forwarded or (request.client.host if request.client else "unknown")
    salt = request.app.state.settings.session_secret.get_secret_value()
    return hashlib.sha256(f"{salt}:{address}".encode()).hexdigest()[:32]


def allow(key: str, per_hour: int, stamp: float | None = None) -> bool:
    stamp = time.time() if stamp is None else stamp
    window = _recent[key]
    while window and window[0] <= stamp - 3600:
        window.popleft()
    if len(window) >= per_hour:
        return False
    window.append(stamp)
    if len(_recent) > 50_000:  # forget idle visitors so memory stays bounded
        for stale in [k for k, v in _recent.items() if not v or v[-1] <= stamp - 3600]:
            del _recent[stale]
    return True


def problem_view(cat: Catalog) -> dict:
    problem = cat.problem(PROBLEM_ID)
    tests = [t for t in problem.tests if len(t.input) <= MAX_TEST_BYTES]
    return dict(
        id=problem.id,
        title=problem.title,
        statement=problem.statement,
        input_format=problem.input_format,
        output_format=problem.output_format,
        constraints=problem.constraints,
        examples=[
            dict(input=e.input, output=e.output, explanation=e.explanation)
            for e in problem.examples
        ],
        starter=problem.starter.get("python")
        or "n, k = map(int, input().split())\nvalues = list(map(int, input().split()))\n\n# Print the largest sum of k consecutive values.\n",
        time_limit_ms=problem.time_limit_ms,
        tests=[
            dict(index=i, input=t.input, expected=t.expected, public=t.public)
            for i, t in enumerate(tests)
        ],
        max_turns=MAX_TURNS,
    )


def ladder_for(history: list[TryTurn], message: str, new_attempt: bool) -> socratic.Ladder:
    """Replay the visitor's turns through the ladder; the client cannot skip levels."""
    ladder = socratic.Ladder()
    for turn in history:
        if turn.role == "user":
            ladder = socratic.advance(ladder, turn.content, False)
    return socratic.advance(ladder, message, new_attempt)


def plan_turn(cat: Catalog, body: TryMessage) -> assistant.TurnPlan:
    problem = cat.problem(PROBLEM_ID)
    ladder = ladder_for(body.history, body.message, body.new_attempt)
    allowed = min(ladder.ceiling, MAX_LEVEL)
    sections = {
        "learner": LEARNER,
        "practice_problem": f"{problem.title}\n{problem.statement}\nInput: {problem.input_format}\n"
        f"Output: {problem.output_format}\nConstraints: {'; '.join(problem.constraints)}",
        "tutor_notes": "Progressive hints (reveal only as the level allows):\n"
        + "\n".join(f"- {h}" for h in problem.hints),
        "learner_code": f"Language: Python\n{body.code[:8000] or '(empty)'}",
        "latest_result": body.result.strip() or "No runs yet.",
        "help_policy": f"ALLOWED_LEVEL: {allowed} — {socratic.LEVELS[allowed]}",
    }
    text = body.message.strip() or (
        "I'd like a hint." if body.intent == "hint" else "Can you help me?"
    )
    turns = [Turn(t.role, t.content) for t in body.history[-12:]]
    turns.append(
        Turn("user", f"{render_context(sections)}\n\n<learner_message>\n{text}\n</learner_message>")
    )
    fallback = assistant.offline_reply(f"problem:{PROBLEM_ID}", allowed, problem, cat, "python")
    return assistant.TurnPlan("", f"problem:{PROBLEM_ID}", allowed, problem, turns, fallback)


@router.get("")
def overview(request: Request):
    if not request.app.state.settings.try_tutor_enabled:
        raise HTTPException(404, "not_found")
    return problem_view(catalog())


@router.post("/messages")
async def message(body: TryMessage, request: Request):
    settings = request.app.state.settings
    if not settings.try_tutor_enabled:
        raise HTTPException(404, "not_found")
    if sum(1 for t in body.history if t.role == "user") >= MAX_TURNS:
        raise HTTPException(429, "try_turns_used")
    if not allow(visitor(request), settings.try_messages_per_hour) or not allow(
        "all-visitors", settings.try_messages_per_hour * GLOBAL_FACTOR
    ):
        raise HTTPException(429, "try_rate_limited")
    cat = catalog()
    bind = engine(request)
    stamp = now()
    with Session(bind) as db:
        spent_today = db.scalar(
            select(func.coalesce(func.sum(AIUsage.cost_usd), 0.0)).where(
                AIUsage.feature == FEATURE, AIUsage.day == budget.day_of(stamp)
            )
        )
    plan = plan_turn(cat, body)
    provider = make_provider(settings)
    if settings.try_daily_budget_usd and float(spent_today or 0) >= settings.try_daily_budget_usd:
        provider = OfflineProvider()
    metered = budget.Metered(provider, bind, settings, user_id=None, feature=FEATURE)

    async def events():
        async for event, data in assistant.stream_reply(metered, plan, settings):
            yield assistant.sse(event, data)

    return StreamingResponse(
        events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
    )
