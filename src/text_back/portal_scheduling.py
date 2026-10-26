"""Schedule page (/client/schedule): the timing rules the engine enforces.

Appointment length, time zone, working hours, quiet hours, reminder delays and
the waiting time before the assistant stops. Every value is a ``client_settings``
row over the env default (app.state.defaults). Saving validates everything first
(exact texts from docs/notes/portal-c/copy-deck.md, section 5), writes all keys
in one transaction, then rebuilds the live policy through
``client_settings.apply_scheduling``. A Reset button posts the whole form with
one group's fields swapped for their defaults (``reset_form``), so nothing else
the owner changed on the page is lost.

Only controls the engine reads are shown: duration -> booking/calendar links,
time zone -> preferred-time parsing, quiet hours/delays/expiry -> follow-ups,
working hours -> booking.book_appointment. The save confirmation (``SAVED``,
built by ``saved_notice``) is pinned to that behaviour by tests/test_portal_scheduling.py.
"""
from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from text_back import working_hours as wh


def _settings_module():
    # client_settings imports client_portal; resolve at call time to keep the import graph one-way.
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
REMINDER1_PRESETS = (30, 60, 120, 240, 480, 1440)
REMINDER2_PRESETS = (120, 240, 1440, 2880, 4320)
EXPIRY_PRESETS = (1440, 2880, 4320, 10080)
HOUR_OPTIONS = tuple(wh.minutes_to_hhmm(m) for m in range(0, 1440, 15))
CLOSE_OPTIONS = tuple(wh.minutes_to_hhmm(m) for m in range(15, 1441, 15))
QUIET_OPTIONS = tuple(wh.minutes_to_hhmm(m) for m in range(0, 1440, 30))

# One-tap hours offered under the any-time warning, in the stored JSON shape.
SUGGESTED_HOURS: dict[str, dict | None] = {day: (dict(window) if window else None)
                                          for day, window in wh.DEFAULT_SET_HOURS.items()}

# --- words (copy deck, section 5; verbatim) ---------------------------------------
ERR_DURATION = "Appointment length must be 15 to 480 minutes, in steps of 5."
# Without JavaScript, a tapped chip and a typed number that disagree (m36).
ERR_DURATION_BOTH = "You tapped one length and typed another. Pick one: tap a length, or tap Custom and type the minutes."
ERR_TIMEZONE = "Pick a time zone from the list."
ERR_MODE = "Choose Any day, any time or Set hours."
ERR_NO_DAYS = "Set at least one open day, or choose Any day, any time."
ERR_TIMES = "Pick times from the list."
ERR_QUIET = "Pick quiet hours from the list."
# Equal times would silently mean "no quiet hours"; the switch is the one way to turn them off (M2).
ERR_QUIET_SAME = "Start and end can't be the same time. To turn quiet hours off, use the switch."
# The times shown under a switched-off quiet hours: the last custom pair, so Off then On brings them back (M2).
QUIET_LAST_KEY = "quiet_hours_last"
ERR_REMINDERS = "Reminder delays must be between 5 minutes and 14 days."
ERR_EXPIRY = "The waiting time must be between 1 hour and 30 days."
# The save notice names only the rules that changed (deck schedule_toast); "Saved." when none did. Then each
# changed rule's own note (APPLIES, or the reminders' consequence), word for word, so the notice never claims
# more than the card under the rule does (m10).
SAVED = "Saved. You changed “{rules}”."
SAVED_NOTHING = "Saved."
CORRUPT_HOURS = "Your saved working hours couldn't be read, so every time counts as open until you save again."
ANY_TIME_WARNING = "Customers can be offered times like 1 AM. Set your hours."
ANY_TIME_BUTTON = "Use Mon–Fri, 8 AM–5 PM"
HOURS_HINTS = {
    "any": "The assistant accepts any time a customer asks for if your calendar is free, including the middle of the night.",
    "set": "The assistant turns down times outside these hours and asks the customer for another time.",
}
# Reset group -> the rule's label (also the accessible name "Reset <label>").
LABELS = {
    "appointment_duration_minutes": "Appointment length",
    "timezone": "Time zone",
    "working_hours": "Working hours",
    "quiet_hours": "Quiet hours",
    "followup_delay_1": "If there's no reply, send a reminder after",
    "followup_delay_2": "Send the last reminder after another",
    "followup_expiry_minutes": "Stop waiting for a reply after",
}
# Under each rule BEFORE saving (deck *_applies). Each claim is pinned to engine behaviour in
# tests/test_portal_scheduling.py (test_save_confirmation_matches_live_behaviour, *_timezone_*, *_quiet_*, *_hours_*).
APPLIES = {
    "appointment_duration_minutes": "Applies right away, including customers mid-conversation.",
    "timezone": "Applies right away to the times in texts.",
    "working_hours": "Applies right away to times the assistant offers. Bookings already made stay as they are.",
    "quiet_hours": "Applies right away to reminders not yet sent.",
}
ANY_TIME_NOTE = "Sets Mon–Fri, 8 AM–5 PM below. Tap Save to keep it."
QUIET_LEGEND, QUIET_AND, QUIET_SWITCH, QUIET_OFF = "Hold reminders between", "and", "Quiet hours", "Off. Texts may go out at any hour."
DAY_WORDS = ("Open", "Closed")
CHANGED_ONE, CHANGED_MANY = "1 rule changed", "{n} rules changed"

