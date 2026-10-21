"""Calendar and Phone pages of the owner portal, and the settings overlay at boot.

The owner (signed in through client_portal) connects the Google calendar the
assistant books against, checks live availability, and on the Phone page
types the business name, the three numbers the product depends on and the
HELP contact, picks a carrier for the forwarding codes and ticks the manual
onboarding checks. Values are stored in the ``client_settings`` table and
applied to the running app; the environment keeps supplying the defaults.
Changing the owner's mobile texts a code to the NEW number and only takes
effect once that code is entered, so a borrowed session can never move the
account to a stranger's phone. Page logic lives in portal_calendar.py and
portal_phone.py; this module owns the routes and the boot-time overlay.
"""
from __future__ import annotations

import dataclasses
import hmac
import json
from datetime import datetime, timedelta

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from text_back.calendars.credentials import GoogleCredentials
from text_back.calendars.protocol import CalendarProviderError
from text_back.client_portal import (
    CODE_FAILURE,
    _now,
    _session,
    _shell,
    check_code,
)
from text_back.policy import format_contact_number
from text_back.portal_ui import render

NAME_MAX = 60
CONNECT_LINK_TTL = timedelta(minutes=15)
CALENDAR_SUBTITLE = "The assistant offers only free times on this calendar. Every booking is added before the customer is told."
PHONE_SUBTITLE = "The numbers the assistant depends on, and the forwarding that sends missed calls to it."


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
    texting = (store.setting("text_back_number") or "").strip()
    if texting:
        state.business_number = texting
        if hasattr(state.telecom, "allowed_from_number"):
            state.telecom.allowed_from_number = texting
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
    Called at boot (after the settings overlay) and after every Scheduling save.
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


# --- routes ---------------------------------------------------------------------

