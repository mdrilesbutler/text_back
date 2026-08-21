from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from text_back.preferred_time import PreferredTimeError, parse_preferred_time


EASTERN = ZoneInfo("America/New_York")
NOW = datetime(2026, 8, 21, 10, 0, tzinfo=EASTERN)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-08-25 14:30", datetime(2026, 8, 25, 14, 30, tzinfo=EASTERN)),
        ("2026-08-25 2:30 PM", datetime(2026, 8, 25, 14, 30, tzinfo=EASTERN)),
        ("08/25/2026 2:30 pm", datetime(2026, 8, 25, 14, 30, tzinfo=EASTERN)),
    ],
)
def test_parse_preferred_time_uses_configured_business_timezone(raw, expected):
    assert parse_preferred_time(raw, timezone_name="America/New_York", now=NOW) == expected


def test_parse_preferred_time_supports_explicit_tomorrow_time():
    parsed = parse_preferred_time(
        "tomorrow at 2 PM",
        timezone_name="America/New_York",
        now=NOW,
    )

    assert parsed == datetime(2026, 8, 22, 14, 0, tzinfo=EASTERN)


@pytest.mark.parametrize(
    "raw",
    [
        "tomorrow afternoon",
        "next Tuesday",
        "whenever",
        "2026-08-25",
    ],
)
def test_parse_preferred_time_rejects_values_without_an_explicit_time(raw):
    with pytest.raises(PreferredTimeError, match="date and time"):
        parse_preferred_time(raw, timezone_name="America/New_York", now=NOW)


def test_parse_preferred_time_rejects_past_time():
    with pytest.raises(PreferredTimeError, match="future"):
        parse_preferred_time(
            "2026-08-20 2:00 PM",
            timezone_name="America/New_York",
            now=NOW,
        )


def test_parse_preferred_time_rejects_nonexistent_dst_local_time():
    with pytest.raises(PreferredTimeError, match="daylight saving"):
        parse_preferred_time(
            "2026-03-08 2:30 AM",
            timezone_name="America/New_York",
            now=datetime(2026, 3, 1, 10, 0, tzinfo=EASTERN),
        )


def test_parse_preferred_time_rejects_ambiguous_dst_local_time():
    with pytest.raises(PreferredTimeError, match="daylight saving"):
        parse_preferred_time(
            "2026-11-01 1:30 AM",
            timezone_name="America/New_York",
            now=NOW,
        )


def test_parse_preferred_time_rejects_unknown_timezone():
    with pytest.raises(PreferredTimeError, match="timezone"):
        parse_preferred_time(
            "2026-08-25 2:00 PM",
            timezone_name="Not/A_Timezone",
            now=NOW,
        )
