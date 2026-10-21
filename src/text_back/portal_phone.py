"""Phone page helpers: the business name, the three typed numbers, the HELP
contact, the texting-number ownership check, the carrier forwarding codes and
the five-step checklist. Routes live in client_settings.install_routes.

Numbers are typed, never picked. The texting number is accepted only when the
telecom provider confirms the account already owns it and its voice/SMS
handlers point at text_back; there is no path here that buys, ports or
provisions anything.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

from text_back import portal_data
from text_back.client_portal import normalize_mobile
from text_back.policy import format_contact_number
from text_back.telecom import TelecomError

NAME_MAX = 60
FIELD_ORDER = ("business_name", "business_line", "text_back_number", "owner_mobile", "business_contact", "carrier")
VERIFIABLE = ("business_line", "text_back_number", "owner_mobile")
LABELS = {
    "business_name": "Business name",
    "business_line": "Your business number",
    "text_back_number": "Texting number",
    "owner_mobile": "Your mobile",
    "business_contact": "Number shown in HELP replies",
    "carrier": "Your carrier",
}
ERR_NAME = f"Enter a business name of 1 to {NAME_MAX} characters."
ERR_LINE = "Enter your business number as digits, like 704 555 0123, or leave it blank."
ERR_SAME = "Your business number and texting number can't be the same."
ERR_TEXTING = "Enter the texting number as digits, like 704 555 0123, or leave it blank."
ERR_MOBILE = "Enter your mobile as digits, like 704 555 0123."
ERR_CONTACT = "Enter the customer phone number as digits, like 704 555 0123, or leave it blank."
ERR_CARRIER = "Pick a carrier from the list."
NOT_SET_UP = "Checking numbers is not set up for this account yet."
UNREACHABLE = "The texting service could not be reached. Try again in a minute."
NOT_OWNED = "{n} is not a number this account owns."
WRONG_HANDLERS = "{n} can't be used: its voice/SMS handlers do not point at text_back."
OWNED_OK = "Owned by this account and pointed at text_back."
NOTHING_TO_CHECK = "Enter a number to check."
SAVED = "Saved."
KEPT = "Kept your current mobile."
CHECKS_SAVED = "Checks saved."
NEW_MOBILE_SAVED = "Saved. Sign-in codes now go to {n}."
SAVED_CONFIRM_MOBILE = "Saved. Now confirm your new mobile."
CARRIERS = (("verizon", "Verizon"), ("tmobile", "T-Mobile"), ("att", "AT&T"), ("cricket", "Cricket"), ("other", "Other"))
CARRIER_KEYS = {key for key, _ in CARRIERS}
MANUAL_CHECKS = {3: "answered_no_text", 5: "deactivation_saved"}
FORWARD_ALL_WARNING = "Only forward busy and unanswered calls. Forward-all would send every call to the assistant."
EVIDENCE_NOTE = "Steps 1, 2 and 4 are ticked from real calls recorded by the assistant."
PLACEHOLDER_DIGITS = "<your texting number>"


# --- values ---------------------------------------------------------------------

def default_texting_number(state) -> str:
    defaults = getattr(state, "defaults", None) or {}
    return str(defaults.get("text_back_number") or "")


def effective_texting_number(state) -> str:
    return str(state.store.setting("text_back_number") or default_texting_number(state) or "")


def current_values(state) -> dict:
    store = state.store
    return {
        "business_name": state.business_name,
        "business_line": store.setting("business_line") or "",
        "text_back_number": effective_texting_number(state),
        "owner_mobile": getattr(state, "owner_mobile", "") or "",
        "business_contact": getattr(state, "business_contact", "") or "",
        "carrier": store.setting("carrier") or "",
    }


def read_form(form) -> dict:
    """Submitted strings; an absent texting-number field is None (leave it untouched), a blank one is ""."""
    values = {key: str(form.get(key, "") or "").strip() for key in FIELD_ORDER}
    if "text_back_number" not in form:
        values["text_back_number"] = None
    return values


def validate(submitted: dict, state) -> tuple[dict, dict]:
    """Normalised values and per-field errors (exact owner-facing reasons)."""
    values, errors = {}, {}
    name = " ".join(submitted.get("business_name", "").split())
    if not name or len(name) > NAME_MAX:
        errors["business_name"] = ERR_NAME
    values["business_name"] = name

    line = submitted.get("business_line", "")
    if line:
        normalized = normalize_mobile(line)
        if normalized is None:
            errors["business_line"] = ERR_LINE
        line = normalized or ""
    values["business_line"] = line

    texting = submitted.get("text_back_number", "")
    if texting is None:  # field not in the form: keep whatever is saved
        texting = str(state.store.setting("text_back_number") or "")
    elif texting:
        normalized = normalize_mobile(texting)
        if normalized is None:
            errors["text_back_number"] = ERR_TEXTING
        texting = normalized or ""
    values["text_back_number"] = texting
    effective = texting or default_texting_number(state)
    if line and effective and line == effective and "business_line" not in errors:
        errors["business_line"] = ERR_SAME

    mobile = normalize_mobile(submitted.get("owner_mobile", ""))
    if mobile is None:
        errors["owner_mobile"] = ERR_MOBILE
    values["owner_mobile"] = mobile or ""

    contact = submitted.get("business_contact", "")
    if contact:
        normalized = normalize_mobile(contact)
        if normalized is None:
            errors["business_contact"] = ERR_CONTACT
        contact = format_contact_number(normalized) if normalized else ""
    values["business_contact"] = contact

    carrier = submitted.get("carrier", "")
    if carrier and carrier not in CARRIER_KEYS:
        errors["carrier"] = ERR_CARRIER
    values["carrier"] = carrier if carrier in CARRIER_KEYS else ""
    return values, errors


def first_error(errors: dict) -> str:
    for key in FIELD_ORDER:
        if errors.get(key):
            return errors[key]
    return next(iter(errors.values()), "")


# --- texting number -------------------------------------------------------------

def check_texting_number(state, e164: str) -> tuple[bool, str]:
    """Is ``e164`` owned by this account with its handlers pointed at text_back?"""
    telecom = state.telecom
    if not hasattr(telecom, "lookup_number"):
        return False, NOT_SET_UP
    try:
        result = telecom.lookup_number(e164)
    except TelecomError:
        return False, UNREACHABLE
    shown = format_contact_number(e164)
    if not result.owned:
        return False, NOT_OWNED.format(n=shown)
    base = str(state.public_base_url).rstrip("/")
    if result.voice_url != base + "/webhooks/voice" or result.sms_url != base + "/webhooks/sms":
        return False, WRONG_HANDLERS.format(n=shown)
    return True, OWNED_OK


def texting_number_changed(state, typed: str) -> bool:
    """True when saving ``typed`` (E.164 or blank) would change the sender in use."""
    current_setting = str(state.store.setting("text_back_number") or "")
    if not typed:
        return bool(current_setting)
    return typed != (current_setting or default_texting_number(state))


def texting_number_problem(state, values: dict) -> str:
    """The reason the typed texting number cannot be saved, or '' (runs the live check only on a change)."""
    typed = values.get("text_back_number", "")
    if not typed or not texting_number_changed(state, typed):
        return ""
    ok, reason = check_texting_number(state, typed)
    return "" if ok else reason


def apply_texting_number(state, e164: str | None, now: datetime | None = None) -> None:
    """Persist the sender and point the running app and telecom guard at it (blank = env default)."""
    state.store.set_setting("text_back_number", e164 or None, now=now)
    number = e164 or default_texting_number(state)
    state.business_number = number
    if hasattr(state.telecom, "allowed_from_number"):
        state.telecom.allowed_from_number = number


# --- verify and save ------------------------------------------------------------

def verify(state, field: str, values: dict) -> tuple[str, str] | None:
    """(kind, text) for the status line under one field; nothing is saved."""
    if field == "business_line":
        number = values.get("business_line", "")
        return ("warn", NOTHING_TO_CHECK) if not number else ("ok", f"Looks good: {format_contact_number(number)}.")
    if field == "text_back_number":
        number = values.get("text_back_number", "") or default_texting_number(state)
        if not number:
            return ("warn", NOTHING_TO_CHECK)
        ok, text = check_texting_number(state, number)
        return ("ok" if ok else "err", text)
    if field == "owner_mobile":
        number = values.get("owner_mobile", "")
        if number == (getattr(state, "owner_mobile", "") or ""):
            return ("ok", "This is the number that signs you in.")
        return ("info", f"Save to text a code to {format_contact_number(number)}.")
    return None


def save(state, values: dict, now: datetime) -> str | None:
    """Write every validated value. Returns the pending new mobile when a code was texted."""
    from text_back.client_portal import send_code

    store = state.store
    typed = values.get("text_back_number", "")
    if texting_number_changed(state, typed):
        apply_texting_number(state, typed or None, now)
    store.set_setting("business_name", values["business_name"], now=now)
    store.set_setting("business_contact", values["business_contact"], now=now)
    store.set_setting("business_line", values["business_line"] or None, now=now)
    store.set_setting("carrier", values["carrier"] or None, now=now)
    state.business_name = values["business_name"]
    state.business_contact = values["business_contact"]
    mobile = values["owner_mobile"]
    if mobile and mobile != (getattr(state, "owner_mobile", "") or ""):
        store.set_setting("owner_mobile_pending", mobile, now=now)
        send_code(state, mobile, now, purpose="new mobile")
        return mobile
    return None


# --- forwarding codes -----------------------------------------------------------

def _rows(entries, digits: str, carrier: str):
    return [{"label": label, "code": code.replace("{d}", digits or PLACEHOLDER_DIGITS),
             "aria": f"{aria} for {carrier}"} for label, code, aria in entries]


def carrier_blocks(digits: str, formatted: str) -> list[dict]:
    """One block per carrier from docs/ONBOARDING-FORWARDING.md with <TB> filled in."""
    gsm_on = [("No answer", "**61*1{d}#", "Copy no-answer activation code"),
              ("Busy", "**67*1{d}#", "Copy busy activation code")]
    gsm_off = [("No answer", "##61#", "Copy no-answer deactivation code"),
               ("Busy", "##67#", "Copy busy deactivation code"),
               ("Reset all forwarding", "##004#", "Copy reset code")]
    shown = formatted or PLACEHOLDER_DIGITS
    blocks = [
        {"key": "verizon", "name": "Verizon", "verified": True, "steps": "",
         "on": _rows([("Busy and no answer", "*71{d}", "Copy activation code")], digits, "Verizon"),
         "off": _rows([("All forwarding", "*73", "Copy deactivation code")], digits, "Verizon"),
         "notes": ["Covers busy and no answer. Dial from your phone while on Verizon's network, then press Call."]},
        {"key": "tmobile", "name": "T-Mobile", "verified": True, "steps": "",
         "on": _rows(gsm_on + [("Unreachable", "**62*1{d}#", "Copy unreachable activation code"),
                               ("No answer, ring 20 seconds first", "**61*1{d}**20#", "Copy ring-delay activation code")], digits, "T-Mobile"),
         "off": _rows(gsm_off[:2] + [("Unreachable", "##62#", "Copy unreachable deactivation code")] + gsm_off[2:], digits, "T-Mobile"),
         "notes": ["Dial each code, then press Call."]},
        {"key": "att", "name": "AT&T", "verified": False,
         "steps": f"Android: open the Phone app, then Settings, then Call forwarding. Set 'When busy' and 'When unanswered' to {shown}.",
         "on": _rows(gsm_on, digits, "AT&T"), "off": _rows(gsm_off, digits, "AT&T"),
         "notes": ["On iPhone, skip the Settings toggle: it forwards every call. Dial the codes instead."]},
        {"key": "cricket", "name": "Cricket", "verified": False, "steps": "",
         "on": _rows(gsm_on, digits, "Cricket"), "off": _rows(gsm_off, digits, "Cricket"),
         "notes": ["Cricket doesn't publish codes. Check with *#61# and *#67#. If forwarding sticks, call 611."]},
        {"key": "other", "name": "Other", "verified": True,
         "steps": f"Ask your carrier to turn on conditional call forwarding, busy and no answer, to {shown}. Never forward all calls.",
         "on": [], "off": [], "notes": []},
    ]
    return blocks


def national_digits(e164: str) -> str:
    digits = re.sub(r"\D", "", e164 or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


# --- checklist ------------------------------------------------------------------

def checklist_context(state, carrier: str, off_code: str) -> dict:
    checklist = portal_data.forwarding_checklist(state)
    for step in checklist["steps"]:
        key = MANUAL_CHECKS.get(step["n"])
        step["name"] = f"check_{key}" if key else ""
        step["code"] = off_code if step["n"] == 5 and carrier else ""
    return checklist


def save_checklist(state, form, now: datetime) -> None:
    """Manual ticks 3 and 5: keep the first tick's timestamp, drop an untick."""
    try:
        current = json.loads(state.store.setting("forwarding_checklist") or "{}")
    except ValueError:
        current = {}
    if not isinstance(current, dict):
        current = {}
    for key in MANUAL_CHECKS.values():
        ticked = str(form.get(f"check_{key}", "")) == "1"
        current[key] = (current.get(key) or now.isoformat()) if ticked else None
    state.store.set_setting("forwarding_checklist", json.dumps(current), now=now)


