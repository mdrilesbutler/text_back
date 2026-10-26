"""The Messages page (/client/messages): every customer text, in the order a customer meets it.

Ported from candidate A's client_portal (cards, receipts, blame/friendly reasons, change
summary) with candidate C's rules:

- Every owner-facing word is a row of docs/notes/portal-c/copy-deck.md, section 4.
- No braces on screen. A template's ``{business_name}`` is shown and edited as the insert
  label ``[Business name]``; ``to_template`` turns the labels back into placeholders before
  ``messages.validate_templates`` (the only validator) sees the text. Anything else typed
  in braces is rejected with the deck's plain reason.
- The example conversation (the rail) is produced by ``portal_sample.render_scenario`` from
  the SAVED templates, so it can never show a step-back or a time reading the product would
  not make. Its links use ``state.public_base_url``.
- The steps-back destination line says where the customer's details really go, from config.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from string import Formatter
from zoneinfo import ZoneInfo

from text_back.calendar_links import CalendarLinks
from text_back.messages import DEFAULT_TEMPLATES, MAX_TEMPLATE_CHARS, OPT_OUT_REQUIRED, PLACEHOLDERS
from text_back.policy import format_contact_number
from text_back.portal_sample import LINK_SECRET, SCENARIOS as SAMPLE_SCENARIOS, render_scenario

# --- words (copy deck, section 4; verbatim; quotes curly per round 2) -----------------------

TITLE = "Messages"
INTRO = "The texts customers get after a missed call, in order. Changes start with the next missed call."
META = "Green bubbles are what customers see. The job, address, time and names are made-up examples."
NOT_ENABLED = "Message editing isn't turned on for your account yet. FluxWorks sets this up for you."
SUPPORT_BUTTON = "Text FluxWorks support"
NETWORK_NOTICE = "Until texting is approved, the network adds a short notice to each text, and the counts here include it."
JUMP_LABEL = "On this page"
JUMP_LEAD, JUMP_NOJS = "Jump to:", "Jump to a step"
OPTIONAL_EYEBROW = "Optional questions"

RULE_STOP = "Phone companies require “Reply STOP to opt out.” If your wording leaves out STOP, we add that line for you."
RULE_STOP_WORD = "The word STOP stays. Phone companies check for it."
RULE_BOOKING_ERROR = "Must say “No booking was made” and can't use the word “call”. The customer stays in the text thread."
RULE_STEPS_BACK = ("This text must tell the customer someone will follow up. Don't ask them to call, and don't say "
                   "they'll be put through to someone.")
RULE_SAFETY = "Must tell people to call 911 if anyone is in danger, and must say someone will follow up."
RULE_PARAGRAPH = f"Sent as one paragraph. Up to {MAX_TEMPLATE_CHARS} characters."
NEXT_HEADING = "What happens next"
NEXT_STEPS = ("TextBack stops texting this customer.", "Their name, number and message go to FluxWorks.",
              "FluxWorks passes them to you. You follow up; the text promised the customer someone would.")
DESTINATION_CHAT = "FluxWorks"  # never "the FluxWorks operator" (m30)
DESTINATION_LOG = "a log FluxWorks can read. Nobody is alerted. Ask FluxWorks to set up where these should go."
DESTINATION_LOG_SHORT = "a log FluxWorks can read"
DESTINATION_LINE = "These go to {label}."
DESTINATION_OFF = "These go nowhere yet. FluxWorks turns this on when your account is set up."

BADGE_CUSTOM, BADGE_STANDARD, BADGE_UNSAVED, BADGE_NOT_SAVED = "Customized", "Standard wording", "Unsaved", "Not saved"
BADGE_ASKED, BADGE_NOT_ASKED = "Asked", "Not asked"
OPTOUT_ADDED = "STOP line added for you"
CHIPS_LABEL = "Insert a detail"
CHIPS_NONE = "This text fills in no details."
SWITCH_OFF = "Off. Customers skip this question."
EDITOR_OPEN = "Edit wording"
RESET, RESET_NOJS = "Reset", "Reset and save"
TRIGGER_LABEL = "When the customer sends something like"
WAS = "Was:"
# Not in the deck yet (layer 2, round-3 panel): under a bubble whose links show as labels.
LINK_NOTE = "Each label is a link. The text count includes the full links."
SPEAKER_CUSTOMER = "Customer"

RAIL_TITLE = "Example conversation"
RAIL_SHOW = "Show"
RAIL_SUB = "Text message"
RAIL_FOOT = "Nothing is sent · names made up"  # under the title "Example conversation": the word appears once
RAIL_NOTICE_HINT = "Each text in this example also starts with the network notice."
RAIL_BACK = "Back to editing"
PILL_MISSED = "Missed call · just now"
PILL_NO_REPLY, PILL_STILL_NO_REPLY = "No reply", "Still no reply"
PILL_STOPS = "Texts stop here"
PILL_NO_BOOKING = "No booking was made"
PILL_BOOKED, PILL_BOOKED_TEST = "Booked · on your calendar", "Booked · on the test calendar"
DIVIDER_STEPS_BACK = "TextBack steps back here"
PILL_DETAILS_SENT = "Customer's details sent to {label}"

SAVEBAR_NOJS = "Saves every text at once"
SAVEBAR_CLEAN = "No unsaved changes"
CHANGED_ONE, CHANGED_MANY = "1 text changed", "{n} texts changed"
SETTING_ONE, SETTING_MANY, CHANGES_MIXED = "1 setting changed", "{n} settings changed", "{n} changes"
NOT_SAVED_COUNT = "Not saved · {count}"
SAVE, SAVING, DISCARD = "Save", "Saving…", "Discard"
DISCARDED = "Changes discarded."

ERROR_SUMMARY = "Not saved. “{title}” needs a change: {reason}"
ERROR_LINK = "Go to that text"
ERROR_KEPT = "Your other edits are still here. Nothing was saved yet."
ERROR_UNPLACED = "Not saved. {reason}"

REASON_NUMBER = ("Take out “{phrase}”. Customers stay in the text thread, so say you'll follow up by text, like "
                 "“We'll follow up with you by text.”")
REASON_FOLLOW_UP = "Add the words “follow up”, like “We'll follow up with you by text.”"
REASON_911 = "Tell people to call 911 if anyone is in danger."
REASON_NO_BOOKING = "Say “No booking was made” and leave out the word “call”."
REASON_STOP = "Include the word STOP. Phone companies require it."
REASON_BAD_INSERT = ("Something typed by hand isn't a detail we can fill in. Use the Insert buttons under the box, "
                     "or remove it.")
REASON_WRONG_INSERT = "This text can't fill in {names}. It can use: {labels}."
REASON_WRONG_INSERT_NONE = "This text can't fill in {names}. It fills in no details."
REASON_TOO_LONG = f"Shorten it to {MAX_TEMPLATE_CHARS} characters or fewer."

# key -> (card title, when-line). followup_1/2 when-lines carry the live reminder delays (when_line).
MESSAGES: dict[str, tuple[str, str]] = {
    "intro": ("First text after a missed call", ""),  # the step blurb already says when it is sent
    "prompt_service": ("Question 1: the job", "Sent only if the customer's first reply is blank, like a photo with no words. Usually that first reply already says what the job is."),
    "prompt_location": ("Question 2: the address", "Asked once the job is known."),
    "prompt_preferred_time": ("Question 3: day and time",
                              "Asked once the address is known. Examples in everyday words help: Wednesday at 2, tomorrow at 10am."),
    "preferred_time_reprompt": ("If the time couldn't be understood",
                                "Sent instead of moving on when the reply isn't a day and time."),
    "prompt_name": ("Question 4: the name", "Asked once the time is known."),
    "prompt_phone": ("Best phone number", "Asked only when switched on. YES keeps the number they're texting from."),
    "phone_reprompt": ("If the phone number couldn't be read", "Sent when the reply isn't a phone number or YES."),
    "prompt_email": ("Email address", "Asked only when switched on. SKIP is allowed."),
    "email_reprompt": ("If the email couldn't be read", "Sent when the reply isn't an email address or SKIP."),
    "slot_unavailable": ("When the time is already taken", "Sent when your calendar shows that time busy."),
    "booking_confirmation": ("Booking confirmation", "Sent only after the appointment is on your calendar."),
    "booking_error": ("When the calendar failed",
                      "Sent if the appointment couldn't be added to your calendar. It tells the customer no booking was made."),
    "followup_1": ("First reminder", "Sent {delay} after the first text if there's no reply."),
    "followup_2": ("Last reminder", "Sent {delay} after the first reminder. After this TextBack stops texting."),
    # The step is "When TextBack steps back"; its card has a title of its own (banned words rule out "hand-off").
    "handoff_ack": ("Steps-back text", "Sent when the customer asks for the owner or TextBack can't help."),
    "handoff_ack_safety": ("When someone may be in danger", "Sent when a text mentions danger."),
    "opt_in": ("Reply to START", "Sent when a customer texts START."),
    "help": ("Reply to HELP", "Sent when a customer texts HELP. The number it shows is set on the Phone page."),
    "opt_out_ack": ("Reply to STOP", "Sent once when a customer texts STOP. Nothing follows it."),
    "opt_out_suffix": ("Opt-out line",
                       "Added to the first text, both reminders and the START and HELP replies when they leave out the word STOP."),
}
RULES = {key: RULE_STOP for key in OPT_OUT_REQUIRED} | {
    "opt_out_suffix": RULE_STOP_WORD, "booking_error": RULE_BOOKING_ERROR,
    "handoff_ack": RULE_STEPS_BACK, "handoff_ack_safety": RULE_SAFETY,
}
DESTINATION_KEYS = ("handoff_ack", "handoff_ack_safety")
# The customer reply that triggers each fallback text (deck trigger_examples); made-up sample lines.
TRIGGERS = {
    "preferred_time_reprompt": "Sometime next week", "phone_reprompt": "my cell", "email_reprompt": "dana at gmail",
    "slot_unavailable": "Wednesday at 10", "booking_error": "Thursday at 10",
    "handoff_ack": "Can I just talk to the owner?",
    "handoff_ack_safety": "A big limb just came down on the power line by our house",
    "opt_in": "START", "help": "HELP", "opt_out_ack": "STOP",
}

# The conversation spine (mockup d1): (step id, heading, blurb, glyph, keys, optional keys). A branch card
# (re-ask, time taken, calendar failed) hangs under the card before it; a switched-off optional question
# hides its branch (still posted).
STEPS: tuple[tuple[str, str, str, str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("missed_call", "Missed call", "A call goes unanswered. Within a minute the caller gets this text.", "phone",
     ("intro",), ()),
    ("questions", "Questions", "Asked one at a time, in this order. TextBack moves on only once it has an answer.",
     "circle-help", ("prompt_service", "prompt_location", "prompt_preferred_time", "preferred_time_reprompt", "prompt_name"),
     ("prompt_phone", "phone_reprompt", "prompt_email", "email_reprompt")),
    ("booking", "Booking", "Once it has the answers, TextBack checks your calendar and books a free time.",
     "calendar", ("slot_unavailable", "booking_confirmation", "booking_error"), ()),
    ("no_reply", "No reply", "If the customer goes quiet, TextBack sends two reminders. Then the texting stops.",
     "bell", ("followup_1", "followup_2"), ()),
    ("steps_back", "When TextBack steps back",
     "When a text needs a person, TextBack stops scheduling and passes the customer's details on.",
     "user-round", ("handoff_ack", "handoff_ack_safety"), ()),
)
KEYWORDS = ("any_time", "START, HELP and STOP", "Required by phone companies. Most businesses never change these.",
            "shield-check", ("opt_in", "help", "opt_out_ack", "opt_out_suffix"), ())
JUMP = (("missed_call", "Missed call"), ("questions", "Questions"), ("booking", "Booking"), ("no_reply", "No reply"),
        ("steps_back", "Steps back"))
BRANCH_OF = {"preferred_time_reprompt": "prompt_preferred_time", "phone_reprompt": "prompt_phone",
             "email_reprompt": "prompt_email"}
BRANCH_KEYS = frozenset(BRANCH_OF) | {"slot_unavailable", "booking_error", "handoff_ack_safety"}
# Round 4: each step's branch texts sit in one disclosure under its main path (deck branches).
BRANCH_SUMMARY = {"questions": "If the answer is unclear", "booking": "If the time is taken or the calendar fails",
                  "steps_back": "If a text mentions danger"}
BRANCH_SEP = " · "

FIELD_KEYS: tuple[str, ...] = tuple(key for *_, keys, optional in (*STEPS, KEYWORDS) for key in (*keys, *optional))
OPTIONAL_QUESTIONS = {"prompt_phone": ("phone", "Also ask for the best phone number"),
                      "prompt_email": ("email", "Also ask for an email address")}

# Rail scenarios in switcher order: (portal_sample scenario, deck label).
RAIL_SCENARIOS = (("booked", "Books a job"), ("unclear", "Unclear answers"), ("noreply", "No reply"),
                  ("failed", "Booking failed"), ("steps_back", "Asks for the owner"), ("safety", "Mentions danger"),
                  ("keywords", "START, HELP and STOP"))

# --- inserts: plain labels on screen, placeholders in the file --------------------------------

# Chip order: Business name first, then the confirmation's details in the deck's order.
INSERT_LABELS: dict[str, str] = {
    "business_name": "Business name", "service": "Job", "when": "Day and time", "location": "Address",
    "calendar_links": "Calendar links", "invite_line": "Invite sentence", "invited_email": "Customer's email",
    "google_link": "Google Calendar link", "outlook_link": "Outlook link", "ical_link": "iCal link",
    "links_page": "Calendar links page", "contact_line": "Your HELP number",
}
# Placeholders that stay valid in a saved file but get no chip (the booking's internal id).
HIDDEN_LABELS = {"event_id": "Booking reference"}
_ALL_LABELS = {**INSERT_LABELS, **HIDDEN_LABELS}
_LABEL_NAMES = {label: name for name, label in _ALL_LABELS.items()}
_LABEL_KEYS = {" ".join(label.lower().split()): name for label, name in _LABEL_NAMES.items()}
_LABEL_RE = re.compile(r"\[\s*(" + "|".join(r"\s+".join(map(re.escape, label.split())) for label in _LABEL_NAMES)
                       + r")\s*\]", re.IGNORECASE)
_TOKEN_RE = re.compile(r"\{(\w+)\}")


def to_display(template: str) -> str:
    """'{business_name} here' -> '[Business name] here' for every known placeholder."""
    return _TOKEN_RE.sub(lambda m: f"[{_ALL_LABELS[m.group(1)]}]" if m.group(1) in _ALL_LABELS else m.group(0), template)


def to_template(text: str) -> str:
    """'[Business name] here' -> '{business_name} here'. Braces typed by hand stay, so the
    validator rejects them and the owner gets REASON_BAD_INSERT."""
    return _LABEL_RE.sub(lambda m: "{" + _LABEL_KEYS[" ".join(m.group(1).lower().split())] + "}", text)


def chips_for(key: str) -> tuple[tuple[str, str], ...]:
    """(insert text, label) for every detail ``key`` may use, in INSERT_LABELS order."""
    return tuple((f"[{label}]", label) for name, label in INSERT_LABELS.items() if name in PLACEHOLDERS[key])


# --- cost line ---------------------------------------------------------------------------

GSM_BASIC = "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
GSM_EXTENDED = "^{}\\[~]|€"
_PLAIN = {"—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "…": "..."}


def sms_parts(text: str) -> tuple[int, int, bool]:
    """(characters, texts billed, fits the plain alphabet) for a rendered text."""
    if all(ch in GSM_BASIC or ch in GSM_EXTENDED for ch in text):
        units = sum(2 if ch in GSM_EXTENDED else 1 for ch in text)
        return len(text), (1 if units <= 160 else math.ceil(units / 153)), True
    # UCS-2: the network counts UTF-16 units, so an emoji takes two (portal.js uses text.length).
    units = len(text.encode("utf-16-le")) // 2
    return units, (1 if units <= 70 else math.ceil(units / 67)), False


# The network notice a text carries until texting approval clears: 24 characters, two of them the brackets
# the plain alphabet bills twice. It models the real prefix's length without its words (never shown).
NOTICE_MODEL = "[" + "a" * 21 + "] "


def count_label(text: str, notice: bool = False) -> str:
    """Deck cost_line. With ``notice`` the count covers the text as it arrives, network notice included."""
    chars, parts, _ = sms_parts(NOTICE_MODEL + text if notice else text)
    return f"{parts} text{'s' if parts != 1 else ''} · {chars} characters" + (" with the notice" if notice else "")


def _first_symbol(text: str) -> str:
    return next((ch for ch in text if ch not in GSM_BASIC and ch not in GSM_EXTENDED), "")


def bill_label(text: str) -> str:
    """'' for one text; otherwise the deck's cost_bill_symbol / cost_bill_long line."""
    _, parts, plain = sms_parts(text)
    if parts < 2:
        return ""
    if plain:
        return f"Billed as {parts} texts. Customers still see one message."
    symbol = _first_symbol(text)
    instead = f"Use “{_PLAIN[symbol]}” instead." if symbol in _PLAIN else "Use a plain letter instead."
    return f"Billed as {parts} texts. The “{symbol}” symbol makes each text hold only 70 characters. {instead}"