# What changing each rule does, by field; working hours depend on the mode (HOURS_HINTS).
CONSEQUENCES = {
    "appointment_duration_minutes": "Used for new bookings. 15 to 480 minutes, in steps of 5.",
    "timezone": "Used for working hours, quiet hours and the times in texts.",
    "quiet_hours": ("Reminders and retried texts wait until quiet hours end. Still sent right away: the first text "
                    "after a missed call, replies to a customer who is texting, and the START, HELP and STOP replies."),
    "followup_delay_1": "A reminder that is already scheduled keeps its time. Later reminders use the new delays.",
    "followup_delay_2": "A reminder that is already scheduled keeps its time. Later reminders use the new delays.",
    "followup_expiry_minutes": 'Counted from the last reminder. The customer is marked "No reply" on Home.',
}

# Rule -> the element id its changed-item link points at (the header save bar and the desktop bar).
ANCHORS = {"appointment_duration_minutes": "rule-duration", "timezone": "rule-timezone", "working_hours": "working-hours",
           "quiet_hours": "quiet_hours", "followup_delay_1": "rule-followup_delay_1",
           "followup_delay_2": "rule-followup_delay_2", "followup_expiry_minutes": "rule-followup_expiry_minutes"}

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


def duration_chips(raw: str) -> tuple[list[dict], bool]:
    """Quick picks: a chip is selected iff int(field) == preset; no match means Custom."""
    try:
        current = int(str(raw).strip())
    except (TypeError, ValueError):
        current = None
    chips = [{"value": str(v), "label": f"{v} min", "selected": current == v} for v in DURATION_PRESETS]
    return chips, not any(chip["selected"] for chip in chips)


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
    # The page edits the first two reminders only; the count is the running policy's, so a
    # save never adds or drops one (1 -> only reminder 1; 3+ -> the rest are kept as they are).
    policy_delays = [int(d) for d in state.followup_policy.delays_minutes]
    raw_hours = store.setting("working_hours")
    hours = wh.parse_working_hours(raw_hours)
    rows = {}
    for day in wh.WEEKDAYS:
        window = (hours or SUGGESTED_HOURS).get(day)
        rows[day] = {"on": bool(window) if hours else bool(SUGGESTED_HOURS[day]),
                     "open": (window or {"open": "08:00"})["open"], "close": (window or {"close": "17:00"})["close"]}
    qs, qe = get("quiet_hours_start"), get("quiet_hours_end")
    dqs, dqe = str(defaults["quiet_hours_start"]), str(defaults["quiet_hours_end"])
    last = str(store.setting(QUIET_LAST_KEY) or "").split("-")
    if len(last) != 2 or last[0] == last[1] or not set(last) <= set(QUIET_OPTIONS):
        last = [dqs, dqe] if dqs != dqe else ["21:00", "08:00"]
    return {
        "appointment_duration_minutes": get("appointment_duration_minutes"),
        "timezone": get("timezone"),
        "hours_mode": "set" if hours else "any",
        "hours": rows,
        "hours_corrupt": wh.is_corrupt(raw_hours),
        "quiet_hours_start": qs, "quiet_hours_end": qe, "no_quiet_hours": qs == qe,
        "quiet_last_start": last[0], "quiet_last_end": last[1],
        "followup_delay_1": d1, "followup_delay_2": d2,
        "reminder_count": max(1, len(policy_delays)),
        "extra_delays": policy_delays[2:],
        "followup_expiry_minutes": get("followup_expiry_minutes"),
        # Control values for Reset (data-default); the display strings are under "defaults".
        "raw_defaults": {
            "appointment_duration_minutes": str(defaults["appointment_duration_minutes"]),
            "timezone": str(defaults["timezone"]),
            "quiet_hours_start": dqs, "quiet_hours_end": dqe, "no_quiet_hours": "1" if dqs == dqe else "0",
            "followup_delay_1": dd1, "followup_delay_2": dd2,
            "followup_expiry_minutes": str(defaults["followup_expiry_minutes"]),
        },
        # The "Default: ..." lines (copy deck: duration_hint, timezone, hours_default, quiet_default, reminder_*).
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
    """(values, errors). ``values`` is what the page re-renders; ``errors`` maps field ids to deck texts.

    ``values["_settings"]`` (setting key -> value or None) is present only when there are no errors.
    """
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
    allowed_tz = {v for v, _ in TIMEZONES} | {values["timezone"]}
    values["timezone"] = tz
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
    last_pair = None
    if no_quiet:
        if qs in QUIET_OPTIONS and qe in QUIET_OPTIONS and qs != qe:
            last_pair = f"{qs}-{qe}"  # the times under the switch, kept for the next time it goes on
        qs = qe = "00:00"
    elif qs not in QUIET_OPTIONS or qe not in QUIET_OPTIONS:
        errors["quiet_hours"] = ERR_QUIET
    elif qs == qe:
        errors["quiet_hours"] = ERR_QUIET_SAME

    # Reminders and the waiting time
    delays = []
    for name in ("followup_delay_1", "followup_delay_2")[: min(2, values["reminder_count"])]:
        raw = text(name)
        values[name] = raw
        try:
            n = int(raw)
            if not (5 <= n <= 20160):
                raise ValueError
            delays.append(n)
        except ValueError:
            errors[name] = ERR_REMINDERS
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
            "followup_delays_minutes": ",".join(str(d) for d in [*delays, *values["extra_delays"]]),
            "followup_expiry_minutes": str(expiry),
        }
        if last_pair:
            values["_settings"][QUIET_LAST_KEY] = last_pair
    return values, errors


