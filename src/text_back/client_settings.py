"""Business details and calendar connection on the client settings pages.

The owner (signed in through client_portal) edits the business name, the
phone number customers are given, and their own mobile, and connects the
Google calendar the assistant books against. Values are stored in the
``client_settings`` table and applied to the running app; the environment
keeps supplying the defaults. Changing the owner's mobile texts a code to the
NEW number and only takes effect once that code is entered, so a borrowed
session can never move the account to a stranger's phone.
"""
from __future__ import annotations

import dataclasses
import hmac
import html
import json
from datetime import datetime, timedelta

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from text_back.calendars.credentials import GoogleCredentials
from text_back.calendars.protocol import CalendarProviderError
from text_back.client_portal import (
    CODE_FAILURE,
    _now,
    _page,
    _session,
    check_code,
    normalize_mobile,
    send_code,
)
from text_back.policy import format_contact_number
from text_back.portal_ui import flash_html

NAME_MAX = 60
CONNECT_LINK_TTL = timedelta(minutes=15)


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


# --- pages ---------------------------------------------------------------------

def _flash(error: str = "", notice: str = "") -> str:
    return flash_html(error, notice)


_FLASH_OK_ICON = '<svg class="i" aria-hidden="true"><use href="#i-check"></use></svg>'


def _attrs(name: str, field: str) -> str:
    """aria-describedby to the hint, plus aria-invalid on the field the error names."""
    return f' aria-describedby={name}-hint' + (' aria-invalid=true' if field == name else '')


def _business_form(state, session, *, error: str = "", notice: str = "", values: dict | None = None, field: str = ""):
    values = values or {}
    name = values.get("business_name", state.business_name)
    contact = values.get("business_contact", state.business_contact or "")
    mobile = values.get("owner_mobile", format_contact_number(state.owner_mobile) if state.owner_mobile else "")
    body = (
        "<p>How the assistant introduces the business and where it reaches you.</p>"
        + _flash(error, notice)
        + "<form method=post action=/client/business class=stack>"
        + f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'>"
        + "<div class=field><label class=label for=business_name>Business name</label>"
        + f"<input class=input id=business_name name=business_name required maxlength={NAME_MAX} value=\"{html.escape(name, quote=True)}\"{_attrs('business_name', field)}>"
        + f"<span class=hint id=business_name-hint>Used in every text, for example \"Thanks for calling {html.escape(state.business_name)}\".</span></div>"
        + "<div class=field><label class=label for=business_contact>Number customers get on HELP</label>"
        + f"<input class=input id=business_contact name=business_contact type=tel inputmode=tel maxlength=24 value=\"{html.escape(contact, quote=True)}\"{_attrs('business_contact', field)}>"
        + "<span class=hint id=business_contact-hint>Shown when a customer texts HELP. Leave blank to show the number the texts come from.</span></div>"
        + "<div class=field><label class=label for=owner_mobile>Your mobile</label>"
        + f"<input class=input id=owner_mobile name=owner_mobile type=tel inputmode=tel required maxlength=24 value=\"{html.escape(mobile, quote=True)}\"{_attrs('owner_mobile', field)}>"
        + "<span class=hint id=owner_mobile-hint>Signs you in here. Changing it texts a code to the new number, which you enter before the change counts.</span></div>"
        + "<button type=submit class='btn btn-primary'>Save business details</button></form>"
    )
    return _page("Your business", body, session=session, active="business", state=state)


def _confirm_form(state, session, pending_mobile: str, *, error: str = ""):
    body = (
        f"<p>We texted a six-digit code to <strong>{html.escape(format_contact_number(pending_mobile))}</strong>. "
        "Enter it to switch sign-in to that number. It expires in ten minutes.</p>"
        + _flash(error)
        + "<form method=post action=/client/business/confirm class=stack>"
        + f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'>"
        + "<div class=field><label class=label for=code>Confirmation code</label><input class=input id=code name=code inputmode=numeric autocomplete=one-time-code pattern='[0-9]{6}' required maxlength=6></div>"
        + "<button type=submit class='btn btn-primary'>Confirm new mobile</button></form>"
        + "<p><a href=/client/business/keep>Keep my current mobile</a></p>"
    )
    return _page("Confirm your new mobile", body, session=session, active="business", state=state)


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


