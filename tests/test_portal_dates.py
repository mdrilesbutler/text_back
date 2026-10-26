from datetime import datetime, timezone

import pytest

from text_back.portal_dates import clock, day, when

NY = "America/New_York"


def test_full_date_from_a_datetime_in_the_business_timezone():
    assert when(datetime(2026, 10, 23, 18, 40, tzinfo=timezone.utc), NY) == "Fri, Oct 23, 2:40 PM"


def test_iso_strings_from_the_database_are_accepted():
    assert when("2026-10-23T18:40:00+00:00", NY) == "Fri, Oct 23, 2:40 PM"


def test_same_day_reads_today():
    now = datetime(2026, 10, 26, 20, 0, tzinfo=timezone.utc)
    assert when(datetime(2026, 10, 26, 13, 12, tzinfo=timezone.utc), NY, now) == "Today, 9:12 AM"


def test_another_year_shows_the_year():
    now = datetime(2027, 1, 2, 12, 0, tzinfo=timezone.utc)
    assert when(datetime(2026, 10, 23, 18, 40, tzinfo=timezone.utc), NY, now) == "Fri, Oct 23, 2026, 2:40 PM"


def test_day_and_clock_helpers():
    at = datetime(2026, 10, 23, 18, 5, tzinfo=timezone.utc)
    assert day(at, NY) == "Fri, Oct 23" and clock(at, NY) == "2:05 PM"


def test_naive_datetimes_are_refused():
    with pytest.raises(ValueError):
        when(datetime(2026, 10, 23, 18, 40), NY)
