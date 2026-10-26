"""Owner settings applied to the running app, and the Home, Schedule, Calendar and Phone pages.

Values are stored in the ``client_settings`` table and overlaid on the env defaults at boot
(``apply_settings``); a Schedule save rebuilds the live policy (``apply_scheduling``). The
pages are thin: each route reads the form, checks CSRF, and hands the work to the page
module (portal_status, portal_scheduling, portal_calendar, portal_phone) in the threadpool
or in a sync route, so SQLite, telecom and calendar I/O never run on the event loop.

Changing the owner's mobile texts a code to the NEW number and only takes effect once that
code is entered, so a borrowed session can never move the account to a stranger's phone.
The texting number is read-only: no route reads or writes it.
"""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timedelta

from fastapi import Form, Request
from fastapi.responses import RedirectResponse
from starlette.concurrency import run_in_threadpool

from text_back.calendars.credentials import GoogleCredentials
from text_back.calendars.protocol import CalendarProviderError
from text_back.client_portal import (
    CODE_FAILURE,
    _now,
    check_csrf,
    page_notice,
    require_session,
    saved_redirect,
    shell,
)
from text_back.portal_flash import clear as clear_flash
from text_back.portal_render import render

CONNECT_LINK_TTL = timedelta(minutes=15)

# Calendar callback error codes (reconnect.py) -> the deck's notices. Only these fixed
# strings can appear; the query string never reaches the page as text.
CALENDAR_ERRORS = {
    "access": "Google didn't give TextBack calendar access. Try connecting again.",
    "no_calendar": "Google didn't show a calendar this account can add appointments to. "
                   "Try again with the account that owns your business calendar.",
}
ERROR_FIELDS = "Not saved. {n} things need a change."
ERROR_FIELDS_ONE = "Not saved. 1 thing needs a change."
ERROR_KEPT = "Your other edits are still here. Nothing was saved yet."
ERROR_GENERIC = "Something went wrong on our side. Nothing was saved. Try again."


# --- settings applied to the running app -------------------------------------

def apply_settings(state) -> None:
    """Overlay the owner's saved settings on the env-derived app state (at boot)."""
    store = state.store
    name = (store.setting("business_name") or "").strip()
    if name:
        state.business_name = name
    contact = store.setting("business_contact")
    if contact is not None:
        state.business_contact = contact
    owner = store.setting("owner_mobile")
    if owner:
        state.owner_mobile = owner
    calendar_id = store.setting("google_calendar_id")
    if calendar_id and getattr(state.calendar, "provider_name", "") == "google":
        state.calendar.calendar_id = calendar_id
    apply_scheduling(state)


SCHEDULING_KEYS = ("timezone", "appointment_duration_minutes", "followup_delays_minutes",
                   "followup_expiry_minutes", "quiet_hours_start", "quiet_hours_end")


def scheduling_defaults(state) -> dict:
    """The env/kwarg values at boot (app.state.defaults), with a fallback for bare states."""
    defaults = dict(getattr(state, "defaults", None) or {})
    policy = state.followup_policy
    defaults.setdefault("timezone", getattr(state, "timezone_name", policy.timezone_name))
    defaults.setdefault("appointment_duration_minutes", getattr(state, "appointment_duration_minutes", 60))
    defaults.setdefault("followup_delays_minutes", ",".join(str(d) for d in policy.delays_minutes))
    defaults.setdefault("followup_expiry_minutes", policy.expiry_minutes)
    defaults.setdefault("quiet_hours_start", policy.quiet_start.strftime("%H:%M"))
    defaults.setdefault("quiet_hours_end", policy.quiet_end.strftime("%H:%M"))
    return defaults


def build_scheduling(state, overrides: dict | None = None):
    """(policy, timezone_name, duration) from saved settings over the defaults.

    ``overrides`` (setting key -> value or None) lets a save handler validate a
    candidate before anything is written; a bad combination raises ValueError
    from ``FollowupPolicy.__post_init__`` and nothing changes.
    """
    from text_back.followup import _parse_hhmm

    store = state.store
    defaults = scheduling_defaults(state)
    overrides = overrides or {}

    def value(key):
        if key in overrides:
            raw = overrides[key]
        else:
            raw = store.setting(key)
        return raw if raw not in (None, "") else defaults[key]

    tz = str(value("timezone"))
    duration = int(value("appointment_duration_minutes"))
    delays = tuple(int(p) for p in str(value("followup_delays_minutes")).split(",") if p.strip())
    expiry = int(value("followup_expiry_minutes"))
    quiet_start = _parse_hhmm(str(value("quiet_hours_start")), "quiet_hours_start")
    quiet_end = _parse_hhmm(str(value("quiet_hours_end")), "quiet_hours_end")
    policy = dataclasses.replace(state.followup_policy, delays_minutes=delays, expiry_minutes=expiry,
                                 quiet_start=quiet_start, quiet_end=quiet_end, timezone_name=tz)
    return policy, tz, duration


