"""Explicit opt-in; clock windows are evaluated in an IANA timezone."""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator

from socrat.models import UserPreferences
from socrat.skillpacks.types import Contract


class Preferences(Contract):
    reminders_consent: bool = False
    reminder_time: str = Field(default="09:00", pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    quiet_start: str = Field(default="21:00", pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    quiet_end: str = Field(default="08:00", pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = Field(default="UTC", max_length=64)
    reduced_motion: bool = False

    @field_validator("timezone")
    @classmethod
    def known_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("Choose an IANA timezone") from exc
        return value


class PreferencesUpdate(Preferences):
    expected_revision: int = Field(ge=0)


def preferences_for(db, user):
    row = db.get(UserPreferences, user.id)
    return {
        "revision": row.revision if row else 0,
        **(row.settings if row else Preferences(timezone=user.timezone).model_dump()),
    }


def local_clock(value, stamp):
    return datetime.fromtimestamp(stamp, ZoneInfo(value["timezone"]))


def quiet(value, stamp):
    clock = local_clock(value, stamp).strftime("%H:%M")
    start, end = value["quiet_start"], value["quiet_end"]
    # Equal boundaries mean quiet all day; consent never overrides quiet hours.
    return start <= clock < end if start < end else clock >= start or clock < end
