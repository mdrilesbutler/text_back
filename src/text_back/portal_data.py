"""Read-only queries behind the owner portal's Home page.

Everything here reads the existing ledgers (outcome_events, sms_outbox,
inbound_jobs, conversation_fields, contacts, handoffs, appointments,
followups) and derives what the owner sees. Nothing is written, nothing is
cached, and status is never stored, so it cannot drift from the ledgers.

Timestamps are ISO strings with offsets; they are parsed in Python like
brief.py does instead of being compared as strings across offsets.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from text_back.policy import format_contact_number

REGISTRATION_DIR_ENV = "TEXT_BACK_REGISTRATION_DIR"
REGISTRATION_DIR_DEFAULT = "~/.config/text_back/registration"
E164 = re.compile(r"^\+[1-9]\d{7,14}$")
SNIPPET_MAX = 60


def _parse(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        parsed = datetime.fromisoformat(str(stamp))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _tz(tz_name: str):
    try:
        return ZoneInfo(tz_name or "UTC")
    except Exception:  # noqa: BLE001 - an unknown zone must not break Home
        return timezone.utc


def week_start(tz_name: str, now: datetime) -> datetime:
    """Monday 00:00 of the current week in the business timezone (aware)."""
    local = now.astimezone(_tz(tz_name))
    monday = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return monday


def week_counts(store, tz_name: str, now: datetime) -> dict[str, int]:
    """This week's numbers: missed calls, texts sent, booked, handed off."""
    start = week_start(tz_name, now)
    counts = {"missed_calls": 0, "texts_sent": 0, "booked": 0, "handed_off": 0}
    wanted = {"call.missed": "missed_calls", "calendar.event_created": "booked", "lead.handoff_requested": "handed_off"}
    with store.lock:
        events = store.conn.execute(
            "SELECT event_type, occurred_at FROM outcome_events WHERE event_type IN (?,?,?)", tuple(wanted)
        ).fetchall()
        texts = store.conn.execute(
            "SELECT created_at FROM sms_outbox WHERE status='sent' AND kind<>'login_code'"
        ).fetchall()
    for event_type, occurred_at in events:
        when = _parse(occurred_at)
        if when is not None and start <= when <= now:
            counts[wanted[event_type]] += 1
    for (created_at,) in texts:
        when = _parse(created_at)
        if when is not None and start <= when <= now:
            counts["texts_sent"] += 1
    return counts


# --- conversation status (IA G.2; first match wins) ----------------------------

STATUS_OPTED_OUT = ("neutral", "Opted out")
STATUS_HANDED_OFF = ("warn", "Handed off")
STATUS_BOOKED = ("ok", "Booked")
STATUS_EXPIRED = ("neutral", "Expired")
STATUS_QUALIFIED = ("info", "Qualified")
STATUS_IN_PROGRESS = ("info", "In progress")
STATUS_NEW = ("neutral", "New")


def conversation_status(store, phone: str) -> tuple[str, str]:
    """(pill kind, word) for one caller, derived from the ledgers at read time."""
    with store.lock:
        conn = store.conn
        if conn.execute("SELECT 1 FROM contacts WHERE phone=? AND opted_out=1", (phone,)).fetchone():
            return STATUS_OPTED_OUT
        if conn.execute("SELECT 1 FROM handoffs WHERE phone=? AND status='active'", (phone,)).fetchone():
            return STATUS_HANDED_OFF
        if conn.execute("SELECT 1 FROM appointments WHERE conversation_id=?", (phone,)).fetchone():
            return STATUS_BOOKED
        types = {row[0] for row in conn.execute(
            "SELECT DISTINCT event_type FROM outcome_events WHERE lead_id=?", (phone,))}
        expired = conn.execute("SELECT 1 FROM followups WHERE phone=? AND status='expired'", (phone,)).fetchone()
    if expired or "lead.expired" in types:
        return STATUS_EXPIRED
    if "lead.qualified" in types:
        return STATUS_QUALIFIED
    if "sms.customer_replied" in types:
        return STATUS_IN_PROGRESS
    return STATUS_NEW