def apply_scheduling(state) -> None:
    """Rebuild the follow-up policy, timezone and appointment length from the saved settings.

    Both ``state.followup_policy`` and ``state.store.sms_policy`` are replaced:
    the worker lanes read the former, ``sms.atomic_sms_handler`` the latter.
    Called at boot (after the settings overlay) and after every Schedule save.
    """
    policy, tz, duration = build_scheduling(state)
    state.followup_policy = policy
    state.store.sms_policy = policy
    state.timezone_name = tz
    state.appointment_duration_minutes = duration


def remember_calendars(state, calendars: list[dict], now: datetime) -> None:
    """After the owner's Google consent: keep the writable calendars for the picker
    and switch to the primary one unless the current calendar is still writable."""
    state.store.set_setting("calendar_choices", json.dumps(calendars), now=now)
    ids = {entry["id"] for entry in calendars}
    if state.calendar.calendar_id not in ids:
        chosen = next((entry["id"] for entry in calendars if entry.get("primary")), calendars[0]["id"])
        use_calendar(state, chosen, now)


def use_calendar(state, calendar_id: str, now: datetime) -> None:
    state.store.set_setting("google_calendar_id", calendar_id, now=now)
    state.calendar.calendar_id = calendar_id


def calendar_choices(state) -> list[dict]:
    try:
        choices = json.loads(state.store.setting("calendar_choices") or "[]")
    except ValueError:
        return []
    return [entry for entry in choices if isinstance(entry, dict) and isinstance(entry.get("id"), str)]



# --- calendar connection state ----------------------------------------------

def calendar_status(state) -> dict:
    """What the calendar page shows: provider, connection state, chosen calendar, whether connecting is possible."""
    calendar = state.calendar
    provider = getattr(calendar, "provider_name", "stub")
    view = {"provider": provider, "status": "managed", "calendar_id": getattr(calendar, "calendar_id", ""), "can_connect": False}
    if provider == "stub":
        view["status"] = "none"
        return view
    if provider != "google":
        return view
    credentials = getattr(calendar, "token_provider", None)
    if not isinstance(credentials, GoogleCredentials):
        return view
    try:
        view["status"] = credentials.status()
    except CalendarProviderError:
        view["status"] = "unavailable"
    view["can_connect"] = bool(credentials.client_file)
    return view




# --- page helpers ----------------------------------------------------------------

def error_summary(errors: dict, order: tuple[str, ...]) -> dict | None:
    """The deck's error_summary_fields block: one linked item per bad field, in page order."""
    if not errors:
        return None
    keys = [key for key in order if key in errors] + [key for key in errors if key not in order]
    count = len(keys)
    return {"title": ERROR_FIELDS_ONE if count == 1 else ERROR_FIELDS.format(n=count), "kept": ERROR_KEPT,
            "items": [{"field": key, "text": errors[key]} for key in keys]}


def _home_page(request: Request, state, session):
    from text_back import portal_status

    now = _now(state)
    items = portal_status.setup_items(state, now)
    for item in items:
        item["node"] = portal_status.node_kind(item["state_word"])
        item.setdefault("example", False)
    first_line = portal_status.counted(items)
    example_note = portal_status.EXAMPLE_NOTE if any(i.get("example") for i in first_line) else ""
    return render(request, "client/home.html.j2", **shell(state, session, title="Home", nav="home"),
                  headline=portal_status.headline(first_line), headline_node=portal_status.headline_kind(first_line),
                  example_note=example_note, setup=items, week=portal_status.this_week(state, now), stepped_back=portal_status.STATUS_STEPPED_BACK)


def portal_messages_discarded() -> str:
    from text_back.portal_messages import DISCARDED
    return DISCARDED