def save(state, settings: dict, now: datetime) -> str | None:
    """Validate the policy, write every key in one transaction, rebuild. Returns an error text or None.

    A value equal to its env default is stored as no row at all, so "Reset" and
    "saved the default by hand" leave the table in the same state. The rebuild
    replaces ``state.followup_policy`` / ``store.sms_policy`` and the live
    duration and time zone, so a conversation already under way books with the
    new rules; rows already in the followups table and the outbox are not touched.
    """
    cs = _settings_module()
    try:
        cs.build_scheduling(state, settings)  # FollowupPolicy.__post_init__ runs here, before any write
    except ValueError as exc:
        return str(exc)
    defaults = cs.scheduling_defaults(state)
    with state.store.transaction():
        for key, value in settings.items():
            if value is not None and (str(value) == "" or (key in defaults and str(value) == str(defaults[key]))):
                value = None  # blank or equal to the default: no row, the env default applies
            state.store.set_setting(key, value, now=now)
    cs.apply_scheduling(state)
    return None


# Rule label -> the current_values() keys that make it up, in page order.
_RULE_KEYS = (
    ("appointment_duration_minutes", ("appointment_duration_minutes",)),
    ("timezone", ("timezone",)),
    ("working_hours", ("hours_mode", "hours")),
    ("quiet_hours", ("quiet_hours_start", "quiet_hours_end")),
    ("followup_delay_1", ("followup_delay_1",)),
    ("followup_delay_2", ("followup_delay_2",)),
    ("followup_expiry_minutes", ("followup_expiry_minutes",)),
)


def changed_rules(before: dict, after: dict) -> list[str]:
    """The labels of the rules whose saved value differs, in page order (both from current_values())."""
    if before.get("hours_mode") == after.get("hours_mode") == "any":
        before, after = dict(before, hours=None), dict(after, hours=None)  # the grid is not in force
    return [LABELS[rule] for rule, keys in _RULE_KEYS if any(before.get(k) != after.get(k) for k in keys)]


def changed_rule_keys(before: dict, after: dict) -> list[str]:
    """The rule keys (LABELS) whose saved value differs, in page order."""
    labels = set(changed_rules(before, after))
    return [rule for rule, _ in _RULE_KEYS if LABELS[rule] in labels]


def _applies_note(rule: str) -> str:
    if rule in ("followup_delay_1", "followup_delay_2"):
        return CONSEQUENCES["followup_delay_1"]
    return APPLIES.get(rule, "")