def relative_label(when: datetime, now: datetime, tz_name: str) -> str:
    """'Today 3:02 PM', a weekday within the last 7 days, else 'Oct 12'."""
    zone = _tz(tz_name)
    local, today = when.astimezone(zone), now.astimezone(zone)
    clock = local.strftime("%I:%M %p").lstrip("0")
    if local.date() == today.date():
        return f"Today {clock}"
    if local.date() == (today - timedelta(days=1)).date():
        return f"Yesterday {clock}"
    if 0 <= (today.date() - local.date()).days < 7:
        return f"{local.strftime('%A')} {clock}"
    return local.strftime("%b %d").replace(" 0", " ")


def _snippet(text: str) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= SNIPPET_MAX else flat[: SNIPPET_MAX - 1].rstrip() + "…"


def recent_conversations(store, limit: int = 10, now: datetime | None = None, tz_name: str = "UTC") -> list[dict]:
    """Latest ``limit`` callers across inbound texts, outbound texts and events.

    Each row: phone, display (name or formatted number), name, status
    (kind, word), last_at, last_label, snippet.
    """
    now = now or datetime.now(timezone.utc)
    with store.lock:
        rows = store.conn.execute(
            "SELECT phone, received_at AS ts, params_json AS body, 'in' AS src FROM inbound_jobs WHERE kind='sms' "
            "UNION ALL SELECT phone, created_at, body, 'out' FROM sms_outbox WHERE kind<>'login_code' "
            "UNION ALL SELECT lead_id, occurred_at, '', 'event' FROM outcome_events"
        ).fetchall()
    latest: dict[str, dict] = {}
    for phone, ts, body, src in rows:
        if not phone or not E164.match(phone):
            continue
        when = _parse(ts)
        if when is None:
            continue
        text = ""
        if src == "in":
            try:
                text = str(json.loads(body or "{}").get("body", ""))
            except ValueError:
                text = ""
        elif src == "out":
            text = str(body or "")
        entry = latest.setdefault(phone, {"last_at": when, "snippet": "", "snippet_at": None})
        if when > entry["last_at"]:
            entry["last_at"] = when
        if text and (entry["snippet_at"] is None or when >= entry["snippet_at"]):
            entry["snippet"], entry["snippet_at"] = _snippet(text), when
    ordered = sorted(latest.items(), key=lambda item: item[1]["last_at"], reverse=True)[:limit]
    out = []
    for phone, entry in ordered:
        with store.lock:
            name_row = store.conn.execute(
                "SELECT value FROM conversation_fields WHERE phone=? AND field='name'", (phone,)).fetchone()
        name = (name_row[0] if name_row else "").strip()
        out.append({
            "phone": phone,
            "name": name,
            "display": name or format_contact_number(phone),
            "status": conversation_status(store, phone),
            "last_at": entry["last_at"],
            "last_label": relative_label(entry["last_at"], now, tz_name),
            "snippet": entry["snippet"],
        })
    return out


# --- messaging registration (read-only, staged responses on disk) ---------------

def registration_dir() -> Path:
    return Path(os.environ.get(REGISTRATION_DIR_ENV) or REGISTRATION_DIR_DEFAULT).expanduser()


def _read_state(path: Path) -> str | None:
    """Lowercased ``state`` from a staged response, '' when the file has none, None when unreadable."""
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if isinstance(data, dict):
        state = data.get("state") or data.get("status") or ""
        return str(state).lower()
    return ""


def registration_status(directory: str | os.PathLike | None = None) -> dict | None:
    """Stage of 10DLC registration from the staged responses, or None if unreadable.

    None means the directory is missing or cannot be read; the Home card is then
    omitted entirely. Otherwise: {"stage", "headline", "detail", "state", "complete"}.
    """
    base = Path(directory).expanduser() if directory is not None else registration_dir()
    try:
        if not base.is_dir():
            return None
        present = {name: (base / f"{name}-response.json").is_file() for name in ("brand", "campaign", "order")}
    except OSError:
        return None
    states = {name: _read_state(base / f"{name}-response.json") for name, ok in present.items() if ok}
    complete = present["order"] and states.get("order") in ("complete", "completed", "approved", "assigned")
    if complete:
        stage, headline = "registered", "Registered"
    elif present["order"]:
        stage, headline = "order", "Number assigned"
    elif present["campaign"]:
        stage, headline = "campaign", "Campaign in review"
    elif present["brand"]:
        stage, headline = "brand", "Brand submitted"
    else:
        stage, headline = "none", "Registration not started"
    latest = next((states[name] for name in ("order", "campaign", "brand") if states.get(name)), "")
    detail = ("Texts go out without a carrier tag." if complete
              else "Texts carry a “[SignalWire Free Trial]” tag until registration completes.")
    return {"stage": stage, "headline": headline, "detail": detail, "state": latest, "complete": bool(complete)}


