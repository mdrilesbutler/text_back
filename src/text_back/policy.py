from __future__ import annotations

import re

from text_back.messages import DEFAULT_MESSAGES, DEFAULT_TEMPLATES, FIELD_PROMPT_KEYS, MessageSet

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

OPT_OUT_ACK = DEFAULT_TEMPLATES["opt_out_ack"]

# Deterministic conversation field collection. No LLM/NLP extraction: each
# inbound "conversation" SMS is treated as the verbatim answer to whichever
# field is next in this fixed order.
CONVERSATION_FIELDS: tuple[str, ...] = ("service", "location", "preferred_time", "name")

# Default prompts; a client's message file can override any of them (see messages.py).
FIELD_PROMPTS: dict[str, str] = {
    field: DEFAULT_TEMPLATES[key] for field, key in FIELD_PROMPT_KEYS.items()
}


def next_missing_field(fields: dict[str, str], order: tuple[str, ...] = CONVERSATION_FIELDS) -> str | None:
    for field in order:
        if not fields.get(field, "").strip():
            return field
    return None


EMAIL_SKIPPED = "(skipped)"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_SAME_NUMBER = frozenset({"yes", "y", "yes.", "yep", "yeah", "same", "this", "this one", "this number", "correct", "ok", "sure"})


def normalize_phone(raw: str) -> str | None:
    """A US/Canada number in any common spelling, or an explicit +country number."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        digits = "1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if 8 <= len(digits) <= 15 and raw.strip().startswith("+"):
        return "+" + digits
    return None


def parse_contact_phone(value: str, caller: str) -> str | None:
    """YES (or similar) means the number the customer is texting from."""
    if value.strip().lower() in _SAME_NUMBER:
        return caller
    return normalize_phone(value)


def parse_contact_email(value: str) -> str | None:
    text = value.strip()
    if text.lower().rstrip(".") in {"skip", "no", "none", "no thanks", "no email", "n/a", "na"}:
        return EMAIL_SKIPPED
    text = text.rstrip(".,;")
    return text.lower() if _EMAIL_RE.match(text) else None


def conversation_prompt(field: str, business_name: str = "", messages: MessageSet | None = None) -> str:
    return (messages or DEFAULT_MESSAGES).field_prompt(field, business_name=business_name)


def preferred_time_reprompt(business_name: str = "", messages: MessageSet | None = None) -> str:
    return (messages or DEFAULT_MESSAGES).render("preferred_time_reprompt", business_name=business_name)


def slot_unavailable_sms(business_name: str = "", messages: MessageSet | None = None) -> str:
    return (messages or DEFAULT_MESSAGES).render("slot_unavailable", business_name=business_name)


def booking_error_sms(business_name: str = "", messages: MessageSet | None = None) -> str:
    return (messages or DEFAULT_MESSAGES).render("booking_error", business_name=business_name)


def phone_reprompt(business_name: str = "", messages: MessageSet | None = None) -> str:
    return (messages or DEFAULT_MESSAGES).render("phone_reprompt", business_name=business_name)


def email_reprompt(business_name: str = "", messages: MessageSet | None = None) -> str:
    return (messages or DEFAULT_MESSAGES).render("email_reprompt", business_name=business_name)


def opt_out_ack_sms(business_name: str = "", messages: MessageSet | None = None) -> str:
    return (messages or DEFAULT_MESSAGES).render("opt_out_ack", business_name=business_name)


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


def handoff_ack_sms(reason: str, business_name: str = "", messages: MessageSet | None = None) -> str:
    key = "handoff_ack_safety" if reason == "safety" else "handoff_ack"
    return (messages or DEFAULT_MESSAGES).render(key, business_name=business_name)


def intro_sms(business_name: str, messages: MessageSet | None = None) -> str:
    return (messages or DEFAULT_MESSAGES).render("intro", business_name=business_name)


def opt_in_sms(business_name: str, messages: MessageSet | None = None) -> str:
    return (messages or DEFAULT_MESSAGES).render("opt_in", business_name=business_name)


def format_contact_number(number: str) -> str:
    digits = re.sub(r"\D", "", number)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return number


def help_sms(business_name: str, business_contact: str = "", text_number: str = "",
             messages: MessageSet | None = None) -> str:
    """Carrier HELP reply: identity, contact info, rates notice, opt-out.

    The contact defaults to the number the customer is already texting; it is
    never the business's own line (customers never get routed to a person).
    """
    contact = business_contact.strip() or format_contact_number(text_number)
    contact_line = f" Contact: {contact}." if contact else ""
    return (messages or DEFAULT_MESSAGES).render("help", business_name=business_name, contact_line=contact_line)


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
