from __future__ import annotations

from text_back.policy import INTRO_SMS, HELP_SMS, OPT_OUT_ACK, classify_inbound_sms, is_terminal_unanswered
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
) -> dict:
    if not is_terminal_unanswered(call_status):
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
    return {"accepted": True, "duplicate": False, "action": "conversation"}