# --- forwarding checklist (IA F.6) ----------------------------------------------

def _last4(number: str) -> str:
    digits = re.sub(r"\D", "", number or "")
    return f"(•••) •••-{digits[-4:]}" if len(digits) >= 4 else "a hidden number"


def _stamp(when: datetime | None, tz_name: str) -> str:
    if when is None:
        return ""
    local = when.astimezone(_tz(tz_name))
    return f"{local.strftime('%b %d').replace(' 0', ' ')}, {local.strftime('%I:%M %p').lstrip('0')}"


def forwarding_checklist(state) -> dict:
    """Five onboarding checks; 1, 2 and 4 from recorded evidence, 3 and 5 from manual ticks."""
    store = state.store
    tz_name = getattr(state, "timezone_name", "UTC")
    business_line = (store.setting("business_line") or "").strip()
    text_back_number = (store.setting("text_back_number") or getattr(state, "business_number", "") or "").strip()
    excluded = {n for n in (business_line, text_back_number) if n}
    try:
        manual = json.loads(store.setting("forwarding_checklist") or "{}")
    except ValueError:
        manual = {}
    if not isinstance(manual, dict):
        manual = {}

    probe = None
    with store.lock:
        for row in store.conn.execute(
                "SELECT lead_id, evidence_id, occurred_at FROM outcome_events WHERE event_type='call.missed' ORDER BY id DESC"):
            if row["lead_id"] not in excluded:
                probe = dict(row)
                break
        sent_at = voice_from = None
        if probe:
            sid = probe["evidence_id"]
            initial = store.conn.execute(
                "SELECT occurred_at FROM outcome_events WHERE event_type='sms.initial_sent' AND idempotency_key=?",
                (f"call:{sid}:initial_sms",)).fetchone()
            intro = store.conn.execute(
                "SELECT status FROM sms_outbox WHERE key=?", (f"{sid}:intro",)).fetchone()
            if initial and intro and intro["status"] == "sent":
                sent_at = _parse(initial["occurred_at"])
            voice = store.conn.execute("SELECT params_json FROM inbound_jobs WHERE key=?", (f"voice:{sid}",)).fetchone()
            if voice:
                try:
                    voice_from = str(json.loads(voice["params_json"]).get("from_number", ""))
                except ValueError:
                    voice_from = None

    steps = []
    probe_at = _parse(probe["occurred_at"]) if probe else None
    steps.append({"n": 1, "label": "A test call rang through", "done": probe is not None, "manual": False,
                  "evidence": f"{_stamp(probe_at, tz_name)} from {_last4(probe['lead_id'])}" if probe else ""})
    steps.append({"n": 2, "label": "Exactly one text went out", "done": sent_at is not None, "manual": False,
                  "evidence": f"Sent {_stamp(sent_at, tz_name)}" if sent_at else ""})
    ticked = manual.get("answered_no_text")
    steps.append({"n": 3, "label": "An answered call sent no text", "done": bool(ticked), "manual": True,
                  "evidence": f"Ticked {_stamp(_parse(ticked), tz_name)}" if ticked else ""})
    caller_ok = bool(business_line) and bool(voice_from) and voice_from not in excluded
    steps.append({"n": 4, "label": "Caller ID came through", "done": caller_ok, "manual": False,
                  "evidence": (f"From {_last4(voice_from)}, not your business number" if caller_ok
                               else ("" if business_line else "Enter your business number first."))})
    saved = manual.get("deactivation_saved")
    steps.append({"n": 5, "label": "Turn-off code saved", "done": bool(saved), "manual": True,
                  "evidence": f"Ticked {_stamp(_parse(saved), tz_name)}" if saved else ""})
    done_count = sum(1 for step in steps if step["done"])
    return {"steps": steps, "done_count": done_count, "verified": done_count == len(steps)}
