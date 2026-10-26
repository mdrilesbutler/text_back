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

# --- words (copy deck, section 4; verbatim) ------------------------------------------------

TITLE = "Your messages"
INTRO = ("The texts customers get after a missed call, in the order they get them. Tap Edit wording to change one. "
         "Changes start with the next missed call after you save.")
META = "Green bubbles are what customers see. The job, address, time and names are made-up examples."
NOT_ENABLED = "Message editing isn't turned on for your account yet. FluxWorks sets this up for you."
SUPPORT_BUTTON = "Text FluxWorks support"
NETWORK_NOTICE = "Until phone companies approve your business for texting, each text starts with a short network notice."
JUMP_LABEL = "On this page"
OPTIONAL_EYEBROW = "Optional questions"

RULE_STOP = ('Phone companies require "Reply STOP to opt out." If your wording leaves out STOP, we add that line for you.')
RULE_STOP_WORD = "The word STOP stays. Phone companies check for it."
RULE_BOOKING_ERROR = 'Must say "No booking was made" and can\'t use the word "call". The customer stays in the text thread.'
RULE_STEPS_BACK = ("This text must tell the customer someone will follow up. Don't ask them to call, and don't say "
                   "they'll be put through to someone.")
RULE_SAFETY = "Must tell people to call 911 if anyone is in danger, and must say someone will follow up."
RULE_PARAGRAPH = f"Sent as one paragraph. Up to {MAX_TEMPLATE_CHARS} characters."
DESTINATION_CHAT = "the FluxWorks operator"
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

RAIL_TITLE = "Example conversation"
RAIL_SHOW = "Show"
RAIL_SUB = "Text message"
RAIL_FOOT = "Example conversation · nothing is sent · names made up"
RAIL_BACK = "Back to editing"
PILL_MISSED = "Missed call · just now"
PILL_NO_REPLY, PILL_STILL_NO_REPLY = "No reply", "Still no reply"
PILL_STOPS = "Texting stops here"
PILL_NO_BOOKING = "No booking was made"
PILL_BOOKED, PILL_BOOKED_TEST = "Booked · on your calendar", "Booked · on the test calendar"
DIVIDER_STEPS_BACK = "The assistant steps back here"
PILL_DETAILS_SENT = "Customer's details sent to {label}"

SAVEBAR_NOJS = "Saves every text at once"
SAVE, SAVING, DISCARD = "Save", "Saving…", "Discard"

ERROR_SUMMARY = 'Not saved. "{title}" needs a change: {reason}'
ERROR_LINK = "Go to that text"
ERROR_KEPT = "Your other edits are still here. Nothing was saved yet."
ERROR_UNPLACED = "Not saved. {reason}"

REASON_NUMBER = ('Take out "{phrase}". Customers stay in the text thread, so say you\'ll follow up by text, like '
                 '"We\'ll follow up with you by text."')
REASON_FOLLOW_UP = 'Add the words "follow up", like "We\'ll follow up with you by text."'
REASON_911 = "Tell people to call 911 if anyone is in danger."
REASON_NO_BOOKING = 'Say "No booking was made" and leave out the word "call".'
REASON_STOP = "Include the word STOP. Phone companies require it."
REASON_BAD_INSERT = ("Something typed by hand isn't a detail we can fill in. Use the Insert buttons under the box, "
                     "or remove it.")
REASON_WRONG_INSERT = "This text can't fill in {names}. It can use: {labels}."
REASON_WRONG_INSERT_NONE = "This text can't fill in {names}. It fills in no details."
REASON_TOO_LONG = f"Shorten it to {MAX_TEMPLATE_CHARS} characters or fewer."

