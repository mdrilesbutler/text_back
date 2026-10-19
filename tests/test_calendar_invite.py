"""The customer's email becomes a guest on the calendar event, so the provider emails the invite."""
import json
from datetime import datetime, timezone

from text_back.app import create_app
from text_back.calendar_stub import CalendarStub
from text_back.handlers import handle_sms_event
from text_back.messages import MessageSet, validate_templates
from text_back.telecom import FakeTelecom

NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
CALLER = "+15551112222"


class InvitingStub(CalendarStub):
    sends_invites = True


def run_conversation(tmp_path, calendar, replies):
    telecom = FakeTelecom()
    app = create_app(db_path=str(tmp_path / "i.db"), calendar=calendar, telecom=telecom, public_base_url="https://example.test",
                     business_name="Acme", timezone_name="America/New_York", now_provider=lambda: NOW)
    messages = MessageSet(validate_templates({"fields": "service, location, preferred_time, name, phone, email"}))
    for i, body in enumerate(replies):
        result = handle_sms_event(store=app.state.store, calendar=calendar, telecom=telecom, handoff_notifier=app.state.handoff_notifier,
                                  handoff_destination="ops", message_sid=f"m{i}", from_number=CALLER, to_number="+15553334444",
                                  body=body, business_name="Acme", timezone_name="America/New_York", appointment_duration_minutes=60,
                                  now=NOW, messages=messages)
    return app, telecom, result


def test_email_becomes_a_guest_and_the_confirmation_says_so(tmp_path):
    calendar = InvitingStub(timezone_name="America/New_York")
    app, telecom, result = run_conversation(tmp_path, calendar, ["trim", "12 Oak St", "thursday at 4", "Pat", "704 555 0123", "Pat@Example.com"])
    assert result["action"] == "booked"
    event = calendar.events[result["event_id"]]
    assert event["attendee_email"] == "pat@example.com"
    assert "Caller: +15551112222" in event["description"] and "Best phone: +17045550123" in event["description"]
    assert "Email: pat@example.com" in event["description"]
    body = [m for m in telecom.outbound if m.kind == "booking_confirmation"][-1].body
    assert "A calendar invite is on its way to pat@example.com." in body


def test_skipped_email_means_no_guest_and_no_invite_line(tmp_path):
    calendar = InvitingStub(timezone_name="America/New_York")
    app, telecom, result = run_conversation(tmp_path, calendar, ["trim", "12 Oak St", "thursday at 4", "Pat", "yes", "skip"])
    event = calendar.events[result["event_id"]]
    assert event["attendee_email"] is None
    assert "Best phone" not in event["description"]  # same number as the caller
    body = [m for m in telecom.outbound if m.kind == "booking_confirmation"][-1].body
    assert "invite" not in body


def test_provider_without_invitations_never_promises_one(tmp_path):
    calendar = CalendarStub(timezone_name="America/New_York")  # sends_invites is False
    app, telecom, result = run_conversation(tmp_path, calendar, ["trim", "12 Oak St", "thursday at 4", "Pat", "yes", "pat@example.com"])
    event = calendar.events[result["event_id"]]
    assert event["attendee_email"] is None
    assert "Email: pat@example.com" in event["description"]  # still recorded for the owner
    body = [m for m in telecom.outbound if m.kind == "booking_confirmation"][-1].body
    assert "invite" not in body


def test_google_adds_the_guest_and_asks_google_to_send_updates():
    from text_back.calendars.credentials import GoogleCredentials  # noqa: F401  (import check)
    from text_back.calendars.google import GoogleCalendarProvider, google_event_id
    from text_back.calendars.transport import FakeHttpTransport, HttpResponse
    start = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 20, 16, 0, tzinfo=timezone.utc)
    expected = google_event_id("conv", start)
    transport = FakeHttpTransport([HttpResponse(200, (), json.dumps({"id": expected}).encode())])
    provider = GoogleCalendarProvider(calendar_id="mike@example.test", token_provider=lambda: "tok", transport=transport)
    assert provider.sends_invites is True
    provider.create_event(start=start, end=end, summary="s", location="l", caller="+15551112222", conversation_id="conv",
                          attendee_email="pat@example.com", description="details")
    request = transport.requests[0]
    assert request.url.endswith("/calendars/mike%40example.test/events?sendUpdates=all")
    body = json.loads(request.body)
    assert body["attendees"] == [{"email": "pat@example.com"}] and body["description"] == "details"
    transport.responses.append(HttpResponse(200, (), json.dumps({"id": expected}).encode()))
    provider.create_event(start=start, end=end, summary="s", location="l", caller="+15551112222", conversation_id="conv")
    assert transport.requests[1].url.endswith("/events") and "attendees" not in json.loads(transport.requests[1].body)


def test_microsoft_adds_a_required_attendee():
    from text_back.calendars.microsoft import MicrosoftGraphProvider
    from text_back.calendars.transport import FakeHttpTransport, HttpResponse
    start = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 20, 16, 0, tzinfo=timezone.utc)
    transport = FakeHttpTransport([HttpResponse(201, (), json.dumps({"id": "AAMk1"}).encode())])
    provider = MicrosoftGraphProvider(user="mike@example.test", token_provider=lambda: "tok", transport=transport)
    assert provider.sends_invites is True
    provider.create_event(start=start, end=end, summary="s", location="l", caller="+15551112222", conversation_id="conv",
                          attendee_email="pat@example.com", description="details")
    body = json.loads(transport.requests[0].body)
    assert body["attendees"] == [{"emailAddress": {"address": "pat@example.com"}, "type": "required"}]
    assert body["body"]["content"] == "details"
