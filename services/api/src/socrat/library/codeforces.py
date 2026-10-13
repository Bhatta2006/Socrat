"""Read-only Codeforces profile sync over the public API (handle only, no credentials).

The API allows about one call every two seconds, so every request goes through one
process-wide throttle. Only ids, verdicts, tags and ratings are read.
"""

import asyncio
import re
import time
from collections import Counter
from typing import Any

import httpx

API = "https://codeforces.com/api"
HANDLE = re.compile(r"^[A-Za-z0-9_.-]{3,24}$")
MIN_GAP_SECONDS = 2.1
MAX_SUBMISSIONS = 10_000
_lock = asyncio.Lock()
_last_call = 0.0


class CodeforcesError(RuntimeError):
    """Code is safe to show: handle_not_found, unavailable, rate_limited, invalid_handle."""


async def _call(client: httpx.AsyncClient, method: str, params: dict) -> Any:
    global _last_call
    async with _lock:
        wait = _last_call + MIN_GAP_SECONDS - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            response = await client.get(f"{API}/{method}", params=params)
        except httpx.HTTPError as exc:
            raise CodeforcesError("unavailable") from exc
        finally:
            _last_call = time.monotonic()
    try:
        body = response.json()
    except ValueError as exc:
        raise CodeforcesError("unavailable") from exc
    if body.get("status") != "OK":
        comment = str(body.get("comment", "")).lower()
        if "not found" in comment:
            raise CodeforcesError("handle_not_found")
        if "limit" in comment:
            raise CodeforcesError("rate_limited")
        raise CodeforcesError("unavailable")
    return body["result"]


def problem_key(problem: dict) -> str | None:
    contest = problem.get("contestId")
    if not contest or contest >= 100_000:  # gym contests are outside the problemset
        return None
    return f"cf:{contest}{problem.get('index', '')}"


def summarize(submissions: list[dict]) -> dict:
    solved: dict[str, list[str]] = {}
    tried: dict[str, list[str]] = {}
    for sub in submissions:
        key = problem_key(sub.get("problem", {}))
        if key is None:
            continue
        tags = sub["problem"].get("tags", [])
        if sub.get("verdict") == "OK":
            solved[key] = tags
        else:
            tried.setdefault(key, tags)
    attempted = {k: v for k, v in tried.items() if k not in solved}
    stats: dict[str, dict[str, int]] = {}
    for tag, count in Counter(t for tags in solved.values() for t in tags).items():
        stats.setdefault(tag, {"solved": 0, "unsolved": 0})["solved"] = count
    for tag, count in Counter(t for tags in attempted.values() for t in tags).items():
        stats.setdefault(tag, {"solved": 0, "unsolved": 0})["unsolved"] = count
    return {"solved": sorted(solved), "attempted": sorted(attempted), "tag_stats": stats}


async def fetch_profile(handle: str, timeout: float = 20) -> dict:
    if not HANDLE.match(handle):
        raise CodeforcesError("invalid_handle")
    async with httpx.AsyncClient(
        timeout=timeout, headers={"User-Agent": "Socrat learning app"}
    ) as client:
        users = await _call(client, "user.info", {"handles": handle})
        user = users[0]
        submissions = await _call(
            client, "user.status", {"handle": user["handle"], "from": 1, "count": MAX_SUBMISSIONS}
        )
    return {
        "handle": user["handle"],
        "rating": user.get("rating"),
        "max_rating": user.get("maxRating"),
        "rank": user.get("rank", "unrated"),
        **summarize(submissions),
    }


_contests: tuple[float, list[dict]] = (0.0, [])
CONTEST_TTL_SECONDS = 3600
RATED_ROUNDS = ("Div. 2", "Div. 3", "Div. 4", "Educational")


async def upcoming_contests(days: int = 14, timeout: float = 15) -> list[dict]:
    """Upcoming rated rounds suitable for learners; cached, and empty when unavailable."""
    global _contests
    fetched, cached = _contests
    if time.monotonic() - fetched < CONTEST_TTL_SECONDS and fetched:
        return cached
    try:
        async with httpx.AsyncClient(
            timeout=timeout, headers={"User-Agent": "Socrat learning app"}
        ) as client:
            contests = await _call(client, "contest.list", {"gym": "false"})
    except CodeforcesError:
        return cached
    horizon = time.time() + days * 86400
    picked = [
        {
            "id": c["id"],
            "name": c["name"],
            "start": c["startTimeSeconds"],
            "duration_minutes": c["durationSeconds"] // 60,
            "url": f"https://codeforces.com/contests/{c['id']}",
        }
        for c in contests
        if c.get("phase") == "BEFORE"
        and c.get("startTimeSeconds", 0) <= horizon
        and any(tag in c.get("name", "") for tag in RATED_ROUNDS)
    ]
    picked.sort(key=lambda c: c["start"])
    _contests = (time.monotonic(), picked)
    return picked