# key -> (card title, when-line). followup_1/2 when-lines carry the live reminder delays (when_line).
MESSAGES: dict[str, tuple[str, str]] = {
    "intro": ("First text after a missed call", "Sent the moment a call goes unanswered."),
    "prompt_service": ("Question 1: the job", "Asked as soon as the customer replies."),
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
    "followup_2": ("Last reminder", "Sent {delay} after the first reminder. After this the assistant stops texting."),
    "handoff_ack": ("When the assistant steps back", "Sent when the customer asks for the owner or the assistant can't help."),
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

# (step id, heading, blurb, ((parent key, (branch keys...)), ...))
STEPS: tuple[tuple[str, str, str, tuple], ...] = (
    ("missed", "Missed call", "A call goes unanswered. Within a minute the caller gets this text.", (("intro", ()),)),
    ("questions", "Questions", "Asked one at a time, in this order. The assistant moves on only once it has an answer.", (
        ("prompt_service", ()), ("prompt_location", ()),
        ("prompt_preferred_time", ("preferred_time_reprompt",)), ("prompt_name", ()),
        ("prompt_phone", ("phone_reprompt",)), ("prompt_email", ("email_reprompt",)))),
    ("booking", "Booking", "Once it has the answers, the assistant checks your calendar and books a free time.",
     (("booking_confirmation", ("slot_unavailable", "booking_error")),)),
    ("noreply", "No reply", "If the customer goes quiet, the assistant sends two reminders. Then the texting stops.",
     (("followup_1", ()), ("followup_2", ()))),
    ("steps_back", "When the assistant steps back",
     "When a text needs a person, the assistant stops scheduling and passes the customer's details on.",
     (("handoff_ack", ()), ("handoff_ack_safety", ()))),
)
KEYWORDS = ("keywords", "START, HELP and STOP", "Required by phone companies. Most businesses never change these.",
            (("opt_in", ()), ("help", ()), ("opt_out_ack", ()), ("opt_out_suffix", ())))
JUMP = (("missed", "Missed call"), ("questions", "Questions"), ("booking", "Booking"), ("noreply", "No reply"),
        ("steps_back", "Steps back"))

FIELD_KEYS: tuple[str, ...] = tuple(key for *_, sets in (*STEPS, KEYWORDS) for parent, branches in sets
                                    for key in (parent, *branches))
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
    "links_page": "Calendar links page", "contact_line": "Contact number sentence",
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
    return len(text), (1 if len(text) <= 70 else math.ceil(len(text) / 67)), False


def count_label(text: str) -> str:
    chars, parts, _ = sms_parts(text)
    return f"{parts} text{'s' if parts != 1 else ''} · {chars} characters"


def bill_label(text: str) -> str:
    """'' for one text; otherwise the deck's cost_bill_symbol / cost_bill_long line."""
    _, parts, plain = sms_parts(text)
    if parts < 2:
        return ""
    if plain:
        return f"Billed as {parts} texts. Customers still see one message."
    symbol = next(ch for ch in text if ch not in GSM_BASIC and ch not in GSM_EXTENDED)
    instead = f'Use "{_PLAIN[symbol]}" instead.' if symbol in _PLAIN else "Use a plain letter instead."
    return f'Billed as {parts} texts. The "{symbol}" symbol makes each text hold only 70 characters. {instead}'


# --- previews ------------------------------------------------------------------------------

SAMPLE_SERVICE, SAMPLE_LOCATION, SAMPLE_EMAIL = "Tree removal", "12 Oak St, Charlotte", "dana@example.com"


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


def preview_values(state, now: datetime) -> dict[str, str]:
    urls = CalendarLinks(str(state.public_base_url), LINK_SECRET).urls(1, "example")
    contact = (getattr(state, "business_contact", "") or "").strip() or format_contact_number(getattr(state, "business_number", "") or "")
    return {
        "business_name": state.business_name, "service": SAMPLE_SERVICE, "when": sample_when(state, now),
        "location": SAMPLE_LOCATION, "event_id": "", "invited_email": SAMPLE_EMAIL,
        "invite_line": f"A calendar invite is on its way to {SAMPLE_EMAIL}.",
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
    if "unbalanced" in error or "placeholders must look like" in error:
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


def change_summary(old: dict[str, str], new: dict[str, str], old_asked: set[str], new_asked: set[str]) -> str:
    """The deck's toast_saved line for one save."""
    changed = [MESSAGES[k][0] for k in FIELD_KEYS if old[k] != new[k] and new[k] != DEFAULT_TEMPLATES[k]]
    changed += [f"{MESSAGES[k][0]} switched {'on' if field in new_asked else 'off'}"
                for k, (field, _) in OPTIONAL_QUESTIONS.items() if (field in old_asked) != (field in new_asked)]
    back = [MESSAGES[k][0] for k in FIELD_KEYS if old[k] != new[k] and new[k] == DEFAULT_TEMPLATES[k]]
    parts = ([f"Saved. You changed {_quoted(changed)}."] if changed else []) + \
            ([f"Saved. Back to standard wording: {_quoted(back)}."] if back else [])
    return " ".join(parts) or "Saved. No wording changed."


# --- config-driven lines ---------------------------------------------------------------------

def destination_label(state) -> str | None:
    """Who receives the customer's details when the assistant steps back, or None when nobody does.

    Only the chat channel with a destination set delivers anywhere a person reads; "log",
    "disabled" and an "unconfigured" destination all read as "nowhere yet"."""
    transport = getattr(state, "delivery_transport", None)
    channel = getattr(transport, "channel_name", "disabled")
    destination = str(getattr(state, "handoff_destination", "") or "")
    if channel == "telegram" and destination and destination != "unconfigured":
        return DESTINATION_CHAT
    return None


def destination_line(state) -> str:
    label = destination_label(state)
    return DESTINATION_LINE.format(label=label) if label else DESTINATION_OFF


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
    suffix: str = ""


@dataclass(frozen=True, slots=True)
class Card:
    key: str
    title: str
    when: str
    rule: str
    destination: str        # the steps-back destination line, steps-back cards only
    default: str            # standard wording, display form (data-default)
    saved: str              # wording in the file, display form (data-saved)
    value: str              # textarea content, display form; never ""
    length: int
    custom: bool            # the textarea differs from the standard wording
    saved_custom: bool      # the saved wording differs from the standard: "Customized"
    body: str
    suffix: str
    count: str
    bill: str
    segments: int
    optout_required: bool
    optout_added: bool
    optional: str           # phone | email | ""
    switch_label: str
    asked: bool
    asked_saved: bool
    branch: bool
    chips: tuple[tuple[str, str], ...]
    error: str
    dirty: bool


@dataclass(frozen=True, slots=True)
class QSet:
    eyebrow: str
    parent: Card
    branches: tuple[Card, ...]


@dataclass(frozen=True, slots=True)
class Step:
    id: str
    heading: str
    blurb: str
    sets: tuple[QSet, ...]
    has_error: bool = False


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    label: str
    thread: tuple[Item, ...]


def _norm(text: str) -> str:
    return " ".join(text.split())


def rail_scenarios(state, now: datetime) -> tuple[Scenario, ...]:
    """The example conversations from the real handlers with the SAVED texts, as thread rows."""
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
                text = {"Missed call": PILL_MISSED, "Booked on the calendar": booked}.get(bubble.text, bubble.text)
                rows.append(Item("booked" if text == booked else "missed" if text == PILL_MISSED else "neutral", text))
                continue
            if bubble.side == "customer":
                rows.append(Item("customer", bubble.text))
                continue
            if bubble.key == "followup_1":
                rows.append(Item("neutral", PILL_NO_REPLY))
            elif bubble.key == "followup_2":
                rows.append(Item("neutral", PILL_STILL_NO_REPLY))
            rows.append(Item("textback", bubble.text, key=bubble.key or ""))
            if bubble.key == "booking_error":
                rows.append(Item("neutral", PILL_NO_BOOKING))
            if bubble.key in DESTINATION_KEYS:
                rows.append(Item("divider", DIVIDER_STEPS_BACK))
                if label:
                    rows.append(Item("neutral", PILL_DETAILS_SENT.format(label=label)))
        out.append(Scenario(name, deck_label, tuple(rows)))
    return tuple(out)


def page_view(state, now: datetime, *, values: dict[str, str] | None = None, asked: set[str] | None = None,
              error: str = "") -> dict:
    """Context for messages.html.j2. ``values`` are the owner's custom texts in display form
    ('' = standard); after a rejected save they are the texts as typed, so nothing is lost."""
    from text_back.portal_registry import network_notice_applies

    current = state.messages.current()
    editable = state.messages.path is not None
    if values is None:
        values = {key: (to_display(current.templates[key]) if current.templates[key] != DEFAULT_TEMPLATES[key] else "")
                  for key in FIELD_KEYS}
    asked_saved = set(current.fields) & {"phone", "email"}
    asked = asked_saved if asked is None else asked
    templates = {key: to_template(values.get(key) or "") or DEFAULT_TEMPLATES[key] for key in FIELD_KEYS}
    sample = preview_values(state, now)
    bad_key, reason = blame(error, templates) if error else (None, "")
    friendly = friendly_reason(reason, bad_key) if error else ""
    destination = destination_line(state)

    def card(key: str, branch: bool) -> Card:
        optional, switch_label = OPTIONAL_QUESTIONS.get(key, ("", ""))
        default = to_display(DEFAULT_TEMPLATES[key])
        saved = to_display(current.templates[key])
        value = values.get(key) or default
        body, suffix = preview_parts(key, templates, sample)
        preview = " ".join(part for part in (body, suffix) if part)
        dirty = _norm(value) != _norm(saved) or (optional in asked) != (optional in asked_saved)
        return Card(
            key=key, title=MESSAGES[key][0], when=when_line(key, state), rule=RULES.get(key, ""),
            destination=destination if key in DESTINATION_KEYS else "",
            default=default, saved=saved, value=value, length=len(value), custom=bool(values.get(key)),
            saved_custom=_norm(current.templates[key]) != _norm(DEFAULT_TEMPLATES[key]),
            body=body, suffix=suffix, count=count_label(preview), bill=bill_label(preview), segments=sms_parts(preview)[1],
            optout_required=key in OPT_OUT_REQUIRED, optout_added=bool(suffix),
            optional=optional, switch_label=switch_label, asked=optional in asked, asked_saved=optional in asked_saved,
            branch=branch, chips=chips_for(key), error=friendly if key == bad_key else "", dirty=dirty,
        )

    def step(sid: str, heading: str, blurb: str, sets) -> Step:
        qsets, eyebrow_used = [], False
        for parent, branches in sets:
            eyebrow = ""
            if parent in OPTIONAL_QUESTIONS and not eyebrow_used:
                eyebrow, eyebrow_used = OPTIONAL_EYEBROW, True
            qsets.append(QSet(eyebrow, card(parent, False), tuple(card(b, True) for b in branches)))
        keys = {key for parent, branches in sets for key in (parent, *branches)}
        return Step(sid, heading, blurb, tuple(qsets), has_error=bad_key in keys)

    error_summary = None
    if error:
        error_summary = {"key": bad_key or "", "title": MESSAGES[bad_key][0] if bad_key else "", "reason": friendly,
                         "text": (ERROR_SUMMARY.format(title=MESSAGES[bad_key][0], reason=friendly) if bad_key
                                  else ERROR_UNPLACED.format(reason=friendly)),
                         "link": ERROR_LINK, "kept": ERROR_KEPT}
    support = str(getattr(state, "support_contact", "") or "").strip()
    return {
        "editable": editable,
        "max_chars": MAX_TEMPLATE_CHARS,
        "steps": tuple(step(*row) for row in STEPS),
        "keywords": step(*KEYWORDS),
        "jump": tuple((f"#g_{sid}", label) for sid, label in JUMP),
        "error_summary": error_summary,
        "asked": tuple(sorted(asked)),
        "network_notice": NETWORK_NOTICE if network_notice_applies(state, now) else "",
        "not_enabled": "" if editable else NOT_ENABLED,
        "support_href": f"sms:{support}" if support and not editable else "",
        "rail": rail_scenarios(state, now),
        "tb_data": {"sample": sample, "labels": {label: name for label, name in _LABEL_NAMES.items()},
                    "gsm": GSM_BASIC, "ext": GSM_EXTENDED} if editable else None,
    }


def read_form(form) -> tuple[dict[str, str], dict[str, str], set[str]]:
    """(values as typed in display form, overrides for the file, asked questions).

    An untouched or re-typed standard text is stored as standard; a Reset button posts the whole
    form with its own key named in ``reset``, so it works without JavaScript and keeps the other edits."""
    submitted = {key: str(form.get(key, "") or "").strip() for key in FIELD_KEYS}
    for key, value in submitted.items():
        if _norm(to_template(value)) == _norm(DEFAULT_TEMPLATES[key]):
            submitted[key] = ""
    reset = str(form.get("reset", "") or "")
    if reset in submitted:
        submitted[reset] = ""
    overrides = {key: to_template(value) for key, value in submitted.items() if value}
    asked = {field for field in ("phone", "email") if form.get(f"ask_{field}")}
    if asked:
        overrides["fields"] = ", ".join(("service", "location", "preferred_time", "name",
                                         *[f for f in ("phone", "email") if f in asked]))
    return submitted, overrides, asked
