"""Messages page (/client/messages): every customer text, grouped by stage.

The owner edits the templates in ``messages.DEFAULT_TEMPLATES``; overrides
live in the JSON file at ``state.messages.path`` (TEXT_BACK_MESSAGES_FILE).
This module owns the owner-facing labels, the sample conversation used by
the phone-frame preview, the SMS segment arithmetic the page shows (mirrored
by portal.js for live updates) and the per-field validation that turns
``messages.validate_templates`` errors into inline messages. It never
renders HTML; client_portal.py passes its context to pages/messages.html.
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from text_back import portal_data
from text_back.messages import (
    DEFAULT_TEMPLATES,
    OPT_OUT_REQUIRED,
    PLACEHOLDERS,
    MessageTemplateError,
    _mentions_stop,
    validate_templates,
)
from text_back.policy import format_contact_number

TRIAL_PREFIX = "[SignalWire Free Trial] "
MAX_CHARS = 480
SAVED = "Saved. New conversations use these messages from now on."
RESET = "Reset to the standard wording."
SAMPLE_CALLER = "Dana"
SAMPLE_EMAIL = "dana@example.com"

# Owner-facing names for the fill-ins ({business_name} -> "Business name").
PLACEHOLDER_LABELS = {
    "business_name": "Business name", "service": "Job", "when": "Day and time", "location": "Location",
    "invite_line": "Invite note", "calendar_links": "Calendar links", "links_page": "Links page",
    "google_link": "Google link", "outlook_link": "Outlook link", "ical_link": "iCal link",
    "invited_email": "Customer email", "event_id": "Booking ID", "contact_line": "Contact line",
}

# (group key, group title, fields). Field = (template key, label, hint, chips in display order).
GROUPS: tuple[tuple[str, str, tuple[tuple[str, str, str, tuple[str, ...]], ...]], ...] = (
    ("first", "First text", (
        ("intro", "First text after a missed call", "Sent the moment a call goes unanswered.", ("business_name",)),
        ("opt_out_suffix", "Opt-out line",
         "Added to the first text, follow-ups, START and HELP replies when they leave out the word STOP.", ()),
    )),
    ("questions", "Questions", (
        ("prompt_service", "The job",
         "Sent only when the caller's first reply is blank. Otherwise the first reply is taken as the job.", ("business_name",)),
        ("prompt_location", "The location", "Asked after the job.", ("business_name",)),
        ("prompt_preferred_time", "Day and time", "Asked after the location.", ("business_name",)),
        ("prompt_name", "The name", "Asked after the time.", ("business_name",)),
        ("prompt_phone", "Best phone number (optional)",
         "Asked only when the switch below is on. YES keeps the number they are texting from.", ("business_name",)),
        ("prompt_email", "Email address (optional)",
         "Asked only when the switch below is on. SKIP is allowed.", ("business_name",)),
        ("preferred_time_reprompt", "When the time can't be read", "", ("business_name",)),
        ("phone_reprompt", "When the phone number can't be read", "Used only when the phone question is on.", ("business_name",)),
        ("email_reprompt", "When the email can't be read", "Used only when the email question is on.", ("business_name",)),
    )),
    ("confirmation", "Confirmation", (
        ("booking_confirmation", "Booking confirmation", "Sent only after the calendar event exists.",
         ("service", "when", "location", "business_name", "invite_line", "calendar_links",
          "links_page", "google_link", "outlook_link", "ical_link", "invited_email", "event_id")),
        ("slot_unavailable", "When the time is taken", "", ("business_name",)),
        ("booking_error", "When the calendar can't be reached",
         "Must say no booking was made and must not contain the word call.", ("business_name",)),
    )),
    ("followups", "Follow-ups", (
        ("followup_1", "First nudge (no reply)", "Sent {delay_1} after the first text if there's no reply.", ("business_name",)),
        ("followup_2", "Last nudge (no reply)", "Sent {delay_2} after the first nudge.", ("business_name",)),
    )),
    ("stop_help", "STOP and HELP", (
        ("help", "Reply to HELP", "The contact number is set on the Phone page.", ("business_name", "contact_line")),
        ("opt_in", "Reply to START", "", ("business_name",)),
        ("opt_out_ack", "Reply to STOP", "", ("business_name",)),
        ("handoff_ack", "When the owner needs to step in", "Must promise a follow up (those two words).", ("business_name",)),
        ("handoff_ack_safety", "Safety hand-off", "Must mention 911 and promise a follow up.", ("business_name",)),
    )),
)
FIELD_SPECS = {key: (label, hint, chips) for _, _, fields in GROUPS for key, label, hint, chips in fields}
EDITABLE_KEYS = tuple(FIELD_SPECS)
LABELS = {key: label for key, (label, _, _) in FIELD_SPECS.items()}
TOGGLES = {
    "prompt_phone": ("ask_phone", "phone", "Also ask for the best phone number"),
    "prompt_email": ("ask_email", "email", "Also ask for an email address"),
}

# --- SMS segment arithmetic (mirrored in portal.js) ------------------------------

GSM_BASIC = ("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡"
             "ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")
GSM_EXT = "^{}\\[~]|€"


def segments(text: str) -> dict:
    """{'chars', 'segments', 'ucs2', 'special'} for one rendered SMS body.

    ``chars`` counts UTF-16 units, the same number portal.js sees in
    ``String.length`` and the one carriers bill for UCS-2 texts.
    """
    septets, ucs2, special = 0, False, ""
    for ch in text:
        if ch in GSM_BASIC:
            septets += 1
        elif ch in GSM_EXT:
            septets += 2
        else:
            ucs2 = True
            special = special or ch
    units = len(text.encode("utf-16-le")) // 2
    if ucs2:
        count = 1 if units <= 70 else math.ceil(units / 67)
    else:
        count = 1 if septets <= 160 else math.ceil(septets / 153)
    return {"chars": units, "segments": count, "ucs2": ucs2, "special": special}


_TOKEN = re.compile(r"\{(\w+)\}")


def render_sample(key: str, template: str, samples: dict, suffix: str, trial: bool) -> tuple[str, bool]:
    """(text as the customer would see it, whether the opt-out line was appended).

    Mirrors MessageSet.render with sample values but never raises, so an
    invalid draft still previews (the error is shown beside the field).
    """
    allowed = PLACEHOLDERS.get(key, frozenset())
    text = _TOKEN.sub(lambda m: str(samples.get(m.group(1), "")) if m.group(1) in allowed else "", template)
    suffixed = key in OPT_OUT_REQUIRED and not _mentions_stop(template)
    if suffixed:
        text = f"{text} {suffix}"
    text = " ".join(text.split())
    return ((TRIAL_PREFIX + text) if trial else text), suffixed


def describe(key: str, template: str, samples: dict, suffix: str, trial: bool) -> str:
    """The counter line: '135 characters · 1 text · Includes the opt-out line.'"""
    text, suffixed = render_sample(key, template, samples, suffix, trial)
    info = segments(text)
    notes = []
    if suffixed:
        notes.append("Includes the opt-out line.")
    if trial:
        notes.append("Includes the '[SignalWire Free Trial]' tag until registration completes.")
    if info["ucs2"]:
        notes.append(f"Uses a special character ({info['special']}), so each text holds 70 characters.")
    if len(template) > MAX_CHARS:
        notes.append(f"Over the {MAX_CHARS}-character limit.")
    line = f"{info['chars']} characters · {info['segments']} {'text' if info['segments'] == 1 else 'texts'}"
    return line + (" · " + " ".join(notes) if notes else "")


# --- sample data and preview script (IA C.2) -------------------------------------

def sample_data(state, *, ask_email: bool) -> dict:
    base = str(getattr(state, "public_base_url", "") or "").rstrip("/")
    root = f"{base}/a/1-000000000000"
    contact = (getattr(state, "business_contact", "") or "").strip() or format_contact_number(getattr(state, "business_number", "") or "")
    try:
        zone = ZoneInfo(getattr(state, "timezone_name", "UTC") or "UTC")
        when = datetime(2026, 10, 22, 16, 0, tzinfo=zone).strftime("%A, %b %d at %I:%M %p %Z").replace(" 0", " ")
    except Exception:  # noqa: BLE001 - a sample must never break the page
        when = "Thursday, Oct 22 at 4:00 PM EDT"
    return {
        "business_name": state.business_name,
        "service": "tree removal",
        "location": "412 Maple St",
        "when": when,
        "event_id": "evt-0001",
        "contact_line": f" Contact: {contact}." if contact else "",
        "calendar_links": f"Add to calendar: Google {root}/g Outlook {root}/o iCal {root}/i",
        "links_page": root, "google_link": f"{root}/g", "outlook_link": f"{root}/o", "ical_link": f"{root}/i",
        "invite_line": f"A calendar invite is on its way to {SAMPLE_EMAIL}." if ask_email else "",
        "invited_email": SAMPLE_EMAIL if ask_email else "",
    }


def preview_script(templates: dict, samples: dict, *, ask_phone: bool, ask_email: bool,
                   delay_labels: tuple[str, str], trial: bool) -> list[dict]:
    """Ordered bubbles: kind in {caption, out, in}; out bubbles carry their template key."""
    suffix = templates.get("opt_out_suffix", DEFAULT_TEMPLATES["opt_out_suffix"])
    items: list[dict] = []

    prefix = TRIAL_PREFIX.strip() if trial else ""

    def out(key, *, cond=False, meta="", when=""):
        # The tag is shown as its own dim span in the bubble, so render without it here.
        text, _ = render_sample(key, templates.get(key, DEFAULT_TEMPLATES[key]), samples, suffix, False)
        items.append({"kind": "out", "key": key, "text": text, "prefix": prefix, "cond": cond, "meta": meta, "when": when})

    def inbound(text, when=""):
        items.append({"kind": "in", "key": "", "text": text, "prefix": "", "cond": False, "meta": "", "when": when})

    def caption(text, when=""):
        items.append({"kind": "caption", "key": "", "text": text, "prefix": "", "cond": False, "meta": "", "when": when})

    caption(f"Missed call from {SAMPLE_CALLER}")
    out("intro")
    out("prompt_service", cond=True, meta="Sent only if the first reply is blank")
    inbound("Tree removal")
    out("prompt_location")
    inbound("412 Maple St")
    out("prompt_preferred_time")
    inbound("Thursday at 4")
    out("prompt_name")
    inbound(SAMPLE_CALLER)
    out("prompt_phone", when="ask_phone")
    inbound("YES", when="ask_phone")
    out("prompt_email", when="ask_email")
    inbound(SAMPLE_EMAIL, when="ask_email")
    out("booking_confirmation")
    caption(f"If {SAMPLE_CALLER} doesn't reply")
    out("followup_1", meta=f"{delay_labels[0]} later")
    out("followup_2", meta=f"{delay_labels[1]} after that")
    caption("If the time is taken")
    out("slot_unavailable")
    caption("If the calendar can't be reached")
    out("booking_error")
    caption("If a reply can't be read")
    out("preferred_time_reprompt")
    out("phone_reprompt", when="ask_phone")
    out("email_reprompt", when="ask_email")
    caption(f"If {SAMPLE_CALLER} texts STOP")
    inbound("STOP")
    out("opt_out_ack")
    caption(f"If {SAMPLE_CALLER} texts HELP")
    inbound("HELP")
    out("help")
    caption(f"If {SAMPLE_CALLER} texts START")
    inbound("START")
    out("opt_in")
    caption(f"If {SAMPLE_CALLER} asks for the owner")
    inbound("Can I talk to someone?")
    out("handoff_ack")
    caption(f"If {SAMPLE_CALLER} mentions an emergency")
    out("handoff_ack_safety")
    for item in items:
        item["hidden"] = (item["when"] == "ask_phone" and not ask_phone) or (item["when"] == "ask_email" and not ask_email)
    return items


def trial_prefix_applies() -> bool:
    """True until the staged registration shows the number as complete (unknown counts as trial)."""
    status = portal_data.registration_status()
    return not (status and status.get("complete"))


# --- validation (IA C.4) -----------------------------------------------------------

_UNSUPPORTED = re.compile(r"^(\w+) uses unsupported placeholder\(s\) (.+); allowed: (.+)$")
_FORBIDDEN = re.compile(r"^(\w+) must not promise a person or the business line \('(.+)'\)$")


def owner_reason(message: str, key: str = "") -> str:
    """Turn a ``messages.validate_templates`` reason into owner copy.

    Field keys become labels ("opt_out_suffix must ..." -> "Opt-out line must ..."),
    engine wording is rewritten ("template", "placeholder", "keep the customer texting"),
    and reasons that carry no key are prefixed with the label of ``key`` (the field
    being checked). Always ends with a full stop.
    """
    label = LABELS.get(key, "")
    prefix = f"{label}: " if label else ""
    if (m := _UNSUPPORTED.match(message)):
        head, bad, allowed = m.groups()
        bad_list = ", ".join(bad.split(", "))
        verb = "isn't a fill-in" if len(bad.split(", ")) == 1 else "aren't fill-ins"
        allowed_text = f" You can use {allowed}." if allowed != "none" else " This text has no fill-ins."
        message = f"{LABELS.get(head, head)}: {bad_list} {verb} for this text.{allowed_text}"
    elif (m := _FORBIDDEN.match(message)):
        head, phrase = m.groups()
        message = f"{LABELS.get(head, head)}: can't contain '{phrase}'"
    elif message == "unbalanced { or } in template":
        message = f"{prefix}a {{ is missing its }}"
    elif message == "placeholders must look like {business_name}":
        message = f"{prefix}fill-ins look like {{business_name}}"
    elif message.startswith("booking_error must say no booking was made"):
        message = f"{LABELS['booking_error']}: must say no booking was made and must not contain the word call"
    elif message.startswith("handoff acknowledgements must promise a follow-up"):
        message = "This text must promise a follow up (those two words)"
    else:
        head, _, rest = message.partition(" ")
        if head in LABELS:
            message = f"{LABELS[head]} {rest}"
    message = message[:1].upper() + message[1:]
    return message if message.endswith((".", "!", "?")) else message + "."


def _fields_for(message: str, key: str, merged: dict) -> list[str]:
    head = message.split(" ", 1)[0]
    if head in DEFAULT_TEMPLATES:
        return [head]
    if message.startswith("handoff acknowledgements"):
        failing = [k for k in ("handoff_ack", "handoff_ack_safety") if "follow up" not in merged.get(k, DEFAULT_TEMPLATES[k]).lower()]
        return failing or ["handoff_ack"]
    return [key]


def validate_fields(overrides: dict[str, str], base: dict[str, str]) -> dict[str, str]:
    """Inline errors {field key: owner text}. ``overrides`` = the non-blank submitted texts
    (plus ``fields``); ``base`` = the overrides currently in the file. Nothing is written here."""
    errors: dict[str, str] = {}
    for key, text in overrides.items():
        if key == "fields":
            continue
        try:
            validate_templates({**base, key: text})
        except MessageTemplateError as exc:
            for field in _fields_for(str(exc), key, {**base, key: text}):
                errors.setdefault(field, owner_reason(str(exc), field))
    if not errors:
        try:
            validate_templates(overrides)
        except MessageTemplateError as exc:
            merged = {**DEFAULT_TEMPLATES, **overrides}
            for field in _fields_for(str(exc), next(iter(overrides), "intro"), merged):
                errors.setdefault(field, owner_reason(str(exc), field))
    return errors


# --- page context --------------------------------------------------------------------

def page_context(state, *, drafts: dict[str, str] | None = None, errors: dict[str, str] | None = None,
                 ask: dict[str, bool] | None = None) -> dict:
    """Everything pages/messages.html needs beyond the layout contract.

    ``drafts`` re-renders what the owner just submitted (after an error);
    otherwise the file's current set is shown. ``ask`` overrides the switches
    the same way.
    """
    from text_back.portal_scheduling import humanize_minutes

    source = state.messages
    current = source.current()
    editable = source.path is not None
    errors = errors or {}
    asked = set(current.fields)
    ask = ask if ask is not None else {"phone": "phone" in asked, "email": "email" in asked}
    templates = dict(current.templates)
    if drafts is not None:
        for key in EDITABLE_KEYS:
            templates[key] = drafts.get(key) or DEFAULT_TEMPLATES[key]
    trial = trial_prefix_applies()
    samples = sample_data(state, ask_email=ask["email"])
    suffix = templates["opt_out_suffix"]
    delays = state.followup_policy.delays_minutes
    delay_labels = (humanize_minutes(delays[0]), humanize_minutes(delays[1] if len(delays) > 1 else delays[0]))

    groups = []
    for group_key, title, fields in GROUPS:
        rows = []
        for key, label, hint, chips in fields:
            template = templates[key]
            if drafts is not None:
                value = drafts.get(key, "")
            else:
                value = template if template != DEFAULT_TEMPLATES[key] else ""
            hint = hint.replace("{delay_1}", delay_labels[0]).replace("{delay_2}", delay_labels[1])
            toggle = None
            if key in TOGGLES:
                name, field, text = TOGGLES[key]
                toggle = {"name": name, "label": text, "on": ask[field]}
            rows.append({
                "key": key, "label": label, "hint": hint, "value": value,
                "default": DEFAULT_TEMPLATES[key], "error": errors.get(key, ""),
                "chips": [(token, PLACEHOLDER_LABELS.get(token, token)) for token in chips],
                "allowed": " ".join(sorted(PLACEHOLDERS[key])),
                "suffix_required": "1" if key in OPT_OUT_REQUIRED else "0",
                "describe": describe(key, template, samples, suffix, trial),
                "toggle": toggle,
            })
        edited = sum(1 for row in rows if row["value"] and row["value"] != row["default"])
        groups.append({"key": group_key, "title": title, "fields": rows, "edited": edited})

    return {
        "groups": groups,
        "editable": editable,
        "ask": ask,
        "trial": trial,
        "samples": samples,
        "preview": preview_script(templates, samples, ask_phone=ask["phone"], ask_email=ask["email"],
                                  delay_labels=delay_labels, trial=trial),
        "sample_caller": SAMPLE_CALLER,
        "max_chars": MAX_CHARS,
    }


def read_form(form) -> tuple[dict[str, str], dict[str, str], dict[str, bool], str]:
    """(drafts, overrides, ask, reset_key) from a posted Messages form."""
    drafts = {key: " ".join(str(form.get(key, "")).split()) for key in EDITABLE_KEYS}
    reset_key = str(form.get("reset", "") or "")
    if reset_key in drafts:
        drafts[reset_key] = ""
    ask = {field: bool(form.get(f"ask_{field}")) for field in ("phone", "email")}
    overrides = {key: text for key, text in drafts.items() if text}
    extra = [field for field in ("phone", "email") if ask[field]]
    if extra:
        overrides["fields"] = ", ".join(("service", "location", "preferred_time", "name", *extra))
    return drafts, overrides, ask, reset_key
