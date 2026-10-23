"""Client settings pages: the business owner signs in and edits message copy.
Business details and the calendar connection live in client_settings.py and
share the sign-in, page frame and code helpers defined here.

Sign-in is passwordless. The owner enters the business mobile that is on
file (TEXT_BACK_OWNER_MOBILE); if it matches, a six-digit code is texted to
that number and nothing else. The code lives ten minutes, allows five
guesses, and a browser session lasts twelve hours. Every page is
server-rendered from the Jinja templates in templates/client through
portal_render.render(), with one stylesheet and one ES module served from
/client/static and a strict Content-Security-Policy; JavaScript only adds
behaviour on top of pages that work without it.

The Messages page is one long page in conversation order: five moments on a
spine (missed call, the questions, booking, no reply, owner steps in) and,
off the spine, the START/HELP/STOP replies that can arrive at any time. Every
message is a card: its title and state, a phone-bubble preview of what the
customer will receive with a receipt line (texts, characters, why a text is
billed as more than one), and the editor in a native disclosure with the rule,
the placeholder chips and a one-tap reset. A phone-frame rail replays whole
sample conversations with the same rendered texts.
"""
from __future__ import annotations

import hashlib
import hmac
import math
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from string import Formatter

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

from text_back.messages import (
    DEFAULT_TEMPLATES,
    MAX_TEMPLATE_CHARS,
    OPT_OUT_REQUIRED,
    PLACEHOLDERS,
    MessageTemplateError,
    write_message_file,
)
from text_back.policy import format_contact_number
from text_back.portal_render import mount_static, render
from text_back.sms import enqueue_sms, run_due_sms

CODE_TTL = timedelta(minutes=10)
CODE_ATTEMPTS = 5
CODES_PER_WINDOW = 3
CODE_WINDOW = timedelta(minutes=15)
SESSION_TTL = timedelta(hours=12)
SESSION_COOKIE = "text_back_client"
PENDING_COOKIE = "text_back_client_login"
CODE_FAILURE = "That code is not right or has expired. Check the text or send a new code."

# --- the Messages page: every text, in the order the customer meets it --------

# key -> (label, when it is sent, the rule the owner should know before saving). Rules say what the
# validator in messages.py checks; they only re-word it.
_OPT_RULE = "Phone companies require \u201cReply STOP to opt out.\u201d If your wording leaves out STOP, we add that line for you."
MESSAGES: dict[str, tuple[str, str, str]] = {
    "intro": ("First text after a missed call", "Sent the moment a call goes unanswered.", _OPT_RULE),
    "prompt_service": ("Question 1: the job", "Asked as soon as the customer replies.", ""),
    "prompt_location": ("Question 2: the location", "Asked once the job is known.", ""),
    "prompt_preferred_time": ("Question 3: day and time", "Asked once the location is known. Spoken examples help: Wednesday at 2, tomorrow at 10am.", ""),
    "preferred_time_reprompt": ("If the time could not be understood", "Sent instead of moving on when the reply is not a day and time.", ""),
    "prompt_name": ("Question 4: the name", "Asked once the time is known.", ""),
    "prompt_phone": ("Best phone number", "Asked only when switched on. YES keeps the number they are texting from.", ""),
    "phone_reprompt": ("If the phone number could not be read", "Sent when the reply is not a phone number or YES.", ""),
    "prompt_email": ("Email address", "Asked only when switched on. SKIP is allowed.", ""),
    "email_reprompt": ("If the email could not be read", "Sent when the reply is not an email address or SKIP.", ""),
    "slot_unavailable": ("When the time is already taken", "Sent when the calendar shows that slot busy.", ""),
    "booking_confirmation": ("Booking confirmation", "Sent only after the appointment exists on your calendar.", ""),
    "booking_error": ("When the calendar failed", "Sent if the appointment could not be created.",
                      "Must say \u201cNo booking was made\u201d and can\u2019t use the word \u201ccall\u201d; the customer stays in the text thread."),
    "followup_1": ("First reminder", "Sent after the first follow-up delay with no reply.", _OPT_RULE),
    "followup_2": ("Last reminder", "Sent after the second delay. After this the assistant stops texting.", _OPT_RULE),
    "handoff_ack": ("When you need to step in", "Sent when the customer asks for a person or the assistant cannot help; you get a lead.",
                    "Must include the words \u201cfollow up\u201d, like \u201cThe owner will follow up with you by text.\u201d "
                    "Don\u2019t ask them to call or say they\u2019ll be put through to someone."),
    "handoff_ack_safety": ("Safety hand-off", "Sent when a text mentions danger; you get an urgent lead.",
                           "Must include \u201c911\u201d and the words \u201cfollow up\u201d."),
    "opt_in": ("Reply to START", "Sent when a customer texts START.", _OPT_RULE),
    "help": ("Reply to HELP", "Sent when a customer texts HELP.", _OPT_RULE),
    "opt_out_ack": ("Reply to STOP", "Sent once when a customer texts STOP; nothing follows it.", ""),
    "opt_out_suffix": ("Opt-out line", "Added to the first text, reminders, START and HELP replies when they leave out the word STOP.",
                       "Must include the word STOP. Phone companies check for it."),
}