def _own_words(template: str) -> str:
    """A template's own wording: what the owner typed, without the details filled in."""
    return re.sub(r"\{[^{}]*\}", "", template)


BILL_LINKS = "Billed as {n} texts. The calendar links make this text long. Customers still see one message."


def bill_info(key: str, templates: dict[str, str], values: dict[str, str], notice: bool) -> tuple[str, str]:
    """(billing line, fix label) for one card. The fix only ever changes the card's own wording: a symbol that
    comes from the business name or the opt-out line is named where it is, with no button."""
    body, suffix = preview_parts(key, templates, values)
    preview = " ".join(part for part in (body, suffix) if part)
    billed = NOTICE_MODEL + preview if notice and key != "opt_out_suffix" else preview
    _, parts, plain = sms_parts(billed)
    if parts < 2:
        return "", ""
    if key == "booking_confirmation":
        # Its length comes from the calendar links; the honest note, and never a fix button (m32).
        own = _first_symbol(_own_words(templates[key]))
        if own:
            return f"Billed as {parts} texts. The “{own}” symbol makes each text hold only 70 characters.", ""
        return BILL_LINKS.format(n=parts), ""
    if plain:
        return f"Billed as {parts} texts. Customers still see one message.", ""
    own = _first_symbol(_own_words(templates[key]))
    if own:
        instead = f"Use “{_PLAIN[own]}” instead." if own in _PLAIN else "Use a plain letter instead."
        line = f"Billed as {parts} texts. The “{own}” symbol makes each text hold only 70 characters. {instead}"
        return line, (f"Replace {own} with {_PLAIN[own]}" if own in _PLAIN else "")
    for where, text in (("Your business name", values.get("business_name", "")), ("Your opt-out line", suffix)):
        symbol = _first_symbol(text or "")
        if symbol:
            return f"Billed as {parts} texts. {where} has a {symbol}, which makes each text hold only 70 characters.", ""
    return bill_label(billed), ""


