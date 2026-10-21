"""Calendar page helpers: the connection state card, the picker, and the live
availability check. Routes live in client_settings.install_routes.

Nothing here writes: connecting and picking a calendar go through the
existing client_settings helpers, and "Check availability now" only reads
``busy_intervals`` for the next two weeks and feeds ``availability``.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from text_back import availability
from text_back.calendars.protocol import CalendarProviderError
from text_back.working_hours import parse_working_hours

HORIZON_DAYS = 14
CONNECT = "Connect Google Calendar"
RECONNECT = "Reconnect Google Calendar"
NOT_TURNED_ON = "Connecting a calendar from this page isn't turned on yet."
CONNECT_REFUSED = "Connecting a calendar is not set up for this account yet."
PICK_ONE = "Pick one of the calendars listed."
RECONNECT_FIRST = "Reconnect first."
NO_CHECK = "Availability check isn't available for this calendar yet."
UNREACHABLE = "Couldn't reach {name}. Try again in a minute."
NO_SLOTS = "No free {n}-minute slot in the next 14 days inside your working hours."
CONSENT_NOTE = "Google will ask you to pick the account that owns your calendar and allow access. Nothing else in that account is read."
PROVIDER_NAMES = {"google": "Google Calendar", "microsoft": "Outlook / Microsoft 365", "icloud": "iCloud"}
MANAGED_NAMES = {"google": "Google", "microsoft": "Microsoft 365", "icloud": "iCloud"}
REQUEST_CARDS = (
    {"key": "microsoft", "name": "Outlook / Microsoft 365",
     "body": "Available on request. text_back can book on Outlook.com and Microsoft 365 calendars."},
    {"key": "icloud", "name": "iCloud",
     "body": "Available on request. text_back can book on an iCloud calendar."},
)


def _settings():
    from text_back import client_settings  # circular at import time

    return client_settings


def status_card(state) -> dict:
    """Headline (icon + word), body, button and picker data for the provider card (IA E.1)."""
    settings = _settings()
    view = settings.calendar_status(state)
    choices = settings.calendar_choices(state)
    names = {entry["id"]: entry.get("summary") or entry["id"] for entry in choices}
    current = view["calendar_id"]
    provider, status, can_connect = view["provider"], view["status"], view["can_connect"]
    card = {
        "provider": provider, "status": status, "can_connect": can_connect,
        "current_id": current, "current_name": names.get(current, current) or "your calendar",
        "choices": choices, "show_picker": provider == "google" and status == "ready" and len(choices) > 1,
        "button": "", "button_variant": "primary", "note": "", "consent_note": CONSENT_NOTE,
    }
    if status == "none":
        card.update(kind="neutral", icon="info", word="Test calendar", title="Test calendar",
                    body="No real calendar is connected. Bookings aren't recorded anywhere yet.")
    elif status == "ready":
        card.update(kind="ok", icon="check", word="Connected", title="Google Calendar", body="")
    elif status == "reauth_required":
        card.update(kind="err", icon="x", word="Disconnected", title="Google Calendar",
                    body="Google has disconnected the calendar. Bookings are paused until you reconnect.")
    elif status == "unavailable":
        card.update(kind="err", icon="x", word="Can't be read", title="Google Calendar",
                    body="The calendar connection could not be read. Reconnect to resume bookings.")
    else:  # managed
        card.update(kind="ok", icon="check", word="Connected", title=PROVIDER_NAMES.get(provider, provider.title()),
                    body=f"Your {MANAGED_NAMES.get(provider, provider.title())} calendar is connected and managed for you.")
    if status in ("none", "ready", "reauth_required", "unavailable"):
        if can_connect:
            card["button"] = RECONNECT if status == "ready" else CONNECT
            card["button_variant"] = "secondary" if status == "ready" else "primary"
        elif status != "ready":
            card["note"] = NOT_TURNED_ON
    return card


def calendar_name(state, view: dict | None = None) -> str:
    """The calendar the check read: its picked name on Google, the provider name when managed, else "Test calendar"."""
    settings = _settings()
    view = view or settings.calendar_status(state)
    if view["status"] == "none":
        return "Test calendar"
    if view["provider"] == "google":
        names = {entry["id"]: entry.get("summary") or entry["id"] for entry in settings.calendar_choices(state)}
        return names.get(view["calendar_id"], view["calendar_id"]) or "Google Calendar"
    return PROVIDER_NAMES.get(view["provider"], "your calendar")


def availability_card(state, result: dict | None) -> dict:
    """What the 'Next free times' card shows: the button, a replacement line, or results."""
    settings = _settings()
    view = settings.calendar_status(state)
    status = view["status"]
    supported = hasattr(state.calendar, "busy_intervals")
    duration = int(getattr(state, "appointment_duration_minutes", 60))
    show_button = supported and status in ("none", "ready", "managed")
    replaced = ""
    if status in ("reauth_required", "unavailable"):
        replaced = RECONNECT_FIRST
    elif not supported:
        replaced = NO_CHECK
    caption = (f"Checked just now · next {HORIZON_DAYS} days on {calendar_name(state, view)} · "
               f"{duration}-minute slots inside your working hours")
    return {
        "show_button": show_button, "replaced": replaced, "result": result, "duration": duration,
        "lead": f"Lists the first three free {duration}-minute slots in the next 14 days, inside your working hours.",
        "caption": caption,
    }


def check_availability(state, now: datetime) -> dict:
    """A real busy read over the next 14 days, reduced to the next three free slots.

    Provider failures come back as ``error`` text for the card, never as an exception.
    """
    settings = _settings()
    status = settings.calendar_status(state)["status"]
    duration = int(getattr(state, "appointment_duration_minutes", 60))
    provider = getattr(state.calendar, "provider_name", "stub")
    name = PROVIDER_NAMES.get(provider, "the calendar")
    base = {"slots": [], "error": "", "empty": "", "checked": False, "duration": duration}
    if status in ("reauth_required", "unavailable"):
        return dict(base, error=RECONNECT_FIRST)
    if not hasattr(state.calendar, "busy_intervals"):
        return dict(base, error=NO_CHECK)
    try:
        busy = state.calendar.busy_intervals(now, now + timedelta(days=HORIZON_DAYS))
    except CalendarProviderError:
        return dict(base, error=UNREACHABLE.format(name=name))
    hours = parse_working_hours(state.store.setting("working_hours"))
    starts = availability.next_free_slots(busy, now, duration, hours, getattr(state, "timezone_name", "UTC"))
    return dict(base, checked=True, slots=[availability.format_slot(start, duration) for start in starts],
                empty="" if starts else NO_SLOTS.format(n=duration))


def page_context(state, result: dict | None = None) -> dict:
    """Everything calendar.html needs beyond the layout contract."""
    card = status_card(state)
    return {
        "card": card,
        "availability": availability_card(state, result),
        "request_cards": [dict(entry) for entry in REQUEST_CARDS if entry["key"] != card["provider"]],
    }