def _schedule_page(request: Request, state, session, *, values=None, errors=None, notice: str = "", unsaved=False):
    from text_back import portal_scheduling

    values = values if values is not None else portal_scheduling.current_values(state)
    context = portal_scheduling.page_context(state, values, errors)
    title = "Not saved · Schedule" if errors else "Schedule"
    page = shell(state, session, title=title, nav="schedule", notice=notice)
    # Answered with values that are not saved (a rejected save, or the one-tap hours): the save bar is up.
    dirty = None
    if errors or unsaved:
        saved_values = portal_scheduling.current_values(state)
        rules = portal_scheduling.changed_rules(saved_values, values) or ([portal_scheduling.LABELS["working_hours"]] if unsaved else [])
        count = (portal_scheduling.CHANGED_ONE if len(rules) == 1 else portal_scheduling.CHANGED_MANY.format(n=len(rules)))
        changed = f"Not saved · {count}" if errors else count
        names = [(f"#{portal_scheduling.ANCHORS[k]}", portal_scheduling.LABELS[k]) for k in portal_scheduling.LABELS
                 if portal_scheduling.LABELS[k] in rules]
        dirty = {"changed": changed, "names": names}
        page["topsave"] = {"form": "schedule-form", "changed": changed, "save": "Save", "names": names}
    return render(request, "client/schedule.html.j2", **page, **context, dirty=dirty,
                  summary=error_summary(errors or {}, portal_scheduling.FIELD_ORDER), unsaved=unsaved)


def _save_schedule(request: Request, state, session, form):
    from text_back import portal_scheduling

    if str(form.get("discard", "") or "") == "1":
        # Discard without JavaScript: back to what is saved; nothing is written.
        return saved_redirect(state, session, "/client/schedule", "discarded")
    # The length chips are radios beside a number field. Without JavaScript they can disagree (m36): whichever
    # the owner touched wins (a tapped chip over an untouched number, a typed number over an untouched chip);
    # "Custom" means the number; both touched and saying different things is refused with "pick one".
    form = {key: form.get(key) for key in form.keys()}
    duration_conflict = False
    typed, shown = str(form.get("appointment_duration_custom") or "").strip(), str(form.get("appointment_duration_shown") or "")
    chip = str(form.get("appointment_duration_minutes") or "custom")
    if shown:
        chip_shown = shown if any(str(v) == shown for v in portal_scheduling.DURATION_PRESETS) else "custom"
        chip_moved, number_moved = chip != chip_shown, bool(typed) and typed != shown
        if number_moved and (not chip_moved or chip == "custom"):
            form["appointment_duration_minutes"] = "custom"
        elif number_moved and chip != typed:
            duration_conflict = True
    # The quiet-hours switch (on = quiet hours apply) stands for the old "No quiet hours" box.
    if str(form.get("quiet_switch") or "") == "1":
        form["no_quiet_hours"] = "" if form.get("quiet_on") else "1"
    if str(form.get("appointment_duration_minutes") or "custom") == "custom":
        form["appointment_duration_minutes"] = form.get("appointment_duration_custom", "")
    reset = str(form.get("reset", "") or "")
    if reset:
        merged = portal_scheduling.reset_form(form, reset, state)
        form = merged if merged is not None else form
    if str(form.get("suggest_hours", "") or "") == "1":
        # "Use Mon–Fri, 8 AM–5 PM" without JavaScript: fill the grid, save nothing.
        values, _ = portal_scheduling.parse_form(form, state)
        values["hours_mode"] = "set"
        for day, window in portal_scheduling.SUGGESTED_HOURS.items():
            values["hours"][day] = {"on": bool(window), "open": (window or {"open": "08:00"})["open"],
                                    "close": (window or {"close": "17:00"})["close"]}
        values.pop("_settings", None)
        return _schedule_page(request, state, session, values=values, unsaved=True)
    values, errors = portal_scheduling.parse_form(form, state)
    if duration_conflict:
        values["appointment_duration_minutes"] = typed
        errors = {"appointment_duration_minutes": portal_scheduling.ERR_DURATION_BOTH, **errors}
    if errors:
        values.pop("_settings", None)
        return _schedule_page(request, state, session, values=values, errors=errors)
    before = portal_scheduling.current_values(state)
    problem = portal_scheduling.save(state, values["_settings"], _now(state))
    if problem:
        return _schedule_page(request, state, session, values=values, errors={"followup_delay_1": problem})
    rules = portal_scheduling.changed_rule_keys(before, portal_scheduling.current_values(state))
    return saved_redirect(state, session, "/client/schedule", "schedule_saved", {"rules": rules})