def fix_label(text: str) -> str:
    """The one-tap fix beside a symbol billing line ("Replace — with -"), or '' when there is none."""
    _, parts, plain = sms_parts(text)
    symbol = _first_symbol(text)
    return f"Replace {symbol} with {_PLAIN[symbol]}" if parts > 1 and not plain and symbol in _PLAIN else ""


_DASHES = frozenset("—–")


def apply_fix(text: str) -> str:
    """The wording with its first billed symbol swapped for the plain one (what the fix button does).
    A dash with no space on a side gets one, so "call—this" becomes "call - this", never "call-this".
    portal.js plainSwap() does the same."""
    symbol = _first_symbol(text)
    if symbol not in _PLAIN:
        return text
    if symbol not in _DASHES:
        return text.replace(symbol, _PLAIN[symbol])
    out = []
    for index, ch in enumerate(text):
        if ch != symbol:
            out.append(ch)
            continue
        before = text[index - 1] if index else " "
        after = text[index + 1] if index + 1 < len(text) else " "
        out.append(("" if before.isspace() else " ") + "-" + ("" if after.isspace() else " "))
    return "".join(out)


# --- previews ------------------------------------------------------------------------------

# The approved mockup's values, the same as the example conversation's script (portal_sample, fix pass P5).
SAMPLE_SERVICE, SAMPLE_LOCATION, SAMPLE_EMAIL = "Tree trimming", "412 Maple St, Charlotte", "dana@example.com"


