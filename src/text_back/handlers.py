from __future__ import annotations

from datetime import datetime, timezone

from text_back.booking import BookingError, SlotUnavailableError, book_appointment
from text_back.calendars.protocol import CalendarProvider
from text_back.delivery import enqueue_handoff_alert
from text_back.followup import (
    FollowupPolicy,
    cancel_followup,
)
from text_back.handoff import (
    HandoffAlert,
    HandoffNotifier,
    build_handoff_summary,
)
from text_back.policy import (
    opt_out_ack_sms,
    CONVERSATION_FIELDS,
    email_reprompt,
    parse_contact_email,
    parse_contact_phone,
    phone_reprompt,
    WIRING_MODE_MANAGED,
    booking_error_sms,
    classify_handoff_request,
    classify_inbound_sms,
    conversation_prompt,
    help_sms,
    handoff_ack_sms,
    intro_sms,
    is_resubscribe_reply,
    is_terminal_unanswered,
    next_missing_field,
    opt_in_sms,
    preferred_time_reprompt,
    slot_unavailable_sms,
)
from text_back.messages import MessageSet
from text_back.preferred_time import PreferredTimeError, parse_preferred_time
from text_back.sms import atomic_sms_handler, enqueue_sms
from text_back.store import Store
from text_back.telecom import Telecom


@atomic_sms_handler
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
    messages: MessageSet | None = None,
    forwarded_from: str = "",
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
        occurred_at=(now or datetime.now(timezone.utc)).isoformat(),
        idempotency_key=f"call:{call_sid}:missed",
        evidence_id=call_sid,
        # ForwardedFrom is the line the carrier forwarded this call from (empty on a direct call).
        # The owner portal's forwarding checks tick only from this evidence.
        metadata={"wiring_mode": wiring_mode, "forwarded_from": forwarded_from or ""},
    )
    if store.is_opted_out(from_number):
        return {"accepted": True, "action": "suppressed", "reason": "opted_out"}
    if store.active_handoff(from_number) is not None:
        return {"accepted": True, "action": "suppressed", "reason": "handoff_active"}
    claimed = store.claim_event("voice", call_sid, "missed_call_intro")
    if not claimed:
        return {"accepted": True, "duplicate": True, "action": "noop"}
    key = f"{call_sid}:intro"
    enqueue_sms(
        store=store, key=key, to=from_number, body=intro_sms(business_name, messages),
        from_number=to_number, kind="missed_call_intro",
        now=now or datetime.now(timezone.utc),
        completion={"event_type": "sms.initial_sent", "outcome_key": f"call:{call_sid}:initial_sms",
                    "call_sid": call_sid, "delays": list(followup_policy.delays_minutes) if followup_policy else []},
    )
    telecom.keys.append(key)
    return {"accepted": True, "duplicate": False, "action": "sent_intro"}


