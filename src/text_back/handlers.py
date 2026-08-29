from __future__ import annotations

from datetime import datetime, timezone

from text_back.booking import BookingError, SlotUnavailableError, book_appointment
from text_back.calendar_stub import CalendarStub
from text_back.delivery import enqueue_handoff_alert
from text_back.followup import (
    FollowupPolicy,
    cancel_followup,
    schedule_followup_sequence,
)
from text_back.handoff import (
    HandoffAlert,
    HandoffNotifier,
    build_handoff_summary,
)
from text_back.policy import (
    OPT_OUT_ACK,
    WIRING_MODE_MANAGED,
    booking_error_sms,
    classify_handoff_request,
    classify_inbound_sms,
    conversation_prompt,
    help_sms,
    handoff_ack_sms,
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
    followup_policy: FollowupPolicy | None = None,
    now: datetime | None = None,
) -> dict:
    # "managed": our number is the client's own number, so only a terminal
    # unanswered status (no-answer/busy/failed/canceled) is a missed call.
    # "forwarded": our number only ever rings after the carrier's
    # conditional call forwarding already decided the client didn't answer,
    # so the first voice webhook for this call_sid IS the missed call,
    # regardless of call_status — fall through unconditionally below.
    if wiring_mode == WIRING_MODE_MANAGED and not is_terminal_unanswered(call_status):
        return {"accepted": True, "action": "ignored", "reason": "not_terminal_unanswered"}
    store.record_outcome(
        lead_id=from_number,
        event_type="call.missed",
        idempotency_key=f"call:{call_sid}:missed",
        evidence_id=call_sid,
        metadata={"wiring_mode": wiring_mode},
    )
    if store.is_opted_out(from_number):
        return {"accepted": True, "action": "suppressed", "reason": "opted_out"}
    if store.active_handoff(from_number) is not None:
        return {"accepted": True, "action": "suppressed", "reason": "handoff_active"}
    claimed = store.claim_event("voice", call_sid, "missed_call_intro")
    if not claimed:
        return {"accepted": True, "duplicate": True, "action": "noop"}
    message_id = telecom.send_sms(
        to=from_number,
        body=intro_sms(business_name),
        from_number=to_number,
        kind="missed_call_intro",
    )
    store.record_outcome(
        lead_id=from_number,
        event_type="sms.initial_sent",
        idempotency_key=f"call:{call_sid}:initial_sms",
        evidence_id=message_id,
        metadata={},
    )
    if followup_policy is not None and now is not None:
        schedule_followup_sequence(
            store=store,
            policy=followup_policy,
            phone=from_number,
            call_sid=call_sid,
            now=now,
        )
    return {"accepted": True, "duplicate": False, "action": "sent_intro"}


def handle_sms_event(
    *,
    store: Store,
    calendar: CalendarStub,
    telecom: Telecom,
    handoff_notifier: HandoffNotifier,
    handoff_destination: str,
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
    store.record_outcome(
        lead_id=from_number,
        event_type="sms.customer_replied",
        idempotency_key=f"sms:{message_sid}:customer_replied",
        evidence_id=message_sid,
        metadata={},
    )
    # Any customer response immediately ends the no-response sequence.
    cancel_followup(store, from_number, "customer_replied")
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
    handoff_reason = classify_handoff_request(body)
    if store.is_opted_out(from_number):
        if handoff_reason is not None:
            return _request_handoff(
                store=store,
                telecom=telecom,
                handoff_notifier=handoff_notifier,
                handoff_destination=handoff_destination,
                from_number=from_number,
                to_number=to_number,
                body=body,
                reason=handoff_reason,
                acknowledge_customer=False,
                now=now,
            )
        return {"accepted": True, "duplicate": False, "action": "suppressed", "reason": "opted_out"}
    if handoff_reason is not None:
        return _request_handoff(
            store=store,
            telecom=telecom,
            handoff_notifier=handoff_notifier,
            handoff_destination=handoff_destination,
            from_number=from_number,
            to_number=to_number,
            body=body,
            reason=handoff_reason,
            acknowledge_customer=True,
            now=now,
        )
    if store.active_handoff(from_number) is not None:
        return {
            "accepted": True,
            "duplicate": False,
            "action": "suppressed",
            "reason": "handoff_active",
        }
    return _collect_conversation_field(
        store=store,
        calendar=calendar,
        telecom=telecom,
        from_number=from_number,
        to_number=to_number,
        body=body,
        message_sid=message_sid,
        business_name=business_name,
        timezone_name=timezone_name,
        appointment_duration_minutes=appointment_duration_minutes,
        now=now,
    )


def _request_handoff(
    *,
    store: Store,
    telecom: Telecom,
    handoff_notifier: HandoffNotifier,
    handoff_destination: str,
    from_number: str,
    to_number: str,
    body: str,
    reason: str,
    acknowledge_customer: bool,
    now: datetime | None,
) -> dict:
    if not store.request_handoff(from_number, reason):
        current = store.active_handoff(from_number)
        return {
            "accepted": True,
            "duplicate": True,
            "action": "handoff_active",
            "reason": current["reason"] if current else reason,
        }

    fields = store.get_conversation_fields(from_number)
    summary = build_handoff_summary(
        caller=from_number,
        reason=reason,
        latest_message=body,
        collected_fields=fields,
    )
    alert = HandoffAlert(
        destination=handoff_destination,
        caller=from_number,
        business_number=to_number,
        reason=reason,
        latest_message=body,
        collected_fields=fields,
        summary=summary,
    )
    alert_id = handoff_notifier.notify(alert)
    store.set_handoff_alert_id(from_number, alert_id)
    store.record_outcome(
        lead_id=from_number,
        event_type="lead.handoff_requested",
        idempotency_key=f"handoff:{alert_id}:requested",
        evidence_id=alert_id,
        metadata={"reason": reason},
    )
    enqueued = enqueue_handoff_alert(
        store=store,
        alert=alert,
        alert_id=alert_id,
        now=now if now is not None else datetime.now(timezone.utc),
    )
    if not enqueued:
        # An operator safety alert must never be dropped silently. With
        # durable-unique alert IDs this cannot fire; if it does, fail loudly
        # so the provider retries the webhook instead of losing the alert.
        raise RuntimeError(
            f"handoff outbox already contains alert_id {alert_id!r}; "
            "refusing to silently drop an operator alert"
        )
    if acknowledge_customer:
        telecom.send_sms(
            to=from_number,
            body=handoff_ack_sms(reason),
            from_number=to_number,
            kind="handoff_ack",
        )
    return {
        "accepted": True,
        "duplicate": False,
        "action": "handoff_requested",
        "reason": reason,
        "alert_id": alert_id,
    }


def _collect_conversation_field(
    *,
    store: Store,
    calendar: CalendarStub,
    telecom: Telecom,
    from_number: str,
    to_number: str,
    body: str,
    message_sid: str,
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
    store.record_outcome(
        lead_id=from_number,
        event_type="lead.field_captured",
        idempotency_key=f"sms:{message_sid}:field:{pending_field}",
        evidence_id=message_sid,
        metadata={"field": pending_field},
    )
    updated_fields = {**fields, pending_field: value}
    next_field = next_missing_field(updated_fields)
    if next_field is None:
        store.record_outcome(
            lead_id=from_number,
            event_type="lead.qualified",
            idempotency_key=f"lead:{from_number}:qualified",
            evidence_id=message_sid,
            metadata={},
        )
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