class _Keep(dict):
    def __missing__(self, key):
        return "[" + _ALL_LABELS.get(key, key) + "]"


def fill(template: str, values: dict[str, str]) -> str:
    try:
        return template.format_map(_Keep(values))
    except (ValueError, IndexError, KeyError, AttributeError, TypeError):
        return template  # a rejected save with broken braces shows the text as typed, never a 500


def sample_when(state, now: datetime) -> str:
    """The example appointment time, formatted exactly as booking.py formats {when}: the next
    Thursday at 10 AM in the business time zone (the example conversation's own reply)."""
    zone = ZoneInfo(getattr(state, "timezone_name", "UTC") or "UTC")
    local = now.astimezone(zone)
    ahead = (3 - local.weekday()) % 7 or 7
    start = (local + timedelta(days=ahead)).replace(hour=10, minute=0, second=0, microsecond=0)
    return start.strftime("%A, %b %d at %I:%M %p %Z").replace(" 0", " ")


INVITE_LINE = f"A calendar invite is on its way to {SAMPLE_EMAIL}."


def preview_values(state, now: datetime, asked: set[str] | None = None) -> dict[str, str]:
    """Example values for the previews. The invite sentence and the customer's email are filled in only
    while the email question is asked (asked=None: as saved), as the booking code does."""
    if asked is None:
        asked = set(state.messages.current().fields) & {"phone", "email"}
    email = "email" in asked
    urls = CalendarLinks(str(state.public_base_url), LINK_SECRET).urls(1, "example")
    contact = (getattr(state, "business_contact", "") or "").strip() or format_contact_number(getattr(state, "business_number", "") or "")
    return {
        "business_name": state.business_name, "service": SAMPLE_SERVICE, "when": sample_when(state, now),
        "location": SAMPLE_LOCATION, "event_id": "", "invited_email": SAMPLE_EMAIL if email else "",
        "invite_line": INVITE_LINE if email else "",
        "calendar_links": CalendarLinks.sms_line(urls), "contact_line": f" Contact: {contact}." if contact else "", **urls,
    }