@atomic_sms_handler
def handle_sms_event(
    *,
    store: Store,
    calendar: CalendarProvider,
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
    business_contact: str = "",
    now: datetime | None = None,
    messages: MessageSet | None = None,
) -> dict:
    claimed = store.claim_event("sms", message_sid, "inbound")
    if not claimed:
        return {"accepted": True, "duplicate": True, "action": "noop"}
    store.record_outcome(
        lead_id=from_number,
        event_type="sms.customer_replied",
        occurred_at=(now or datetime.now(timezone.utc)).isoformat(),
        idempotency_key=f"sms:{message_sid}:customer_replied",
        evidence_id=message_sid,
        metadata={},
    )
    store.conn.execute("""UPDATE sms_outbox SET status='cancelled' WHERE phone=? AND status='pending'
        AND kind IN ('missed_call_intro','followup','field_prompt','preferred_time_reprompt','phone_reprompt','email_reprompt','slot_unavailable','booking_error','opt_in_ack')""", (from_number,))
    # Any customer response immediately ends the no-response sequence.
    cancel_followup(store, from_number, "customer_replied")
    kind = classify_inbound_sms(body)
    if kind == "stop":
        store.set_opted_out(from_number, True)
        store.record_outcome(lead_id=from_number, event_type="lead.opted_out",
            occurred_at=(now or datetime.now(timezone.utc)).isoformat(),
            idempotency_key=f"sms:{message_sid}:opted_out", evidence_id=message_sid, metadata={})
        telecom.send_sms(to=from_number, body=opt_out_ack_sms(business_name, messages), from_number=to_number, kind="opt_out_ack")
        return {"accepted": True, "duplicate": False, "action": "opt_out"}
    if kind == "help":
        telecom.send_sms(
            to=from_number,
            body=help_sms(business_name, business_contact, to_number, messages),
            from_number=to_number,
            kind="help",
        )
        return {"accepted": True, "duplicate": False, "action": "help"}
    if kind == "opt_in" or (store.is_opted_out(from_number) and is_resubscribe_reply(body)):
        store.set_opted_out(from_number, False)
        store.record_outcome(lead_id=from_number, event_type="lead.opted_in",
            occurred_at=(now or datetime.now(timezone.utc)).isoformat(),
            idempotency_key=f"sms:{message_sid}:opted_in", evidence_id=message_sid, metadata={})
        telecom.send_sms(
            to=from_number,
            body=opt_in_sms(business_name, messages),
            from_number=to_number,
            kind="opt_in_ack",
        )
        return {"accepted": True, "duplicate": False, "action": "opt_in"}
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
                business_name=business_name,
                messages=messages,
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
            business_name=business_name,
            messages=messages,
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
        messages=messages,
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
    business_name: str = "",
    messages: MessageSet | None = None,
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
        occurred_at=(now or datetime.now(timezone.utc)).isoformat(),
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
            body=handoff_ack_sms(reason, business_name, messages),
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
    calendar: CalendarProvider,
    telecom: Telecom,
    from_number: str,
    to_number: str,
    body: str,
    message_sid: str,
    business_name: str,
    timezone_name: str,
    appointment_duration_minutes: int,
    now: datetime | None,
    messages: MessageSet | None = None,
) -> dict:
    """Deterministic slot-filling: each reply answers the next missing field
    in a fixed order (service, location, preferred_time, name). No LLM or
    free-text extraction is used; policy owns what field is asked for next.
    """
    fields = store.get_conversation_fields(from_number)
    order = (messages.fields if messages is not None else None) or CONVERSATION_FIELDS
    pending_field = next_missing_field(fields, order)
    if pending_field is None:
        if store.appointment_by_conversation(from_number) is None:
            # All fields were collected but no appointment was saved — the
            # crash window between create_event and save_appointment, or a
            # booking that previously failed. Re-attempt the booking: the
            # deterministic (conversation, slot) provider IDs make a genuine
            # same-slot retry dedupe at the provider instead of double-booking.
            return _book_collected_fields(
                store=store,
                calendar=calendar,
                telecom=telecom,
                from_number=from_number,
                to_number=to_number,
                fields=fields,
                business_name=business_name,
                timezone_name=timezone_name,
                appointment_duration_minutes=appointment_duration_minutes,
                now=now,
                messages=messages,
            )
        return {"accepted": True, "duplicate": False, "action": "conversation", "fields_complete": True}

    value = body.strip()
    if not value:
        telecom.send_sms(
            to=from_number,
            body=conversation_prompt(pending_field, business_name, messages),
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
                body=preferred_time_reprompt(business_name, messages),
                from_number=to_number,
                kind="preferred_time_reprompt",
            )
            return {
                "accepted": True,
                "duplicate": False,
                "action": "preferred_time_invalid",
                "field": pending_field,
            }

    if pending_field == "phone":
        parsed = parse_contact_phone(value, from_number)
        if parsed is None:
            telecom.send_sms(to=from_number, body=phone_reprompt(business_name, messages), from_number=to_number, kind="phone_reprompt")
            return {"accepted": True, "duplicate": False, "action": "phone_invalid", "field": pending_field}
        value = parsed
    if pending_field == "email":
        parsed = parse_contact_email(value)
        if parsed is None:
            telecom.send_sms(to=from_number, body=email_reprompt(business_name, messages), from_number=to_number, kind="email_reprompt")
            return {"accepted": True, "duplicate": False, "action": "email_invalid", "field": pending_field}
        value = parsed

    store.set_conversation_field(from_number, pending_field, value)
    store.record_outcome(
        lead_id=from_number,
        event_type="lead.field_captured",
        occurred_at=(now or datetime.now(timezone.utc)).isoformat(),
        idempotency_key=f"sms:{message_sid}:field:{pending_field}",
        evidence_id=message_sid,
        metadata={"field": pending_field},
    )
    updated_fields = {**fields, pending_field: value}
    next_field = next_missing_field(updated_fields, order)
    if next_field is None:
        store.record_outcome(
            lead_id=from_number,
            event_type="lead.qualified",
        occurred_at=(now or datetime.now(timezone.utc)).isoformat(),
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
            messages=messages,
        )

    telecom.send_sms(
        to=from_number,
        body=conversation_prompt(next_field, business_name, messages),
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
    calendar: CalendarProvider,
    telecom: Telecom,
    from_number: str,
    to_number: str,
    fields: dict[str, str],
    business_name: str,
    timezone_name: str,
    appointment_duration_minutes: int,
    now: datetime | None,
    messages: MessageSet | None = None,
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
            body=preferred_time_reprompt(business_name, messages),
            from_number=to_number,
            kind="preferred_time_reprompt",
        )
        return {
            "accepted": True,
            "duplicate": False,
            "action": "preferred_time_invalid",
            "fields_complete": False,
        }

    from text_back.booking_jobs import queue_booking, finish_booking_job
    payload = dict(caller=from_number, business_number=to_number, service=fields['service'],
                   location=fields['location'], customer_name=fields['name'], business_name=business_name,
                   timezone_name=timezone_name, start=start, duration_minutes=appointment_duration_minutes,
                   conversation_id=from_number, customer_email=fields.get('email', ''), customer_phone=fields.get('phone', ''))
    job_key = queue_booking(store, payload, now or datetime.now(timezone.utc))
    try:
        booking = book_appointment(calendar=calendar, store=store, telecom=telecom, now=now, messages=messages, **payload)
        finish_booking_job(store, job_key)
    except SlotUnavailableError:
        finish_booking_job(store, job_key)
        store.delete_conversation_field(from_number, "preferred_time")
        telecom.send_sms(
            to=from_number,
            body=slot_unavailable_sms(business_name, messages),
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
            body=booking_error_sms(business_name, messages),
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
