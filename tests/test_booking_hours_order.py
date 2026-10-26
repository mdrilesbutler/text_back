"""Working hours are enforced at booking time, but never ahead of recovering our own event.

If the owner narrows working hours while a booking retry is pending for a slot whose calendar
event already exists, the retry must recover that event and confirm it, not refuse it and leave
an orphaned event. A slot outside the hours with no existing event is refused like a busy slot.
"""
import json
from datetime import datetime, timezone

import pytest

from text_back.booking import SlotUnavailableError, book_appointment
from text_back.store import Store
from text_back.telecom import FakeTelecom


class HoursCalendar:
    provider_name = "fake"

    def __init__(self, *, free: bool, existing: str | None):
        self.free, self.existing, self.created = free, existing, 0

    def is_free(self, start, end):
        return self.free

    def find_event(self, *, conversation_id, start, end):
        return self.existing

    def create_event(self, **kwargs):
        self.created += 1
        return "evt-new"


def _store(tmp_path, hours: dict | None):
    store = Store(str(tmp_path / "t.db"))
    if hours is not None:
        store.set_setting("working_hours", json.dumps(hours))
    return store


def _book(store, calendar, start):
    return book_appointment(
        calendar=calendar, store=store, telecom=FakeTelecom(), caller="+19805550141",
        business_number="+17045550100", service="tree removal", location="12 Elm St",
        customer_name="Dana", business_name="Oak & Pine Tree Care", timezone_name="America/New_York",
        start=start, duration_minutes=60, conversation_id="+19805550141",
        now=datetime(2026, 10, 26, 14, 0, tzinfo=timezone.utc),
    )


MON_TO_FRI_8_TO_5 = {d: {"open": "08:00", "close": "17:00"} for d in ("mon", "tue", "wed", "thu", "fri")}
SATURDAY_10AM_EDT = datetime(2026, 10, 31, 14, 0, tzinfo=timezone.utc)
TUESDAY_10AM_EDT = datetime(2026, 10, 27, 14, 0, tzinfo=timezone.utc)


def test_recovery_runs_before_the_hours_check(tmp_path):
    store = _store(tmp_path, MON_TO_FRI_8_TO_5)
    calendar = HoursCalendar(free=False, existing="evt-already-there")
    result = _book(store, calendar, SATURDAY_10AM_EDT)
    assert result["booked"] is True and result["event_id"] == "evt-already-there"
    assert calendar.created == 0
    assert store.appointment_by_conversation("+19805550141")["event_id"] == "evt-already-there"


def test_outside_hours_without_an_existing_event_is_refused(tmp_path):
    store = _store(tmp_path, MON_TO_FRI_8_TO_5)
    calendar = HoursCalendar(free=True, existing=None)
    with pytest.raises(SlotUnavailableError, match="outside working hours"):
        _book(store, calendar, SATURDAY_10AM_EDT)
    assert calendar.created == 0
    assert store.appointment_by_conversation("+19805550141") is None


def test_inside_hours_books_normally(tmp_path):
    store = _store(tmp_path, MON_TO_FRI_8_TO_5)
    calendar = HoursCalendar(free=True, existing=None)
    assert _book(store, calendar, TUESDAY_10AM_EDT)["event_id"] == "evt-new"


def test_no_hours_setting_means_any_time(tmp_path):
    store = _store(tmp_path, None)
    assert _book(store, HoursCalendar(free=True, existing=None), SATURDAY_10AM_EDT)["booked"] is True
