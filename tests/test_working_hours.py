"""Working hours: parsing, the slot check behind booking, and the owner-facing description."""
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from text_back.working_hours import (
    DEFAULT_SET_HOURS,
    WEEKDAYS,
    describe,
    hhmm_to_minutes,
    is_corrupt,
    parse_working_hours,
    slot_within_hours,
)

NY = ZoneInfo("America/New_York")
WEEKDAY_HOURS = {**{d: {"open": "08:00", "close": "17:00"} for d in WEEKDAYS[:5]}, "sat": None, "sun": None}


def _slot(year, month, day, hour, minute=0, *, minutes=60, fold=0):
    start = datetime(year, month, day, hour, minute, tzinfo=NY, fold=fold)
    return start, start + timedelta(minutes=minutes)


def test_parse_accepts_the_documented_shape_and_fills_missing_days_as_closed():
    hours = parse_working_hours(json.dumps({"mon": {"open": "08:00", "close": "17:00"}, "sat": None}))
    assert hours["mon"] == {"open": "08:00", "close": "17:00"}
    assert all(hours[d] is None for d in WEEKDAYS if d != "mon")
    assert parse_working_hours(json.dumps({"fri": {"open": "08:00", "close": "24:00"}}))["fri"]["close"] == "24:00"


@pytest.mark.parametrize("raw", [
    None, "", "   ", "{nope", "[]", json.dumps({"funday": {"open": "08:00", "close": "17:00"}}),
    json.dumps({"mon": {"open": "08:07", "close": "17:00"}}), json.dumps({"mon": {"open": "17:00", "close": "08:00"}}),
    json.dumps({"mon": {"open": "08:00"}}), json.dumps({"mon": "08:00-17:00"}), json.dumps({d: None for d in WEEKDAYS}),
])
def test_absent_or_invalid_values_mean_any_time(raw):
    assert parse_working_hours(raw) is None


def test_is_corrupt_flags_only_a_stored_value_that_cannot_be_used():
    assert is_corrupt("{nope") and is_corrupt(json.dumps({"mon": {"open": "9", "close": "x"}}))
    assert not is_corrupt(None) and not is_corrupt("") and not is_corrupt(json.dumps(DEFAULT_SET_HOURS))


def test_hhmm_to_minutes_handles_midnight_close():
    assert hhmm_to_minutes("00:00") == 0 and hhmm_to_minutes("08:30") == 510 and hhmm_to_minutes("24:00") == 1440
    with pytest.raises(ValueError):
        hhmm_to_minutes("25:00")


def test_no_hours_means_every_slot_is_fine():
    start, end = _slot(2026, 10, 24, 23)  # Saturday night
    assert slot_within_hours(start, end, None, NY)


def test_inside_the_window_passes_and_the_edges_are_inclusive():
    assert slot_within_hours(*_slot(2026, 10, 19, 10), WEEKDAY_HOURS, NY)  # Monday 10:00-11:00
    assert slot_within_hours(*_slot(2026, 10, 19, 8), WEEKDAY_HOURS, NY)  # opens 08:00
    assert slot_within_hours(*_slot(2026, 10, 19, 16), WEEKDAY_HOURS, NY)  # ends exactly at close


def test_a_slot_that_ends_after_close_or_starts_before_open_is_rejected():
    assert not slot_within_hours(*_slot(2026, 10, 19, 16, 30), WEEKDAY_HOURS, NY)  # 16:30-17:30
    assert not slot_within_hours(*_slot(2026, 10, 19, 7, 30), WEEKDAY_HOURS, NY)  # 07:30-08:30
    assert not slot_within_hours(*_slot(2026, 10, 19, 17), WEEKDAY_HOURS, NY)


def test_a_closed_day_rejects_everything():
    assert not slot_within_hours(*_slot(2026, 10, 24, 10), WEEKDAY_HOURS, NY)  # Saturday


def test_midnight_close_allows_an_end_exactly_at_midnight_but_not_past_it():
    late = {**WEEKDAY_HOURS, "sat": {"open": "20:00", "close": "24:00"}}
    assert slot_within_hours(*_slot(2026, 10, 24, 23), late, NY)  # 23:00-00:00
    assert not slot_within_hours(*_slot(2026, 10, 24, 23, 30), late, NY)  # crosses midnight


def test_the_check_uses_the_business_timezone_not_the_callers():
    utc_start = datetime(2026, 10, 19, 14, 0, tzinfo=ZoneInfo("UTC"))  # 10:00 EDT Monday
    assert slot_within_hours(utc_start, utc_start + timedelta(hours=1), WEEKDAY_HOURS, NY)
    utc_late = datetime(2026, 10, 19, 21, 0, tzinfo=ZoneInfo("UTC"))  # 17:00 EDT
    assert not slot_within_hours(utc_late, utc_late + timedelta(hours=1), WEEKDAY_HOURS, NY)


def test_dst_spring_forward_day_reads_the_clock_like_a_person():
    all_day = {d: {"open": "00:00", "close": "24:00"} for d in WEEKDAYS}
    start, end = _slot(2026, 3, 8, 1, 30)  # 01:30 EST; the clock jumps 02:00 -> 03:00
    assert slot_within_hours(start, end, all_day, NY)
    assert not slot_within_hours(start, end, {**all_day, "sun": {"open": "08:00", "close": "17:00"}}, NY)


def test_dst_fall_back_day_is_handled_for_both_folds():
    all_day = {d: {"open": "00:00", "close": "24:00"} for d in WEEKDAYS}
    sunday_hours = {**WEEKDAY_HOURS, "sun": {"open": "08:00", "close": "17:00"}}
    for fold in (0, 1):
        start, end = _slot(2026, 11, 1, 1, 30, fold=fold)
        assert slot_within_hours(start, end, all_day, NY)
        assert not slot_within_hours(start, end, sunday_hours, NY)
    assert slot_within_hours(*_slot(2026, 11, 1, 10), sunday_hours, NY)


def test_describe_groups_consecutive_days():
    assert describe(None) == "Any day, any time"
    assert describe(WEEKDAY_HOURS) == "Mon–Fri 8:00 AM–5:00 PM"
    with_sat = {**WEEKDAY_HOURS, "sat": {"open": "09:00", "close": "12:00"}}
    assert describe(with_sat) == "Mon–Fri 8:00 AM–5:00 PM, Sat 9:00 AM–12:00 PM"
    split = {**WEEKDAY_HOURS, "wed": None}
    assert describe(split) == "Mon–Tue 8:00 AM–5:00 PM, Thu–Fri 8:00 AM–5:00 PM"
    assert describe({**WEEKDAY_HOURS, "fri": {"open": "08:00", "close": "24:00"}}).endswith("Fri 8:00 AM–midnight")
