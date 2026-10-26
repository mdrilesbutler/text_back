"""Phone page helpers for the owner portal (candidate C).

The business name, the business number, the owner's mobile (changed in two steps: a code is
texted to the NEW number and nothing moves until it is entered), the number shown in the HELP
reply, the carrier with its forwarding codes, and the five-step forwarding checklist from
portal_forwarding. Routes live in client_settings; templates render what page_context returns.

The texting number is read-only here. It is shown from the running sender with the locked
sentence "Set up by FluxWorks. It can't be changed here." and no form field can change it:
read_form ignores a posted value, validate and save never look at one.

Every owner-facing string comes from docs/notes/portal-c/copy-deck.md. Carrier codes come
from docs/ONBOARDING-FORWARDING.md; its VERIFIED / UNVERIFIED labels are carried as data.
"""
from __future__ import annotations

import re
from datetime import datetime

from text_back import portal_forwarding
from text_back.client_portal import check_code, normalize_mobile, send_code
from text_back.policy import format_contact_number

NAME_MAX = 60
FIELD_ORDER = ("business_name", "business_line", "owner_mobile", "business_contact", "carrier")
VERIFIABLE = ("business_line", "owner_mobile")
PENDING_MOBILE_KEY = "owner_mobile_pending"
CODE_PURPOSE = "new mobile"

LABELS = {
    "business_name": "Business name",
    "business_line": "Your business number",
    "text_back_number": "Texting number",
    "owner_mobile": "Your mobile",
    "business_contact": "Number in the HELP reply",
    "carrier": "Your carrier",
}
ERR_NAME = f"Enter a business name of 1 to {NAME_MAX} characters."
ERR_LINE = "Enter your business number as 10 digits, like 704 555 0123, or leave it blank."
ERR_SAME = "Your business number and the texting number can't be the same."
ERR_MOBILE = "Enter your mobile as 10 digits, like 704 555 0123."
ERR_CONTACT = "Enter the phone number as 10 digits, like 704 555 0123, or leave it blank."
ERR_CARRIER = "Pick a carrier from the list."
CARRIER_PROMPT = "Pick your carrier to see the codes."
NOTHING_TO_CHECK = "Enter a number to check."
LINE_FORMAT_OK = "Format looks right: {n}. This checks the digits only, not that the number rings."
MOBILE_UNCHANGED = "This is the number that signs you in."
MOBILE_CHANGED = "Save to text a code to {n}."
SAVED = "Saved."
SAVED_CONFIRM_MOBILE = "Saved. Now confirm your new mobile."
NEW_MOBILE_SAVED = "Saved. Sign-in codes now go to {n}."
KEPT = "Kept your current mobile."
CHECKS_SAVED = "Checks saved."
TEXTING_READ_ONLY = "Set up by FluxWorks. It can't be changed here."
TEXTING_NOT_ASSIGNED = "Not assigned yet. FluxWorks sets this up for you."
CODES_NEED_NUMBER = "The codes fill in once FluxWorks assigns your texting number."
UNVERIFIED = "We haven't confirmed these codes on {carrier}. Make a test call afterwards to check."
FORWARDING_INTRO = ("Forward the calls you don't answer to your texting number. Your business number stays "
                    "the same, and answered calls still reach you.")
FORWARD_ALL_WARNING = ("Only forward busy and unanswered calls. Forwarding every call stops answered calls "
                       "from reaching you.")
EVIDENCE_NOTE = "Checks 1, 2 and 4 tick themselves from real calls TextBack recorded. Checks 3 and 5 are yours."
RENAME_ACCEPT = "Update them"
RENAME_DECLINE = "Leave them"
CONFIRM_INTRO = ("We texted a six-digit code to {n}. Enter it to move sign-in to that number. It expires in "
                 "ten minutes; until then codes still go to your current mobile.")
CONFIRM_KEEP = "Keep my current mobile"

CARRIERS = (("verizon", "Verizon"), ("tmobile", "T-Mobile"), ("att", "AT&T"), ("cricket", "Cricket"), ("other", "Other"))
CARRIER_KEYS = {key for key, _ in CARRIERS}
CARRIER_NAMES = dict(CARRIERS)
MANUAL_CHECKS = portal_forwarding.MANUAL  # {3: "answered_no_text", 5: "deactivation_saved"}

