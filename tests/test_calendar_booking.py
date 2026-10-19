from datetime import datetime, timedelta, timezone

from text_back.booking import BookingError, book_appointment
from text_back.calendar_stub import CalendarStub
from text_back.store import Store
from text_back.telecom import FakeTelecom


TZ = timezone.utc
SLOT = datetime(2026, 8, 20, 15, 0, tzinfo=TZ)


def _book(calendar=None, store=None, telecom=None, start=SLOT, **overrides):
    calendar = calendar or CalendarStub()
    store = store or Store()
    telecom = telecom or FakeTelecom()
    payload = {
        "caller": "+15551112222",
        "business_number": "+15553334444",
        "service": "tree removal",
        "location": "12 Oak St",
        "customer_name": "John Smith",
        "business_name": "Mike",
        "timezone_name": "UTC",
        "start": start,
        "duration_minutes": 60,
        "conversation_id": "conv-1",
    }
    payload.update(overrides)
    return book_appointment(calendar=calendar, store=store, telecom=telecom, **payload), calendar, store, telecom


def test_books_only_when_slot_is_free_and_persists_event_id():
    result, calendar, store, telecom = _book()
    assert result["booked"] is True
    assert result["event_id"]
    assert calendar.events[result["event_id"]]["location"] == "12 Oak St"
    assert "John Smith" in calendar.events[result["event_id"]]["summary"]
    assert store.appointment_by_event(result["event_id"])["event_id"] == result["event_id"]
    assert len(telecom.outbound) == 1
    assert telecom.outbound[0].kind == "booking_confirmation"
    assert "Thursday, Aug 20" in telecom.outbound[0].body
    assert "3:00 PM" in telecom.outbound[0].body
    assert "UTC" in telecom.outbound[0].body
    assert "Mike" in telecom.outbound[0].body


def test_conflict_does_not_create_event_or_claim_booking():
    calendar = CalendarStub()
    calendar.busy.append((SLOT, SLOT + timedelta(hours=1)))
    try:
        book_appointment(
            calendar=calendar,
            store=Store(),
            telecom=FakeTelecom(),
            caller="+15551112222",
            business_number="+15553334444",
            service="trim",
            location="1 Main",
            customer_name="John Smith",
            business_name="Mike",
            timezone_name="UTC",
            start=SLOT,
            duration_minutes=60,
            conversation_id="conv-2",
        )
    except BookingError as exc:
        assert "unavailable" in str(exc).lower()
    else:
        raise AssertionError("expected BookingError")
    assert calendar.events == {}


def test_create_failure_does_not_send_confirmation():
    class BrokenCalendar(CalendarStub):
        def create_event(self, **kwargs):
            return None

    telecom = FakeTelecom()
    try:
        book_appointment(
            calendar=BrokenCalendar(),
            store=Store(),
            telecom=telecom,
            caller="+15551112222",
            business_number="+15553334444",
            service="trim",
            location="1 Main",
            customer_name="John Smith",
            business_name="Mike",
            timezone_name="UTC",
            start=SLOT,
            duration_minutes=60,
            conversation_id="conv-3",
        )
    except BookingError as exc:
        assert "event" in str(exc).lower()
    else:
        raise AssertionError("expected BookingError")
    assert telecom.outbound == []


def test_duplicate_conversation_booking_is_idempotent():
    calendar = CalendarStub()
    store = Store()
    telecom = FakeTelecom()
    first, *_ = _book(calendar=calendar, store=store, telecom=telecom, conversation_id="same")
    second, *_ = _book(calendar=calendar, store=store, telecom=telecom, conversation_id="same")
    assert first["event_id"] == second["event_id"]
    assert len(calendar.events) == 1
    assert len(telecom.outbound) == 1


def test_opted_out_contact_does_not_receive_booking_confirmation():
    store = Store()
    store.set_opted_out("+15551112222", True)
    telecom = FakeTelecom()
    try:
        book_appointment(
            calendar=CalendarStub(),
            store=store,
            telecom=telecom,
            caller="+15551112222",
            business_number="+15553334444",
            service="trim",
            location="1 Main",
            customer_name="John Smith",
            business_name="Mike",
            timezone_name="UTC",
            start=SLOT,
            duration_minutes=60,
            conversation_id="conv-optout",
        )
    except BookingError as exc:
        assert "opt" in str(exc).lower()
    else:
        raise AssertionError("expected BookingError")
    assert telecom.outbound == []


def test_naive_start_time_is_rejected_without_event_or_confirmation():
    calendar, telecom = CalendarStub(), FakeTelecom()

    try:
        _book(
            calendar=calendar,
            telecom=telecom,
            start=datetime(2026, 8, 25, 14, 0),
            conversation_id="conv-naive",
        )
    except BookingError as exc:
        assert "timezone" in str(exc).lower()
    else:
        raise AssertionError("expected BookingError")

    assert calendar.events == {}
    assert telecom.outbound == []


def test_active_handoff_blocks_new_calendar_event():
    import pytest
    calendar,store,telecom=CalendarStub(),Store(),FakeTelecom()
    store.request_handoff('+15551112222','customer_requested')
    with pytest.raises(BookingError,match='handoff'):
        _book(calendar=calendar,store=store,telecom=telecom)
    assert calendar.events=={}
    assert telecom.outbound==[]