def _calendar_page(request: Request, state, session, *, result=None, notice: str = "", error: str = "",
                   picker_error: str = ""):
    from text_back import portal_calendar

    context = portal_calendar.page_context(state, result)
    support = str(getattr(state, "support_contact", "") or "").strip()
    return render(request, "client/calendar.html.j2", **shell(state, session, title="Calendar", nav="calendar", notice=notice),
                  **context, page_error=error, picker_error=picker_error, support_contact=support)


def _phone_page(request: Request, state, session, *, values=None, errors=None, notice: str = "", page_error: str = "",
                ticks=None):
    from text_back import portal_forwarding, portal_messages, portal_phone

    now = _now(state)
    context = portal_phone.page_context(state, values, errors, now=now)
    if ticks is not None:  # a rejected save keeps the ticks as posted
        for row in context["check_rows"]:
            key = portal_phone.MANUAL_CHECKS.get(row["n"])
            if key:
                row["ticked"] = bool(ticks.get(key))
    for row in context["check_rows"]:
        row.setdefault("ticked", row["state"] == portal_forwarding.YOU_CHECKED)
    current = state.messages.current()
    preview_name = (context["values"].get("business_name") or state.business_name).strip() or state.business_name
    sample = {**portal_messages.preview_values(state, now), "business_name": preview_name}
    templates = dict(current.templates)
    rename = None
    old_name = state.store.setting(RENAME_FROM_KEY) or ""
    if old_name:
        rename = portal_phone.rename_offer(_saved_overrides(state), old_name, state.business_name)
    from text_back.policy import format_contact_number

    shown = context["values"]
    display = {key: str(shown.get(key, "") or "") for key in portal_phone.FIELD_ORDER}
    for key in ("business_line", "owner_mobile"):
        if display[key].startswith("+") and not (errors or {}).get(key):
            display[key] = format_contact_number(display[key])
    title = f"Not saved · {portal_phone.TITLE}" if errors else portal_phone.TITLE
    page = shell(state, session, title=title, nav="phone", notice=notice)
    # The rename offer rides in the one notice under the header (with the save it followed, if any).
    if rename:
        page["notice"] = notice or ""
        page["notice_offer"] = rename
    dirty = None
    if errors:
        labels = portal_phone.changed_labels(portal_phone.current_values(state), dict(context["values"]),
                                             portal_forwarding.manual_ticks(state.store), ticks or {})
        count = portal_phone.CHANGED_ONE if len(labels) == 1 else portal_phone.CHANGED_MANY.format(n=max(1, len(labels)))
        anchors = {portal_phone.LABELS[k]: f"#{k}" for k in portal_phone.LABELS}
        names = [(anchors.get(label, "#checks"), label) for label in labels]
        dirty = {"changed": f"Not saved · {count}", "names": names}
        page["topsave"] = {"form": "phone-form", "changed": dirty["changed"], "save": "Save", "names": names}
    body, suffix = portal_messages.preview_parts("intro", templates, sample)
    # The plain text alphabet, for the live symbol line under the business name (M7); the same data as Messages.
    page["tb_data"] = {"gsm": portal_messages.GSM_BASIC, "ext": portal_messages.GSM_EXTENDED}
    return render(request, "client/phone.html.j2", **page, name_symbol=portal_phone.name_symbol_line(preview_name),
                  name_symbol_template=portal_phone.NAME_SYMBOL,
                  **context, display=display, page_error=page_error, rename_offer=rename, dirty=dirty,
                  title_text=portal_phone.TITLE, values_saved_mobile=format_contact_number(getattr(state, "owner_mobile", "") or ""),
                  name_preview=body, name_suffix=suffix,
                  name_template=portal_messages.to_display(templates["intro"]),
                  summary=error_summary(errors or {}, portal_phone.FIELD_ORDER))


def _confirm_page(request: Request, state, session, *, error: str = "", notice: str = ""):
    from text_back import portal_phone

    context = portal_phone.page_context(state, now=_now(state), code_error=error)
    return render(request, "client/phone_confirm.html.j2",
                  **shell(state, session, title="Confirm your new mobile", nav="phone", notice=notice), **context)


RENAME_FROM_KEY = "rename_offer_from"


def _saved_overrides(state) -> dict[str, str]:
    from text_back.messages import DEFAULT_TEMPLATES

    current = state.messages.current().templates
    return {key: value for key, value in current.items() if value != DEFAULT_TEMPLATES[key]}


