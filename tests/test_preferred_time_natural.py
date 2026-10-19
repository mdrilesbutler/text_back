"""Customers answer "when?" the way they talk, not in ISO. These pin the rules.

NOW is Monday 2026-10-19 10:00 Eastern. Hours without am/pm follow business
daytime: 7-11 are AM, 12 and 1-6 are PM. A bare or "this" weekday is the
nearest one (today counts while the time is still ahead); "next <weekday>"
is that weekday in the following calendar week.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from text_back.preferred_time import PreferredTimeError, parse_preferred_time

TZ = "America/New_York"
EASTERN = ZoneInfo(TZ)
NOW = datetime(2026, 10, 19, 10, 0, tzinfo=EASTERN)  # a Monday


def at(month, day, hour, minute=0, year=2026):
    return datetime(year, month, day, hour, minute, tzinfo=EASTERN)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Michael's examples
        ("this wednesday at 2", at(10, 21, 14)),
        ("next thursday at 4:00", at(10, 29, 16)),
        # bare weekdays, abbreviations, "at"/"@"/no joiner, time first
        ("wednesday at 2pm", at(10, 21, 14)),
        ("Wed 2pm", at(10, 21, 14)),
        ("weds @ 2", at(10, 21, 14)),
        ("2pm wednesday", at(10, 21, 14)),
        ("Thursday 4", at(10, 22, 16)),
        ("thurs at 4:30", at(10, 22, 16, 30)),
        ("tues 9am", at(10, 20, 9)),
        ("friday at 10", at(10, 23, 10)),
        ("on Friday at 10:15 a.m.", at(10, 23, 10, 15)),
        ("sat 8", at(10, 24, 8)),
        ("sunday at noon", at(10, 25, 12)),
        ("mon at 2", at(10, 19, 14)),            # today is Monday, 2 PM is still ahead
        ("monday at 9", at(10, 26, 9)),          # 9 AM today already passed -> next Monday
        ("this monday at 2", at(10, 19, 14)),
        # next = following calendar week
        ("next monday at 8", at(10, 26, 8)),
        ("next wednesday 2", at(10, 28, 14)),
        ("next sunday at 1", at(11, 1, 13)),
        # today / tomorrow / tonight
        ("today at 3", at(10, 19, 15)),
        ("today 11", at(10, 19, 11)),
        ("tonight at 7", at(10, 19, 19)),
        ("tomorrow at 10", at(10, 20, 10)),
        ("tomorrow 2pm", at(10, 20, 14)),
        ("tomorrow at 2 PM", at(10, 20, 14)),
        ("tmrw 4", at(10, 20, 16)),
        ("tomorrow at 7 in the evening", at(10, 20, 19)),
        ("tomorrow at 7 in the morning", at(10, 20, 7)),
        ("noon tomorrow", at(10, 20, 12)),
        # month/day forms
        ("oct 22 at 4", at(10, 22, 16)),
        ("October 22nd at 4pm", at(10, 22, 16)),
        ("Oct 22, 2026 4:00 PM", at(10, 22, 16)),
        ("22 oct at 4", at(10, 22, 16)),
        ("nov 3 at 9", at(11, 3, 9)),
        ("jan 5 at 2", at(1, 5, 14, year=2027)),  # already passed this year -> next year
        ("10/22 at 4", at(10, 22, 16)),
        ("10/22/26 4:00 pm", at(10, 22, 16)),
        ("10/22/2026 16:00", at(10, 22, 16)),
        # the old explicit formats still work
        ("2026-10-22 14:30", at(10, 22, 14, 30)),
        ("2026-10-22 2:30 PM", at(10, 22, 14, 30)),
        ("10/22/2026 2:30 pm", at(10, 22, 14, 30)),
        # 24-hour clock and fillers
        ("wednesday at 14:00", at(10, 21, 14)),
        ("Wednesday at 2 works", at(10, 21, 14)),
        ("wednesday at 2 please", at(10, 21, 14)),
        ("Wednesday at 2.", at(10, 21, 14)),
        ("Wednesday, at 2 o'clock", at(10, 21, 14)),
    ],
)
def test_natural_phrases(raw, expected):
    assert parse_preferred_time(raw, timezone_name=TZ, now=NOW) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "wednesday",            # no time
        "next week",
        "tomorrow afternoon",   # no clock time
        "2",                    # no day
        "at 2pm",
        "wednesday at 13pm",
        "wednesday at 25",
        "wednesday at 2:75",
        "whenever",
        "asap",
        "2026-10-22",
        "wednesday at midnight",
    ],
)
def test_vague_or_broken_values_still_fail_closed(raw):
    with pytest.raises(PreferredTimeError, match="date and time"):
        parse_preferred_time(raw, timezone_name=TZ, now=NOW)


def test_today_with_a_time_that_already_passed_is_rejected():
    with pytest.raises(PreferredTimeError, match="future"):
        parse_preferred_time("today at 9", timezone_name=TZ, now=NOW)


def test_weekday_rolls_to_next_week_when_today_and_time_passed():
    parsed = parse_preferred_time("monday at 9", timezone_name=TZ, now=NOW)
    assert parsed == at(10, 26, 9)


def test_next_weekday_on_sunday_means_the_week_starting_tomorrow():
    sunday = datetime(2026, 10, 25, 10, 0, tzinfo=EASTERN)
    assert parse_preferred_time("next monday at 8", timezone_name=TZ, now=sunday) == at(10, 26, 8)
    assert parse_preferred_time("next sunday at 1", timezone_name=TZ, now=sunday) == at(11, 1, 13)
