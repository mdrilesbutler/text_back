from datetime import datetime, timedelta, timezone

import pytest

from text_back.calendar_stub import CalendarStub
from text_back.handoff import FakeHandoffNotifier
from text_back.handlers import handle_sms_event, handle_voice_event
from text_back.store import Store
from text_back.telecom import FakeTelecom


CALLER = "+15551112222"
BUSINESS_NUMBER = "+15553334444"
NOW = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)
REQUESTED_START = datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc)


def _send(
    *,
    store: Store,
    calendar: CalendarStub,
    telecom: FakeTelecom,
    notifier: FakeHandoffNotifier,
    message_sid: str,
    body: str,
) -> dict:
    return handle_sms_event(
        store=store,
        calendar=calendar,
        telecom=telecom,
        handoff_notifier=notifier,
        handoff_destination="operator-queue",
        message_sid=message_sid,
        from_number=CALLER,
        to_number=BUSINESS_NUMBER,
        body=body,
        business_name="Oak & Pine Tree Care",
        timezone_name="UTC",
        appointment_duration_minutes=60,
        now=NOW,
    )


def test_outcome_store_is_append_only_and_idempotent_by_key():
    store = Store()

    first = store.record_outcome(
        lead_id=CALLER,
        event_type="call.missed",
        idempotency_key="call:CA-1:missed",
        evidence_id="CA-1",
        metadata={"wiring_mode": "forwarded"},
    )
    duplicate = store.record_outcome(
        lead_id=CALLER,
        event_type="call.missed",
        idempotency_key="call:CA-1:missed",
        evidence_id="different-evidence-must-not-overwrite",
        metadata={"wiring_mode": "managed"},
    )

    assert first is True
    assert duplicate is False
    events = store.list_outcome_events(CALLER)
    assert len(events) == 1
    assert events[0]["event_type"] == "call.missed"
    assert events[0]["evidence_id"] == "CA-1"
    assert events[0]["metadata"] == {"wiring_mode": "forwarded"}
    assert events[0]["occurred_at"]


def test_missed_call_records_contact_evidence_ids_in_order():
    store, telecom = Store(), FakeTelecom()

    result = handle_voice_event(
        store=store,
        telecom=telecom,
        call_sid="CA-outcome-1",
        call_status="ringing",
        from_number=CALLER,
        to_number=BUSINESS_NUMBER,
        wiring_mode="forwarded",
        business_name="Oak & Pine Tree Care",
    )

    assert result["action"] == "sent_intro"
    events = store.list_outcome_events(CALLER)
    assert [event["event_type"] for event in events] == [
        "call.missed",
        "sms.initial_sent",
    ]
    assert events[0]["evidence_id"] == "CA-outcome-1"
    assert events[1]["evidence_id"] == "SM-0001"


def test_duplicate_missed_call_does_not_duplicate_outcome_events():
    store, telecom = Store(), FakeTelecom()
    payload = {
        "store": store,
        "telecom": telecom,
        "call_sid": "CA-outcome-duplicate",
        "call_status": "ringing",
        "from_number": CALLER,
        "to_number": BUSINESS_NUMBER,
        "wiring_mode": "forwarded",
        "business_name": "Oak & Pine Tree Care",
    }

    first = handle_voice_event(**payload)
    second = handle_voice_event(**payload)

    assert first["action"] == "sent_intro"
    assert second["duplicate"] is True
    assert [
        event["event_type"] for event in store.list_outcome_events(CALLER)
    ] == ["call.missed", "sms.initial_sent"]