def _save_phone(request: Request, state, session, form):
    from text_back import portal_phone

    from text_back import portal_forwarding, portal_messages

    now = _now(state)
    if str(form.get("discard", "") or "") == "1":
        # Discard without JavaScript (after a rejected save): back to what is saved; nothing is written.
        return saved_redirect(state, session, "/client/phone", "discarded")
    submitted = portal_phone.read_form(form)  # the texting number is not a field: a posted one is ignored
    values, errors = portal_phone.validate(submitted, state)
    # The manual checks post with the page's one Save (the form carries them as check_<key>).
    with_checks = str(form.get("checks_in_form", "") or "") == "1"
    ticks = {key: str(form.get(f"check_{key}", "") or "") == "1" for key in portal_phone.MANUAL_CHECKS.values()}
    if errors:
        shown = dict(submitted)
        return _phone_page(request, state, session, values=shown, errors=errors, ticks=ticks if with_checks else None)
    before = portal_phone.current_values(state)
    ticks_before = {k: bool(v) for k, v in portal_forwarding.manual_ticks(state.store).items()}
    old_name = state.business_name
    pending = portal_phone.save(state, values, now)
    if with_checks:
        portal_phone.save_checklist(state, form, now)
    if old_name != values["business_name"] and portal_phone.texts_with_old_name(_saved_overrides(state), old_name):
        state.store.set_setting(RENAME_FROM_KEY, old_name, now=now)
    after = dict(portal_phone.current_values(state), owner_mobile=values["owner_mobile"])
    ticks_after = {k: bool(v) for k, v in portal_forwarding.manual_ticks(state.store).items()}
    if pending:
        # The confirm step answers GET /client/phone while a new mobile waits for its code (m34).
        return saved_redirect(state, session, "/client/phone", "mobile_code_sent")
    fields, checks = portal_phone.changed_keys(before, after, ticks_before, ticks_after)
    reset = "business_line" in fields and bool(before.get("business_line"))
    return saved_redirect(state, session, "/client/phone", "phone_saved", {"fields": fields, "checks": checks, "reset": reset})


def _rename_texts(request: Request, state, session, form):
    from text_back import portal_phone
    from text_back.messages import MESSAGE_FILE_LOCK, MessageTemplateError, write_message_file

    now = _now(state)
    old_name = state.store.setting(RENAME_FROM_KEY) or ""
    if str(form.get("action", "") or "") != "update" or not old_name:
        kept = len(portal_phone.texts_with_old_name(_saved_overrides(state), old_name)) if old_name else 0
        state.store.set_setting(RENAME_FROM_KEY, None, now=now)
        if kept:  # "Leave them" says what it did (m17)
            return saved_redirect(state, session, "/client/phone", "texts_kept", {"n": kept})
        return RedirectResponse("/client/phone", status_code=303)
    with MESSAGE_FILE_LOCK:  # same lock as Messages saves: read, write, re-read as a unit
        overrides = _saved_overrides(state)
        keys = portal_phone.texts_with_old_name(overrides, old_name)
        if keys and state.messages.path is not None:
            try:
                write_message_file(state.messages.path, portal_phone.rename_in_texts(overrides, old_name, state.business_name))
            except MessageTemplateError:
                return _phone_page(request, state, session, page_error=ERROR_GENERIC)
            state.messages.current()  # pick up the new file right away
    if not keys or state.messages.path is None:
        state.store.set_setting(RENAME_FROM_KEY, None, now=now)
        return RedirectResponse("/client/phone", status_code=303)
    state.store.set_setting(RENAME_FROM_KEY, None, now=now)
    return saved_redirect(state, session, "/client/phone", "renamed", {"n": len(keys)})


def _confirm_mobile(request: Request, state, session, form):
    from text_back import portal_phone

    now = _now(state)
    if not portal_phone.pending_mobile(state):
        return RedirectResponse("/client/phone", status_code=303)
    if str(form.get("action", "") or "") == "resend":
        portal_phone.resend_mobile_code(state, now)
        return RedirectResponse("/client/phone", status_code=303)  # a reload never texts another code
    confirmed = portal_phone.confirm_new_mobile(state, str(form.get("code", "") or ""), now)
    if not confirmed:
        return _confirm_page(request, state, session, error=CODE_FAILURE)
    return saved_redirect(state, session, "/client/phone", "mobile_confirmed")


def _keep_mobile(request: Request, state, session, form):
    from text_back import portal_phone

    portal_phone.keep_current_mobile(state, _now(state))
    return saved_redirect(state, session, "/client/phone", "mobile_kept")


