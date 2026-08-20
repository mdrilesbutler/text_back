from __future__ import annotations

TERMINAL_UNANSWERED = frozenset({"no-answer", "busy", "failed", "canceled"})
STOP_KEYWORDS = frozenset({"stop", "stopall", "unsubscribe", "cancel", "end", "quit"})
HELP_KEYWORDS = frozenset({"help", "info"})

INTRO_SMS = (
    "Hey, sorry we missed your call—this is Mike’s scheduling assistant. "
    "What were you calling about?"
)
HELP_SMS = (
    "Mike’s scheduling assistant. Reply with the job type, location, and a time that works. "
    "For a person, call the business line. Reply STOP to opt out."
)
OPT_OUT_ACK = "You are unsubscribed and will not receive more automated texts. Reply START only if you want scheduling messages again. STOP request recorded."


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
