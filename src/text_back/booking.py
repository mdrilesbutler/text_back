from __future__ import annotations

from datetime import datetime

from text_back.calendar_stub import CalendarStub, slot_end
from text_back.store import Store
from text_back.telecom import FakeTelecom


class BookingError(Exception):
    pass


def book_appointment(
    *,
    calendar: CalendarStub,
    store: Store,
    telecom: FakeTelecom,
    caller: str,
    business_number: str,
    service: str,
    location: str,
    start: datetime,
    duration_minutes: int,
    conversation_id: str,
) -> dict:
    existing = store.appointment_by_conversation(conversation_id)
    if existing:
        return {"booked": True, "event_id": existing["event_id"], "duplicate": True}

    if store.is_opted_out(caller):
        raise BookingError("contact opted out; booking confirmation blocked")

    end = slot_end(start, duration_minutes)
    if not calendar.is_free(start, end):
        raise BookingError("requested slot is unavailable")
    # Recheck immediately before create, matching PRD.
    if not calendar.is_free(start, end):
        raise BookingError("requested slot is unavailable")

    event_id = calendar.create_event(
        start=start,
        end=end,
        summary=f"{service} for {caller}",
        location=location,
        caller=caller,
        conversation_id=conversation_id,
    )
    if not event_id:
        raise BookingError("calendar did not return an event id")

    store.save_appointment(
        conversation_id=conversation_id,
        event_id=event_id,
        caller=caller,
        start=start.isoformat(),
        location=location,
        service=service,
    )
    when = start.strftime("%Y-%m-%d %H:%M UTC")
    telecom.send_sms(
        to=caller,
        from_number=business_number,
        kind="booking_confirmation",
        body=(
            f"Booked: {service} on {when} at {location}. "
            f"This is Mike’s scheduling assistant. Event {event_id}."
        ),
    )
    return {"booked": True, "event_id": event_id, "duplicate": False}
