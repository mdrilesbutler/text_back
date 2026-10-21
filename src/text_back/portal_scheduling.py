"""Scheduling page (/client/scheduling): the timing rules the engine enforces.

Appointment length, time zone, working hours, quiet hours, nudge delays and
the give-up time. Every value is a ``client_settings`` row over the env
default (app.state.defaults). Saving validates everything first (exact texts
in the IA, D.6), writes all keys in one transaction, then rebuilds the live
policy through ``client_settings.apply_scheduling``. A Reset button posts the
whole form with one group's fields swapped for their defaults (``reset_form``),
so nothing else the owner changed on the page is lost.

Only controls the engine reads are shown: duration -> booking/calendar links,
time zone -> preferred-time parsing, quiet hours/delays/expiry -> follow-ups,
working hours -> booking.book_appointment.
"""
from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from text_back import working_hours as wh


def _settings_module():
    # client_settings imports client_portal, which imports this module: resolve at call time.
    from text_back import client_settings
    return client_settings

TIMEZONES: tuple[tuple[str, str], ...] = (
    ("America/New_York", "Eastern (New York)"),
    ("America/Chicago", "Central (Chicago)"),
    ("America/Denver", "Mountain (Denver)"),
    ("America/Phoenix", "Arizona (Phoenix)"),
    ("America/Los_Angeles", "Pacific (Los Angeles)"),
    ("America/Anchorage", "Alaska"),
    ("Pacific/Honolulu", "Hawaii"),
    ("America/Puerto_Rico", "Puerto Rico"),
    ("America/Halifax", "Atlantic (Halifax)"),
    ("America/St_Johns", "Newfoundland"),
    ("America/Toronto", "Eastern (Toronto)"),
    ("America/Winnipeg", "Central (Winnipeg)"),
    ("America/Regina", "Saskatchewan (Regina)"),
    ("America/Edmonton", "Mountain (Edmonton)"),
    ("America/Vancouver", "Pacific (Vancouver)"),
    ("UTC", "UTC"),
)
DURATION_PRESETS = (30, 45, 60, 90, 120)
NUDGE1_PRESETS = (30, 60, 120, 240, 480, 1440)
NUDGE2_PRESETS = (120, 240, 1440, 2880, 4320)
EXPIRY_PRESETS = (1440, 2880, 4320, 10080)
HOUR_OPTIONS = tuple(wh.minutes_to_hhmm(m) for m in range(0, 1440, 15))
CLOSE_OPTIONS = tuple(wh.minutes_to_hhmm(m) for m in range(15, 1441, 15))
QUIET_OPTIONS = tuple(wh.minutes_to_hhmm(m) for m in range(0, 1440, 30))

ERR_DURATION = "Appointment length must be 15 to 480 minutes, in steps of 5."
ERR_TIMEZONE = "Pick a time zone from the list."
ERR_MODE = "Choose Any day, any time or Set hours."
ERR_NO_DAYS = "Set at least one open day, or choose Any day, any time."
ERR_TIMES = "Pick times from the list."
ERR_QUIET = "Pick quiet hours from the list."
ERR_NUDGES = "Nudge delays must be between 5 minutes and 14 days."
ERR_EXPIRY = "Give-up time must be between 1 hour and 30 days."
SAVED = "Saved. New conversations use these hours and delays."
RESET = "Reset to the default."
CORRUPT_HOURS = ("Saved working hours couldn't be read; the assistant is treating every time as open "
                 "until you save again.")
HOURS_HINTS = {
    "any": "Every time a caller asks for is accepted if the calendar is free.",
    "set": "Times a caller asks for outside these hours are declined. The caller is asked for another time.",
}

# Page order, used to pick the "first reason" for the top flash.
FIELD_ORDER = ("appointment_duration_minutes", "timezone", "hours_mode", "hours",
               *(f"hours_{d}" for d in wh.WEEKDAYS), "quiet_hours", "followup_delay_1", "followup_delay_2",
               "followup_expiry_minutes")

