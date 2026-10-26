"""Calendar page (/client/calendar): the connection card, the picker and the free-times check.

Nothing here writes. Connecting and picking a calendar go through the existing
``client_settings`` helpers and routes; ``check_availability`` only reads the
busy periods for the next ``HORIZON_DAYS`` and hands them to ``availability``.
Every owner-facing word is a verbatim row of docs/notes/portal-c/copy-deck.md,
section 6 (``DECK_STRINGS``), pinned by tests/test_portal_calendar.py; the few
sentences the deck lacks are listed in ``OPEN_STRINGS``.

Design rules (docs/notes/ui-bakeoff-2026-10-26/design-prompt-100.md, page 4):
- No state is a dead end: every card has a next step, as a button when one
  exists (Connect, Reconnect, the picker, or "Text FluxWorks support" when
  ``state.support_contact`` is set) and otherwise as a sentence naming who
  does it.
- The free-times card is titled "Test calendar, not yours" whenever the stub
  is in use, and the slots it lists are filtered through the owner's working
  hours before they are formatted, so a 1 AM slot can only appear when hours
  are "Any day, any time", and then the card says so.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from text_back import availability
from text_back import working_hours as wh
from text_back.calendars.protocol import CalendarProviderError

HORIZON_DAYS = 14

# --- words (copy deck, section 6; verbatim) ---------------------------------------
WORD_CONNECTED = "Connected"
TITLE_GOOGLE = "Google Calendar"
BODY_CONNECTED = "Bookings go here: {name}."
BTN_RECONNECT = "Reconnect Google Calendar"
WORD_NOT_CONNECTED = "Not connected"
TITLE_NOT_CONNECTED = "No calendar yet"
# Same words as Home's Calendar card; then why connecting matters (with Connect) or who sets it up (without).
BODY_NOT_CONNECTED = "No calendar of yours yet. Until you connect one, bookings go on a test calendar you can't see."
WHY_CONNECT = ("Connect the Google account that owns your business calendar, so the assistant offers your real "
               "free times and books onto your calendar.")
BODY_NO_WEB = ("To book onto your own calendar, it has to be connected. Connecting from this page isn't set up "
               "for your account yet. FluxWorks sets this up for you.")
BTN_CONNECT = "Connect Google Calendar"
BTN_CONNECT_BUSY = "Opening Google…"
BODY_NO_CONNECT = "Connecting from this page isn't set up for your account yet. FluxWorks sets this up for you."
BTN_SUPPORT = "Text FluxWorks support"
WORD_RECONNECT = "Reconnect needed"
BODY_RECONNECT = ("Google disconnected the calendar, so bookings are paused until you reconnect. "
                  "Customers are told no booking was made.")
WORD_UNREADABLE = "Couldn't be read"
BODY_UNREADABLE = "TextBack couldn't read the calendar connection. Bookings are paused until you reconnect."
CONSENT_NOTE = ("What Google will ask: (1) You pick the Google account that owns your business calendar. "
                "(2) Google asks you to let TextBack see and edit your calendars. "
                "TextBack uses this only to find free times and add bookings. "
                "(3) Afterwards you choose which calendar it uses.")
PICKER_LEGEND = "Which calendar should the assistant use?"
PICKER_HINT = "Free times are checked on this calendar and new appointments are added to it."
PICKER_MAIN = "(main calendar)"
PICKER_PILL = "In use"
PICKER_BUTTON = "Use this calendar"
PICKER_ERROR = "Pick one of the calendars listed."
PICKER_ONLY = "This is the only calendar this account can add appointments to."
TOAST_PICKED = "Saved. The assistant now books on {name}."
ERR_NO_ACCESS = "Google didn't give TextBack calendar access. Try connecting again."
ERR_NOT_SET_UP = "Connecting a calendar isn't set up for this account yet."
AVAIL_TITLE = "Next free times on {name}"
AVAIL_TITLE_TEST = "Test calendar, not yours"
AVAIL_INTRO = "The first three free {n}-minute times in the next 14 days, inside your working hours."
AVAIL_INTRO_TEST = "Shows how the check works. These times are not from your calendar."
AVAIL_BUTTON = "Check free times"
AVAIL_BUTTON_BUSY = "Checking…"
AVAIL_CAPTION = "Checked just now · next 14 days · working hours {hours}"
AVAIL_EMPTY = "No free {n}-minute time in the next 14 days inside your working hours."
AVAIL_UNREACHABLE = "Couldn't reach Google Calendar. Try again in a minute."
AVAIL_RECONNECT_FIRST = "Reconnect the calendar first."

DECK_STRINGS: tuple[str, ...] = (
    WORD_CONNECTED, TITLE_GOOGLE, BODY_CONNECTED, BTN_RECONNECT,
    WORD_NOT_CONNECTED, TITLE_NOT_CONNECTED, BODY_NOT_CONNECTED, WHY_CONNECT, BODY_NO_WEB, BTN_CONNECT, BTN_CONNECT_BUSY,
    BODY_NO_CONNECT, BTN_SUPPORT, WORD_RECONNECT, BODY_RECONNECT,
    WORD_UNREADABLE, BODY_UNREADABLE, CONSENT_NOTE,
    PICKER_LEGEND, PICKER_HINT, PICKER_MAIN, PICKER_PILL, PICKER_BUTTON, PICKER_ERROR, PICKER_ONLY,
    TOAST_PICKED, ERR_NO_ACCESS, ERR_NOT_SET_UP,
    AVAIL_TITLE, AVAIL_TITLE_TEST, AVAIL_INTRO, AVAIL_INTRO_TEST, AVAIL_BUTTON, AVAIL_BUTTON_BUSY,
    AVAIL_CAPTION, AVAIL_EMPTY, AVAIL_UNREACHABLE, AVAIL_RECONNECT_FIRST,
)

# Reused from the Schedule page (deck section 5): shown under the free times while hours are "any time".
ANY_TIME_NOTE = "Customers can be offered times like 1 AM. Set your hours."

# Sentences the deck has no row for yet (reported as Open; keep short and plain). The connected card's
# account line and "Use a different calendar" came back with the layer-5 review (the spec requires them);
# the deck rows cal_connected / cal_connected_buttons still need them restored.
BODY_MANAGED = "Set up by FluxWorks. It can't be changed here."
NO_CHECK = "Checking free times isn't available for this calendar yet."
BODY_CONNECTED_AS = "Bookings go here: {name}. Connected as {account}."
BTN_CHANGE = "Use a different calendar"
OPEN_STRINGS: tuple[str, ...] = (BODY_MANAGED, NO_CHECK, BODY_CONNECTED_AS, BTN_CHANGE)
# The consent note as the list the page shows (deck cal_asks): heading, then the numbered steps.
CONSENT_HEADING = "What Google will ask:"
CONSENT_STEPS = ("You pick the Google account that owns your business calendar.",
                 "Google asks you to let TextBack see and edit your calendars. TextBack uses this only to find free "
                 "times and add bookings.",
                 "Afterwards you choose which calendar it uses.")

PROVIDER_NAMES = {"google": "Google Calendar", "microsoft": "Outlook / Microsoft 365", "icloud": "iCloud"}


def _settings():
    # client_settings imports the portal; resolve at call time to keep the import graph one-way.
    from text_back import client_settings
    return client_settings


def _zone(state) -> ZoneInfo:
    try:
        return ZoneInfo(str(getattr(state, "timezone_name", "UTC") or "UTC"))
    except Exception:  # noqa: BLE001 - an unknown zone must not break the page
        return ZoneInfo("UTC")


def _hours(state):
    return wh.parse_working_hours(state.store.setting("working_hours"))


def _duration(state) -> int:
    return int(getattr(state, "appointment_duration_minutes", 60) or 60)


def _names(state) -> dict[str, str]:
    return {entry["id"]: entry.get("summary") or entry["id"] for entry in _settings().calendar_choices(state)}


def _support_button(state) -> list[dict]:
    contact = str(getattr(state, "support_contact", "") or "").strip()
    return [{"label": BTN_SUPPORT, "href": f"sms:{contact}", "kind": "secondary"}] if contact else []


def _connect_button(label: str, kind: str) -> dict:
    return {"label": label, "action": "connect", "kind": kind, "busy_label": BTN_CONNECT_BUSY}


def calendar_name(state, view: dict | None = None) -> str:
    """The calendar bookings go to: its picked name on Google, else the calendar id, else the provider."""
    view = view or _settings().calendar_status(state)
    current = view.get("calendar_id") or ""
    if view["provider"] == "google":
        return _names(state).get(current, current) or TITLE_GOOGLE
    return current or PROVIDER_NAMES.get(view["provider"], view["provider"].title())


def connected_account(state) -> str:
    """The connected Google account: the id of its main (primary) calendar, which Google sets to the
    account's address. Empty when the picker list has not been fetched yet (the line is then left out)."""
    for entry in _settings().calendar_choices(state):
        if entry.get("primary") and "@" in str(entry.get("id", "")):
            return str(entry["id"])
    return ""