def install_routes(app):
    from text_back import portal_calendar, portal_phone

    state = app.state

    def _require(request: Request):
        session = _session(state, request)
        if not session:
            raise _Redirect("/client/login")
        return session

    class _Redirect(Exception):
        def __init__(self, target):
            self.target = target

    @app.exception_handler(_Redirect)
    async def _redirect(request, exc):
        return RedirectResponse(exc.target, status_code=303)

    async def _checked_form(request: Request, session):
        form = await request.form()
        if not hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
            raise HTTPException(400, "Form expired; reload the page and try again")
        return form

    # --- Calendar ---

    def _calendar(session, *, error: str = "", notice: str = "", result: dict | None = None):
        return render("pages/calendar.html", **_shell(
            state, session, title="Calendar", active="calendar", subtitle=CALENDAR_SUBTITLE,
            error=error, notice=notice, **portal_calendar.page_context(state, result)))

    @app.get("/client/calendar", include_in_schema=False)
    def calendar_page(request: Request, error: str = ""):
        session = _require(request)
        return _calendar(session, error=error[:200])

    @app.post("/client/calendar", include_in_schema=False)
    async def calendar_action(request: Request):
        session = _require(request)
        form = await _checked_form(request, session)
        now = _now(state)
        if str(form.get("action", "")) == "connect":
            if not calendar_status(state)["can_connect"]:
                return _calendar(session, error=portal_calendar.CONNECT_REFUSED)
            from text_back.reconnect import create_link
            return RedirectResponse(create_link(state, "client", CONNECT_LINK_TTL), status_code=303,
                                    headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        chosen = str(form.get("calendar_id", ""))
        choices = {entry["id"]: entry for entry in calendar_choices(state)}
        if chosen not in choices:
            return _calendar(session, error=portal_calendar.PICK_ONE)
        use_calendar(state, chosen, now)
        return _calendar(session, notice=f"The assistant now uses {choices[chosen].get('summary') or chosen}.")

    @app.post("/client/calendar/availability", include_in_schema=False)
    async def calendar_availability(request: Request):
        session = _require(request)
        await _checked_form(request, session)
        return _calendar(session, result=portal_calendar.check_availability(state, _now(state)))

    # --- Phone ---

    def _phone(session, *, values=None, errors=None, statuses=None, error: str = "", notice: str = "",
               pending: str | None = None, code_error: str = ""):
        return render("pages/phone.html", **_shell(
            state, session, title="Phone", active="phone", subtitle=PHONE_SUBTITLE, error=error, notice=notice,
            **portal_phone.page_context(state, values, errors, statuses, pending=pending, code_error=code_error)))

    def _pending_mobile():
        return state.store.setting("owner_mobile_pending") or None

    @app.get("/client/phone", include_in_schema=False)
    def phone_page(request: Request):
        session = _require(request)
        return _phone(session, pending=_pending_mobile())

    @app.post("/client/phone", include_in_schema=False)
    async def save_phone(request: Request):
        session = _require(request)
        form = await _checked_form(request, session)
        now = _now(state)
        submitted = portal_phone.read_form(form)
        values, errors = portal_phone.validate(submitted, state)
        if not errors:
            problem = portal_phone.texting_number_problem(state, values)
            if problem:
                errors["text_back_number"] = problem
        if errors:
            return _phone(session, values=submitted, errors=errors,
                          error=f"Not saved: {portal_phone.first_error(errors)}")
        pending = portal_phone.save(state, values, now)
        if pending:
            return _phone(session, pending=pending, notice=portal_phone.SAVED_CONFIRM_MOBILE)
        return _phone(session, notice=portal_phone.SAVED)

    @app.post("/client/phone/verify", include_in_schema=False)
    async def verify_phone(request: Request):
        session = _require(request)
        form = await _checked_form(request, session)
        field = str(form.get("verify", ""))
        submitted = portal_phone.read_form(form)
        values, all_errors = portal_phone.validate(submitted, state)
        errors = {field: all_errors[field]} if field in all_errors else {}
        statuses = {}
        if not errors and field in portal_phone.VERIFIABLE:
            status = portal_phone.verify(state, field, values)
            if status:
                statuses[field] = status
        return _phone(session, values=submitted, errors=errors, statuses=statuses, error=errors.get(field, ""))

    @app.post("/client/phone/confirm", include_in_schema=False)
    async def confirm_mobile(request: Request):
        session = _require(request)
        form = await _checked_form(request, session)
        now = _now(state)
        pending = _pending_mobile()
        if not pending:
            return _phone(session)
        if str(form.get("cancel", "")):
            state.store.set_setting("owner_mobile_pending", None)
            return _phone(session, notice=portal_phone.KEPT)
        if not check_code(state, pending, str(form.get("code", "")), now):
            return _phone(session, pending=pending, code_error=CODE_FAILURE)
        state.store.set_setting("owner_mobile", pending, now=now)
        state.store.set_setting("owner_mobile_pending", None)
        state.owner_mobile = pending
        return _phone(session, notice=portal_phone.NEW_MOBILE_SAVED.format(n=format_contact_number(pending)))

    @app.post("/client/phone/checklist", include_in_schema=False)
    async def save_checklist(request: Request):
        session = _require(request)
        form = await _checked_form(request, session)
        portal_phone.save_checklist(state, form, _now(state))
        return _phone(session, notice=portal_phone.CHECKS_SAVED, pending=_pending_mobile())

    # --- the old Business page moved to Phone ---

    @app.get("/client/business", include_in_schema=False)
    @app.get("/client/business/{rest:path}", include_in_schema=False)
    def business_moved(request: Request, rest: str = ""):
        return RedirectResponse("/client/phone", status_code=301)

    @app.post("/client/business", include_in_schema=False)
    async def business_post_moved(request: Request):
        return RedirectResponse("/client/phone", status_code=303)  # the old body is dropped on purpose

    @app.post("/client/business/confirm", include_in_schema=False)
    async def business_confirm_moved(request: Request):
        return RedirectResponse("/client/phone/confirm", status_code=307)
