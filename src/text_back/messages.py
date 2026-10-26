"""Per-client customer-facing message copy.

Every text Recover sends is a template here. A client can override any of them
in a JSON file (TEXT_BACK_MESSAGES_FILE); the defaults are the copy the product
ships with. The file is re-read when it changes, so an edit from the client
settings page applies without a restart.

Two rules are enforced on every template, default or custom:

* Carrier compliance: the first automated text, both follow-ups, the opt-in
  acknowledgement and the HELP reply must tell the customer how to stop. If a
  custom template leaves the word STOP out, the (also editable) `opt_out_suffix`
  is appended. The suffix itself must contain STOP.
* No live human: customer copy never promises a person or routes the caller
  back to the business line (Michael, 2026-08-29; see
  tests/test_no_live_human_copy.py).
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from string import Formatter

log = logging.getLogger(__name__)

MAX_TEMPLATE_CHARS = 480

DEFAULT_TEMPLATES: dict[str, str] = {
    "intro": (
        "Hey, sorry we missed your call—this is {business_name}'s scheduling assistant. "
        "What were you calling about?"
    ),
    "followup_1": (
        "Hi again from {business_name}'s scheduling assistant—still happy "
        "to get you on the calendar. What job do you need done?"
    ),
    "followup_2": (
        "Last check-in from {business_name}'s scheduling assistant. Reply with "
        "the job you need and we'll set a time."
    ),
    "prompt_service": "What's the job you need done (e.g. tree removal, trimming, stump grinding)?",
    "prompt_location": "What's the address or location for the job?",
    "prompt_preferred_time": (
        "What day and time works best? "
        "For example: Wednesday at 2, tomorrow at 10am, or Friday at 4pm."
    ),
    "prompt_name": "What name should we put the appointment under?",
    "prompt_phone": "Is this the best number to reach you? Reply YES, or send a different number.",
    "prompt_email": "What's your email? We'll send a calendar invite. Reply SKIP if you'd rather not.",
    "phone_reprompt": "Please send a phone number with area code, like 704 555 0123, or reply YES to use this one.",
    "email_reprompt": "That doesn't look like an email address. Please send it like name@example.com, or reply SKIP.",
    "fields": "service, location, preferred_time, name",
    "preferred_time_reprompt": (
        "Please send a day and a time, like Wednesday at 2, tomorrow at 10am, "
        "or Friday at 4pm."
    ),
    "slot_unavailable": (
        "That time is unavailable. Please send another day and time, "
        "like Thursday at 4."
    ),
    "booking_error": (
        "We couldn't confirm that appointment. No booking was made. "
        "Please send another date and time and we'll try again."
    ),
    "booking_confirmation": (
        "Booked: {service} on {when} at {location}. "
        "This is {business_name}'s scheduling assistant. {invite_line} {calendar_links}"
    ),
    "handoff_ack": (
        "Got it. Automated scheduling is paused, and we'll follow up with you directly."
    ),
    "handoff_ack_safety": (
        "Automated scheduling is paused. We'll follow up with you as soon as possible. "
        "If anyone is in immediate danger, call 911 now."
    ),
    "opt_in": (
        "You're subscribed to {business_name}'s scheduling texts. "
        "Msg & data rates may apply. Reply HELP for help or STOP to opt out."
    ),
    "help": (
        "{business_name}'s scheduling assistant. Reply with the job type, location, "
        "and a time that works. Anything we can't handle by text, the owner "
        "follows up on.{contact_line} Msg & data rates may apply."
    ),
    "opt_out_ack": (
        "You are unsubscribed and will not receive more automated texts. "
        "Reply UNSTOP only if you want scheduling messages again. STOP request recorded."
    ),
    "opt_out_suffix": "Reply STOP to opt out.",
}

# Placeholders each template may use. Anything else is rejected at load time
# so a typo in the settings page cannot crash a live send.
PLACEHOLDERS: dict[str, frozenset[str]] = {
    "intro": frozenset({"business_name"}),
    "followup_1": frozenset({"business_name"}),
    "followup_2": frozenset({"business_name"}),
    "prompt_service": frozenset({"business_name"}),
    "prompt_location": frozenset({"business_name"}),
    "prompt_preferred_time": frozenset({"business_name"}),
    "prompt_name": frozenset({"business_name"}),
    "prompt_phone": frozenset({"business_name"}),
    "prompt_email": frozenset({"business_name"}),
    "phone_reprompt": frozenset({"business_name"}),
    "email_reprompt": frozenset({"business_name"}),
    "fields": frozenset(),
    "preferred_time_reprompt": frozenset({"business_name"}),
    "slot_unavailable": frozenset({"business_name"}),
    "booking_error": frozenset({"business_name"}),
    "booking_confirmation": frozenset({"business_name", "service", "when", "location", "event_id",
                                       "calendar_links", "links_page", "google_link", "outlook_link", "ical_link",
                                       "invite_line", "invited_email"}),
    "handoff_ack": frozenset({"business_name"}),
    "handoff_ack_safety": frozenset({"business_name"}),
    "opt_in": frozenset({"business_name"}),
    "help": frozenset({"business_name", "contact_line"}),
    "opt_out_ack": frozenset({"business_name"}),
    "opt_out_suffix": frozenset(),
}

# Templates that must carry opt-out wording (CTIA / 10DLC reviewers check the
# first text, re-engagement texts, the opt-in confirmation and HELP).
OPT_OUT_REQUIRED = frozenset({"intro", "followup_1", "followup_2", "opt_in", "help"})

FORBIDDEN_PHRASES = (
    "business line",
    "reach a person",
    "for a person",
    "speak to a person",
    "talk to a human",
    "representative",
)

# Field name used by the conversation -> template key for its prompt.
FIELD_PROMPT_KEYS = {
    "service": "prompt_service",
    "location": "prompt_location",
    "preferred_time": "prompt_preferred_time",
    "name": "prompt_name",
    "phone": "prompt_phone",
    "email": "prompt_email",
}
# Questions a booking cannot do without; a client may add phone and email and reorder.
REQUIRED_FIELDS = ("service", "location", "preferred_time", "name")


def parse_fields(value: str) -> tuple[str, ...]:
    names = tuple(name.strip() for name in value.split(",") if name.strip())
    unknown = [n for n in names if n not in FIELD_PROMPT_KEYS]
    if unknown:
        raise MessageTemplateError(f"unknown question(s): {', '.join(unknown)}; choose from {', '.join(FIELD_PROMPT_KEYS)}")
    if len(set(names)) != len(names):
        raise MessageTemplateError("a question is listed twice")
    missing = [n for n in REQUIRED_FIELDS if n not in names]
    if missing:
        raise MessageTemplateError(f"questions must include {', '.join(missing)}")
    return names


class MessageTemplateError(ValueError):
    """A custom template is unusable; the previous good set stays active."""


_STOP_WORD = re.compile(r"\bstop\b", re.IGNORECASE)


def _mentions_stop(text: str) -> bool:
    """True only for the word STOP, not a business name like Pitstop."""
    return _STOP_WORD.search(text) is not None


def _placeholders(template: str) -> set[str]:
    names = set()
    try:
        parsed = list(Formatter().parse(template))
    except ValueError:
        raise MessageTemplateError("unbalanced { or } in template") from None
    for _, field_name, _, _ in parsed:
        if field_name is None:
            continue
        if field_name == "" or not field_name.isidentifier():
            raise MessageTemplateError("placeholders must look like {business_name}")
        names.add(field_name)
    return names


def validate_templates(templates: dict[str, str]) -> dict[str, str]:
    """Return a full, validated template set (defaults filled in)."""
    if not isinstance(templates, dict):
        raise MessageTemplateError("message templates must be a JSON object")
    unknown = sorted(set(templates) - set(DEFAULT_TEMPLATES))
    if unknown:
        raise MessageTemplateError(f"unknown message keys: {', '.join(unknown)}")
    merged = dict(DEFAULT_TEMPLATES)
    for key, value in templates.items():
        if not isinstance(value, str):
            raise MessageTemplateError(f"{key} must be text")
        text = " ".join(value.split())
        if not text:
            raise MessageTemplateError(f"{key} cannot be empty")
        if key == "fields":
            merged[key] = ", ".join(parse_fields(text))
            continue
        if len(text) > MAX_TEMPLATE_CHARS:
            raise MessageTemplateError(f"{key} is longer than {MAX_TEMPLATE_CHARS} characters")
        extra = _placeholders(text) - PLACEHOLDERS[key]
        if extra:
            allowed = ", ".join("{" + name + "}" for name in sorted(PLACEHOLDERS[key])) or "none"
            raise MessageTemplateError(
                f"{key} uses unsupported placeholder(s) {', '.join('{' + e + '}' for e in sorted(extra))}; "
                f"allowed: {allowed}"
            )
        lowered = text.lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lowered:
                raise MessageTemplateError(
                    f"{key} must not promise a person or the business line ({phrase!r})"
                )
        merged[key] = text
    if not _mentions_stop(merged["opt_out_suffix"]):
        raise MessageTemplateError("opt_out_suffix must tell the customer to reply STOP")
    if "911" not in merged["handoff_ack_safety"]:
        raise MessageTemplateError("handoff_ack_safety must direct emergencies to 911")
    if "follow up" not in merged["handoff_ack"].lower() or "follow up" not in merged["handoff_ack_safety"].lower():
        raise MessageTemplateError("handoff acknowledgements must promise a follow-up")
    if "no booking was made" not in merged["booking_error"].lower() or "call" in merged["booking_error"].lower():
        raise MessageTemplateError("booking_error must say no booking was made and keep the customer texting")
    return merged


@dataclass(frozen=True)
class MessageSet:
    templates: dict[str, str]

    def render(self, key: str, **values: str) -> str:
        context = {name: values.get(name, "") for name in PLACEHOLDERS[key]}
        try:
            text = self.templates[key].format_map(context)
        except (KeyError, ValueError, IndexError):
            # Never let copy take a live send down: fall back to the shipped text.
            log.error("message template %s failed to render; using default copy", key)
            text = DEFAULT_TEMPLATES[key].format_map(context)
        if key in OPT_OUT_REQUIRED and not _mentions_stop(self.templates[key]):
            # Decide on the template, not the rendered text, so a business
            # named "Pitstop" still gets the carrier-required opt-out line.
            text = f"{text} {self.templates['opt_out_suffix']}"
        return " ".join(text.split())

    def field_prompt(self, field: str, **values: str) -> str:
        return self.render(FIELD_PROMPT_KEYS[field], **values)

    @property
    def fields(self) -> tuple[str, ...]:
        """The questions to ask, in order."""
        return parse_fields(self.templates["fields"])


DEFAULT_MESSAGES = MessageSet(dict(DEFAULT_TEMPLATES))


def load_message_file(path: str | os.PathLike[str]) -> MessageSet:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise MessageTemplateError(f"cannot read message file: {exc.strerror}") from None
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        raise MessageTemplateError("message file is not valid JSON") from None
    return MessageSet(validate_templates(data))


# Owner-portal writers (Messages saves, the rename-texts offer) hold this around their
# read-modify-write so two requests never interleave on the messages file.
MESSAGE_FILE_LOCK = threading.Lock()


def write_message_file(path: str | os.PathLike[str], templates: dict[str, str]) -> MessageSet:
    """Validate, then atomically write only the keys that differ from the defaults.

    The new content goes to a uniquely named temp file in the same directory, then
    os.replace swaps it in, so concurrent writers never share a temp name and a reader
    always sees a whole file."""
    merged = validate_templates(templates)
    overrides = {k: v for k, v in merged.items() if v != DEFAULT_TEMPLATES[k]}
    target = Path(path)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, prefix=f".{target.name}.",
                                     suffix=".tmp", delete=False) as handle:
        tmp = Path(handle.name)
    try:
        os.chmod(tmp, 0o600)
        tmp.write_text(json.dumps(overrides, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return MessageSet(merged)


class MessageSource:
    """Hands out the current MessageSet, re-reading the file when it changes.

    A broken edit never takes a live send down: the last good set stays in
    use and the problem is logged (and surfaced through `last_error`).
    """

    def __init__(self, path: str | None):
        self.path = Path(path) if path else None
        self._stamp: tuple[int, int] | None = None
        self._current = DEFAULT_MESSAGES
        self.last_error: str | None = None
        if self.path is not None and self.path.exists():
            self._current = load_message_file(self.path)  # fail closed at boot
            self._stamp = self._file_stamp()

    def _file_stamp(self) -> tuple[int, int] | None:
        try:
            stat = self.path.stat()
        except OSError:
            return None
        return (stat.st_mtime_ns, stat.st_size)

    def current(self) -> MessageSet:
        if self.path is None:
            return self._current
        stamp = self._file_stamp()
        if stamp == self._stamp:
            return self._current
        self._stamp = stamp
        if stamp is None:
            self._current = DEFAULT_MESSAGES
            self.last_error = None
            return self._current
        try:
            self._current = load_message_file(self.path)
            self.last_error = None
        except MessageTemplateError as exc:
            self.last_error = str(exc)
            log.error("message file %s rejected, keeping previous copy: %s", self.path, exc)
        return self._current