def preview_parts(key: str, templates: dict[str, str], values: dict[str, str]) -> tuple[str, str]:
    """(wording, opt-out line added for the owner or '') with the details filled in."""
    body = " ".join(fill(templates[key], values).split())
    if key in OPT_OUT_REQUIRED and not re.search(r"\bstop\b", templates[key], re.IGNORECASE):
        return body, " ".join(fill(templates["opt_out_suffix"], values).split())
    return body, ""


def preview_text(key: str, templates: dict[str, str], values: dict[str, str]) -> str:
    return " ".join(part for part in preview_parts(key, templates, values) if part)


# --- errors ----------------------------------------------------------------------------------

def blame(error: str, templates: dict[str, str]) -> tuple[str | None, str]:
    """Which text a MessageTemplateError is about, and the reason without the key."""
    match = re.match(r"^(\w+) (.+)$", error)
    if match and match.group(1) in DEFAULT_TEMPLATES:
        return match.group(1), match.group(2)
    if error.startswith("handoff acknowledgements"):
        for key in DESTINATION_KEYS:
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


def friendly_reason(error: str, key: str | None) -> str:
    """The validator's reason in the deck's words; the validation itself is unchanged."""
    phrase = re.search(r"business line \('(.+)'\)", error)
    if phrase:
        return REASON_NUMBER.format(phrase=phrase.group(1))
    if "promise a follow-up" in error:
        return REASON_FOLLOW_UP
    if "911" in error:
        return REASON_911
    if "no booking was made" in error:
        return REASON_NO_BOOKING
    if "reply STOP" in error:
        return REASON_STOP
    if "unbalanced" in error or "placeholders must look like" in error or "unknown insert" in error:
        return REASON_BAD_INSERT
    extra = re.search(r"unsupported placeholder\(s\) (.+?); allowed", error)
    if extra and key:
        names = [n.strip().strip("{}") for n in extra.group(1).split(",")]
        if not all(n in _ALL_LABELS for n in names):
            return REASON_BAD_INSERT
        shown = ", ".join(_ALL_LABELS[n] for n in names)
        labels = [label for _, label in chips_for(key)]
        if not labels:
            return REASON_WRONG_INSERT_NONE.format(names=shown)
        return REASON_WRONG_INSERT.format(names=shown, labels=", ".join(labels))
    if "longer than" in error:
        return REASON_TOO_LONG
    return REASON_BAD_INSERT if "{" in error or "}" in error else error[:1].upper() + error[1:]


# --- save notice -------------------------------------------------------------------------

def _quoted(titles: list[str]) -> str:
    return ", ".join(f"“{t}”" for t in titles)


def change_params(old: dict[str, str], new: dict[str, str], old_asked: set[str], new_asked: set[str]) -> dict:
    """What one save changed, as keys only (the one-time notice carries these, never text)."""
    switched = [field for field in ("phone", "email") if (field in old_asked) != (field in new_asked)]
    return {"changed": [k for k in FIELD_KEYS if old[k] != new[k] and new[k] != DEFAULT_TEMPLATES[k]],
            "back": [k for k in FIELD_KEYS if old[k] != new[k] and new[k] == DEFAULT_TEMPLATES[k]],
            "on": [f for f in switched if f in new_asked], "off": [f for f in switched if f not in new_asked]}