# docs/ONBOARDING-FORWARDING.md: {d} is the 10-digit texting number. The GSM codes carry the
# leading 1 as the doc writes them (`**61*1<TB>#`).
_GSM_ON = (("No answer", "**61*1{d}#"), ("Busy", "**67*1{d}#"))
_GSM_OFF = (("No answer", "##61#"), ("Busy", "##67#"), ("Reset all forwarding", "##004#"))
_CARRIER_CODES = {
    "verizon": {
        "verified": True,
        "enable": (("Busy and no answer", "*71{d}"),),
        "disable": (("Reset all forwarding", "*73"),),
        "note": "Covers busy and no answer. Dial from your phone while on Verizon's network, then press Call.",
        "steps": "",
    },
    "tmobile": {
        "verified": True,
        "enable": _GSM_ON + (("Unreachable", "**62*1{d}#"), ("No answer, ring 20 seconds first", "**61*1{d}**20#")),
        "disable": (("No answer", "##61#"), ("Busy", "##67#"), ("Unreachable", "##62#"), ("Reset all forwarding", "##004#")),
        "note": "Dial each code, then press Call.",
        "steps": "",
    },
    "att": {
        "verified": False,
        "enable": _GSM_ON,
        "disable": _GSM_OFF,
        "note": "On iPhone, skip the Settings toggle: it forwards every call. Dial the codes instead.",
        "steps": ('Android: open the Phone app, then Settings, then Call forwarding. '
                  'Set "When busy" and "When unanswered" to {f}.'),
    },
    "cricket": {
        "verified": False,
        "enable": _GSM_ON,
        "disable": _GSM_OFF,
        "note": "Cricket doesn't publish codes. Check with *#61# and *#67#. If forwarding won't turn off, call 611.",
        "steps": "",
    },
    "other": {
        "verified": True,
        "enable": (),
        "disable": (),
        "note": "",
        "steps": ("Ask your carrier to forward only busy and unanswered calls to {f}. "
                  "They call it conditional call forwarding. Never forward all calls."),
    },
}


# --- values ---------------------------------------------------------------------

def texting_number(state) -> str:
    """The sender in use (E.164 or ''). Read-only in the portal."""
    return str(getattr(state, "business_number", "") or "")


def current_values(state) -> dict:
    store = state.store
    return {
        "business_name": state.business_name,
        "business_line": store.setting("business_line") or "",
        "text_back_number": texting_number(state),
        "owner_mobile": getattr(state, "owner_mobile", "") or "",
        "business_contact": getattr(state, "business_contact", "") or "",
        "carrier": store.setting("carrier") or "",
    }


def read_form(form) -> dict:
    """The submitted strings for the editable fields only; a posted texting number is ignored."""
    return {key: str(form.get(key, "") or "").strip() for key in FIELD_ORDER}


def validate(submitted: dict, state) -> tuple[dict, dict]:
    """Normalised values and per-field errors with the exact owner-facing reasons."""
    values, errors = {}, {}
    name = " ".join(str(submitted.get("business_name", "")).split())
    if not name or len(name) > NAME_MAX:
        errors["business_name"] = ERR_NAME
    values["business_name"] = name

    line = str(submitted.get("business_line", "") or "")
    if line:
        normalized = normalize_mobile(line)
        if normalized is None:
            errors["business_line"] = ERR_LINE
        line = normalized or ""
    texting = texting_number(state)
    if line and texting and line == texting and "business_line" not in errors:
        errors["business_line"] = ERR_SAME
    values["business_line"] = line

    mobile = normalize_mobile(str(submitted.get("owner_mobile", "") or ""))
    if mobile is None:
        errors["owner_mobile"] = ERR_MOBILE
    values["owner_mobile"] = mobile or ""

    contact = str(submitted.get("business_contact", "") or "")
    if contact:
        normalized = normalize_mobile(contact)
        if normalized is None:
            errors["business_contact"] = ERR_CONTACT
        contact = format_contact_number(normalized) if normalized else ""
    values["business_contact"] = contact

    carrier = str(submitted.get("carrier", "") or "")
    if carrier and carrier not in CARRIER_KEYS:
        errors["carrier"] = ERR_CARRIER
    values["carrier"] = carrier if carrier in CARRIER_KEYS else ""
    return values, errors


def first_error(errors: dict) -> str:
    for key in FIELD_ORDER:
        if errors.get(key):
            return errors[key]
    return next(iter(errors.values()), "")


# --- verify and save ------------------------------------------------------------

def verify(state, field: str, values: dict) -> tuple[str, str] | None:
    """(kind, text) for the status line under one field; nothing is saved or texted.

    The business number is checked for format only, and the text says so."""
    if field == "business_line":
        number = values.get("business_line", "")
        if not number:
            return ("warn", NOTHING_TO_CHECK)
        return ("ok", LINE_FORMAT_OK.format(n=format_contact_number(number)))
    if field == "owner_mobile":
        number = values.get("owner_mobile", "")
        if not number:
            return ("warn", NOTHING_TO_CHECK)
        if number == (getattr(state, "owner_mobile", "") or ""):
            return ("ok", MOBILE_UNCHANGED)
        return ("info", MOBILE_CHANGED.format(n=format_contact_number(number)))
    return None


