"""Working hours: the owner's open window per weekday, enforced on every booking.

The setting ``working_hours`` (client_settings table) is JSON like
``{"mon": {"open": "08:00", "close": "17:00"}, ..., "sat": null, "sun": null}``.
Times are wall-clock in the business timezone, in 15-minute steps; ``close``
may be ``"24:00"``. A ``null`` day is closed, and so is a weekday missing from
the object (the Scheduling page always writes all seven keys). An absent or
unreadable setting, or one that closes every day, means any day, any time,
which is the behaviour before this setting existed.

``booking.book_appointment`` calls ``slot_within_hours`` before it asks the
calendar whether a slot is free, so a request outside the window is declined
exactly like a busy slot (the customer gets ``slot_unavailable`` and is asked
for another time). The retry path in booking_jobs runs the same function.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

WEEKDAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_NAMES: dict[str, str] = {
    "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
    "fri": "Friday", "sat": "Saturday", "sun": "Sunday",
}
DAY_SHORT: dict[str, str] = {d: DAY_NAMES[d][:3] for d in WEEKDAYS}
STEP_MINUTES = 15
# What the page pre-fills when the owner switches from "Any day, any time" to "Set hours".
DEFAULT_SET_HOURS: dict[str, dict | None] = {
    **{d: {"open": "08:00", "close": "17:00"} for d in WEEKDAYS[:5]},
    "sat": None, "sun": None,
}


def hhmm_to_minutes(value: str) -> int:
    """'08:30' -> 510; '24:00' -> 1440. Raises ValueError on anything else."""
    hour, minute = str(value).strip().split(":")
    hour, minute = int(hour), int(minute)
    if hour == 24 and minute == 0:
        return 1440
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"not a time: {value!r}")
    return hour * 60 + minute


def minutes_to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _valid_day(day) -> bool:
    if day is None:
        return True
    if not isinstance(day, dict):
        return False
    try:
        open_m = hhmm_to_minutes(day["open"])
        close_m = hhmm_to_minutes(day["close"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return False
    if open_m >= 1440 or open_m % STEP_MINUTES or close_m % STEP_MINUTES:
        return False
    return open_m < close_m


def parse_working_hours(raw: str | None) -> dict[str, dict | None] | None:
    """The stored JSON as {weekday: {"open", "close"} | None}, or None for "any time".

    Invalid JSON or an invalid shape also yields None (fail open to today's
    behaviour) and is logged, so a bad row can never stop bookings.
    """
    if raw is None or not str(raw).strip():
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        log.error("working_hours setting is not valid JSON; treating every time as open")
        return None
    if not isinstance(data, dict) or not set(data) <= set(WEEKDAYS) or not all(_valid_day(v) for v in data.values()):
        log.error("working_hours setting has an unexpected shape; treating every time as open")
        return None
    hours = {day: data.get(day) for day in WEEKDAYS}
    if all(v is None for v in hours.values()):
        log.error("working_hours setting closes every day; treating every time as open")
        return None
    return {day: ({"open": v["open"], "close": v["close"]} if v else None) for day, v in hours.items()}


def is_corrupt(raw: str | None) -> bool:
    """True when a stored value exists but cannot be used (the page warns about it)."""
    return raw is not None and str(raw).strip() != "" and parse_working_hours(raw) is None


def slot_within_hours(start: datetime, end: datetime, hours: dict | None, tz: ZoneInfo) -> bool:
    """True when [start, end] lies inside the open window of start's weekday in ``tz``.

    Both instants are converted to the business zone first, then compared as
    wall-clock minutes from local midnight of the start day, so a DST change
    inside the slot is handled the way a person reads the clock.
    """
    if hours is None:
        return True
    # Through UTC first: an aware datetime converted to its own zone is returned
    # unchanged, which would keep a wall-clock end that a DST change moved.
    local_start = start.astimezone(timezone.utc).astimezone(tz)
    local_end = end.astimezone(timezone.utc).astimezone(tz)
    day = hours.get(WEEKDAYS[local_start.weekday()])
    if day is None:
        return False
    open_m = hhmm_to_minutes(day["open"])
    close_m = hhmm_to_minutes(day["close"])
    start_m = local_start.hour * 60 + local_start.minute
    end_m = (local_end.date() - local_start.date()).days * 1440 + local_end.hour * 60 + local_end.minute
    if local_end.second or local_end.microsecond:
        end_m += 1  # never round a late end down into the window
    return open_m <= start_m and end_m <= close_m


def format_time(value: str) -> str:
    """'08:00' -> '8:00 AM'; '24:00' -> 'midnight'."""
    minutes = hhmm_to_minutes(value)
    if minutes == 1440:
        return "midnight"
    hour, minute = divmod(minutes, 60)
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    return f"{hour12}:{minute:02d} {suffix}"


def describe(hours: dict | None) -> str:
    """'Mon–Fri 8:00 AM–5:00 PM, Sat 9:00 AM–12:00 PM' or 'Any day, any time'."""
    if hours is None:
        return "Any day, any time"
    runs: list[tuple[list[str], dict]] = []
    for day in WEEKDAYS:
        window = hours.get(day)
        if window is None:
            continue
        if runs and runs[-1][1] == window and WEEKDAYS.index(runs[-1][0][-1]) == WEEKDAYS.index(day) - 1:
            runs[-1][0].append(day)
        else:
            runs.append(([day], window))
    parts = []
    for days, window in runs:
        label = DAY_SHORT[days[0]] if len(days) == 1 else f"{DAY_SHORT[days[0]]}–{DAY_SHORT[days[-1]]}"
        parts.append(f"{label} {format_time(window['open'])}–{format_time(window['close'])}")
    return ", ".join(parts) if parts else "Closed every day"