_QUESTION_TITLES = {field: MESSAGES[key][0] for key, (field, _) in OPTIONAL_QUESTIONS.items()}


def saved_text(*, changed=(), back=(), on=(), off=()) -> str:
    """The deck's toast_saved line: one "Saved." then what changed, a switch named as a setting (m29)."""
    parts = ([f"You changed {_quoted([MESSAGES[k][0] for k in changed])}."] if changed else []) + \
            ([f"Back to standard wording: {_quoted([MESSAGES[k][0] for k in back])}."] if back else []) + \
            ([f"You turned on {_quoted([_QUESTION_TITLES[f] for f in on])}."] if on else []) + \
            ([f"You turned off {_quoted([_QUESTION_TITLES[f] for f in off])}."] if off else [])
    return "Saved. " + " ".join(parts) if parts else "Saved. No wording changed."


def change_summary(old: dict[str, str], new: dict[str, str], old_asked: set[str], new_asked: set[str]) -> str:
    """The deck's toast_saved line for one save."""
    return saved_text(**change_params(old, new, old_asked, new_asked))


# --- config-driven lines ---------------------------------------------------------------------

def _channel(state) -> str:
    """chat | log | off: where the customer's details go when TextBack steps back."""
    transport = getattr(state, "delivery_transport", None)
    channel = getattr(transport, "channel_name", "disabled")
    destination = str(getattr(state, "handoff_destination", "") or "")
    if channel == "telegram" and destination and destination != "unconfigured":
        return "chat"
    return "log" if channel == "log" and destination != "unconfigured" else "off"


def destination_label(state) -> str | None:
    """Who receives the customer's details (short form), or None when nobody does."""
    return {"chat": DESTINATION_CHAT, "log": DESTINATION_LOG_SHORT}.get(_channel(state))


def destination_line(state) -> str:
    """The line that replaces the three next steps when they would not be true (log or off)."""
    return {"chat": DESTINATION_LINE.format(label=DESTINATION_CHAT), "log": f"These go to {DESTINATION_LOG}",
            "off": DESTINATION_OFF}[_channel(state)]


def when_line(key: str, state) -> str:
    from text_back.portal_scheduling import humanize_minutes
    when = MESSAGES[key][1]
    if key in ("followup_1", "followup_2"):
        delays = tuple(getattr(state.followup_policy, "delays_minutes", ()) or (120, 1440))
        index = 0 if key == "followup_1" else min(1, len(delays) - 1)
        return when.format(delay=humanize_minutes(delays[index]))
    return when


# --- view models -----------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Item:
    """One row of a thread: a bubble, a pill or the steps-back divider."""
    kind: str        # customer | textback | missed | neutral | booked | divider
    text: str
    key: str = ""
    links: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class Card:
    key: str
    title: str
    when: str
    rules: tuple[str, ...]
    next_steps: tuple[str, ...]  # steps-back cards with a real destination: the three steps
    destination: str             # steps-back cards otherwise: the line that replaces them
    default: str                 # standard wording, display form (data-default)
    saved: str                   # wording in the file, display form (data-saved)
    value: str                   # textarea content, display form; never ""
    length: int
    custom: bool                 # the textarea differs from the standard wording
    saved_custom: bool           # the saved wording differs from the standard: "Customized"
    body: str                    # bubble words, links taken out
    links: tuple[tuple[str, str], ...]
    suffix: str                  # the opt-out line added for the owner, or ''
    was: str                     # the saved text as sent, for "Was: …" while the draft differs
    count: str
    bill: str
    fix: str                     # "Replace — with -" or ''
    segments: int
    optout_required: bool
    optional: str                # phone | email | ""
    switch_label: str
    asked: bool
    asked_saved: bool
    branch: bool
    hidden: bool                 # the branch of a switched-off optional question
    chips: tuple[tuple[str, str], ...]
    error: str
    dirty: bool
    text_dirty: bool             # the wording differs from the saved one (a switch alone does not count)
    trigger: str
    who: str                     # speaker label over the bubble when a customer reply is shown above it


@dataclass(frozen=True, slots=True)
class Step:
    id: str
    heading: str
    blurb: str
    glyph: str
    cards: tuple[Card, ...]       # the main path, always open
    optional: tuple[Card, ...]    # optional questions (main path, behind their switches)
    has_error: bool = False
    branches: tuple[Card, ...] = ()  # re-asks, time taken, calendar failed: one disclosure
    branch_label: str = ""
    branch_count: str = ""        # "1 text" / "3 texts": the branch texts a customer can get now
    branch_titles: str = ""       # their titles, " · " between
    branch_open: bool = False     # holds a customized, unsaved or rejected text


def texts_word(n: int) -> str:
    return f"{n} text{'s' if n != 1 else ''}"


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    label: str
    thread: tuple[Item, ...]


def _norm(text: str) -> str:
    return " ".join(text.split())