# Reset button value -> the setting keys it returns to their default.
RESET_GROUPS = {
    "appointment_duration_minutes": ("appointment_duration_minutes",),
    "timezone": ("timezone",),
    "working_hours": ("working_hours",),
    "quiet_hours": ("quiet_hours_start", "quiet_hours_end"),
    "followup_delay_1": ("followup_delays_minutes",),
    "followup_delay_2": ("followup_delays_minutes",),
    "followup_expiry_minutes": ("followup_expiry_minutes",),
}


def humanize_minutes(minutes: int) -> str:
    """120 -> '2 hours'; 1440 -> '1 day'; 90 -> '1 hour 30 minutes'; 30 -> '30 minutes'."""
    minutes = int(minutes)
    if minutes % 1440 == 0 and minutes:
        days = minutes // 1440
        return f"{days} day{'s' if days != 1 else ''}"
    if minutes % 60 == 0 and minutes:
        hours = minutes // 60
        return f"{hours} hour{'s' if hours != 1 else ''}"
    if minutes > 60:
        hours, rest = divmod(minutes, 60)
        return f"{hours} hour{'s' if hours != 1 else ''} {rest} minutes"
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def _options(presets, *extra: str) -> list[tuple[str, str]]:
    """Preset minutes plus any extra values (the current and the default) that are not presets."""
    values = list(presets)
    for raw in extra:
        try:
            if int(raw) not in values:
                values.append(int(raw))
        except (TypeError, ValueError):
            pass
    values.sort()
    return [(str(v), humanize_minutes(v)) for v in values]


def _time_options(values, current: str = "") -> list[tuple[str, str]]:
    options = list(values)
    if current and current not in options:
        options.append(current)
    return [(v, wh.format_time(v)) for v in options]


def timezone_options(current: str) -> list[tuple[str, str]]:
    options = list(TIMEZONES)
    if current and current not in {v for v, _ in options}:
        options.append((current, f"{current} (current)"))
    return options


def timezone_label(name: str) -> str:
    return dict(TIMEZONES).get(name, name)


def _split_delays(raw) -> tuple[str, str]:
    parts = [p.strip() for p in str(raw).split(",") if p.strip()]
    first = parts[0] if parts else "120"
    second = parts[1] if len(parts) > 1 else first
    return first, second


def current_values(state) -> dict:
    """What the form shows: saved values over defaults, plus the defaults for the grey lines."""
    store = state.store
    defaults = _settings_module().scheduling_defaults(state)

    def get(key):
        raw = store.setting(key)
        return str(raw) if raw not in (None, "") else str(defaults[key])

    d1, d2 = _split_delays(get("followup_delays_minutes"))
    dd1, dd2 = _split_delays(defaults["followup_delays_minutes"])
    raw_hours = store.setting("working_hours")
    hours = wh.parse_working_hours(raw_hours)
    rows = {}
    for day in wh.WEEKDAYS:
        window = (hours or wh.DEFAULT_SET_HOURS).get(day)
        rows[day] = {"on": bool(window) if hours else bool(wh.DEFAULT_SET_HOURS[day]),
                     "open": (window or {"open": "08:00"})["open"], "close": (window or {"close": "17:00"})["close"]}
    qs, qe = get("quiet_hours_start"), get("quiet_hours_end")
    dqs, dqe = str(defaults["quiet_hours_start"]), str(defaults["quiet_hours_end"])
    return {
        "appointment_duration_minutes": get("appointment_duration_minutes"),
        "timezone": get("timezone"),
        "hours_mode": "set" if hours else "any",
        "hours": rows,
        "hours_corrupt": wh.is_corrupt(raw_hours),
        "quiet_hours_start": qs, "quiet_hours_end": qe, "no_quiet_hours": qs == qe,
        "followup_delay_1": d1, "followup_delay_2": d2,
        "followup_expiry_minutes": get("followup_expiry_minutes"),
        # Control values for Reset (data-default); the display strings are under "defaults".
        "raw_defaults": {
            "appointment_duration_minutes": str(defaults["appointment_duration_minutes"]),
            "timezone": str(defaults["timezone"]),
            "quiet_hours_start": dqs, "quiet_hours_end": dqe, "no_quiet_hours": "1" if dqs == dqe else "0",
            "followup_delay_1": dd1, "followup_delay_2": dd2,
            "followup_expiry_minutes": str(defaults["followup_expiry_minutes"]),
        },
        "defaults": {
            "appointment_duration_minutes": f"{defaults['appointment_duration_minutes']} minutes",
            "timezone": timezone_label(str(defaults["timezone"])),
            "working_hours": "Any day, any time",
            "quiet_hours": "No quiet hours" if dqs == dqe else f"{wh.format_time(dqs)}–{wh.format_time(dqe)}",
            "followup_delay_1": humanize_minutes(dd1),
            "followup_delay_2": humanize_minutes(dd2),
            "followup_expiry_minutes": humanize_minutes(defaults["followup_expiry_minutes"]),
        },
    }


