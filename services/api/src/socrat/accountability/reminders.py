"""Durable in-app reminders; no email addresses or provider dispatch in M10."""

from sqlalchemy import select

from socrat.accountability.preferences import local_clock, quiet
from socrat.database import record_event
from socrat.models import CurriculumHead, CurriculumRevision, LearningSession, Reminder


def eligible(db, user_id, value, stamp):
    if not value["reminders_consent"] or quiet(value, stamp):
        return False
    local = local_clock(value, stamp)
    hour, minute = map(int, value["reminder_time"].split(":"))
    delta = local.hour * 60 + local.minute - hour * 60 - minute
    if not 0 <= delta < 60:
        return False
    heads = db.scalars(
        select(CurriculumHead)
        .join(CurriculumRevision, CurriculumHead.active_id == CurriculumRevision.id)
        .where(CurriculumRevision.user_id == user_id, CurriculumHead.status == "confirmed")
    )
    for head in heads:
        plan = db.get(CurriculumRevision, head.active_id).snapshot
        day = next((x for x in plan["days"] if x["date"] == local.date().isoformat()), None)
        if not day or not day["blocks"]:
            continue
        session = db.scalar(
            select(LearningSession).where(
                LearningSession.goal_id == head.goal_id, LearningSession.local_date == day["date"]
            )
        )
        if session is None or session.status != "completed":
            return True
    return False


def enqueue(db, user_id, value, stamp):
    if not eligible(db, user_id, value, stamp):
        return
    day = local_clock(value, stamp).date().isoformat()
    if db.scalar(select(Reminder).where(Reminder.user_id == user_id, Reminder.local_date == day)):
        return
    db.add(Reminder(user_id=user_id, local_date=day, created_at=stamp))
    record_event(db, user_id, "reminder_sent")


def inbox(db, user_id, value, stamp):
    if not value["reminders_consent"] or quiet(value, stamp):
        return {"items": []}
    day = local_clock(value, stamp).date().isoformat()
    # Re-check pause/rest/completion at read time, including already enqueued reminders.
    if not eligible(
        db, user_id, {**value, "reminder_time": local_clock(value, stamp).strftime("%H:%M")}, stamp
    ):
        return {"items": []}
    return {
        "items": [
            {
                "id": row.id,
                "message": "Your planned learning session is ready. Choose a comfortable time to start.",
            }
            for row in db.scalars(
                select(Reminder).where(
                    Reminder.user_id == user_id,
                    Reminder.local_date == day,
                    Reminder.opened_at.is_(None),
                )
            )
        ]
    }
