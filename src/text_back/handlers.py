from __future__ import annotations

from datetime import datetime

from text_back.booking import BookingError, SlotUnavailableError, book_appointment
from text_back.calendar_stub import CalendarStub
from text_back.policy import (
    OPT_OUT_ACK,
    WIRING_MODE_MANAGED,
    booking_error_sms,
    classify_inbound_sms,
    conversation_prompt,
    help_sms,
    intro_sms,
    is_terminal_unanswered,
    next_missing_field,
    preferred_time_reprompt,
    slot_unavailable_sms,
)
from text_back.preferred_time import PreferredTimeError, parse_preferred_time
from text_back.store import Store
from text_back.telecom import Telecom


def handle_voice_event(
    *,
    store: Store,
    telecom: Telecom,
    call_sid: str,
    call_status: str,
    from_number: str,
    to_number: str,
    wiring_mode: str,
    business_name: str,
) -> dict:
    # "managed": our number is the client's own number, so only a terminal
    # unanswered status (no-answer/busy/failed/canceled) is a missed call.
    # "forwarded": our number only ever rings after the carrier's
    # conditional call forwarding already decided the client didn't answer,
    # so the first voice webhook for this call_sid IS the missed call,
    # regardless of call_status — fall through unconditionally below.
    if wiring_mode == WIRING_MODE_MANAGED and not is_terminal_unanswered(call_status):
        return {"accepted": True, "action": "ignored", "reason": "not_terminal_unanswered"}
    if store.is_opted_out(from_number):
        return {"accepted": True, "action": "suppressed", "reason": "opted_out"}
    claimed = store.claim_event("voice", call_sid, "missed_call_intro")
    if not claimed:
        return {"accepted": True, "duplicate": True, "action": "noop"}
    telecom.send_sms(
        to=from_number,
        body=intro_sms(business_name),
        from_number=to_number,
        kind="missed_call_intro",
    )
    return {"accepted": True, "duplicate": False, "action": "sent_intro"}


def handle_sms_event(
    *,
    store: Store,
    calendar: CalendarStub,
    telecom: Telecom,
    message_sid: str,
    from_number: str,
    to_number: str,
    body: str,
    business_name: str,
    timezone_name: str,
    appointment_duration_minutes: int,
    now: datetime | None = None,
) -> dict:
    claimed = store.claim_event("sms", message_sid, "inbound")
    if not claimed:
        return {"accepted": True, "duplicate": True, "action": "noop"}
    kind = classify_inbound_sms(body)
    if kind == "stop":
        store.set_opted_out(from_number, True)
        telecom.send_sms(to=from_number, body=OPT_OUT_ACK, from_number=to_number, kind="opt_out_ack")
        return {"accepted": True, "duplicate": False, "action": "opt_out"}
    if kind == "help":
        telecom.send_sms(
            to=from_number,
            body=help_sms(business_name),
            from_number=to_number,
            kind="help",
        )
        return {"accepted": True, "duplicate": False, "action": "help"}
    if store.is_opted_out(from_number):
        return {"accepted": True, "duplicate": False, "action": "suppressed", "reason": "opted_out"}
    return _collect_conversation_field(
        store=store,
        calendar=calendar,
        telecom=telecom,
        from_number=from_number,
        to_number=to_number,
        body=body,
        business_name=business_name,
        timezone_name=timezone_name,
        appointment_duration_minutes=appointment_duration_minutes,
        now=now,
    )


def _collect_conversation_field(
    *,
    store: Store,
    calendar: CalendarStub,
    telecom: Telecom,
    from_number: str,
    to_number: str,
    body: str,
    business_name: str,
    timezone_name: str,
    appointment_duration_minutes: int,
    now: datetime | None,
) -> dict:
    """Deterministic slot-filling: each reply answers the next missing field
    in a fixed order (service, location, preferred_time, name). No LLM or
    free-text extraction is used; policy owns what field is asked for next.
    """
    fields = store.get_conversation_fields(from_number)
    pending_field = next_missing_field(fields)
    if pending_field is None:
        return {"accepted": True, "duplicate": False, "action": "conversation", "fields_complete": True}

    value = body.strip()
    if not value:
        telecom.send_sms(
            to=from_number,
            body=conversation_prompt(pending_field),
            from_number=to_number,
            kind="field_prompt",
        )
        return {"accepted": True, "duplicate": False, "action": "field_prompt_repeated", "field": pending_field}

    if pending_field == "preferred_time":
        try:
            parse_preferred_time(value, timezone_name=timezone_name, now=now)
        except PreferredTimeError:
            telecom.send_sms(
                to=from_number,
                body=preferred_time_reprompt(),
                from_number=to_number,
                kind="preferred_time_reprompt",
            )
            return {
                "accepted": True,
                "duplicate": False,
                "action": "preferred_time_invalid",
                "field": pending_field,
            }

    store.set_conversation_field(from_number, pending_field, value)
    updated_fields = {**fields, pending_field: value}
    next_field = next_missing_field(updated_fields)
    if next_field is None:
        return _book_collected_fields(
            store=store,
            calendar=calendar,
            telecom=telecom,
            from_number=from_number,
            to_number=to_number,
            fields=updated_fields,
            business_name=business_name,
            timezone_name=timezone_name,
            appointment_duration_minutes=appointment_duration_minutes,
            now=now,
        )

    telecom.send_sms(
        to=from_number,
        body=conversation_prompt(next_field),
        from_number=to_number,
        kind="field_prompt",
    )
    return {
        "accepted": True,
        "duplicate": False,
        "action": "field_collected",
        "field": pending_field,
        "next_field": next_field,
    }


def _book_collected_fields(
    *,
    store: Store,
    calendar: CalendarStub,
    telecom: Telecom,
    from_number: str,
    to_number: str,
    fields: dict[str, str],
    business_name: str,
    timezone_name: str,
    appointment_duration_minutes: int,
    now: datetime | None,
) -> dict:
    try:
        start = parse_preferred_time(
            fields["preferred_time"],
            timezone_name=timezone_name,
            now=now,
        )
    except PreferredTimeError:
        store.delete_conversation_field(from_number, "preferred_time")
        telecom.send_sms(
            to=from_number,
            body=preferred_time_reprompt(),
            from_number=to_number,
            kind="preferred_time_reprompt",
        )
        return {
            "accepted": True,
            "duplicate": False,
            "action": "preferred_time_invalid",
            "fields_complete": False,
        }

    try:
        booking = book_appointment(
            calendar=calendar,
            store=store,
            telecom=telecom,
            caller=from_number,
            business_number=to_number,
            service=fields["service"],
            location=fields["location"],
            customer_name=fields["name"],
            business_name=business_name,
            timezone_name=timezone_name,
            start=start,
            duration_minutes=appointment_duration_minutes,
            conversation_id=from_number,
        )
    except SlotUnavailableError:
        store.delete_conversation_field(from_number, "preferred_time")
        telecom.send_sms(
            to=from_number,
            body=slot_unavailable_sms(),
            from_number=to_number,
            kind="slot_unavailable",
        )
        return {
            "accepted": True,
            "duplicate": False,
            "action": "slot_unavailable",
            "fields_complete": False,
        }
    except BookingError:
        telecom.send_sms(
            to=from_number,
            body=booking_error_sms(),
            from_number=to_number,
            kind="booking_error",
        )
        return {
            "accepted": True,
            "duplicate": False,
            "action": "booking_failed",
            "fields_complete": True,
        }

    return {
        "accepted": True,
        "duplicate": booking["duplicate"],
        "action": "booked",
        "fields_complete": True,
        "event_id": booking["event_id"],
    }
