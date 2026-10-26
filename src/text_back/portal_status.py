"""Home page truth: is TextBack working, what is left to set up, and this week in one window.

Every word here comes from real state: the calendar connection, the forwarding checks
(portal_forwarding), the texting approval (portal_registry) and the ledgers. The counts and the
caller rows always cover the same window, so a zero never sits above rows.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from text_back.client_settings import calendar_status
from text_back.policy import format_contact_number
from text_back.portal_dates import day, when
from text_back.portal_forwarding import checklist
from text_back.portal_registry import approval_words, texting_approval

E164 = re.compile(r"^\+\d{8,15}$")
SNIPPET_MAX = 60

# Caller status words, first match wins (copy deck home_caller_status).
STATUS_STOPPED = "Asked us to stop"
STATUS_STEPPED_BACK = "Assistant stepped back"
STATUS_BOOKED = "Booked"
STATUS_BOOKED_TEST = "Booked on test calendar"
STATUS_NO_REPLY = "No reply"
STATUS_WAITING = "Waiting for a reply"
STATUS_TEXTING = "Texting"


def week_start(tz_name: str, now: datetime) -> datetime:
    local = now.astimezone(ZoneInfo(tz_name or "UTC"))
    return (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def _parse(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        value = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _calendar_name(state, view: dict) -> str:
    for entry in json.loads(state.store.setting("calendar_choices") or "[]") if view.get("calendar_id") else []:
        if entry.get("id") == view["calendar_id"]:
            return entry.get("summary") or entry["id"]
    return view.get("calendar_id") or "your calendar"


def setup_items(state, now: datetime) -> list[dict]:
    """One card per setup item: key, title, state_word, detail, action_label, action_href."""
    items = []
    view = calendar_status(state)
    status = view["status"]
    if status == "ready" or (status == "managed" and view["provider"] != "stub"):
        items.append(dict(key="calendar", title="Calendar", state_word="Done",
                          detail=f"Bookings go on {_calendar_name(state, view)}.",
                          action_label="Open Calendar", action_href="/client/calendar"))
    elif status == "reauth_required":
        items.append(dict(key="calendar", title="Calendar", state_word="Needs you",
                          detail="Google disconnected the calendar. Bookings are paused until you reconnect.",
                          action_label="Reconnect", action_href="/client/calendar"))
    else:
        items.append(dict(key="calendar", title="Calendar", state_word="Needs you",
                          detail=("No calendar of yours yet. Until you connect one, bookings go on a test calendar you can't see."
                                  if status == "none" else "No calendar yet. Nothing can be booked until you connect one."),
                          action_label="Connect calendar" if view.get("can_connect") else "Open Calendar",
                          action_href="/client/calendar"))
    checks = checklist(state, now)
    if checks["all_done"]:
        first = next(s for s in checks["steps"] if s["n"] == 1)
        items.append(dict(key="forwarding", title="Call forwarding", state_word="Done",
                          detail=first["evidence"], action_label="Open Phone", action_href="/client/phone"))
    else:
        items.append(dict(key="forwarding", title="Call forwarding", state_word="Needs you",
                          detail=f"{checks['done_count']} of {checks['total']} checks done.",
                          action_label="Finish forwarding", action_href="/client/phone"))
    approval = approval_words(texting_approval(state, now))
    items.append(dict(key="approval", title="Texting approval", state_word=approval["state_word"],
                      detail=approval["detail"], action_label=None, action_href=None))
    return items


def headline(items: list[dict]) -> str:
    """The first line of Home, from the setup cards only.

    Every "Needs you" card (a turned-down texting approval included) is a step left; any other
    card that is not Done ("Waiting on phone companies", "Not started", "Couldn't check") reads
    as waiting on the phone companies."""
    needs_you = [i for i in items if i["state_word"] == "Needs you"]
    if needs_you:
        n = len(needs_you)
        return f"Not working yet: {n} step{'s' if n != 1 else ''} left."
    if any(i["state_word"] != "Done" for i in items):
        return "Set up on your side. Waiting on the phone companies to approve texting."
    return "Working: missed calls get a text within a minute."


def caller_status(store, phone: str, *, test_calendar: bool = False) -> str:
    with store.lock:
        conn = store.conn
        if conn.execute("SELECT 1 FROM contacts WHERE phone=? AND opted_out=1", (phone,)).fetchone():
            return STATUS_STOPPED
        if conn.execute("SELECT 1 FROM handoffs WHERE phone=? AND status='active'", (phone,)).fetchone():
            return STATUS_STEPPED_BACK
        if conn.execute("SELECT 1 FROM appointments WHERE conversation_id=?", (phone,)).fetchone():
            return STATUS_BOOKED_TEST if test_calendar else STATUS_BOOKED
        types = {row[0] for row in conn.execute("SELECT DISTINCT event_type FROM outcome_events WHERE lead_id=?", (phone,))}
        expired = conn.execute("SELECT 1 FROM followups WHERE phone=? AND status='expired'", (phone,)).fetchone()
    if expired or "lead.expired" in types:
        return STATUS_NO_REPLY
    if "sms.customer_replied" in types:
        return STATUS_TEXTING
    return STATUS_WAITING


def _snippet(text: str) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= SNIPPET_MAX else flat[: SNIPPET_MAX - 1].rstrip() + "…"


def this_week(state, now: datetime) -> dict:
    """Counts and caller rows for [Monday 00:00 local, now]: the SAME window for both."""
    store = state.store
    tz_name = getattr(state, "timezone_name", "UTC")
    start = week_start(tz_name, now)
    counts = {"missed_calls": 0, "customers_texted": 0, "booked": 0, "stepped_back": 0}
    wanted = {"call.missed": "missed_calls", "calendar.event_created": "booked", "lead.handoff_requested": "stepped_back"}
    texted: set[str] = set()
    activity: dict[str, dict] = {}
    # Stamps are written as datetime.isoformat() of an aware UTC time ("...+00:00"), which sorts
    # as text in time order, so SQLite narrows each table to the window. The floor sits one day
    # early so a stamp written with any other offset (at most 14 hours away) is still read; the
    # exact [start, now] check below then decides, as before.
    floor = (start.astimezone(timezone.utc) - timedelta(days=1)).isoformat()
    with store.lock:
        events = store.conn.execute(
            "SELECT lead_id, event_type, occurred_at FROM outcome_events WHERE occurred_at >= ?", (floor,)).fetchall()
        outbound = store.conn.execute(
            "SELECT phone, body, created_at FROM sms_outbox WHERE status='sent' AND kind<>'login_code' AND created_at >= ?",
            (floor,)).fetchall()
        inbound = store.conn.execute(
            "SELECT phone, params_json, received_at FROM inbound_jobs WHERE kind='sms' AND received_at >= ?", (floor,)).fetchall()

    def touch(phone, at, text=""):
        if not phone or not E164.match(phone):
            return
        entry = activity.setdefault(phone, {"last_at": at, "snippet": "", "snippet_at": None})
        entry["last_at"] = max(entry["last_at"], at)
        if text and (entry["snippet_at"] is None or at >= entry["snippet_at"]):
            entry["snippet"], entry["snippet_at"] = _snippet(text), at

    for phone, event_type, occurred_at in events:
        at = _parse(occurred_at)
        if at is None or not (start <= at <= now):
            continue
        if event_type in wanted:
            counts[wanted[event_type]] += 1
        touch(phone, at)
    for phone, body, created_at in outbound:
        at = _parse(created_at)
        if at is None or not (start <= at <= now):
            continue
        texted.add(phone); touch(phone, at, body)
    for phone, params_json, received_at in inbound:
        at = _parse(received_at)
        if at is None or not (start <= at <= now):
            continue
        try:
            text = str(json.loads(params_json or "{}").get("body", ""))
        except ValueError:
            text = ""
        touch(phone, at, text)
    counts["customers_texted"] = len(texted)
    # Preview harnesses mark their seeded callers; production never sets these, so nothing is tagged there.
    examples = set(getattr(state, "preview_example_phones", ()) or ())
    test_calendar = getattr(getattr(state, "calendar", None), "provider_name", "stub") == "stub"
    rows = []
    for phone, entry in sorted(activity.items(), key=lambda item: item[1]["last_at"], reverse=True):
        with store.lock:
            name_row = store.conn.execute("SELECT value FROM conversation_fields WHERE phone=? AND field='name'", (phone,)).fetchone()
        name = (name_row[0] if name_row else "").strip()
        rows.append({"phone": phone, "name": name, "display": name or format_contact_number(phone),
                     "status": caller_status(store, phone, test_calendar=test_calendar),
                     "example": phone in examples, "last_at": entry["last_at"],
                     "last_label": when(entry["last_at"], tz_name, now), "snippet": entry["snippet"]})
    return {"start": start, "since_label": day(start, tz_name), "counts": counts, "rows": rows,
            "example": bool(examples) and any(r["example"] for r in rows)}
