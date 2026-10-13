"""Streaks with earned protection.

A streak counts consecutive scheduled study days with activity; rest days never break it.
Meeting a whole week's study goal banks a streak freeze (at most FREEZE_CAP). A missed
scheduled day spends a freeze instead of resetting the streak, so one bad day after a good
week costs nothing. Pure: the caller supplies minutes per local day.
"""

from datetime import date, timedelta

FREEZE_CAP = 2


def _week_goal_met(
    minutes: dict[date, int], monday: date, weekdays: set[int], start: date, daily_goal: int
) -> bool:
    days = [monday + timedelta(days=i) for i in range(7)]
    scheduled = [d for d in days if d >= start and d.weekday() in weekdays]
    if not scheduled or daily_goal <= 0:
        return False
    return sum(minutes.get(d, 0) for d in days) >= daily_goal * len(scheduled)


def compute(
    minutes: dict[date, int],
    today: date,
    weekdays: set[int],
    start: date,
    daily_goal: int,
) -> dict:
    """`minutes`: local day -> minutes studied (a day with any activity counts as studied)."""
    studied = set(minutes)
    first = min([start, *studied]) if studied else start
    run = longest = freezes = 0
    frozen: list[date] = []
    cursor = first
    while cursor < today:
        if cursor in studied:
            run += 1
            longest = max(longest, run)
        elif cursor.weekday() in weekdays and cursor >= start:
            if freezes:
                freezes -= 1
                frozen.append(cursor)
            else:
                run = 0
        if cursor.weekday() == 6:  # Sunday closes the week
            monday = cursor - timedelta(days=6)
            if _week_goal_met(minutes, monday, weekdays, start, daily_goal):
                freezes = min(FREEZE_CAP, freezes + 1)
        cursor += timedelta(days=1)
    current = run + (1 if today in studied else 0)
    monday = today - timedelta(days=today.weekday())
    week_days = [monday + timedelta(days=i) for i in range(7)]
    week_goal = daily_goal * sum(1 for d in week_days if d >= start and d.weekday() in weekdays)
    return {
        "current": current,
        "longest": max(longest, current),
        "studied_today": today in studied,
        "freezes": freezes,
        "frozen": [d.isoformat() for d in frozen if (today - d).days <= 14],
        "week_minutes": sum(minutes.get(d, 0) for d in week_days if d <= today),
        "week_goal": week_goal,
    }


def days_away(studied: set[date], today: date, weekdays: set[int], start: date) -> int:
    """Scheduled study days missed since the learner last studied (0 when active)."""
    if not studied:
        return 0
    last = max(d for d in studied if d <= today) if any(d <= today for d in studied) else None
    if last is None:
        return 0
    missed, cursor = 0, last + timedelta(days=1)
    while cursor < today:
        if cursor.weekday() in weekdays and cursor >= start:
            missed += 1
        cursor += timedelta(days=1)
    return missed