def rail_scenarios(state, now: datetime) -> tuple[Scenario, ...]:
    """The example conversations from the real handlers with the SAVED texts, as thread rows."""
    from text_back.portal_render import split_links

    current = state.messages.current()
    saved = {key: current.templates[key] for key in FIELD_KEYS if current.templates[key] != DEFAULT_TEMPLATES[key]}
    asked = set(current.fields) & {"phone", "email"}
    booked = PILL_BOOKED_TEST if getattr(state.calendar, "provider_name", "stub") == "stub" else PILL_BOOKED
    label = destination_label(state)
    out = []
    for name, deck_label in RAIL_SCENARIOS:
        assert name in SAMPLE_SCENARIOS
        bubbles = render_scenario(name, templates=saved, business_name=state.business_name, asked=asked, now=now,
                                  public_base_url=str(state.public_base_url), tz_name=state.timezone_name)
        rows: list[Item] = []
        for bubble in bubbles:
            if bubble.side == "event":
                text = {"Missed call": PILL_MISSED, "Booked on the calendar": booked,
                        "Texting stops here": PILL_STOPS}.get(bubble.text, bubble.text)
                rows.append(Item("booked" if text == booked else "missed" if text == PILL_MISSED else "neutral", text))
                continue
            if bubble.side == "customer":
                rows.append(Item("customer", bubble.text))
                continue
            if bubble.key == "followup_1":
                rows.append(Item("neutral", PILL_NO_REPLY))
            elif bubble.key == "followup_2":
                rows.append(Item("neutral", PILL_STILL_NO_REPLY))
            body, links = split_links(bubble.text, str(state.public_base_url))
            rows.append(Item("textback", body, key=bubble.key or "", links=links))
            if bubble.key == "booking_error":
                rows.append(Item("neutral", PILL_NO_BOOKING))
            if bubble.key in DESTINATION_KEYS:
                rows.append(Item("divider", DIVIDER_STEPS_BACK))
                if label:
                    rows.append(Item("neutral", PILL_DETAILS_SENT.format(label=label)))
        out.append(Scenario(name, deck_label, tuple(rows)))
    return tuple(out)


def changed_words(n: int, settings: int = 0) -> str:
    """'1 text changed' / '2 texts changed'; a question switch is a setting ('1 setting changed'); both: '3 changes'."""
    if n and settings:
        return f"{n + settings} changes"
    if settings:
        return SETTING_ONE if settings == 1 else SETTING_MANY.format(n=settings)
    return CHANGED_ONE if n == 1 else CHANGED_MANY.format(n=n)