def saved_text(rules: list[str]) -> str:
    """The save notice for these rule keys: what changed, then each rule's own note once."""
    if not rules:
        return SAVED_NOTHING
    notice = SAVED.format(rules="”, “".join(LABELS[rule] for rule in rules))
    notes: list[tuple[str, str]] = []
    for rule in rules:
        note = _applies_note(rule)
        if note and note not in {n for _, n in notes}:
            notes.append((rule, note))
    if len(notes) == 1:
        return f"{notice} {notes[0][1]}"
    named = {"followup_delay_1": "Reminders", "followup_delay_2": "Reminders"}
    return " ".join([notice] + [f"{named.get(rule, LABELS[rule])}: {note[0].lower()}{note[1:]}" for rule, note in notes])


def saved_notice(before: dict, after: dict) -> str:
    return saved_text(changed_rule_keys(before, after))


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


def reset_targets(values: dict) -> tuple[dict, dict]:
    """(control values each Reset puts back, whether each rule already is at its default). portal.js resets a rule
    in place from the first (it stays local until Save, m11); a rule at its default shows no Reset."""
    raw = values["raw_defaults"]
    quiet_default_on = raw["no_quiet_hours"] != "1"
    targets = {
        "appointment_duration_minutes": {"appointment_duration_custom": raw["appointment_duration_minutes"],
                                         "appointment_duration_minutes": raw["appointment_duration_minutes"]
                                         if int(raw["appointment_duration_minutes"]) in DURATION_PRESETS else "custom"},
        "timezone": {"timezone": raw["timezone"]},
        "working_hours": {"hours_mode": "any"},
        "quiet_hours": {"quiet_on": quiet_default_on,
                        **({"quiet_hours_start": raw["quiet_hours_start"], "quiet_hours_end": raw["quiet_hours_end"]}
                           if quiet_default_on else {})},
        "followup_delay_1": {"followup_delay_1": raw["followup_delay_1"]},
        "followup_delay_2": {"followup_delay_2": raw["followup_delay_2"]},
        "followup_expiry_minutes": {"followup_expiry_minutes": raw["followup_expiry_minutes"]},
    }
    quiet_on = not values["no_quiet_hours"]
    at_default = {
        "appointment_duration_minutes": str(values["appointment_duration_minutes"]) == raw["appointment_duration_minutes"],
        "timezone": values["timezone"] == raw["timezone"],
        "working_hours": values["hours_mode"] == "any",
        "quiet_hours": quiet_on == quiet_default_on and (not quiet_on or (
            values["quiet_hours_start"], values["quiet_hours_end"]) == (raw["quiet_hours_start"], raw["quiet_hours_end"])),
        **{key: str(values[key]) == raw[key] for key in ("followup_delay_1", "followup_delay_2", "followup_expiry_minutes")},
    }
    return targets, at_default


def page_context(state, values: dict, errors: dict | None = None) -> dict:
    """Everything schedule.html.j2 needs beyond the layout contract."""
    errors = errors or {}
    raw = values["raw_defaults"]
    targets, at_default = reset_targets(values)
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
    chips, custom = duration_chips(values["appointment_duration_minutes"])
    any_time = values["hours_mode"] == "any"
    return {
        "values": values,
        "errors": errors,
        "defaults": values["defaults"],
        "labels": LABELS,
        "consequences": {**CONSEQUENCES, "working_hours": HOURS_HINTS["any" if any_time else "set"]},
        "timezone_options": timezone_options(values["timezone"]),
        "duration_chips": chips,
        "duration_custom": custom,
        "day_rows": day_rows,
        "quiet_options": _time_options(QUIET_OPTIONS),
        "reminder_count": values["reminder_count"],
        "delay1_options": _options(REMINDER1_PRESETS, values["followup_delay_1"], raw["followup_delay_1"]),
        "delay2_options": _options(REMINDER2_PRESETS, values["followup_delay_2"], raw["followup_delay_2"]),
        "expiry_options": _options(EXPIRY_PRESETS, values["followup_expiry_minutes"], raw["followup_expiry_minutes"]),
        "hours_warning": CORRUPT_HOURS if values.get("hours_corrupt") else "",
        "any_time_warning": any_time,
        "any_time_warning_text": ANY_TIME_WARNING,
        "any_time_button": ANY_TIME_BUTTON,
        "suggested_hours": {day: (dict(window) if window else None) for day, window in SUGGESTED_HOURS.items()},
        "raw_defaults": raw,
        "hours_hints": HOURS_HINTS,
        "applies": APPLIES,
        "any_time_note": ANY_TIME_NOTE,
        "reset_values": targets, "at_default": at_default,
    }


def first_error(errors: dict) -> str:
    for key in FIELD_ORDER:
        if errors.get(key):
            return errors[key]
    return next(iter(errors.values()), "")