# (group id, heading, what happens at this moment, message keys in order)
GROUPS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("missed", "Missed call", "A call goes unanswered. Within seconds the caller gets this text.", ("intro",)),
    ("questions", "The questions", "Asked one at a time, in this order. The assistant only moves on once it has an answer.",
     ("prompt_service", "prompt_location", "prompt_preferred_time", "preferred_time_reprompt", "prompt_name",
      "prompt_phone", "phone_reprompt", "prompt_email", "email_reprompt")),
    ("booking", "Booking", "With the answers in hand the assistant checks your calendar and books a free slot.",
     ("slot_unavailable", "booking_confirmation", "booking_error")),
    ("noreply", "No reply", "If the customer goes quiet, two reminders. Then it stops.", ("followup_1", "followup_2")),
    ("owner", "You step in", "When a text needs you, automated scheduling pauses and you get a lead.",
     ("handoff_ack", "handoff_ack_safety")),
    ("keywords", "START, HELP and STOP", "Required by phone companies. Most businesses never change these.",
     ("opt_in", "help", "opt_out_ack", "opt_out_suffix")),
)

# Optional questions: the on/off switch lives on the question's own card.
OPTIONAL_QUESTIONS = {"prompt_phone": ("phone", "Also ask for the best phone number"), "prompt_email": ("email", "Also ask for an email address")}

FIELD_KEYS: tuple[str, ...] = tuple(key for _, _, _, keys in GROUPS for key in keys)
# Kept for callers that only need (key, label, hint).
FIELDS = tuple((key, MESSAGES[key][0], MESSAGES[key][1]) for key in FIELD_KEYS)

# --- the Messages page layout: spine, triggers, rail scenarios ------------------
# GROUPS stays as it is (its order and headings are tested); the page is drawn from
# LAYOUT, which adds the spine structure: a parent card and the cards sent instead of
# it when something needs another try (the dashed branches).

_BLURB = {gid: blurb for gid, _, blurb, _ in GROUPS}

# (moment id, heading, node icon, ((parent key, (branch keys, ...)), ...))
LAYOUT = (
    ("missed", "Missed call", "phone-missed", (("intro", ()),)),
    ("questions", "The questions", "message-circle-question", (
        ("prompt_service", ()), ("prompt_location", ()),
        ("prompt_preferred_time", ("preferred_time_reprompt",)), ("prompt_name", ()),
        ("prompt_phone", ("phone_reprompt",)), ("prompt_email", ("email_reprompt",)))),
    ("booking", "Booking", "calendar-check", (("booking_confirmation", ("slot_unavailable", "booking_error")),)),
    ("noreply", "No reply", "clock", (("followup_1", ()), ("followup_2", ()))),
    ("owner", "Owner steps in", "hand", (("handoff_ack", ()), ("handoff_ack_safety", ()))),
)
# Off the spine: these replies can arrive at any point in a conversation.
ANYTIME = ("keywords", "START, HELP and STOP", "", (("opt_in", ()), ("help", ()), ("opt_out_ack", ()), ("opt_out_suffix", ())))
# The jump row under the page lead: (moment id, short label); "Whole conversation" goes to the rail.
JUMP = (("missed", "Missed call"), ("questions", "Questions"), ("booking", "Booking"), ("noreply", "No reply"),
        ("owner", "Owner steps in"), ("keywords", "START, HELP, STOP"))


# Thread rows: (kind, text or template key, icon, optional question the row belongs to).
def _c(text: str, ask: str = "") -> tuple[str, str, str, str]:
    return ("customer", text, "", ask)


def _t(key: str, ask: str = "") -> tuple[str, str, str, str]:
    return ("textback", key, "", ask)


def _p(kind: str, text: str, icon: str = "") -> tuple[str, str, str, str]:
    return (kind, text, icon, "")  # kind: missed | neutral | booked


def _h(text: str) -> tuple[str, str, str, str]:
    return ("handoff", text, "", "")


MISSED = _p("missed", "Missed call · just now")
BOOKED = _p("booked", "Booked · on your calendar", "check")

# key -> (rows shown before the TextBack bubble in its card, rows after). Sample customer lines.
TRIGGERS = {
    "intro": ((MISSED,), ()),
    "preferred_time_reprompt": ((_c("Sometime next week"),), ()),
    "phone_reprompt": ((_c("Use my work phone"),), ()),
    "email_reprompt": ((_c("alex at example"),), ()),
    "slot_unavailable": ((_c("Wednesday at 10"),), ()),
    "booking_confirmation": ((), (BOOKED,)),
    "followup_1": ((_p("neutral", "No reply", "clock"),), ()),
    "followup_2": ((_p("neutral", "Still no reply", "clock"),), (_p("neutral", "Texts stop here"),)),
    "handoff_ack": ((_c("Can I just talk to the owner about pricing?"),), ()),
    "handoff_ack_safety": ((_c("A big limb just came down on the power line by our house"),), ()),
    "opt_in": ((_c("START"),), ()),
    "help": ((_c("HELP"),), ()),
    "opt_out_ack": ((_c("STOP"),), ()),
}

