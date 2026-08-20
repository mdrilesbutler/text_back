from __future__ import annotations

from text_back.policy import (
    HELP_SMS,
    INTRO_SMS,
    OPT_OUT_ACK,
    WIRING_MODE_MANAGED,
    classify_inbound_sms,
    conversation_prompt,
    conversation_summary_sms,
    is_terminal_unanswered,
    next_missing_field,
)
from text_back.store import Store
from text_back.telecom import FakeTelecom


def handle_voice_event(
    *,
    store: Store,
    telecom: FakeTelecom,
    call_sid: str,
    call_status: str,
    from_number: str,
    to_number: str,
    wiring_mode: str,
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
        body=INTRO_SMS,
        from_number=to_number,
        kind="missed_call_intro",
    )
    return {"accepted": True, "duplicate": False, "action": "sent_intro"}


def handle_sms_event(
    *,
    store: Store,
    telecom: FakeTelecom,
    message_sid: str,
    from_number: str,
    to_number: str,
    body: str,
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
        telecom.send_sms(to=from_number, body=HELP_SMS, from_number=to_number, kind="help")
        return {"accepted": True, "duplicate": False, "action": "help"}
    if store.is_opted_out(from_number):
        return {"accepted": True, "duplicate": False, "action": "suppressed", "reason": "opted_out"}
    return _collect_conversation_field(
        store=store,
        telecom=telecom,
        from_number=from_number,
        to_number=to_number,
        body=body,
    )


def _collect_conversation_field(
    *,
    store: Store,
    telecom: FakeTelecom,
    from_number: str,
    to_number: str,
    body: str,
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

    store.set_conversation_field(from_number, pending_field, value)
    updated_fields = {**fields, pending_field: value}
    next_field = next_missing_field(updated_fields)
    if next_field is None:
        telecom.send_sms(
            to=from_number,
            body=conversation_summary_sms(updated_fields),
            from_number=to_number,
            kind="collection_complete",
        )
        return {
            "accepted": True,
            "duplicate": False,
            "action": "field_collected",
            "field": pending_field,
            "fields_complete": True,
        }

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
