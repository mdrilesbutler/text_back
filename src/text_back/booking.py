from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from text_back.calendar_stub import slot_end
from text_back.calendars.protocol import CalendarProvider, CalendarProviderError
from text_back.sms import atomic_sms_handler, enqueue_sms
from text_back.store import Store
from text_back.telecom import Telecom


class BookingError(Exception):
    pass


class SlotUnavailableError(BookingError):
    pass


class CalendarEventError(BookingError):
    pass


@atomic_sms_handler
def book_appointment(
    *,
    calendar: CalendarProvider,
    store: Store,
    telecom: Telecom,
    caller: str,
    business_number: str,
    service: str,
    location: str,
    customer_name: str,
    business_name: str,
    timezone_name: str,
    start: datetime,
    duration_minutes: int,
    conversation_id: str,
    now: datetime | None = None,
) -> dict:
    existing = store.appointment_by_conversation(conversation_id)
    if existing:
        _queue_confirmation(store, telecom, existing, business_number, business_name, timezone_name, now)
        return {"booked": True, "event_id": existing["event_id"], "duplicate": True}

    if store.active_handoff(caller) is not None:
        raise BookingError("active handoff; automated booking blocked")
    if store.is_opted_out(caller):
        raise BookingError("contact opted out; booking confirmation blocked")
    if start.tzinfo is None or start.utcoffset() is None:
        raise BookingError("appointment start must include a timezone")
    if duration_minutes <= 0:
        raise BookingError("appointment duration must be positive")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        raise BookingError("business timezone is invalid") from None

    end = slot_end(start, duration_minutes)
    try:
        first_check_available = calendar.is_free(start, end)
    except CalendarProviderError:
        raise CalendarEventError(
            "calendar availability could not be verified"
        ) from None
    if not first_check_available:
        # A prior create may have reached the provider before the local commit.
        # Verify its deterministic identity before treating our own event as a conflict.
        try:
            recovered = calendar.find_event(conversation_id=conversation_id, start=start, end=end) if hasattr(calendar, 'find_event') else None
        except CalendarProviderError:
            raise CalendarEventError("calendar event recovery could not be verified") from None
        if recovered:
            return _finish_booking(store=store, telecom=telecom, caller=caller, business_number=business_number,
                service=service, location=location, business_name=business_name, timezone_name=timezone_name,
                start=start, conversation_id=conversation_id, event_id=recovered, now=now)
        _record_slot_check(store=store, caller=caller, conversation_id=conversation_id, start=start, available=False, checks=1)
        raise SlotUnavailableError("requested slot is unavailable")
    # Recheck immediately before create, matching PRD.
    try:
        second_check_available = calendar.is_free(start, end)
    except CalendarProviderError:
        raise CalendarEventError(
            "calendar availability could not be verified"
        ) from None
    _record_slot_check(
        store=store,
        caller=caller,
        conversation_id=conversation_id,
        start=start,
        available=second_check_available,
        checks=2,
    )
    if not second_check_available:
        raise SlotUnavailableError("requested slot is unavailable")

    try:
        event_id = calendar.create_event(
            start=start,
            end=end,
            summary=f"{service} for {customer_name} ({caller})",
            location=location,
            caller=caller,
            conversation_id=conversation_id,
        )
    except CalendarProviderError:
        raise CalendarEventError(
            "calendar provider failed; booking not confirmed"
        ) from None
    if not event_id:
        raise CalendarEventError("calendar did not return an event id")
    return _finish_booking(store=store, telecom=telecom, caller=caller, business_number=business_number,
        service=service, location=location, business_name=business_name, timezone_name=timezone_name,
        start=start, conversation_id=conversation_id, event_id=event_id, now=now)


def _finish_booking(*, store, telecom, caller, business_number, service, location,
                    business_name, timezone_name, start, conversation_id, event_id, now):
    store.record_outcome(
        lead_id=caller,
        event_type="calendar.event_created",
        occurred_at=(now or datetime.now(timezone.utc)).isoformat(),
        idempotency_key=f"calendar:{event_id}:created",
        evidence_id=event_id,
        metadata={"conversation_id": conversation_id},
    )

    store.save_appointment(
        conversation_id=conversation_id,
        event_id=event_id,
        caller=caller,
        start=start.isoformat(),
        location=location,
        service=service,
    )
    store.cancel_followup(caller, "booked")
    _queue_confirmation(store, telecom, store.appointment_by_conversation(conversation_id),
                        business_number, business_name, timezone_name, now)
    return {"booked": True, "event_id": event_id, "duplicate": False}


def _queue_confirmation(store, telecom, appointment, business_number, business_name, timezone_name, now):
    event_id = appointment['event_id']
    when = datetime.fromisoformat(appointment['start']).astimezone(ZoneInfo(timezone_name)).strftime("%A, %b %d at %I:%M %p %Z").replace(" 0", " ")
    key = f"{appointment['conversation_id']}:confirmation:{event_id}"
    enqueue_sms(store=store, key=key, to=appointment['caller'], from_number=business_number,
                kind="booking_confirmation", now=now or datetime.now(timezone.utc),
                body=f"Booked: {appointment['service']} on {when} at {appointment['location']}. This is {business_name}'s scheduling assistant. Event {event_id}.",
                completion={"event_type": "appointment.confirmed", "outcome_key": f"calendar:{event_id}:confirmed", "metadata": {"calendar_event_id": event_id}})
    telecom.keys.append(key)


def _record_slot_check(
    *,
    store: Store,
    caller: str,
    conversation_id: str,
    start: datetime,
    available: bool,
    checks: int,
) -> None:
    store.record_outcome(
        lead_id=caller,
        event_type="calendar.slot_checked",
        idempotency_key=f"conversation:{conversation_id}:slot:{start.isoformat()}",
        evidence_id=start.isoformat(),
        metadata={"available": available, "checks": checks},
    )
