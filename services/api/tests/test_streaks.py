"""Streaks: rest days never break them, earned freezes cover a missed study day."""

from datetime import date, timedelta

from socrat.learn import streaks

MON = date(2026, 10, 5)  # a Monday
WEEKDAYS = {0, 1, 2, 3, 4}  # Mon-Fri


def days(*offsets: int, minutes: int = 30) -> dict[date, int]:
    return {MON + timedelta(days=o): minutes for o in offsets}


def test_rest_days_do_not_break_and_missed_study_days_do():
    # Mon-Fri studied, weekend rest, Monday studied: streak continues to 6.
    result = streaks.compute(days(0, 1, 2, 3, 4, 7), MON + timedelta(days=7), WEEKDAYS, MON, 60)
    assert result["current"] == 6 and result["studied_today"]
    # Missing Wednesday (no freeze earned yet) resets.
    broken = streaks.compute(days(0, 1, 3, 4), MON + timedelta(days=4), WEEKDAYS, MON, 30)
    assert broken["current"] == 2 and broken["longest"] == 2


def test_a_full_week_earns_a_freeze_that_covers_one_miss():
    week_one = days(0, 1, 2, 3, 4, minutes=30)  # 150 min = goal of 5 x 30
    second = {**week_one, **days(7, 9, minutes=30)}  # Tuesday of week two missed
    result = streaks.compute(second, MON + timedelta(days=9), WEEKDAYS, MON, 30)
    assert result["current"] == 7  # 5 + Monday + Wednesday, Tuesday frozen
    assert result["frozen"] == [(MON + timedelta(days=8)).isoformat()]
    assert result["freezes"] == 0


def test_a_short_week_earns_nothing_and_the_bank_is_capped():
    short = days(0, 1, 2, 3, 4, minutes=10)
    assert streaks.compute(short, MON + timedelta(days=7), WEEKDAYS, MON, 30)["freezes"] == 0
    three_weeks = {
        **days(*range(0, 5), minutes=30),
        **days(*range(7, 12), minutes=30),
        **days(*range(14, 19), minutes=30),
    }
    banked = streaks.compute(three_weeks, MON + timedelta(days=21), WEEKDAYS, MON, 30)
    assert banked["freezes"] == streaks.FREEZE_CAP


def test_week_progress_and_days_away():
    result = streaks.compute(days(0, 1), MON + timedelta(days=2), WEEKDAYS, MON, 30)
    assert result["week_minutes"] == 60 and result["week_goal"] == 150
    studied = set(days(0))
    assert streaks.days_away(studied, MON + timedelta(days=5), WEEKDAYS, MON) == 4
    assert streaks.days_away(studied, MON + timedelta(days=1), WEEKDAYS, MON) == 0
    assert streaks.days_away(set(), MON, WEEKDAYS, MON) == 0