def save(state, values: dict, now: datetime) -> str | None:
    """Write every validated value. Returns the pending new mobile when a code was texted to it.

    The owner's mobile itself is not changed here: see confirm_new_mobile."""
    store = state.store
    with store.transaction():
        store.set_setting("business_name", values["business_name"], now=now)
        store.set_setting("business_contact", values["business_contact"], now=now)
        store.set_setting("business_line", values["business_line"] or None, now=now)
        store.set_setting("carrier", values["carrier"] or None, now=now)
    state.business_name = values["business_name"]
    state.business_contact = values["business_contact"]
    mobile = values.get("owner_mobile", "")
    if mobile and mobile != (getattr(state, "owner_mobile", "") or ""):
        store.set_setting(PENDING_MOBILE_KEY, mobile, now=now)
        send_code(state, mobile, now, purpose=CODE_PURPOSE)
        return mobile
    return None


# --- owner mobile, step two -----------------------------------------------------

def pending_mobile(state) -> str | None:
    """The new mobile waiting for its code, or None."""
    return state.store.setting(PENDING_MOBILE_KEY) or None


def keep_current_mobile(state, now: datetime | None = None) -> None:
    """'Keep my current mobile': drop the pending change; sign-in stays where it is."""
    state.store.set_setting(PENDING_MOBILE_KEY, None, now=now)


def confirm_new_mobile(state, code: str, now: datetime) -> str | None:
    """Move sign-in to the pending mobile when ``code`` is its live code. Returns the new
    mobile on success; None when nothing is pending or the code is wrong or expired."""
    pending = pending_mobile(state)
    if not pending or not check_code(state, pending, code, now):
        return None
    with state.store.transaction():
        state.store.set_setting("owner_mobile", pending, now=now)
        state.store.set_setting(PENDING_MOBILE_KEY, None, now=now)
    state.owner_mobile = pending
    return pending


def resend_mobile_code(state, now: datetime) -> str | None:
    """Text a fresh code to the pending mobile (rate limited by send_code). Returns it, or None."""
    pending = pending_mobile(state)
    if not pending:
        return None
    send_code(state, pending, now, purpose=CODE_PURPOSE)
    return pending


# --- rename offer ---------------------------------------------------------------

def texts_with_old_name(templates: dict[str, str], old_name: str) -> list[str]:
    """Keys of the owner's customized texts that still contain ``old_name`` literally
    (case-sensitive substring), in the order the dict holds them."""
    if not old_name:
        return []
    return [key for key, text in templates.items() if isinstance(text, str) and old_name in text]


def rename_in_texts(templates: dict[str, str], old_name: str, new_name: str) -> dict[str, str]:
    """A new override dict with ``old_name`` replaced by ``new_name`` in the texts that hold it."""
    keys = set(texts_with_old_name(templates, old_name))
    return {key: (text.replace(old_name, new_name) if key in keys else text) for key, text in templates.items()}


def rename_offer_text(count: int, old_name: str) -> str:
    if count == 1:
        return f'Update 1 text that still says "{old_name}"'
    return f'Update {count} texts that still say "{old_name}"'


def rename_done_text(count: int) -> str:
    return "Updated 1 text." if count == 1 else f"Updated {count} texts."


def rename_offer(templates: dict[str, str], old_name: str, new_name: str) -> dict | None:
    """What to offer after a rename, or None when no customized text still says the old name."""
    if not old_name or old_name == new_name:
        return None
    keys = texts_with_old_name(templates, old_name)
    if not keys:
        return None
    return {
        "count": len(keys), "keys": keys, "old_name": old_name, "new_name": new_name,
        "text": rename_offer_text(len(keys), old_name),
        "accept": RENAME_ACCEPT, "decline": RENAME_DECLINE, "done": rename_done_text(len(keys)),
    }


# --- forwarding codes -----------------------------------------------------------

