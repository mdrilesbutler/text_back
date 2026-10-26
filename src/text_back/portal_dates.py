"""The one date formatter the owner portal uses. Every date on screen comes from a datetime here."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


def _local(value: datetime | str, tz_name: str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("portal dates need an aware datetime")
    return value.astimezone(ZoneInfo(tz_name or "UTC"))


def _clock(local: datetime) -> str:
    return local.strftime("%I:%M %p").lstrip("0")


def when(value: datetime | str, tz_name: str, now: datetime | None = None) -> str:
    """'Fri, Oct 23, 2:40 PM'; 'Today, 2:40 PM' on the same local day; adds the year when it differs."""
    local = _local(value, tz_name)
    if now is not None:
        today = _local(now, tz_name)
        if local.date() == today.date():
            return f"Today, {_clock(local)}"
        if local.year != today.year:
            return f"{local.strftime('%a, %b')} {local.day}, {local.year}, {_clock(local)}"
    return f"{local.strftime('%a, %b')} {local.day}, {_clock(local)}"


def day(value: datetime | str, tz_name: str) -> str:
    """'Fri, Oct 23' (no clock)."""
    local = _local(value, tz_name)
    return f"{local.strftime('%a, %b')} {local.day}"


def clock(value: datetime | str, tz_name: str) -> str:
    """'2:40 PM'."""
    return _clock(_local(value, tz_name))