def parse_form(form, state) -> tuple[dict, dict]:
    """(values, errors). ``values`` is what the page re-renders; ``errors`` maps field ids to D.6 texts."""
    values = current_values(state)
    errors: dict[str, str] = {}

    def text(name, fallback=""):
        return str(form.get(name, fallback) or "").strip()

    # Appointment length
    duration_raw = text("appointment_duration_minutes")
    values["appointment_duration_minutes"] = duration_raw
    try:
        duration = int(duration_raw)
        if not (15 <= duration <= 480) or duration % 5:
            raise ValueError
    except ValueError:
        duration = None
        errors["appointment_duration_minutes"] = ERR_DURATION

    # Time zone
    tz = text("timezone")
    values["timezone"] = tz
    allowed_tz = {v for v, _ in TIMEZONES} | {current_values(state)["timezone"]}
    try:
        if tz not in allowed_tz:
            raise ZoneInfoNotFoundError(tz)
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        errors["timezone"] = ERR_TIMEZONE

    # Working hours
    mode = text("hours_mode")
    values["hours_mode"] = mode if mode in ("any", "set") else values["hours_mode"]
    if mode not in ("any", "set"):
        errors["hours_mode"] = ERR_MODE
    rows = {}
    for day in wh.WEEKDAYS:
        rows[day] = {"on": bool(form.get(f"open_{day}")),
                     "open": text(f"{day}_open", values["hours"][day]["open"]),
                     "close": text(f"{day}_close", values["hours"][day]["close"])}
    values["hours"] = rows
    hours_json = None
    if mode == "set":
        open_days = [d for d in wh.WEEKDAYS if rows[d]["on"]]
        if not open_days:
            errors["hours"] = ERR_NO_DAYS
        payload = {}
        for day in wh.WEEKDAYS:
            if not rows[day]["on"]:
                payload[day] = None
                continue
            open_t, close_t = rows[day]["open"], rows[day]["close"]
            if open_t not in HOUR_OPTIONS or close_t not in CLOSE_OPTIONS:
                errors.setdefault(f"hours_{day}", ERR_TIMES)
                continue
            open_m, close_m = wh.hhmm_to_minutes(open_t), wh.hhmm_to_minutes(close_t)
            if open_m >= close_m:
                errors.setdefault(f"hours_{day}", f"{wh.DAY_NAMES[day]}: opening time must be before closing time.")
                continue
            if duration is not None and close_m - open_m < duration:
                errors.setdefault(f"hours_{day}", f"{wh.DAY_NAMES[day]}: the hours are shorter than one appointment ({duration} minutes).")
                continue
            payload[day] = {"open": open_t, "close": close_t}
        if not errors.get("hours") and not any(k.startswith("hours_") for k in errors):
            hours_json = json.dumps(payload, separators=(",", ":"))

    # Quiet hours
    no_quiet = bool(form.get("no_quiet_hours"))
    qs, qe = text("quiet_hours_start"), text("quiet_hours_end")
    values.update(no_quiet_hours=no_quiet, quiet_hours_start=qs or values["quiet_hours_start"],
                  quiet_hours_end=qe or values["quiet_hours_end"])
    if no_quiet:
        qs = qe = "00:00"
    elif qs not in QUIET_OPTIONS or qe not in QUIET_OPTIONS:
        errors["quiet_hours"] = ERR_QUIET

    # Nudges and give-up
    delays = []
    for name in ("followup_delay_1", "followup_delay_2"):
        raw = text(name)
        values[name] = raw
        try:
            n = int(raw)
            if not (5 <= n <= 20160):
                raise ValueError
            delays.append(n)
        except ValueError:
            errors[name] = ERR_NUDGES
    expiry_raw = text("followup_expiry_minutes")
    values["followup_expiry_minutes"] = expiry_raw
    try:
        expiry = int(expiry_raw)
        if not (60 <= expiry <= 43200):
            raise ValueError
    except ValueError:
        expiry = None
        errors["followup_expiry_minutes"] = ERR_EXPIRY

    if not errors:
        values["_settings"] = {
            "appointment_duration_minutes": str(duration),
            "timezone": tz,
            "working_hours": hours_json,
            "quiet_hours_start": qs,
            "quiet_hours_end": qe,
            "followup_delays_minutes": f"{delays[0]},{delays[1]}",
            "followup_expiry_minutes": str(expiry),
        }
    return values, errors