def status_card(state) -> dict:
    """state_word / title / body / buttons for the connection card. Every state has a next step."""
    view = _settings().calendar_status(state)
    provider, status, can_connect = view["provider"], view["status"], bool(view["can_connect"])
    name = calendar_name(state, view)
    card = {"provider": provider, "status": status, "can_connect": can_connect, "calendar_name": name,
            "connected": status in ("ready", "managed"), "state_word": "", "title": "", "body": "", "why": "", "buttons": [],
            "kind": "ok"}

    def not_connected_next_step(body: str, label: str, kind: str) -> None:
        """Connect/Reconnect when the Google web client is configured; otherwise who sets it up, and a text action if one exists."""
        if can_connect:
            card["body"] = body
            card["buttons"] = [_connect_button(label, kind)]
        else:
            card["body"] = f"{body} {BODY_NO_CONNECT}"
            card["buttons"] = _support_button(state)

    if status == "ready":
        account = connected_account(state)
        body = BODY_CONNECTED_AS.format(name=name, account=account) if account else BODY_CONNECTED.format(name=name)
        card.update(state_word=WORD_CONNECTED, title=TITLE_GOOGLE, body=body, account=account)
        # "Use a different calendar" opens the picker; Reconnect stays a link-styled post.
        card["buttons"] = [{"label": BTN_CHANGE, "action": "pick", "kind": "secondary"}]
        if can_connect:
            card["buttons"].append(_connect_button(BTN_RECONNECT, "link"))
    elif status == "reauth_required":
        card.update(state_word=WORD_RECONNECT, title=TITLE_GOOGLE, kind="err")
        not_connected_next_step(BODY_RECONNECT, BTN_RECONNECT, "primary")
    elif status == "unavailable":
        card.update(state_word=WORD_UNREADABLE, title=TITLE_GOOGLE, kind="err")
        not_connected_next_step(BODY_UNREADABLE, BTN_RECONNECT, "primary")
    elif status == "none":
        card.update(state_word=WORD_NOT_CONNECTED, title=TITLE_NOT_CONNECTED, kind="warn", body=BODY_NOT_CONNECTED)
        if can_connect:
            card.update(why=WHY_CONNECT, buttons=[_connect_button(BTN_CONNECT, "primary")])
        else:
            card.update(why=BODY_NO_WEB, buttons=_support_button(state))
    else:  # managed: a provider FluxWorks configured in the environment
        card.update(state_word=WORD_CONNECTED, title=PROVIDER_NAMES.get(provider, provider.title()),
                    body=f"{BODY_CONNECTED.format(name=name)} {BODY_MANAGED}")
        card["buttons"] = _support_button(state)
    return card