def test_complete_conversation_records_evidence_backed_booking_lifecycle():
    store = Store()
    calendar = CalendarStub()
    telecom = FakeTelecom()
    notifier = FakeHandoffNotifier()
    replies = (
        ("SM-in-1", "tree removal"),
        ("SM-in-2", "12 Oak St"),
        ("SM-in-3", "2026-08-25 2:00 PM"),
        ("SM-in-4", "John Smith"),
    )

    result = None
    for message_sid, body in replies:
        result = _send(
            store=store,
            calendar=calendar,
            telecom=telecom,
            notifier=notifier,
            message_sid=message_sid,
            body=body,
        )

    assert result is not None
    assert result["action"] == "booked"
    event_id = result["event_id"]
    events = store.list_outcome_events(CALLER)
    assert [event["event_type"] for event in events] == [
        "sms.customer_replied",
        "lead.field_captured",
        "sms.customer_replied",
        "lead.field_captured",
        "sms.customer_replied",
        "lead.field_captured",
        "sms.customer_replied",
        "lead.field_captured",
        "lead.qualified",
        "calendar.slot_checked",
        "calendar.event_created",
        "appointment.confirmed",
    ]
    field_events = [
        event for event in events if event["event_type"] == "lead.field_captured"
    ]
    assert [event["metadata"]["field"] for event in field_events] == [
        "service",
        "location",
        "preferred_time",
        "name",
    ]
    assert all(event["evidence_id"].startswith("SM-in-") for event in field_events)
    assert events[-3]["metadata"]["available"] is True
    assert events[-2]["evidence_id"] == event_id
    assert events[-1]["metadata"]["calendar_event_id"] == event_id
    assert events[-1]["evidence_id"] == "SM-0004"


def test_unavailable_slot_records_failed_check_without_booking_evidence():
    store = Store()
    calendar = CalendarStub()
    calendar.busy.append((REQUESTED_START, REQUESTED_START + timedelta(hours=1)))
    telecom = FakeTelecom()
    notifier = FakeHandoffNotifier()
    replies = (
        ("SM-busy-1", "tree removal"),
        ("SM-busy-2", "12 Oak St"),
        ("SM-busy-3", "2026-08-25 2:00 PM"),
        ("SM-busy-4", "John Smith"),
    )

    for message_sid, body in replies:
        result = _send(
            store=store,
            calendar=calendar,
            telecom=telecom,
            notifier=notifier,
            message_sid=message_sid,
            body=body,
        )

    assert result["action"] == "slot_unavailable"
    events = store.list_outcome_events(CALLER)
    slot_events = [event for event in events if event["event_type"] == "calendar.slot_checked"]
    assert len(slot_events) == 1
    assert slot_events[0]["metadata"]["available"] is False
    event_types = {event["event_type"] for event in events}
    assert "calendar.event_created" not in event_types
    assert "appointment.confirmed" not in event_types


def test_handoff_outcome_uses_notifier_alert_as_evidence():
    store, calendar, telecom, notifier = (
        Store(),
        CalendarStub(),
        FakeTelecom(),
        FakeHandoffNotifier(),
    )

    result = _send(
        store=store,
        calendar=calendar,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-handoff-outcome",
        body="human please",
    )

    assert result["action"] == "handoff_requested"
    events = store.list_outcome_events(CALLER)
    assert [event["event_type"] for event in events] == [
        "sms.customer_replied",
        "lead.handoff_requested",
    ]
    assert events[-1]["evidence_id"] == result["alert_id"]
    assert events[-1]["metadata"] == {"reason": "customer_requested"}


def test_confirmation_transport_failure_has_no_confirmed_outcome():
    class ConfirmationFailureTelecom(FakeTelecom):
        def send_sms(self, *, to, body, from_number, kind):
            if kind == "booking_confirmation":
                raise RuntimeError("simulated confirmation transport failure")
            return super().send_sms(
                to=to,
                body=body,
                from_number=from_number,
                kind=kind,
            )

    store = Store()
    calendar = CalendarStub()
    telecom = ConfirmationFailureTelecom()
    notifier = FakeHandoffNotifier()
    replies = (
        ("SM-fail-1", "tree removal"),
        ("SM-fail-2", "12 Oak St"),
        ("SM-fail-3", "2026-08-25 2:00 PM"),
        ("SM-fail-4", "John Smith"),
    )

    with pytest.raises(RuntimeError, match="transport failure"):
        for message_sid, body in replies:
            _send(
                store=store,
                calendar=calendar,
                telecom=telecom,
                notifier=notifier,
                message_sid=message_sid,
                body=body,
            )

    event_types = {
        event["event_type"] for event in store.list_outcome_events(CALLER)
    }
    assert "calendar.event_created" in event_types
    assert "appointment.confirmed" not in event_types
