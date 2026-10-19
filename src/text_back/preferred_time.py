from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class PreferredTimeError(ValueError):
    """The requested time cannot be converted into one safe local instant."""


# Customers answer "when?" the way they talk. The grammar below is deliberately
# deterministic: one date part (today, tomorrow, a weekday, a month/day, a
# numeric date) plus one clock time. Vague answers ("tomorrow afternoon",
# "next week") still fail closed so the conversation re-prompts.

_WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2, "weds": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}
_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_WEEKDAY_ALT = "|".join(sorted(_WEEKDAYS, key=len, reverse=True))
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))

_DATE_RE = re.compile(
    r"\b(?:"
    r"(?P<today>today|tonight)"
    r"|(?P<tomorrow>tomorrow|tomorow|tmrw|tmw|tmr)"
    r"|(?:(?P<rel>this|next)\s+)?(?P<weekday>" + _WEEKDAY_ALT + r")"
    r"|(?P<month>" + _MONTH_ALT + r")\.?\s+(?P<mday>\d{1,2})(?:st|nd|rd|th)?(?:\s+(?P<year>\d{4}))?"
    r"|(?P<mday2>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month2>" + _MONTH_ALT + r")\.?(?:\s+(?P<year2>\d{4}))?"
    r"|(?P<iso>\d{4}-\d{2}-\d{2})"
    r"|(?P<nmonth>\d{1,2})/(?P<nday>\d{1,2})(?:/(?P<nyear>\d{4}|\d{2}))?"
    r")\b",
    re.IGNORECASE,
)
_TIME_RE = re.compile(
    r"^(?:"
    r"(?P<noon>noon|midday)"
    r"|(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<period>am|pm|a\.m\.|p\.m\.|a|p)?"
    r")$",
    re.IGNORECASE,
)
_HINT_RE = re.compile(r"\b(?:in\s+the\s+)?(?P<hint>morning|afternoon|evening)\b")
_FILLER_RE = re.compile(
    r"\b(?:please|pls|plz|thanks|thank\s+you|thx|ok|okay|if\s+possible|ideally|preferably|"
    r"works(?:\s+for\s+me)?|would\s+(?:work|be\s+(?:great|good|fine|best))|is\s+(?:good|fine|best))\b"
)
_JOINER_RE = re.compile(r"\b(?:at|on|around|about|for|sometime)\b")


def parse_preferred_time(
    value: str,
    *,
    timezone_name: str,
    now: datetime | None = None,
) -> datetime:
    """Parse a customer's requested day and clock time.

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

    local_naive = _parse_local_naive(value, current)
    requested = _resolve_local_time(local_naive, business_timezone)
    if requested <= current:
        raise PreferredTimeError("requested time must be in the future")
    return requested


def _normalize(value: str) -> str:
    text = value.strip().lower()
    text = text.replace("@", " at ").replace(",", " ")
    text = re.sub(r"\bo'?clock\b", " ", text)
    text = re.sub(r"\b(\d{1,2})\s*(a|p)\.?m\.?\b", r"\1 \2m", text)  # "2 p.m." -> "2 pm"
    text = re.sub(r"[.!?]+$", "", text)
    return " ".join(text.split())


def _parse_local_naive(value: str, current: datetime) -> datetime:
    text = _normalize(value)
    if not text:
        raise PreferredTimeError("preferred time needs an explicit date and time")

    date_match = _DATE_RE.search(text)
    if date_match is None:
        raise PreferredTimeError("preferred time needs an explicit date and time")
    remainder = text[: date_match.start()] + " " + text[date_match.end():]

    hint = None
    hint_match = _HINT_RE.search(remainder)
    if hint_match:
        hint = hint_match.group("hint")
        remainder = remainder[: hint_match.start()] + " " + remainder[hint_match.end():]
    if date_match.group("today") == "tonight" and hint is None:
        hint = "evening"

    remainder = _FILLER_RE.sub(" ", remainder)
    remainder = _JOINER_RE.sub(" ", remainder)
    remainder = " ".join(remainder.split())

    hour, minute = _parse_clock(remainder, hint)
    day = _resolve_date(date_match, current, hour, minute)
    return datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)


def _parse_clock(text: str, hint: str | None) -> tuple[int, int]:
    time_match = _TIME_RE.fullmatch(text)
    if time_match is None:
        raise PreferredTimeError("preferred time needs an explicit date and time")
    if time_match.group("noon"):
        return 12, 0
    hour = int(time_match.group("hour"))
    minute = int(time_match.group("minute") or "0")
    period = (time_match.group("period") or "").replace(".", "")[:1]  # "", "a" or "p"
    if minute > 59:
        raise PreferredTimeError("preferred time needs an explicit date and time")
    if not period and hint:
        period = "a" if hint == "morning" else "p"
    if period:
        if hour < 1 or hour > 12:
            raise PreferredTimeError("preferred time needs an explicit date and time")
        return hour % 12 + (12 if period == "p" else 0), minute
    if hour > 23:
        raise PreferredTimeError("preferred time needs an explicit date and time")
    if hour == 0:
        raise PreferredTimeError("preferred time needs an explicit date and time")
    if hour >= 13:
        return hour, minute  # explicit 24-hour clock
    # No am/pm: assume business daytime. 7-11 are morning; 12 and 1-6 afternoon.
    if hour >= 7 and hour <= 11:
        return hour, minute
    return hour % 12 + 12, minute


def _resolve_date(match: re.Match, current: datetime, hour: int, minute: int) -> date:
    today = current.date()
    if match.group("today"):
        return today
    if match.group("tomorrow"):
        return today + timedelta(days=1)
    if match.group("weekday"):
        target = _WEEKDAYS[match.group("weekday")]
        if (match.group("rel") or "").lower() == "next":
            next_week_start = today + timedelta(days=7 - today.weekday())
            return next_week_start + timedelta(days=target)
        offset = (target - today.weekday()) % 7
        candidate = today + timedelta(days=offset)
        if offset == 0 and (hour, minute) <= (current.hour, current.minute):
            candidate += timedelta(days=7)
        return candidate
    if match.group("iso"):
        try:
            return date.fromisoformat(match.group("iso"))
        except ValueError:
            raise PreferredTimeError("preferred time needs an explicit date and time") from None
    if match.group("month") or match.group("month2"):
        month = _MONTHS[(match.group("month") or match.group("month2")).lower()]
        day = int(match.group("mday") or match.group("mday2"))
        year = match.group("year") or match.group("year2")
        return _month_day(month, day, year, today)
    month = int(match.group("nmonth"))
    day = int(match.group("nday"))
    return _month_day(month, day, match.group("nyear"), today)


def _month_day(month: int, day: int, year: str | None, today: date) -> date:
    if year is not None:
        year_number = int(year) + (2000 if len(year) == 2 else 0)
        return _safe_date(year_number, month, day)
    candidate = _safe_date(today.year, month, day)
    if candidate < today:
        candidate = _safe_date(today.year + 1, month, day)
    return candidate


def _safe_date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError:
        raise PreferredTimeError("preferred time needs an explicit date and time") from None


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