# The rail's sample conversations, in switcher order. In "retry" Wednesday at 10 is the
# taken slot, so the confirmation's sample time (Thursday at 4) stays true.
SCENARIOS = (
    ("booked", "Books a job", (
        MISSED, _t("intro"), _c("Yes, I need some tree work."), _t("prompt_service"),
        _c("Tree removal. An oak is leaning toward the house."), _t("prompt_location"), _c("12 Elm St"),
        _t("prompt_preferred_time"), _c("Thursday at 4"), _t("prompt_name"), _c("Alex Rivera"),
        _t("prompt_phone", "phone"), _c("YES", "phone"), _t("prompt_email", "email"), _c("alex@example.com", "email"),
        _t("booking_confirmation"), BOOKED)),
    ("retry", "Unclear answers", (
        _p("neutral", "After the job and address"), _t("prompt_preferred_time"), _c("Sometime next week"),
        _t("preferred_time_reprompt"), _c("Wednesday at 10"), _t("prompt_name"), _c("Alex Rivera"),
        _t("prompt_phone", "phone"), _c("Use my work phone", "phone"), _t("phone_reprompt", "phone"), _c("YES", "phone"),
        _t("prompt_email", "email"), _c("alex at example", "email"), _t("email_reprompt", "email"),
        _c("alex@example.com", "email"), _t("slot_unavailable"), _c("Thursday at 4"), _t("booking_confirmation"), BOOKED)),
    ("noreply", "No reply", (
        MISSED, _t("intro"), _p("neutral", "No reply", "clock"), _t("followup_1"),
        _p("neutral", "Still no reply", "clock"), _t("followup_2"), _p("neutral", "Texts stop here"))),
    ("failed", "Booking failed", (
        _p("neutral", "After all the questions"), _t("prompt_name"), _c("Alex Rivera"), _t("booking_error"),
        _p("neutral", "No booking was made"))),
    ("needsyou", "Asks for you", (
        _t("prompt_preferred_time"), _c("Can I just talk to the owner about pricing?"), _t("handoff_ack"),
        _h("You take it from here"), _p("neutral", "You get a lead with this conversation", "bell"))),
    ("safety", "Safety", (
        _t("prompt_location"), _c("A big limb just came down on the power line by our house"), _t("handoff_ack_safety"),
        _h("You take it from here"), _p("neutral", "You get an urgent lead", "bell"))),
    ("keywords", "STOP and HELP", (_c("START"), _t("opt_in"), _c("HELP"), _t("help"), _c("STOP"), _t("opt_out_ack"))),
)

# Plain names for the placeholder chips, most useful first. {event_id} stays valid in a template
# (messages.PLACEHOLDERS) but gets no chip: it means nothing to a customer.
CHIP_NAMES = {
    "service": "Job", "when": "Day and time", "location": "Address", "business_name": "Business name",
    "links_page": "Calendar links page", "calendar_links": "Add-to-calendar links", "google_link": "Google Calendar link",
    "outlook_link": "Outlook link", "ical_link": "iCal link", "invite_line": "Invite sentence",
    "invited_email": "Customer email", "contact_line": "Contact number sentence",
}


def chips_for(key: str) -> tuple[tuple[str, str], ...]:
    """("{token}", plain name) for every placeholder ``key`` may use, in CHIP_NAMES order."""
    return tuple(("{%s}" % name, label) for name, label in CHIP_NAMES.items() if name in PLACEHOLDERS[key])

# The first scenario whose thread holds each key's bubble; the rail switches to it when
# that card has focus. The opt-out line is shown inside the intro bubble.
CARD_SCENARIO = {
    key: next(sid for sid, _, rows in SCENARIOS if any(r[0] == "textback" and r[1] == key for r in rows))
    for key in FIELD_KEYS if key != "opt_out_suffix"
} | {"opt_out_suffix": "booked"}


# View models. Frozen dataclasses, not dicts: Jinja resolves x.items / x.values / x.keys
# on a dict to the dict methods.

@dataclass(frozen=True, slots=True)
class Item:
    """One row of a thread, in a card's preview well or in the rail."""
    kind: str        # customer | textback | missed | neutral | booked | handoff
    text: str        # sample, pill or divider text; for textback the rendered text without the opt-out line
    key: str = ""    # template key, textback only (becomes data-preview)
    icon: str = ""   # sprite id without "i-", pills only
    ask: str = ""    # phone | email: the row exists only when that question is asked
    suffix: str = "" # textback only: the opt-out line added for the owner, drawn as its own span


@dataclass(frozen=True, slots=True)
class Card:
    key: str
    label: str
    when: str
    rule: str
    default: str            # data-default
    saved: str              # wording in force in the file: data-saved
    value: str              # textarea content: submitted or custom text, else the default; never ""
    length: int
    custom: bool            # the textarea differs from the standard wording: Reset shows, not the caption
    saved_custom: bool      # the SAVED wording differs from the standard: the Customized pill
    preview: str            # the whole text the customer gets (body + suffix)
    body: str               # the rendered wording
    suffix: str             # the opt-out line added for the owner, or ""
    count: str              # receipt: "1 text · 43 characters"
    bill: str               # receipt, 2+ texts only: why it is billed as more than one
    segments: int
    optout_required: bool
    optout_added: bool
    speakers: bool          # a customer bubble shares the preview: the role badges show
    help: str               # the help line under the chips
    optional: str           # phone | email | ""
    switch_label: str
    asked: bool             # switch state to render (as submitted, on a rejected save)
    asked_saved: bool       # switch state in the file: data-saved-checked
    branch: bool
    chips: tuple[tuple[str, str], ...]
    before: tuple[Item, ...]
    after: tuple[Item, ...]
    scenario: str           # data-scenario
    sync: str               # rail bubble to ring while this card has focus: data-sync
    error: str              # friendly_reason() when this card is the offender
    dirty: bool = False     # textarea or switch differs from the saved file (a rejected save, a specimen)