def _save_checks(request: Request, state, session, form):
    from text_back import portal_phone

    portal_phone.save_checklist(state, form, _now(state))
    return saved_redirect(state, session, "/client/phone", "checks_saved", anchor="checks")


# --- routes --------------------------------------------------------------------

def install_routes(app):
    state = app.state

    def _guarded(request: Request, form, reload_url: str, handler):
        """Session and CSRF first, then the page's handler; runs in the threadpool."""
        session = require_session(state, request)
        check_csrf(form, session, reload_url)
        return handler(request, state, session, form)

    @app.get("/client/home", include_in_schema=False)
    def home_page(request: Request):
        session = require_session(state, request)
        return _home_page(request, state, session)

    @app.get("/client/business", include_in_schema=False)
    def business_moved(request: Request):
        # Business details now live on Phone; old bookmarks land there.
        require_session(state, request)
        return RedirectResponse("/client/phone", status_code=303)

    # --- Schedule ------------------------------------------------------------------

    @app.get("/client/schedule", include_in_schema=False)
    def schedule_page(request: Request):
        session = require_session(state, request)
        return clear_flash(request, _schedule_page(request, state, session,
                                                   notice=page_notice(state, request, session, "/client/schedule")))

    @app.post("/client/schedule", include_in_schema=False)
    async def schedule_save(request: Request):
        form = await request.form()
        return await run_in_threadpool(_guarded, request, form, "/client/schedule", _save_schedule)

    @app.get("/client/calendar", include_in_schema=False)
    def calendar_page(request: Request, error: str = ""):
        session = require_session(state, request)
        return clear_flash(request, _calendar_page(request, state, session, error=CALENDAR_ERRORS.get(error, ""),
                                                   notice=page_notice(state, request, session, "/client/calendar")))

    @app.post("/client/calendar", include_in_schema=False)
    def calendar_action(request: Request, csrf: str = Form(""), action: str = Form(""), calendar_id: str = Form("")):
        # A sync route: the free-times check and the connect link both do calendar or DB I/O.
        from text_back import portal_calendar

        session = require_session(state, request)
        check_csrf({"csrf": csrf}, session, "/client/calendar")
        now = _now(state)
        if action == "connect":
            if not calendar_status(state)["can_connect"]:
                return _calendar_page(request, state, session, error=portal_calendar.ERR_NOT_SET_UP)
            from text_back.reconnect import create_link
            return RedirectResponse(create_link(state, "client", CONNECT_LINK_TTL), status_code=303,
                                    headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        if action == "check":
            return _calendar_page(request, state, session, result=portal_calendar.check_availability(state, now))
        choices = {entry["id"]: entry for entry in calendar_choices(state)}
        if calendar_status(state)["status"] != "ready" or calendar_id not in choices:
            return _calendar_page(request, state, session, picker_error=portal_calendar.PICKER_ERROR)
        use_calendar(state, calendar_id, now)
        return saved_redirect(state, session, "/client/calendar", "calendar_picked", {"id": calendar_id})

    # --- Phone ---------------------------------------------------------------------

    @app.get("/client/phone", include_in_schema=False)
    def phone_page(request: Request):
        from text_back import portal_phone

        session = require_session(state, request)
        notice = page_notice(state, request, session, "/client/phone")
        if portal_phone.pending_mobile(state):
            return clear_flash(request, _confirm_page(request, state, session, notice=notice))
        return clear_flash(request, _phone_page(request, state, session, notice=notice))

    @app.post("/client/phone", include_in_schema=False)
    async def phone_save(request: Request):
        form = await request.form()
        return await run_in_threadpool(_guarded, request, form, "/client/phone", _save_phone)

    @app.post("/client/phone/confirm", include_in_schema=False)
    async def phone_confirm(request: Request):
        form = await request.form()
        return await run_in_threadpool(_guarded, request, form, "/client/phone", _confirm_mobile)

    @app.post("/client/phone/keep", include_in_schema=False)
    async def phone_keep(request: Request):
        form = await request.form()
        return await run_in_threadpool(_guarded, request, form, "/client/phone", _keep_mobile)

    @app.post("/client/phone/checks", include_in_schema=False)
    async def phone_checks(request: Request):
        form = await request.form()
        return await run_in_threadpool(_guarded, request, form, "/client/phone", _save_checks)

    @app.post("/client/phone/rename-texts", include_in_schema=False)
    async def phone_rename_texts(request: Request):
        form = await request.form()
        return await run_in_threadpool(_guarded, request, form, "/client/phone", _rename_texts)
