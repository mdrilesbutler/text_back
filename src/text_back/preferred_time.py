from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class PreferredTimeError(ValueError):
    """The requested time cannot be converted into one safe local instant."""


_ABSOLUTE_FORMATS = (
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %I:%M %p",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %I:%M %p",
)
_TOMORROW_RE = re.compile(
    r"^tomorrow(?:\s+at)?\s+(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<period>am|pm)$",
    re.IGNORECASE,
)


def parse_preferred_time(
    value: str,
    *,
    timezone_name: str,
    now: datetime | None = None,
) -> datetime:
    """Parse a deliberately small set of explicit customer time formats.

    The result is timezone-aware in the configured business timezone. Vague,
    past, nonexistent, and daylight-saving-ambiguous values fail closed.
    """
    try:
        business_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        raise PreferredTimeError("configured business timezone is invalid") from None

    current = now or datetime.now(business_timezone)
    if current.tzinfo is None or current.utcoffset() is None:
        raise PreferredTimeError("current time must include a timezone")
    current = current.astimezone(business_timezone)

    normalized = " ".join(value.strip().split())
    local_naive = _parse_local_naive(normalized, current)
    requested = _resolve_local_time(local_naive, business_timezone)
    if requested <= current:
        raise PreferredTimeError("requested time must be in the future")
    return requested


def _parse_local_naive(value: str, current: datetime) -> datetime:
    tomorrow_match = _TOMORROW_RE.fullmatch(value)
    if tomorrow_match:
        hour = int(tomorrow_match.group("hour"))
        minute = int(tomorrow_match.group("minute") or "0")
        period = tomorrow_match.group("period").lower()
        if hour < 1 or hour > 12 or minute > 59:
            raise PreferredTimeError("preferred time needs an explicit date and time")
        hour = hour % 12 + (12 if period == "pm" else 0)
        tomorrow = current.date() + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time()).replace(
            hour=hour,
            minute=minute,
        )

    for time_format in _ABSOLUTE_FORMATS:
        try:
            return datetime.strptime(value, time_format)
        except ValueError:
            continue
    raise PreferredTimeError("preferred time needs an explicit date and time")


def _resolve_local_time(local_naive: datetime, timezone: ZoneInfo) -> datetime:
    candidates: dict[datetime, datetime] = {}
    for fold in (0, 1):
        candidate = local_naive.replace(tzinfo=timezone, fold=fold)
        utc_instant = candidate.astimezone(UTC)
        round_trip = utc_instant.astimezone(timezone).replace(tzinfo=None)
        if round_trip == local_naive:
            candidates[utc_instant] = candidate

    if len(candidates) != 1:
        raise PreferredTimeError(
            "requested local time is invalid or ambiguous due to daylight saving time"
        )
    return next(iter(candidates.values()))
