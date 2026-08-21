from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from text_back.calendar_stub import CalendarStub, slot_end
from text_back.store import Store
from text_back.telecom import Telecom


class BookingError(Exception):
    pass


class SlotUnavailableError(BookingError):
    pass


class CalendarEventError(BookingError):
    pass


def book_appointment(
    *,
    calendar: CalendarStub,
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
) -> dict:
    existing = store.appointment_by_conversation(conversation_id)
    if existing:
        return {"booked": True, "event_id": existing["event_id"], "duplicate": True}

    if store.is_opted_out(caller):
        raise BookingError("contact opted out; booking confirmation blocked")
    if start.tzinfo is None or start.utcoffset() is None:
        raise BookingError("appointment start must include a timezone")
    if duration_minutes <= 0:
        raise BookingError("appointment duration must be positive")
    try:
        business_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        raise BookingError("business timezone is invalid") from None

    end = slot_end(start, duration_minutes)
    first_check_available = calendar.is_free(start, end)
    if not first_check_available:
        _record_slot_check(
            store=store,
            caller=caller,
            conversation_id=conversation_id,
            start=start,
            available=False,
            checks=1,
        )
        raise SlotUnavailableError("requested slot is unavailable")
    # Recheck immediately before create, matching PRD.
    second_check_available = calendar.is_free(start, end)
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

    event_id = calendar.create_event(
        start=start,
        end=end,
        summary=f"{service} for {customer_name} ({caller})",
        location=location,
        caller=caller,
        conversation_id=conversation_id,
    )
    if not event_id:
        raise CalendarEventError("calendar did not return an event id")
    store.record_outcome(
        lead_id=caller,
        event_type="calendar.event_created",
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
    local_start = start.astimezone(business_timezone)
    when = local_start.strftime("%Y-%m-%d %I:%M %p %Z")
    confirmation_message_id = telecom.send_sms(
        to=caller,
        from_number=business_number,
        kind="booking_confirmation",
        body=(
            f"Booked: {service} on {when} at {location}. "
            f"This is {business_name}'s scheduling assistant. Event {event_id}."
        ),
    )
    store.record_outcome(
        lead_id=caller,
        event_type="appointment.confirmed",
        idempotency_key=f"calendar:{event_id}:confirmed",
        evidence_id=confirmation_message_id,
        metadata={"calendar_event_id": event_id},
    )
    return {"booked": True, "event_id": event_id, "duplicate": False}


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