def picker(state, view: dict | None = None) -> dict | None:
    """The calendar picker, only while Google is connected; None otherwise."""
    view = view or _settings().calendar_status(state)
    if view["provider"] != "google" or view["status"] != "ready":
        return None
    current = view.get("calendar_id") or ""
    choices = [{"id": entry["id"], "name": entry.get("summary") or entry["id"], "in_use": entry["id"] == current,
                "main": bool(entry.get("primary"))} for entry in _settings().calendar_choices(state)]
    return {"legend": PICKER_LEGEND, "hint": PICKER_HINT, "choices": choices, "main_suffix": PICKER_MAIN,
            "pill": PICKER_PILL, "button": PICKER_BUTTON, "error": PICKER_ERROR,
            "only": PICKER_ONLY if len(choices) == 1 else ""}


def _supported(state, status: str) -> bool:
    return status == "none" or hasattr(state.calendar, "busy_intervals")


def _within_hours(state, starts) -> list[datetime]:
    """Only the starts whose whole appointment lies inside the saved working hours (business zone)."""
    hours, zone, length = _hours(state), _zone(state), timedelta(minutes=_duration(state))
    kept = []
    for start in starts:
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if wh.slot_within_hours(start, start + length, hours, zone):
            kept.append(start.astimezone(zone))
    return kept


