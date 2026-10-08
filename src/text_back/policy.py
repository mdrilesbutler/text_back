from __future__ import annotations

import re

TERMINAL_UNANSWERED = frozenset({"no-answer", "busy", "failed", "canceled"})
STOP_KEYWORDS = frozenset(
    {"stop", "stopall", "unsubscribe", "cancel", "end", "quit", "optout", "revoke"}
)
STOP_REQUEST = re.compile(
    r"^(?:please )?(?:stop all|stop texting|stop messaging|stop sending(?: texts| messages)?"
    r"|do not text|don't text|dont text|opt out|unsubscribe)(?: me| us)?(?: please)?(?: now)?$"
)
# Opt-in keywords re-subscribe only when the whole reply is the keyword, so an
# ordinary answer such as "start time 2pm" stays a conversation reply.
OPT_IN_KEYWORDS = frozenset({"start", "unstop", "subscribe"})
HELP_KEYWORDS = frozenset({"help", "info"})
HANDOFF_SAFETY_TERMS = frozenset(
    {"danger", "emergency", "fire", "injured", "injury", "urgent"}
)
HANDOFF_SAFETY_PHRASES = ("downed line", "gas leak", "power line")
HANDOFF_REQUEST_TERMS = frozenset({"human", "representative"})
HANDOFF_REQUEST_PHRASES = (
    "a person",
    "call me",
    "person please",
    "speak to someone",
    "talk to someone",
)

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

OPT_OUT_ACK = "You are unsubscribed and will not receive more automated texts. Reply UNSTOP only if you want scheduling messages again. STOP request recorded."

# Deterministic conversation field collection. No LLM/NLP extraction: each
# inbound "conversation" SMS is treated as the verbatim answer to whichever
# field is next in this fixed order.
CONVERSATION_FIELDS: tuple[str, ...] = ("service", "location", "preferred_time", "name")

FIELD_PROMPTS: dict[str, str] = {
    "service": "What's the job you need done (e.g. tree removal, trimming, stump grinding)?",
    "location": "What's the address or location for the job?",
    "preferred_time": (
        "What day and start time works best? "
        "Please use YYYY-MM-DD with a time, or say tomorrow at 2 PM."
    ),
    "name": "Last thing—what name should we put the appointment under?",
}


def next_missing_field(fields: dict[str, str]) -> str | None:
    for field in CONVERSATION_FIELDS:
        if not fields.get(field, "").strip():
            return field
    return None


def conversation_prompt(field: str) -> str:
    return FIELD_PROMPTS[field]


def preferred_time_reprompt() -> str:
    return (
        "Please send a specific future date and time, like YYYY-MM-DD 2:00 PM "
        "or tomorrow at 2 PM."
    )


def slot_unavailable_sms() -> str:
    return (
        "That time is unavailable. Please send another future date and time, "
        "like YYYY-MM-DD 2:00 PM."
    )


def booking_error_sms() -> str:
    return (
        "We couldn't confirm that appointment. No booking was made. "
        "Please send another date and time and we'll try again."
    )


def classify_handoff_request(body: str) -> str | None:
    words = re.findall(r"[a-z0-9']+", body.lower())
    tokens = frozenset(words)
    normalized = " ".join(words)
    if tokens & HANDOFF_SAFETY_TERMS or any(
        phrase in normalized for phrase in HANDOFF_SAFETY_PHRASES
    ):
        return "safety"
    if tokens & HANDOFF_REQUEST_TERMS or any(
        phrase in normalized for phrase in HANDOFF_REQUEST_PHRASES
    ):
        return "customer_requested"
    return None


def handoff_ack_sms(reason: str) -> str:
    if reason == "safety":
        return (
            "Automated scheduling is paused. The owner will follow up with you "
            "as soon as possible. If anyone is in immediate danger, call 911 now."
        )
    return (
        "Got it—automated scheduling is paused. The owner will follow up "
        "with you directly."
    )


def intro_sms(business_name: str) -> str:
    return (
        f"Hey, sorry we missed your call—this is {business_name}'s scheduling assistant. "
        "What were you calling about? Reply STOP to opt out."
    )


def opt_in_sms(business_name: str) -> str:
    return (
        f"You're subscribed to {business_name}'s scheduling texts. "
        "Msg & data rates may apply. Reply HELP for help or STOP to opt out."
    )


def format_contact_number(number: str) -> str:
    digits = re.sub(r"\D", "", number)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return number


def help_sms(business_name: str, business_contact: str = "", text_number: str = "") -> str:
    """Carrier HELP reply: identity, contact info, rates notice, opt-out.

    The contact defaults to the number the customer is already texting; it is
    never the business's own line (customers never get routed to a person).
    """
    contact = business_contact.strip() or format_contact_number(text_number)
    contact_line = f" Contact: {contact}." if contact else ""
    return (
        f"{business_name}'s scheduling assistant. Reply with the job type, location, "
        "and a time that works. Anything we can't handle by text, the owner "
        f"follows up on.{contact_line} Msg & data rates may apply. Reply STOP to opt out."
    )


def is_terminal_unanswered(call_status: str) -> bool:
    return call_status.strip().lower() in TERMINAL_UNANSWERED


def classify_inbound_sms(body: str) -> str:
    # Hyphenated words stay whole: "opt-out" is a keyword, "stop-by" is not.
    tokens = re.findall(r"[a-z0-9']+(?:-[a-z0-9']+)*", body.strip().lower())
    if not tokens:
        return "conversation"
    first = tokens[0].replace("-", "")
    normalized = " ".join(tokens).replace("-", " ")
    if (first in STOP_KEYWORDS and "-" not in tokens[0] or first == "optout"
            or STOP_REQUEST.fullmatch(normalized)):
        return "stop"
    if tokens[0] in HELP_KEYWORDS:
        return "help"
    if body.strip().rstrip(".!?").lower() in OPT_IN_KEYWORDS:
        return "opt_in"
    return "conversation"


def is_resubscribe_reply(body: str) -> bool:
    """A bare YES re-subscribes a contact who previously opted out."""
    return re.fullmatch(r"yes[.!?]*", body.strip(), re.I) is not None