def _calendar_page(state, session, *, error: str = "", notice: str = ""):
    view = calendar_status(state)
    choices = calendar_choices(state)
    names = {entry["id"]: entry.get("summary") or entry["id"] for entry in choices}
    current = view["calendar_id"]
    current_label = names.get(current, current)
    if view["provider"] == "google":
        if view["status"] == "ready":
            state_line = (f"<div class='flash ok' role='status'>{_FLASH_OK_ICON}<div>Google Calendar is connected. Appointments are checked against "
                          f"and booked on <strong>{html.escape(current_label)}</strong>.</div></div>")
        elif view["status"] == "reauth_required":
            state_line = _flash(error="Google has disconnected the calendar. Bookings are paused until you reconnect.")
        else:
            state_line = _flash(error="The calendar connection could not be read. Reconnect to resume bookings.")
        if view["can_connect"]:
            verb = "Reconnect" if view["status"] == "ready" else "Connect"
            connect = (
                "<form method=post action=/client/calendar>"
                f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'><input type=hidden name=action value=connect>"
                f"<button type=submit class='btn btn-primary'>{verb} Google Calendar</button></form>"
                "<p class=muted>You will be sent to Google to choose the account that owns your business calendar and allow calendar access. "
                "Nothing else in that account is read.</p>"
            )
        else:
            connect = "<p class=muted>Connecting a calendar from this page isn't turned on yet.</p>"
        picker = ""
        if len(choices) > 1:
            options = "".join(
                f"<label><input type=radio name=calendar_id value=\"{html.escape(entry['id'], quote=True)}\"{' checked' if entry['id'] == current else ''}> "
                f"{html.escape(entry.get('summary') or entry['id'])}{' (main calendar)' if entry.get('primary') else ''}</label>"
                for entry in choices
            )
            picker = (
                "<h2>Calendar the assistant uses</h2>"
                "<p>Free times are checked on this calendar and new appointments are added to it.</p>"
                "<form method=post action=/client/calendar>"
                f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'>{options}"
                "<button type=submit class='btn btn-primary'>Use this calendar</button></form>"
            )
        body_main = state_line + connect + picker
    elif view["provider"] == "stub":
        body_main = _flash(error="No calendar is connected yet. Bookings are not recorded anywhere.")
    else:
        body_main = _flash(notice=f"Your {view['provider']} calendar is connected and managed for you.")
    body = (
        "<p>The assistant offers only free times on this calendar. Every booking is added before the customer is told.</p>"
        + _flash(error, notice)
        + body_main
    )
    return _page("Your calendar", body, session=session, active="calendar", state=state)


def install_routes(app):
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

    @app.get("/client/business", include_in_schema=False)
    def business_page(request: Request):
        session = _require(request)
        pending = state.store.setting("owner_mobile_pending")
        if pending:
            return _confirm_form(state, session, pending)
        return _business_form(state, session)

    @app.post("/client/business", include_in_schema=False)
    async def save_business(request: Request):
        session = _require(request)
        form = await _checked_form(request, session)
        now = _now(state)
        submitted = {key: str(form.get(key, "")).strip() for key in ("business_name", "business_contact", "owner_mobile")}
        name = " ".join(submitted["business_name"].split())
        if not name or len(name) > NAME_MAX:
            return _business_form(state, session, error=f"Enter a business name of 1 to {NAME_MAX} characters.", values=submitted, field="business_name")
        contact = ""
        if submitted["business_contact"]:
            normalized = normalize_mobile(submitted["business_contact"])
            if normalized is None:
                return _business_form(state, session, error="Enter the customer phone number as digits, like 704 555 0123, or leave it blank.", values=submitted, field="business_contact")
            contact = format_contact_number(normalized)
        mobile = normalize_mobile(submitted["owner_mobile"])
        if mobile is None:
            return _business_form(state, session, error="Enter your mobile as digits, like 704 555 0123.", values=submitted, field="owner_mobile")
        state.store.set_setting("business_name", name, now=now)
        state.store.set_setting("business_contact", contact, now=now)
        state.business_name = name
        state.business_contact = contact
        if mobile != state.owner_mobile:
            state.store.set_setting("owner_mobile_pending", mobile, now=now)
            send_code(state, mobile, now, purpose="new mobile")
            return _confirm_form(state, session, mobile)
        return _business_form(state, session, notice="Saved.")

    @app.post("/client/business/confirm", include_in_schema=False)
    async def confirm_mobile(request: Request):
        session = _require(request)
        form = await _checked_form(request, session)
        now = _now(state)
        pending = state.store.setting("owner_mobile_pending")
        if not pending:
            return _business_form(state, session)
        if str(form.get("cancel", "")):
            state.store.set_setting("owner_mobile_pending", None)
            return _business_form(state, session, notice="Kept your current mobile.")
        if not check_code(state, pending, str(form.get("code", "")), now):
            return _confirm_form(state, session, pending, error=CODE_FAILURE)
        state.store.set_setting("owner_mobile", pending, now=now)
        state.store.set_setting("owner_mobile_pending", None)
        state.owner_mobile = pending
        return _business_form(state, session, notice=f"Saved. Sign-in codes now go to {format_contact_number(pending)}.")

    @app.get("/client/business/keep", include_in_schema=False)
    def keep_mobile(request: Request):
        session = _require(request)
        state.store.set_setting("owner_mobile_pending", None)
        return _business_form(state, session, notice="Kept your current mobile.")

    @app.get("/client/calendar", include_in_schema=False)
    def calendar_page(request: Request, error: str = ""):
        session = _require(request)
        return _calendar_page(state, session, error=error[:200])

    @app.post("/client/calendar", include_in_schema=False)
    async def calendar_action(request: Request):
        session = _require(request)
        form = await _checked_form(request, session)
        now = _now(state)
        if str(form.get("action", "")) == "connect":
            if not calendar_status(state)["can_connect"]:
                return _calendar_page(state, session, error="Connecting a calendar is not set up for this account yet.")
            from text_back.reconnect import create_link
            return RedirectResponse(create_link(state, "client", CONNECT_LINK_TTL), status_code=303,
                                    headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        chosen = str(form.get("calendar_id", ""))
        choices = {entry["id"]: entry for entry in calendar_choices(state)}
        if chosen not in choices:
            return _calendar_page(state, session, error="Pick one of the calendars listed.")
        use_calendar(state, chosen, now)
        return _calendar_page(state, session, notice=f"The assistant now uses {choices[chosen].get('summary') or chosen}.")