def availability_card(state, result: dict | None) -> dict:
    """What the free-times card shows: title, intro, the button or its replacement, and the result."""
    view = _settings().calendar_status(state)
    status = view["status"]
    duration = _duration(state)
    hours = _hours(state)
    test = status == "none"
    replaced = ""
    if status in ("reauth_required", "unavailable"):
        replaced = AVAIL_RECONNECT_FIRST
    elif not _supported(state, status):
        replaced = NO_CHECK
    result = result or {}
    starts = _within_hours(state, result.get("starts") or [])
    checked = bool(result.get("checked")) and not result.get("error")
    return {
        "title": AVAIL_TITLE_TEST if test else AVAIL_TITLE.format(name=calendar_name(state, view)),
        "intro": AVAIL_INTRO_TEST if test else AVAIL_INTRO.format(n=duration),
        "button": "" if replaced else AVAIL_BUTTON, "busy_label": AVAIL_BUTTON_BUSY, "replaced": replaced,
        "checked": checked, "duration": duration,
        "slots": [availability.format_slot(start, duration) for start in starts],
        "starts": starts,  # the datetimes behind ``slots``; templates format them with the `when` filter
        "empty": AVAIL_EMPTY.format(n=duration) if checked and not starts else "",
        "error": str(result.get("error") or ""),
        "caption": AVAIL_CAPTION.format(hours=wh.describe(hours)) if checked else "",
        "note": ANY_TIME_NOTE if hours is None else "",
    }


def _stub_busy(calendar, time_min: datetime, time_max: datetime) -> list[tuple[datetime, datetime]]:
    periods = list(getattr(calendar, "busy", [])) + [(e["start"], e["end"]) for e in getattr(calendar, "events", {}).values()]
    return sorted((s, e) for s, e in periods if s < time_max and e > time_min)


def check_availability(state, now: datetime) -> dict:
    """A busy read over the next HORIZON_DAYS reduced to the next three free starts inside working hours.

    Provider failures come back as ``error`` text, never as an exception; a
    paused connection is refused before any network call (fail closed).
    """
    status = _settings().calendar_status(state)["status"]
    duration = _duration(state)
    base = {"checked": False, "starts": [], "slots": [], "error": "", "empty": "", "duration": duration}
    if status in ("reauth_required", "unavailable"):
        return dict(base, error=AVAIL_RECONNECT_FIRST)
    if not _supported(state, status):
        return dict(base, error=NO_CHECK)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    window = (now, now + timedelta(days=HORIZON_DAYS))
    try:
        busy = _stub_busy(state.calendar, *window) if status == "none" else state.calendar.busy_intervals(*window)
    except CalendarProviderError:
        return dict(base, error=AVAIL_UNREACHABLE)
    starts = availability.next_free_slots(busy, now, duration, _hours(state), _zone(state), horizon_days=HORIZON_DAYS)
    starts = _within_hours(state, starts)
    return dict(base, checked=True, starts=starts,
                slots=[availability.format_slot(start, duration) for start in starts],
                empty="" if starts else AVAIL_EMPTY.format(n=duration))


def page_context(state, result: dict | None = None) -> dict:
    """Everything the Calendar template needs beyond the layout contract."""
    view = _settings().calendar_status(state)
    return {
        "card": status_card(state),
        "availability": availability_card(state, result),
        "picker": picker(state, view),
        "consent_note": CONSENT_NOTE,
        "consent_heading": CONSENT_HEADING, "consent_steps": CONSENT_STEPS,
    }