@dataclass(frozen=True, slots=True)
class QSet:
    eyebrow: str
    parent: Card
    branches: tuple[Card, ...]


@dataclass(frozen=True, slots=True)
class Moment:
    id: str
    heading: str
    blurb: str
    icon: str
    sets: tuple[QSet, ...]
    has_error: bool = False  # one of its cards is the offender: "Any time" renders open


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    label: str
    thread: tuple[Item, ...]


@dataclass(frozen=True, slots=True)
class Rail:
    business_name: str
    initials: str
    scenarios: tuple[Scenario, ...]

# Example values so the preview reads like a real text.
SAMPLE_SERVICE, SAMPLE_WHEN, SAMPLE_LOCATION, SAMPLE_EMAIL = "tree removal", "Thursday, Oct 22 at 4:00 PM", "12 Elm St", "alex@example.com"

# GSM-7 alphabet: texts made only of these fit 160 characters per segment;
# anything else (em dash, curly quotes, emoji) drops the limit to 70.
GSM_BASIC = "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
GSM_EXTENDED = "^{}\\[~]|€"


def sms_parts(text: str) -> tuple[int, int, bool]:
    """(characters, text segments, fits the plain GSM alphabet) for a rendered text."""
    if all(ch in GSM_BASIC or ch in GSM_EXTENDED for ch in text):
        units = sum(2 if ch in GSM_EXTENDED else 1 for ch in text)
        return len(text), (1 if units <= 160 else math.ceil(units / 153)), True
    return len(text), (1 if len(text) <= 70 else math.ceil(len(text) / 67)), False


def count_label(text: str) -> str:
    """Receipt line, texts first: "1 text · 43 characters"."""
    chars, parts, _ = sms_parts(text)
    return f"{parts} text{'s' if parts != 1 else ''} · {chars} characters"


def bill_label(text: str) -> str:
    """Why a text is billed as more than one ("" for one text). Names the first symbol outside
    the plain alphabet, the one that drops each text to 70 characters (portal.js billLabel)."""
    _, parts, plain = sms_parts(text)
    if parts < 2:
        return ""
    if plain:
        return f"Billed as {parts} texts. Customers still see one message."
    symbol = next(ch for ch in text if ch not in GSM_BASIC and ch not in GSM_EXTENDED)
    return f"Billed as {parts} texts. The \u201c{symbol}\u201d symbol limits each text to 70 characters."


