"""Next free appointment slots, computed from a calendar's busy list.

Pure: no I/O. The Calendar page's "Check availability now" reads the busy
periods for the coming two weeks through the provider's ``busy_intervals``
and asks this module for the first few starts that
- begin on a step boundary after ``now`` (never ``now`` itself),
- fit the appointment length inside the owner's working hours
  (``working_hours.slot_within_hours``, the same rule booking enforces), and
- do not overlap any busy period.

Candidates advance in UTC so a daylight-saving change on the way never
produces a wall-clock time that does not exist; results are returned in the
business zone for display.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable
from zoneinfo import ZoneInfo

from text_back.working_hours import slot_within_hours


def _zone(tz_name) -> ZoneInfo:
    if isinstance(tz_name, ZoneInfo):
        return tz_name
    try:
        return ZoneInfo(str(tz_name or "UTC"))
    except Exception:  # noqa: BLE001 - an unknown zone must not break the page
        return ZoneInfo("UTC")


def _ceil_to_step(local: datetime, step_minutes: int) -> datetime:
    """The first step boundary at or after ``local`` (wall clock in its zone)."""
    base = local.replace(second=0, microsecond=0)
    minutes = base.hour * 60 + base.minute
    rounded = -(-minutes // step_minutes) * step_minutes
    if base < local:
        rounded = minutes // step_minutes * step_minutes + step_minutes
    day = base.replace(hour=0, minute=0)
    return day + timedelta(minutes=rounded)


def next_free_slots(busy: Iterable[tuple[datetime, datetime]], now: datetime, duration_minutes: int,
                    working_hours: dict | None, tz_name, *, count: int = 3, step_minutes: int = 30,
                    horizon_days: int = 14) -> list[datetime]:
    """Up to ``count`` aware start times in the business zone, earliest first."""
    if duration_minutes <= 0 or count <= 0 or step_minutes <= 0:
        return []
    zone = _zone(tz_name)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    periods = [(s.astimezone(timezone.utc), e.astimezone(timezone.utc)) for s, e in busy]
    local_now = now.astimezone(zone)
    first = _ceil_to_step(local_now, step_minutes)
    if first <= local_now:
        first = first + timedelta(minutes=step_minutes)
    cursor = first.astimezone(timezone.utc)
    limit = now.astimezone(timezone.utc) + timedelta(days=horizon_days)
    step = timedelta(minutes=step_minutes)
    length = timedelta(minutes=duration_minutes)
    out: list[datetime] = []
    while cursor < limit and len(out) < count:
        end = cursor + length
        if slot_within_hours(cursor, end, working_hours, zone) and not any(cursor < b_end and end > b_start for b_start, b_end in periods):
            out.append(cursor.astimezone(zone))
        cursor += step
    return out


def format_slot(start: datetime, duration_minutes: int) -> str:
    """'Thu, Oct 23 · 4:00–5:00 PM' (or '11:30 AM–12:30 PM' across noon)."""
    end = start + timedelta(minutes=duration_minutes)
    day = start.strftime("%a, %b %d").replace(" 0", " ")
    start_clock = start.strftime("%I:%M").lstrip("0")
    end_clock = end.strftime("%I:%M %p").lstrip("0")
    if start.strftime("%p") == end.strftime("%p") and end.date() == start.date():
        return f"{day} · {start_clock}–{end_clock}"
    return f"{day} · {start_clock} {start.strftime('%p')}–{end_clock}"