def save(state, settings: dict, now: datetime) -> str | None:
    """Validate the policy, write every key in one transaction, rebuild. Returns an error text or None.

    A value equal to its env default is stored as no row at all, so "Reset" and
    "saved the default by hand" leave the table in the same state.
    """
    cs = _settings_module()
    try:
        cs.build_scheduling(state, settings)  # FollowupPolicy.__post_init__ runs here, before any write
    except ValueError as exc:
        return str(exc)
    defaults = cs.scheduling_defaults(state)
    with state.store.transaction():
        for key, value in settings.items():
            if value is not None and key in defaults and str(value) == str(defaults[key]):
                value = None
            state.store.set_setting(key, value, now=now)
    cs.apply_scheduling(state)
    return None


def reset_form(form, group: str, state) -> dict | None:
    """The posted form with one Reset group's fields replaced by their defaults; None for an unknown button.

    The result goes through ``parse_form`` and ``save`` like any other post, so
    the owner's other unsaved edits on the page are kept (same rule as Messages).
    """
    if group not in RESET_GROUPS:
        return None
    merged = {key: form.get(key) for key in form.keys()}
    raw = current_values(state)["raw_defaults"]
    if group == "working_hours":
        merged["hours_mode"] = "any"
    elif group == "quiet_hours":
        merged["quiet_hours_start"] = raw["quiet_hours_start"]
        merged["quiet_hours_end"] = raw["quiet_hours_end"]
        merged.pop("no_quiet_hours", None)
        if raw["no_quiet_hours"] == "1":
            merged["no_quiet_hours"] = "1"
    else:
        merged[group] = raw[group]
    return merged


def page_context(state, values: dict, errors: dict | None = None) -> dict:
    """Everything scheduling.html needs beyond the layout contract."""
    errors = errors or {}
    raw = values["raw_defaults"]
    day_rows = []
    for day in wh.WEEKDAYS:
        row = values["hours"][day]
        day_rows.append({
            "key": day, "name": wh.DAY_NAMES[day], "on": row["on"],
            "open": row["open"], "close": row["close"],
            "open_options": _time_options(HOUR_OPTIONS, row["open"]),
            "close_options": _time_options(CLOSE_OPTIONS, row["close"]),
            "error": errors.get(f"hours_{day}", ""),
        })
    return {
        "values": values,
        "errors": errors,
        "defaults": values["defaults"],
        "timezone_options": timezone_options(values["timezone"]),
        "duration_presets": [str(v) for v in DURATION_PRESETS],
        "day_rows": day_rows,
        "quiet_options": _time_options(QUIET_OPTIONS),
        "delay1_options": _options(NUDGE1_PRESETS, values["followup_delay_1"], raw["followup_delay_1"]),
        "delay2_options": _options(NUDGE2_PRESETS, values["followup_delay_2"], raw["followup_delay_2"]),
        "expiry_options": _options(EXPIRY_PRESETS, values["followup_expiry_minutes"], raw["followup_expiry_minutes"]),
        "hours_warning": CORRUPT_HOURS if values.get("hours_corrupt") else "",
        "raw_defaults": raw,
        "hours_hints": HOURS_HINTS,
    }


def first_error(errors: dict) -> str:
    for key in FIELD_ORDER:
        if errors.get(key):
            return errors[key]
    return next(iter(errors.values()), "")
