from __future__ import annotations

TERMINAL_UNANSWERED = frozenset({"no-answer", "busy", "failed", "canceled"})
STOP_KEYWORDS = frozenset({"stop", "stopall", "unsubscribe", "cancel", "end", "quit"})
HELP_KEYWORDS = frozenset({"help", "info"})

# wiring_mode: how our number relates to the client's real phone line.
# - "forwarded" (default): our number is not the client's public number. The
#   carrier only forwards a call to us after no-answer/busy on the client's
#   real line, so ANY inbound voice webhook we receive already represents a
#   missed call — trigger on arrival, regardless of CallStatus.
# - "managed": our number IS the client's public number (current/legacy
#   behavior). Only terminal-unanswered statuses represent a missed call;
#   ringing/in-progress/answered must not trigger an intro SMS.
WIRING_MODE_FORWARDED = "forwarded"
WIRING_MODE_MANAGED = "managed"
WIRING_MODES = frozenset({WIRING_MODE_FORWARDED, WIRING_MODE_MANAGED})

OPT_OUT_ACK = "You are unsubscribed and will not receive more automated texts. Reply START only if you want scheduling messages again. STOP request recorded."

# Deterministic conversation field collection. No LLM/NLP extraction: each
# inbound "conversation" SMS is treated as the verbatim answer to whichever
# field is next in this fixed order.
CONVERSATION_FIELDS: tuple[str, ...] = ("service", "location", "preferred_time", "name")

FIELD_PROMPTS: dict[str, str] = {
    "service": "What's the job you need done (e.g. tree removal, trimming, stump grinding)?",
    "location": "What's the address or location for the job?",
    "preferred_time": "What day and time works best for you?",
    "name": "Last thing—what name should we put the appointment under?",
}


def next_missing_field(fields: dict[str, str]) -> str | None:
    for field in CONVERSATION_FIELDS:
        if not fields.get(field, "").strip():
            return field
    return None


def conversation_prompt(field: str) -> str:
    return FIELD_PROMPTS[field]


def intro_sms(business_name: str) -> str:
    return (
        f"Hey, sorry we missed your call—this is {business_name}'s scheduling assistant. "
        "What were you calling about?"
    )


def help_sms(business_name: str) -> str:
    return (
        f"{business_name}'s scheduling assistant. Reply with the job type, location, "
        "and a time that works. For a person, call the business line. "
        "Reply STOP to opt out."
    )


def conversation_summary_sms(fields: dict[str, str], business_name: str) -> str:
    return (
        f"Thanks {fields['name']}! We've got: {fields['service']} at {fields['location']}, "
        f"preferred time {fields['preferred_time']}. "
        f"{business_name} will confirm your appointment shortly."
    )


def is_terminal_unanswered(call_status: str) -> bool:
    return call_status.strip().lower() in TERMINAL_UNANSWERED


def classify_inbound_sms(body: str) -> str:
    tokens = body.strip().lower().replace(",", " ").split()
    if not tokens:
        return "conversation"
    if tokens[0] in STOP_KEYWORDS:
        return "stop"
    if tokens[0] in HELP_KEYWORDS:
        return "help"
    return "conversation"