# --- page -----------------------------------------------------------------------

def page_context(state, values: dict | None = None, errors: dict | None = None, statuses: dict | None = None,
                 *, pending: str | None = None, code_error: str = "") -> dict:
    """Everything phone.html needs beyond the layout contract."""
    values = dict(values) if values is not None else current_values(state)
    errors = errors or {}
    statuses = statuses or {}
    # Dial codes are built from the texting number in use, never from a typed one that was
    # refused or has not been saved yet.
    texting = effective_texting_number(state)
    if values.get("text_back_number") is None:
        values["text_back_number"] = texting
    digits = national_digits(texting)
    formatted = format_contact_number(texting) if texting else ""
    carrier = values.get("carrier", "") if values.get("carrier", "") in CARRIER_KEYS else ""
    blocks = carrier_blocks(digits, formatted)
    off_code = next((row["code"] for block in blocks if block["key"] == carrier for row in block["off"]), "")
    texting_hint = ("The number texts come from. It must already be on this account." if (texting or values.get("text_back_number"))
                    else "Ask text_back for the texting number assigned to you.")
    return {
        "values": values, "errors": errors, "statuses": statuses, "labels": LABELS,
        "pending": pending, "code_error": code_error,
        "carriers": CARRIERS, "carrier": carrier, "carrier_blocks": blocks, "has_number": bool(digits),
        "checklist": checklist_context(state, carrier, off_code),
        "forward_all_warning": FORWARD_ALL_WARNING, "evidence_note": EVIDENCE_NOTE,
        "hints": {
            "business_name": f'Used in every text, for example "Thanks for calling {state.business_name}".',
            "business_line": "The number customers call. It forwards to your texting number when you don't answer. We never change it.",
            "text_back_number": texting_hint,
            "owner_mobile": "Sign-in codes and alerts go here. Changing it texts a code to the new number first.",
            "business_contact": "Customers who text HELP see this number. Leave blank to show the texting number.",
        },
    }