class _Keep(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def fill(template: str, values: dict[str, str]) -> str:
    try:
        return template.format_map(_Keep(values))
    except (ValueError, IndexError, KeyError, AttributeError, TypeError):
        # {a.b} and {x[y]} reach here on a rejected save: show the text as typed, never a 500.
        return template


def preview_values(state) -> dict[str, str]:
    base = str(state.public_base_url).rstrip("/")
    contact = (getattr(state, "business_contact", "") or "").strip() or format_contact_number(getattr(state, "business_number", "") or "")
    links = {name: f"{base}/a/k7q2-ref{suffix}" for name, suffix in
             (("links_page", ""), ("google_link", "/g"), ("outlook_link", "/o"), ("ical_link", "/i"))}
    return {
        "business_name": state.business_name, "service": SAMPLE_SERVICE, "when": SAMPLE_WHEN, "location": SAMPLE_LOCATION,
        "event_id": "", "invited_email": SAMPLE_EMAIL, "invite_line": f"A calendar invite is on its way to {SAMPLE_EMAIL}.",
        "calendar_links": f"Add to calendar: Google {links['google_link']} Outlook {links['outlook_link']} iCal {links['ical_link']}",
        "contact_line": f" Contact: {contact}." if contact else "", **links,
    }


def preview_parts(key: str, templates: dict[str, str], values: dict[str, str]) -> tuple[str, str]:
    """(wording, opt-out line added for the owner or "") for ``key``, placeholders filled and
    whitespace collapsed; the line is added where carriers require it (MessageSet.render)."""
    body = " ".join(fill(templates[key], values).split())
    if key in OPT_OUT_REQUIRED and not re.search(r"\bstop\b", templates[key], re.IGNORECASE):
        return body, " ".join(fill(templates["opt_out_suffix"], values).split())
    return body, ""


def preview_text(key: str, templates: dict[str, str], values: dict[str, str]) -> str:
    """What the customer receives for ``key``: the wording plus any opt-out line."""
    return " ".join(part for part in preview_parts(key, templates, values) if part)


def blame(error: str, templates: dict[str, str]) -> tuple[str | None, str]:
    """Which message a MessageTemplateError is about, and the reason without the key."""
    match = re.match(r"^(\w+) (.+)$", error)
    if match and match.group(1) in DEFAULT_TEMPLATES:
        return match.group(1), match.group(2)
    if error.startswith("handoff acknowledgements"):
        for key in ("handoff_ack", "handoff_ack_safety"):
            if "follow up" not in templates[key].lower():
                return key, "must promise a follow-up"
    if "unbalanced" in error or "placeholders must look like" in error:
        for key in FIELD_KEYS:
            try:
                for _, name, _, _ in Formatter().parse(templates[key]):
                    if name is not None and (name == "" or not name.isidentifier()):
                        return key, error
            except ValueError:
                return key, error
    return None, error


_TRY_THIS = "\u201cThe owner will follow up with you by text.\u201d"


def friendly_reason(error: str, key: str | None) -> str:
    """The validator's reason (blame()) in the owner's words; the validation itself is unchanged.
    Unknown reasons come back as they are, first letter capitalised."""
    phrase = re.search(r"business line \('(.+)'\)", error)
    if phrase:
        return (f"Take out \u201c{phrase.group(1)}\u201d. Customers stay in the text thread, so say you\u2019ll "
                f"follow up by text, like {_TRY_THIS}")
    if "promise a follow-up" in error:
        return f"Add the words \u201cfollow up\u201d, like {_TRY_THIS}"
    if "911" in error:
        return "Tell people to call 911 if anyone is in danger."
    if "no booking was made" in error:
        return "Say \u201cNo booking was made\u201d and leave out the word \u201ccall\u201d."
    if "reply STOP" in error:
        return "Include the word STOP. Phone companies require it."
    if "unbalanced" in error or "placeholders must look like" in error:
        return ("Something in { } isn\u2019t a detail we can fill in. Use the buttons under the box to add one, "
                "or remove the { }.")
    extra = re.search(r"unsupported placeholder\(s\) (.+?); allowed", error)
    if extra and key:
        names = ", ".join(name for _, name in chips_for(key))
        can = f"It can use: {names}." if names else "It doesn\u2019t fill in any details."
        return f"This text can\u2019t fill in {extra.group(1)}. {can}"
    if "longer than" in error:
        return f"Shorten it to {MAX_TEMPLATE_CHARS} characters or fewer."
    return error[:1].upper() + error[1:]


def change_summary(old: dict[str, str], new: dict[str, str], old_asked: set[str], new_asked: set[str]) -> str:
    """The rest of the save toast's line after "Saved.": which messages a save changed, by their card titles."""
    changed = [MESSAGES[k][0] for k in FIELD_KEYS if old[k] != new[k] and new[k] != DEFAULT_TEMPLATES[k]]
    changed += [f"{MESSAGES[k][0]} (switched {'on' if field in new_asked else 'off'})"
                for k, (field, _) in OPTIONAL_QUESTIONS.items() if (field in old_asked) != (field in new_asked)]
    back = [MESSAGES[k][0] for k in FIELD_KEYS if old[k] != new[k] and new[k] == DEFAULT_TEMPLATES[k]]
    lines = ([f"Changed: {', '.join(changed)}."] if changed else []) + \
            ([f"Back to standard wording: {', '.join(back)}."] if back else [])
    return " ".join(lines) or "No wording changed."


# --- page frame ----------------------------------------------------------------

class FormExpired(Exception):
    """A POST whose CSRF token does not match the session: answered with the HTML
    "This page expired" page (status 400) instead of a JSON error."""

    def __init__(self, reload_url: str):
        super().__init__(reload_url)
        self.reload_url = reload_url


def _shell(state, session, *, title: str, nav: str | None, notice: str = "", page_error: str = "",
           tb_data: dict | None = None, notice_detail: str = "") -> dict:
    """Context every signed-in page needs: topbar, account menu, nav, notices."""
    return {
        "title": title,
        "business_name": state.business_name,
        "nav_active": nav,
        "csrf": session["csrf"],
        "signed_in_with": format_contact_number(session["phone"]),
        "notice": notice,
        "notice_detail": notice_detail,
        "page_error": page_error,
        "tb_data": tb_data,
    }


def _now(state):
    return state.now_provider() if state.now_provider else datetime.now(timezone.utc)


def _mac(state, value: str) -> str:
    return hmac.new(state.webhook_secret.encode(), ("client-portal:" + value).encode(), hashlib.sha256).hexdigest()


def normalize_mobile(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        digits = "1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if 8 <= len(digits) <= 15 and raw.strip().startswith("+"):
        return "+" + digits
    return None


def _secure(state) -> bool:
    return str(state.public_base_url).lower().startswith("https://")


def _session(state, request: Request):
    token = request.cookies.get(SESSION_COOKIE, "")
    if not token:
        return None
    now = _now(state)
    with state.store.lock:
        # pending=0: a "code requested" row must never pass as a signed-in session.
        row = state.store.conn.execute(
            "SELECT * FROM client_sessions WHERE token_hash=? AND pending=0 AND expires_at>?", (_mac(state, token), now.isoformat())
        ).fetchone()
    return dict(row) if row else None


# --- sign in -------------------------------------------------------------------

def _login_form(request: Request, state, *, error: str = "") -> HTMLResponse:
    return render(request, "client/login.html.j2", title="Sign in", business_name=state.business_name, error=error)


def _verify_form(request: Request, state, *, error: str = "") -> HTMLResponse:
    # Inputs are the business name and the error only: no number, csrf, clock or
    # per-request value, so the page is identical for an unknown number and a wrong code.
    return render(request, "client/verify.html.j2", title="Enter code", business_name=state.business_name, error=error)


# --- the Messages page ----------------------------------------------------------

def initials(name: str) -> str:
    """Avatar letters for the rail: first letters of the first two words, "TB" if none."""
    words = re.findall(r"[A-Za-z0-9]+", name or "")
    return "".join(word[0] for word in words[:2]).upper() or "TB"


def _item(row: tuple[str, str, str, str], templates: dict[str, str], sample: dict[str, str]) -> Item:
    kind, text, icon, ask = row
    if kind == "textback":
        body, suffix = preview_parts(text, templates, sample)
        return Item("textback", body, key=text, ask=ask, suffix=suffix)
    return Item(kind, text, icon=icon, ask=ask)


def help_line(key: str, sample: dict[str, str]) -> str:
    if "business_name" not in PLACEHOLDERS[key]:
        return f"Sent as one paragraph. Up to {MAX_TEMPLATE_CHARS} characters."
    return (f"Sent as one paragraph. Words in {{ }} are filled in for you, like {{business_name}} \u2192 "
            f"{sample['business_name']}. Up to {MAX_TEMPLATE_CHARS} characters.")


def card_view(key: str, *, values: dict[str, str], templates: dict[str, str], current, sample: dict[str, str],
              asked: set[str], asked_saved: set[str], branch: bool, error: str, dirty: bool = False,
              saved: str | None = None) -> Card:
    """One message card. ``saved`` overrides the file's wording (styleguide specimens only)."""
    label, when, rule = MESSAGES[key]
    optional, switch_label = OPTIONAL_QUESTIONS.get(key, ("", ""))
    value = values.get(key) or DEFAULT_TEMPLATES[key]
    saved = current.templates[key] if saved is None else saved
    body, suffix = preview_parts(key, templates, sample)
    preview = " ".join(part for part in (body, suffix) if part)
    before, after = TRIGGERS.get(key, ((), ()))
    before = tuple(_item(row, templates, sample) for row in before)
    after = tuple(_item(row, templates, sample) for row in after)
    dirty = dirty or _norm(value) != _norm(saved) or (optional in asked) != (optional in asked_saved)
    return Card(
        key=key, label=label, when=when, rule=rule, default=DEFAULT_TEMPLATES[key], saved=saved,
        value=value, length=len(value), custom=bool(values.get(key)),
        saved_custom=_norm(saved) != _norm(DEFAULT_TEMPLATES[key]), preview=preview, body=body, suffix=suffix,
        count=count_label(preview), bill=bill_label(preview), segments=sms_parts(preview)[1],
        optout_required=key in OPT_OUT_REQUIRED, optout_added=bool(suffix),
        speakers=any(it.kind == "customer" for it in before + after), help=help_line(key, sample),
        optional=optional, switch_label=switch_label, asked=optional in asked, asked_saved=optional in asked_saved,
        branch=branch, chips=chips_for(key), before=before, after=after,
        scenario=CARD_SCENARIO[key], sync="intro" if key == "opt_out_suffix" else key, error=error, dirty=dirty,
    )


def rail_view(state, templates: dict[str, str], sample: dict[str, str]) -> Rail:
    return Rail(state.business_name, initials(state.business_name), tuple(
        Scenario(sid, label, tuple(_item(row, templates, sample) for row in rows)) for sid, label, rows in SCENARIOS))


def messages_view(state, *, values: dict[str, str] | None = None, asked: set[str] | None = None, error: str = "") -> dict:
    """Context for the Messages page. ``values`` are the owner's custom texts ("" = standard);
    after a rejected save they are the texts as typed, so nothing is lost."""
    current = state.messages.current()
    editable = state.messages.path is not None
    if values is None:
        values = {key: (current.templates[key] if current.templates[key] != DEFAULT_TEMPLATES[key] else "") for key in FIELD_KEYS}
    asked_saved = set(current.fields) & {"phone", "email"}
    if asked is None:
        asked = asked_saved
    templates = {key: values.get(key) or DEFAULT_TEMPLATES[key] for key in FIELD_KEYS}
    sample = preview_values(state)
    bad_key, reason = blame(error, templates) if error else (None, "")
    friendly = friendly_reason(reason, bad_key) if error else ""

    def card(key: str, branch: bool) -> Card:
        return card_view(key, values=values, templates=templates, current=current, sample=sample, asked=asked,
                         asked_saved=asked_saved, branch=branch, error=friendly if key == bad_key else "")

    def moment(mid: str, heading: str, icon: str, sets) -> Moment:
        qsets, eyebrow_used = [], False
        for parent, branches in sets:
            eyebrow = ""
            if parent in OPTIONAL_QUESTIONS and not eyebrow_used:
                eyebrow, eyebrow_used = "Optional questions", True
            qsets.append(QSet(eyebrow, card(parent, False), tuple(card(b, True) for b in branches)))
        keys = {key for parent, branches in sets for key in (parent, *branches)}
        return Moment(mid, heading, _BLURB[mid], icon, tuple(qsets), has_error=bad_key in keys)

    error_summary = None
    if error:
        error_summary = {"key": bad_key or "", "label": MESSAGES[bad_key][0] if bad_key else "", "reason": friendly}
    return {
        "editable": editable,
        "max_chars": MAX_TEMPLATE_CHARS,
        "moments": tuple(moment(*row) for row in LAYOUT),
        "anytime": moment(*ANYTIME),
        "jump": tuple((f"#g_{mid}", label) for mid, label in JUMP) + (("#conversation", "Whole conversation"),),
        "error_summary": error_summary,
        "asked": tuple(sorted(asked)),
        "rail": rail_view(state, templates, sample),
        "tb_data": {"sample": sample, "gsm": GSM_BASIC, "ext": GSM_EXTENDED} if editable else None,
    }


def _messages_form(request: Request, state, session, *, error: str = "", notice: str = "", page_error: str = "",
                   values: dict[str, str] | None = None, asked: set[str] | None = None,
                   notice_detail: str = "") -> HTMLResponse:
    view = messages_view(state, values=values, asked=asked, error=error)
    tb_data = view.pop("tb_data")
    savebar_initial = "error" if view["error_summary"] else ("saved" if notice else "clean")
    title = "Not saved · Messages" if view["error_summary"] else "Messages"
    return render(
        request, "client/messages.html.j2",
        **_shell(state, session, title=title, nav="messages", notice=notice, page_error=page_error, tb_data=tb_data,
                 notice_detail=notice_detail),
        savebar_initial=savebar_initial, **view,
    )


def _norm(text: str) -> str:
    return " ".join(text.split())


# --- codes ---------------------------------------------------------------------

def send_code(state, mobile: str, now: datetime, *, purpose: str = "sign-in") -> None:
    """Text a fresh six-digit code to ``mobile`` (rate limited per number)."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    key = f"login:{mobile}:{secrets.token_hex(8)}"
    with state.store.transaction():
        # The outbox is the durable record of codes actually texted.
        recent = state.store.conn.execute(
            "SELECT count(*) FROM sms_outbox WHERE kind='login_code' AND phone=? AND created_at>?",
            (mobile, (now - CODE_WINDOW).isoformat()),
        ).fetchone()[0]
        if recent >= CODES_PER_WINDOW:
            return
        state.store.conn.execute("DELETE FROM client_login_codes WHERE phone=?", (mobile,))
        state.store.conn.execute(
            "INSERT INTO client_login_codes(phone,code_hash,expires_at,attempts,created_at) VALUES(?,?,?,0,?)",
            (mobile, _mac(state, code), (now + CODE_TTL).isoformat(), now.isoformat()),
        )
        enqueue_sms(
            store=state.store, key=key, to=mobile, from_number=state.business_number, now=now,
            kind="login_code", body=f"{state.business_name} settings {purpose} code: {code}. It expires in 10 minutes.",
        )
    run_due_sms(store=state.store, telecom=state.telecom, now=now, policy=state.followup_policy,
                keys=[key], callback_base_url=state.public_base_url, immediate=True)
    with state.store.transaction():
        # Once handed to the carrier the code has no business sitting in the outbox.
        state.store.conn.execute(
            "UPDATE sms_outbox SET body='[sign-in code]' WHERE key=? AND status IN ('sent','unknown','dead_letter')", (key,)
        )


def check_code(state, phone: str, code: str, now: datetime) -> bool:
    """True when ``code`` is the live code for ``phone``; the code is consumed on success.
    Every failure (no code, expired, too many guesses, wrong digits) looks the same."""
    code = re.sub(r"\D", "", code or "")
    with state.store.transaction():
        row = state.store.conn.execute(
            "SELECT * FROM client_login_codes WHERE phone=? AND expires_at>?", (phone, now.isoformat())
        ).fetchone()
        if row is None or row["attempts"] >= CODE_ATTEMPTS:
            return False
        state.store.conn.execute("UPDATE client_login_codes SET attempts=attempts+1 WHERE phone=?", (phone,))
        if len(code) != 6 or not hmac.compare_digest(row["code_hash"], _mac(state, code)):
            return False
        state.store.conn.execute("DELETE FROM client_login_codes WHERE phone=?", (phone,))
        return True


# --- routes --------------------------------------------------------------------

def install_routes(app):
    state = app.state
    mount_static(app)

    @app.exception_handler(FormExpired)
    async def _form_expired(request: Request, exc: FormExpired):
        session = _session(state, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        nav = exc.reload_url.rsplit("/", 1)[-1]  # messages | business | calendar
        return render(request, "client/expired.html.j2", status_code=400,
                      **_shell(state, session, title="This page expired", nav=nav), reload_url=exc.reload_url)

    @app.get("/client", include_in_schema=False)
    @app.get("/client/", include_in_schema=False)
    def client_root(request: Request):
        return RedirectResponse("/client/messages" if _session(state, request) else "/client/login", status_code=303)

    @app.get("/client/login", include_in_schema=False)
    def login_page(request: Request):
        if _session(state, request):
            return RedirectResponse("/client/messages", status_code=303)
        return _login_form(request, state)

    @app.post("/client/login", include_in_schema=False)
    async def login(request: Request):
        form = await request.form()
        mobile = normalize_mobile(str(form.get("mobile", "")))
        now = _now(state)
        if mobile is None:
            return _login_form(request, state, error="Enter the mobile number as digits, like 704 555 0123.")
        owner = getattr(state, "owner_mobile", "")
        if owner and hmac.compare_digest(mobile, owner):
            send_code(state, mobile, now)
        # Same answer either way so the page never confirms which number is on file.
        response = RedirectResponse("/client/verify", status_code=303)
        pending = secrets.token_urlsafe(24)
        with state.store.transaction():
            state.store.conn.execute(
                "INSERT INTO client_sessions(token_hash,csrf,phone,expires_at,created_at,pending) VALUES(?,?,?,?,?,1)",
                (_mac(state, pending), secrets.token_urlsafe(24), mobile, (now + CODE_TTL).isoformat(), now.isoformat()),
            )
        response.set_cookie(PENDING_COOKIE, pending, secure=_secure(state), httponly=True, samesite="lax",
                            max_age=int(CODE_TTL.total_seconds()), path="/client")
        return response

    def _pending(request: Request):
        token = request.cookies.get(PENDING_COOKIE, "")
        if not token:
            return None
        now = _now(state)
        with state.store.lock:
            row = state.store.conn.execute(
                "SELECT * FROM client_sessions WHERE token_hash=? AND pending=1 AND expires_at>?",
                (_mac(state, token), now.isoformat()),
            ).fetchone()
        return dict(row) if row else None

    @app.get("/client/verify", include_in_schema=False)
    def verify_page(request: Request):
        if _session(state, request):
            return RedirectResponse("/client/messages", status_code=303)
        if not _pending(request):
            return RedirectResponse("/client/login", status_code=303)
        return _verify_form(request, state)

    @app.post("/client/verify", include_in_schema=False)
    async def verify(request: Request):
        pending = _pending(request)
        if not pending:
            return RedirectResponse("/client/login", status_code=303)
        form = await request.form()
        now = _now(state)
        # One message for a wrong code, an expired code, too many guesses and a
        # number that is not on file, so the page never confirms which number is.
        if not check_code(state, pending["phone"], str(form.get("code", "")), now):
            return _verify_form(request, state, error=CODE_FAILURE)
        with state.store.transaction():
            state.store.conn.execute("DELETE FROM client_sessions WHERE token_hash=?", (pending["token_hash"],))
            token = secrets.token_urlsafe(32)
            state.store.conn.execute(
                "INSERT INTO client_sessions(token_hash,csrf,phone,expires_at,created_at,pending) VALUES(?,?,?,?,?,0)",
                (_mac(state, token), secrets.token_urlsafe(24), pending["phone"], (now + SESSION_TTL).isoformat(), now.isoformat()),
            )
        response = RedirectResponse("/client/messages", status_code=303)
        response.set_cookie(SESSION_COOKIE, token, secure=_secure(state), httponly=True, samesite="lax",
                            max_age=int(SESSION_TTL.total_seconds()), path="/client")
        response.delete_cookie(PENDING_COOKIE, path="/client")
        return response

    @app.get("/client/messages", include_in_schema=False)
    def messages_page(request: Request):
        session = _session(state, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        return _messages_form(request, state, session)

    @app.post("/client/messages", include_in_schema=False)
    async def save_messages(request: Request):
        session = _session(state, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        form = await request.form()
        if not hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
            raise FormExpired("/client/messages")
        if state.messages.path is None:
            return _messages_form(request, state, session, page_error="Message editing is not set up for this account yet.")
        submitted = {key: str(form.get(key, "")).strip() for key in FIELD_KEYS}
        for key, value in submitted.items():
            # The editors are pre-filled with the real wording: an untouched (or re-typed)
            # standard text is stored as standard, never pinned into the owner's file.
            if _norm(value) == _norm(DEFAULT_TEMPLATES[key]):
                submitted[key] = ""
        reset = str(form.get("reset", ""))
        if reset in submitted:
            submitted[reset] = ""  # "Use standard wording" without JavaScript
        overrides = {key: value for key, value in submitted.items() if value}
        asked = {field for field in ("phone", "email") if form.get(f"ask_{field}")}
        if asked:
            overrides["fields"] = ", ".join(("service", "location", "preferred_time", "name", *[f for f in ("phone", "email") if f in asked]))
        before = state.messages.current()
        try:
            write_message_file(state.messages.path, overrides)
        except MessageTemplateError as exc:
            return _messages_form(request, state, session, error=str(exc), values=submitted, asked=asked)
        after = state.messages.current()  # pick up the new file right away
        detail = change_summary(before.templates, after.templates, set(before.fields), set(after.fields))
        return _messages_form(request, state, session, notice="Saved.", notice_detail=detail)

    @app.get("/client/styleguide", include_in_schema=False)
    def styleguide_page(request: Request):
        # Owner-only review page: every token and component, in every state. Not linked from the nav.
        session = _session(state, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        from text_back.portal_styleguide import styleguide_context  # imports this module
        return render(request, "client/styleguide.html.j2", headers={"X-Robots-Tag": "noindex"},
                      **styleguide_context(state, session))

    @app.post("/client/logout", include_in_schema=False)
    async def logout(request: Request):
        session = _session(state, request)
        form = await request.form()
        if session and hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
            with state.store.transaction():
                state.store.conn.execute("DELETE FROM client_sessions WHERE token_hash=?", (session["token_hash"],))
        response = RedirectResponse("/client/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE, path="/client")
        return response
