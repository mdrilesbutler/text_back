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
    if not calendar.is_free(start, end):
        raise SlotUnavailableError("requested slot is unavailable")
    # Recheck immediately before create, matching PRD.
    if not calendar.is_free(start, end):
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
    telecom.send_sms(
        to=caller,
        from_number=business_number,
        kind="booking_confirmation",
        body=(
            f"Booked: {service} on {when} at {location}. "
            f"This is {business_name}'s scheduling assistant. Event {event_id}."
        ),
    )
    return {"booked": True, "event_id": event_id, "duplicate": False}
