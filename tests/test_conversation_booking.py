import base64
import hashlib
import hmac
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.calendar_stub import CalendarStub
from text_back.handoff import FakeHandoffNotifier
from text_back.handlers import handle_sms_event
from text_back.store import Store
from text_back.telecom import FakeTelecom


CALLER = "+15551112222"
BUSINESS_NUMBER = "+15553334444"
TIMEZONE_NAME = "America/New_York"
EASTERN = ZoneInfo(TIMEZONE_NAME)
NOW = datetime(2026, 8, 21, 10, 0, tzinfo=EASTERN)
REQUESTED_START = datetime(2026, 8, 25, 14, 0, tzinfo=EASTERN)
WEBHOOK_SECRET = "test-webhook-secret"
SMS_URL = "https://example.test/webhooks/sms"


def _send(
    *,
    store: Store,
    calendar: CalendarStub,
    telecom: FakeTelecom,
    message_sid: str,
    body: str,
) -> dict:
    return handle_sms_event(
        store=store,
        calendar=calendar,
        telecom=telecom,
        handoff_notifier=FakeHandoffNotifier(),
        handoff_destination="operator-queue",
        message_sid=message_sid,
        from_number=CALLER,
        to_number=BUSINESS_NUMBER,
        body=body,
        business_name="Oak & Pine Tree Care",
        timezone_name=TIMEZONE_NAME,
        appointment_duration_minutes=60,
        now=NOW,
    )


def _collect_through_time(store, calendar, telecom, preferred_time="2026-08-25 2:00 PM"):
    _send(
        store=store,
        calendar=calendar,
        telecom=telecom,
        message_sid="SM-service",
        body="tree removal",
    )
    _send(
        store=store,
        calendar=calendar,
        telecom=telecom,
        message_sid="SM-location",
        body="12 Oak St",
    )
    return _send(
        store=store,
        calendar=calendar,
        telecom=telecom,
        message_sid="SM-time",
        body=preferred_time,
    )


def _sign(params: dict[str, str]) -> str:
    data = SMS_URL + "".join(f"{key}{value}" for key, value in sorted(params.items()))
    digest = hmac.new(WEBHOOK_SECRET.encode(), data.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def test_complete_conversation_books_all_fields_and_confirms_after_event_id():
    store, calendar, telecom = Store(), CalendarStub(TIMEZONE_NAME), FakeTelecom()
    _collect_through_time(store, calendar, telecom)

    result = _send(
        store=store,
        calendar=calendar,
        telecom=telecom,
        message_sid="SM-name",
        body="John Smith",
    )

    assert result["action"] == "booked"
    assert result["event_id"]
    event = calendar.events[result["event_id"]]
    assert event["start"] == REQUESTED_START
    assert event["end"] == REQUESTED_START + timedelta(minutes=60)
    assert event["location"] == "12 Oak St"
    assert "tree removal" in event["summary"]
    assert "John Smith" in event["summary"]
    appointment = store.appointment_by_event(result["event_id"])
    assert appointment is not None
    assert appointment["caller"] == CALLER
    assert telecom.outbound[-1].kind == "booking_confirmation"
    assert result["event_id"] in telecom.outbound[-1].body
    assert "Oak & Pine Tree Care" in telecom.outbound[-1].body
    assert "EDT" in telecom.outbound[-1].body


def test_ambiguous_preferred_time_is_not_stored_and_gets_format_reprompt():
    store, calendar, telecom = Store(), CalendarStub(TIMEZONE_NAME), FakeTelecom()

    result = _collect_through_time(
        store,
        calendar,
        telecom,
        preferred_time="tomorrow afternoon",
    )

    assert result["action"] == "preferred_time_invalid"
    assert "preferred_time" not in store.get_conversation_fields(CALLER)
    assert telecom.outbound[-1].kind == "preferred_time_reprompt"
    assert "YYYY-MM-DD 2:00 PM" in telecom.outbound[-1].body
    assert calendar.events == {}


def test_unavailable_slot_is_not_confirmed_and_time_is_collected_again():
    store, calendar, telecom = Store(), CalendarStub(TIMEZONE_NAME), FakeTelecom()
    calendar.busy.append((REQUESTED_START, REQUESTED_START + timedelta(hours=1)))
    _collect_through_time(store, calendar, telecom)

    result = _send(
        store=store,
        calendar=calendar,
        telecom=telecom,
        message_sid="SM-name",
        body="John Smith",
    )

    assert result["action"] == "slot_unavailable"
    assert store.appointment_by_conversation(CALLER) is None
    fields = store.get_conversation_fields(CALLER)
    assert "preferred_time" not in fields
    assert fields["name"] == "John Smith"
    assert telecom.outbound[-1].kind == "slot_unavailable"
    assert all(item.kind != "booking_confirmation" for item in telecom.outbound)


def test_calendar_create_failure_never_sends_booking_confirmation():
    class BrokenCalendar(CalendarStub):
        def create_event(self, **kwargs):
            return None

    store = Store()
    calendar = BrokenCalendar(TIMEZONE_NAME)
    telecom = FakeTelecom()
    _collect_through_time(store, calendar, telecom)

    result = _send(
        store=store,
        calendar=calendar,
        telecom=telecom,
        message_sid="SM-name",
        body="John Smith",
    )

    assert result["action"] == "booking_failed"
    assert store.appointment_by_conversation(CALLER) is None
    assert telecom.outbound[-1].kind == "booking_error"
    assert all(item.kind != "booking_confirmation" for item in telecom.outbound)


def test_webhook_conversation_uses_configured_calendar_timezone_and_duration():
    store, calendar, telecom = Store(), CalendarStub(TIMEZONE_NAME), FakeTelecom()
    app = create_app(
        webhook_secret=WEBHOOK_SECRET,
        public_base_url="https://example.test",
        store=store,
        calendar=calendar,
        telecom=telecom,
        business_name="Oak & Pine Tree Care",
        timezone_name=TIMEZONE_NAME,
        appointment_duration_minutes=90,
        now_provider=lambda: NOW,
    )
    client = TestClient(app)
    replies = (
        ("SM-web-service", "tree removal"),
        ("SM-web-location", "12 Oak St"),
        ("SM-web-time", "2026-08-25 2:00 PM"),
        ("SM-web-name", "John Smith"),
    )

    response = None
    for message_sid, body in replies:
        params = {
            "MessageSid": message_sid,
            "From": CALLER,
            "To": BUSINESS_NUMBER,
            "Body": body,
        }
        response = client.post(
            "/webhooks/sms",
            data=params,
            headers={"X-Twilio-Signature": _sign(params)},
        )
        assert response.status_code == 200

    assert response is not None
    payload = response.json()
    assert payload["action"] == "booked"
    event = calendar.events[payload["event_id"]]
    assert event["start"] == REQUESTED_START
    assert event["end"] == REQUESTED_START + timedelta(minutes=90)