def page_view(state, now: datetime, *, values: dict[str, str] | None = None, asked: set[str] | None = None,
              error: str = "", unsaved: bool = False) -> dict:
    """Context for messages.html.j2. ``values`` are the owner's custom texts in display form
    ('' = standard); after a rejected save they are the texts as typed, so nothing is lost."""
    from text_back.portal_registry import network_notice_applies
    from text_back.portal_render import split_links

    current = state.messages.current()
    editable = state.messages.path is not None
    if values is None:
        values = {key: (to_display(current.templates[key]) if current.templates[key] != DEFAULT_TEMPLATES[key] else "")
                  for key in FIELD_KEYS}
    asked_saved = set(current.fields) & {"phone", "email"}
    asked = asked_saved if asked is None else asked
    templates = {key: to_template(values.get(key) or "") or DEFAULT_TEMPLATES[key] for key in FIELD_KEYS}
    saved_templates = {key: current.templates[key] for key in FIELD_KEYS}
    sample = preview_values(state, now, asked)
    bad_key, reason = blame(error, templates) if error else (None, "")
    friendly = friendly_reason(reason, bad_key) if error else ""
    notice = network_notice_applies(state, now)
    channel_line = destination_line(state)
    chat = _channel(state) == "chat"

    def card(key: str) -> Card:
        optional, switch_label = OPTIONAL_QUESTIONS.get(key, ("", ""))
        default = to_display(DEFAULT_TEMPLATES[key])
        saved = to_display(current.templates[key])
        value = values.get(key) or default
        body, suffix = preview_parts(key, templates, sample)
        preview = " ".join(part for part in (body, suffix) if part)
        words, links = split_links(body, str(state.public_base_url))
        billed = NOTICE_MODEL + preview if notice and key != "opt_out_suffix" else preview
        parent = BRANCH_OF.get(key)
        trigger = TRIGGERS.get(key, "")
        dirty = _norm(value) != _norm(saved) or (optional in asked) != (optional in asked_saved)
        return Card(
            key=key, title=MESSAGES[key][0], when=when_line(key, state),
            rules=(RULES[key],) if key in RULES else (),
            next_steps=NEXT_STEPS if key in DESTINATION_KEYS and chat else (),
            destination=channel_line if key in DESTINATION_KEYS and not chat else "",
            default=default, saved=saved, value=value, length=len(value), custom=bool(values.get(key)),
            saved_custom=_norm(current.templates[key]) != _norm(DEFAULT_TEMPLATES[key]),
            body=words, links=links, suffix=suffix, was=split_links(preview_text(key, saved_templates, sample), str(state.public_base_url))[0],
            count=count_label(preview, notice and key != "opt_out_suffix"),
            bill=bill_info(key, templates, sample, notice)[0], fix=bill_info(key, templates, sample, notice)[1],
            segments=sms_parts(billed)[1],
            optout_required=key in OPT_OUT_REQUIRED, optional=optional, switch_label=switch_label,
            asked=optional in asked, asked_saved=optional in asked_saved,
            branch=key in BRANCH_KEYS, hidden=bool(parent and OPTIONAL_QUESTIONS.get(parent) and
                                                   OPTIONAL_QUESTIONS[parent][0] not in asked),
            chips=chips_for(key), error=friendly if key == bad_key else "", dirty=dirty,
            text_dirty=_norm(value) != _norm(saved), trigger=trigger, who=state.business_name if trigger else "",
        )

    def step(sid, heading, blurb, glyph, keys, optional) -> Step:
        branches = tuple(card(k) for k in (*keys, *optional) if k in BRANCH_KEYS)
        live = [c for c in branches if not c.hidden or c.error]
        return Step(sid, heading, blurb, glyph, tuple(card(k) for k in keys if k not in BRANCH_KEYS),
                    tuple(card(k) for k in optional if k not in BRANCH_KEYS), has_error=bad_key in (*keys, *optional),
                    branches=branches, branch_label=BRANCH_SUMMARY.get(sid, ""), branch_count=texts_word(len(live)),
                    branch_titles=BRANCH_SEP.join(c.title for c in live),
                    branch_open=any(c.saved_custom or c.dirty or c.error for c in live))

    steps = tuple(step(*row) for row in STEPS)
    keywords = step(*KEYWORDS)
    every = [c for st in (*steps, keywords) for c in (*st.cards, *st.optional, *st.branches)]
    dirty = [c for c in every if c.dirty]
    texts = [c for c in every if c.text_dirty]
    switches = [c for c in every if c.optional and c.asked != c.asked_saved]
    error_summary = None
    if error:
        error_summary = {"key": bad_key or "", "title": MESSAGES[bad_key][0] if bad_key else "", "reason": friendly,
                         "text": (ERROR_SUMMARY.format(title=MESSAGES[bad_key][0], reason=friendly) if bad_key
                                  else ERROR_UNPLACED.format(reason=friendly)),
                         "link": ERROR_LINK, "kept": ERROR_KEPT}
    names = tuple((f"#card-{c.key}", c.title) for c in (*texts, *switches))
    count = NOT_SAVED_COUNT.format(count=changed_words(len(texts), len(switches))) if dirty else ""
    support = str(getattr(state, "support_contact", "") or "").strip()
    return {
        "editable": editable,
        "max_chars": MAX_TEMPLATE_CHARS,
        "steps": steps,
        "keywords": keywords,
        "jump": JUMP,
        "error_summary": error_summary,
        "asked": tuple(sorted(asked)),
        "network_notice": NETWORK_NOTICE if notice else "",
        "intro": INTRO, "meta": META, "rail_foot": RAIL_FOOT,
        "not_enabled": "" if editable else NOT_ENABLED,
        "support_href": f"sms:{support}" if support and not editable else "",
        "rail": rail_scenarios(state, now),
        # A rejected save answers with the typed texts: the header (phone) and the bar (desktop) say so.
        "dirty_count": count, "dirty_names": names,
        "topsave": ({"form": "messages-form", "changed": count, "save": SAVE, "names": names}
                    if editable and dirty and (error or unsaved) else None),
        "tb_data": {"sample": sample, "invite": {"invite_line": INVITE_LINE, "invited_email": SAMPLE_EMAIL}, "labels": {label: name for label, name in _LABEL_NAMES.items()},
                    "gsm": GSM_BASIC, "ext": GSM_EXTENDED, "notice": notice} if editable else None,
    }


_BRACKETS = re.compile(r"\[([^\[\]]*)\]")


def unknown_insert(submitted: dict[str, str]) -> str:
    """'' when every [ … ] in the submitted texts is a known insert label (any case or spacing); otherwise a
    validator-style error naming the first text with one, which friendly_reason words as REASON_BAD_INSERT."""
    for key in FIELD_KEYS:
        for match in _BRACKETS.finditer(submitted.get(key, "") or ""):
            if " ".join(match.group(1).lower().split()) not in _LABEL_KEYS:
                return f"{key} has an unknown insert"
    return ""


def read_form(form, *, apply_buttons: bool = True) -> tuple[dict[str, str], dict[str, str], set[str]]:
    """(values as typed in display form, overrides for the file, asked questions).

    An untouched or re-typed standard text is stored as standard. A Reset button posts the whole form with
    its own key named in ``reset``, and a "Replace — with -" button names its key in ``fix``, so both work
    without JavaScript and keep the other edits."""
    submitted = {key: str(form.get(key, "") or "").strip() for key in FIELD_KEYS}
    fix = str(form.get("fix", "") or "") if apply_buttons else ""
    if fix in submitted:
        submitted[fix] = apply_fix(submitted[fix] or to_display(DEFAULT_TEMPLATES[fix]))
    for key, value in submitted.items():
        if _norm(to_template(value)) == _norm(DEFAULT_TEMPLATES[key]):
            submitted[key] = ""
    reset = str(form.get("reset", "") or "") if apply_buttons else ""
    if reset in submitted:
        submitted[reset] = ""
    overrides = {key: to_template(value) for key, value in submitted.items() if value}
    asked = {field for field in ("phone", "email") if form.get(f"ask_{field}")}
    if asked:
        overrides["fields"] = ", ".join(("service", "location", "preferred_time", "name",
                                         *[f for f in ("phone", "email") if f in asked]))
    return submitted, overrides, asked