def national_digits(number: str) -> str:
    """The 10 national digits of a US number in any format, or ''."""
    digits = re.sub(r"\D", "", number or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def forwarding_codes(carrier: str, texting_number: str) -> dict:
    """The dial codes for one carrier with the texting number filled in.

    Keys: name, enable [(label, code)], disable [(label, code)], verified, unverified (the
    warning text, '' when verified), note, steps. With no carrier, an unknown one, or no
    texting number there are no codes and ``note`` says why."""
    empty = {"key": carrier if carrier in CARRIER_KEYS else "", "name": CARRIER_NAMES.get(carrier, ""),
             "enable": [], "disable": [], "verified": True, "unverified": "", "note": "", "steps": ""}
    if carrier not in CARRIER_KEYS:
        return {**empty, "note": CARRIER_PROMPT}
    digits = national_digits(texting_number)
    if not digits:
        return {**empty, "note": CODES_NEED_NUMBER}
    spec = _CARRIER_CODES[carrier]
    formatted = format_contact_number(digits)
    name = CARRIER_NAMES[carrier]
    return {
        "key": carrier, "name": name,
        "enable": [(label, code.format(d=digits)) for label, code in spec["enable"]],
        "disable": [(label, code.format(d=digits)) for label, code in spec["disable"]],
        "verified": spec["verified"],
        "unverified": "" if spec["verified"] else UNVERIFIED.format(carrier=name),
        "note": spec["note"],
        "steps": spec["steps"].format(f=formatted),
    }


def turn_off_code(carrier: str, texting_number: str) -> str:
    """The code that turns forwarding off for check 5, or '' when there is none."""
    disable = forwarding_codes(carrier, texting_number)["disable"]
    return disable[0][1] if disable else ""


# --- checklist ------------------------------------------------------------------

def checklist_context(state, now: datetime, carrier: str = "") -> dict:
    """portal_forwarding.checklist plus the form name of each manual step and the turn-off
    code for check 5 (blank until a carrier is picked)."""
    result = portal_forwarding.checklist(state, now)
    code = turn_off_code(carrier, texting_number(state))
    for step in result["steps"]:
        key = MANUAL_CHECKS.get(step["n"])
        step["name"] = f"check_{key}" if key else ""
        step["code"] = code if step["n"] == 5 else ""
    return result


def save_checklist(state, form, now: datetime) -> None:
    """Manual ticks 3 and 5 from the form: a first tick keeps its timestamp, an untick drops it."""
    current = portal_forwarding.manual_ticks(state.store)
    changes = {}
    for key in MANUAL_CHECKS.values():
        ticked = str(form.get(f"check_{key}", "")) == "1"
        if ticked != bool(current.get(key)):
            changes[key] = ticked
    portal_forwarding.save_manual_ticks(state.store, changes, now)


# --- page -----------------------------------------------------------------------

def page_context(state, values: dict | None = None, errors: dict | None = None, statuses: dict | None = None,
                 *, now: datetime, pending: str | None = None, code_error: str = "",
                 rename: dict | None = None) -> dict:
    """Everything phone.html.j2 needs beyond the layout contract."""
    values = dict(values) if values is not None else current_values(state)
    texting = texting_number(state)
    values["text_back_number"] = texting
    carrier = values.get("carrier", "") if values.get("carrier", "") in CARRIER_KEYS else ""
    formatted = format_contact_number(texting) if texting else ""
    pending = pending if pending is not None else pending_mobile(state)
    return {
        "values": values, "errors": errors or {}, "statuses": statuses or {}, "labels": LABELS,
        "texting_number": formatted,
        "texting_note": TEXTING_READ_ONLY if texting else TEXTING_NOT_ASSIGNED,
        "pending": pending,
        "pending_formatted": format_contact_number(pending) if pending else "",
        "confirm_intro": CONFIRM_INTRO.format(n=format_contact_number(pending)) if pending else "",
        "confirm_keep": CONFIRM_KEEP,
        "code_error": code_error,
        "rename": rename,
        "carriers": CARRIERS, "carrier": carrier,
        "codes": forwarding_codes(carrier, texting),
        "has_number": bool(national_digits(texting)),
        "forwarding_intro": FORWARDING_INTRO,
        "forward_all_warning": FORWARD_ALL_WARNING,
        "evidence_note": EVIDENCE_NOTE,
        "checklist": checklist_context(state, now, carrier),
        "hints": {
            "business_name": ('Used in every text, for example "Hey, sorry we missed your call—this is '
                              f'{state.business_name}\'s scheduling assistant."'),
            "business_line": ("The number customers call. Calls you don't answer forward from here to the "
                              "texting number."),
            "owner_mobile": ("Sign-in codes come to this number. If you change it, we text a code to the new "
                             "number and nothing changes until you enter it."),
            "business_contact": (f"Shown when a customer texts HELP. Leave blank to show {formatted or 'the texting number'}. "
                                 "Customers are never transferred to it; the assistant handles the texting."),
        },
    }
