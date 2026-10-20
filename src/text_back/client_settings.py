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
    _flash,
    _now,
    _page,
    _session,
    check_code,
    nav_html,
    normalize_mobile,
    send_code,
)
from text_back.policy import format_contact_number

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

def _business_form(state, session, *, error: str = "", notice: str = "", values: dict | None = None):
    values = values or {}
    name = values.get("business_name", state.business_name)
    contact = values.get("business_contact", state.business_contact or "")
    mobile = values.get("owner_mobile", format_contact_number(state.owner_mobile) if state.owner_mobile else "")
    sender = format_contact_number(getattr(state, "business_number", "") or "") or "the number the texts come from"
    body = (
        nav_html(state, session, "Your business", "business")
        + "<p class=lead>How the assistant introduces the business, where customers are pointed, and where sign-in codes go.</p>"
        + _flash(error, notice)
        + "<form method=post action=/client/business><div class=card>"
        + f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'>"
        + "<label for=business_name>Business name"
        "<span class=help>Used in every text, for example \"Thanks for calling {business_name}\".</span></label>"
        + f"<input id=business_name name=business_name required maxlength={NAME_MAX} autocomplete=organization value=\"{html.escape(name, quote=True)}\">"
        + "<label for=business_contact>Phone number customers should call"
        f"<span class=help>Shown when a customer texts HELP. Leave blank to show {html.escape(sender)}. "
        "Customers are never transferred to it; the assistant handles the texting.</span></label>"
        + f"<input id=business_contact name=business_contact type=tel inputmode=tel maxlength=24 placeholder='704 555 0123' value=\"{html.escape(contact, quote=True)}\">"
        + "<label for=owner_mobile>Your mobile"
        "<span class=help>Sign-in codes come to this number. If you change it, we text a code to the new number and nothing changes until you enter it.</span></label>"
        + f"<input id=owner_mobile name=owner_mobile type=tel inputmode=tel required maxlength=24 autocomplete=tel value=\"{html.escape(mobile, quote=True)}\">"
        + "</div><p><button type=submit class=primary>Save business details</button></p></form>"
    )
    return _page("Your business", body)


def _confirm_form(state, session, pending_mobile: str, *, error: str = ""):
    body = (
        nav_html(state, session, "Confirm your new mobile", "business")
        + "<div class=steps><div class='step done'>1. Details saved</div><div class='step now'>2. Confirm the new number</div></div>"
        + f"<p class=lead>We texted a six-digit code to <strong>{html.escape(format_contact_number(pending_mobile))}</strong>. "
        "Enter it to move sign-in to that number. It expires in ten minutes; until then codes still go to your current mobile.</p>"
        + _flash(error)
        + "<form method=post action=/client/business/confirm><div class=card>"
        + f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'>"
        + "<label for=code>Code from the text</label><input id=code name=code class=code inputmode=numeric autocomplete=one-time-code pattern='[0-9]{6}' required maxlength=6 autofocus>"
        + "</div><p><button type=submit class=primary>Confirm new mobile</button></p></form>"
        + "<p><a href=/client/business/keep>Keep my current mobile instead</a></p>"
    )
    return _page("Confirm your new mobile", body)


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


_ICONS = {
    "ok": "<svg viewBox='0 0 24 24' aria-hidden=true><circle cx=12 cy=12 r=11 fill='#1d6b3a'/><path d='M7 12.5l3.2 3.2L17 9' stroke='#fff' stroke-width='2.4' fill='none' stroke-linecap='round' stroke-linejoin='round'/></svg>",
    "warn": "<svg viewBox='0 0 24 24' aria-hidden=true><path d='M12 2.5L22.5 21h-21z' fill='#F0B429'/><path d='M12 9v5.5' stroke='#1c1300' stroke-width='2.4' stroke-linecap='round'/><circle cx=12 cy=17.5 r=1.4 fill='#1c1300'/></svg>",
    "err": "<svg viewBox='0 0 24 24' aria-hidden=true><circle cx=12 cy=12 r=11 fill='#b3261e'/><path d='M8 8l8 8M16 8l-8 8' stroke='#fff' stroke-width='2.4' stroke-linecap='round'/></svg>",
    "none": "<svg viewBox='0 0 24 24' aria-hidden=true><rect x=3 y=4 width=18 height=17 rx=3 fill='none' stroke='#596270' stroke-width='2'/><path d='M3 9h18M8 2.5v4M16 2.5v4' stroke='#596270' stroke-width='2' stroke-linecap='round'/></svg>",
}


def _status_block(kind: str, headline: str, detail: str) -> str:
    return f"<div class='status {kind}'>{_ICONS[kind]}<div><strong>{headline}</strong><p>{detail}</p></div></div>"


def _calendar_page(state, session, *, error: str = "", notice: str = ""):
    view = calendar_status(state)
    choices = calendar_choices(state)
    names = {entry["id"]: entry.get("summary") or entry["id"] for entry in choices}
    current = view["calendar_id"]
    current_label = names.get(current, current)
    picker = connect = ""
    if view["provider"] == "google":
        if view["status"] == "ready":
            status = _status_block("ok", "Connected to Google Calendar",
                                   f"Google Calendar is connected. Appointments are checked against and booked on <strong>{html.escape(current_label)}</strong>.")
        elif view["status"] == "reauth_required":
            status = _status_block("warn", "Reconnect needed",
                                   "Google has disconnected the calendar. Bookings are paused until you reconnect.")
        else:
            status = _status_block("err", "The calendar could not be read",
                                   "The calendar connection could not be read. Reconnect to resume bookings.")
        if view["can_connect"]:
            verb = "Reconnect" if view["status"] == "ready" else "Connect"
            connect = (
                "<div class=card><h2>What Google will ask</h2>"
                "<p>You will be sent to Google to pick the account that owns your business calendar. Google then asks you to allow this "
                "assistant to see and edit your calendars. It uses that only to check free times and add appointments. "
                "Nothing else in that account is read, and you can pick which calendar it uses afterwards.</p>"
                "<form method=post action=/client/calendar>"
                f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'><input type=hidden name=action value=connect>"
                f"<p><button type=submit class=primary>{verb} Google Calendar</button></p></form></div>"
            )
        else:
            connect = "<p class=muted>Connecting a calendar from this page is still being set up by your operator.</p>"
        if len(choices) > 1:
            options = "".join(
                f"<label class=choice><input type=radio name=calendar_id value=\"{html.escape(entry['id'], quote=True)}\"{' checked' if entry['id'] == current else ''}> "
                f"{html.escape(entry.get('summary') or entry['id'])}{' (main calendar)' if entry.get('primary') else ''}</label>"
                for entry in choices
            )
            picker = (
                "<form method=post action=/client/calendar><div class=card><h2>Which calendar should the assistant use?</h2>"
                "<p class=muted style='margin-top:0'>Free times are checked on this calendar and new appointments are added to it.</p>"
                f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'><fieldset class=plain><legend class=vh>Calendar</legend>{options}</fieldset>"
                "<p><button type=submit class=primary>Use this calendar</button></p></div></form>"
            )
    elif view["provider"] == "stub":
        status = _status_block("none", "Test mode: no calendar connected",
                               "No real calendar is connected (test mode). Bookings are not recorded anywhere yet.")
    else:
        status = _status_block("ok", f"{html.escape(view['provider'].title())} calendar connected",
                               f"Your {html.escape(view['provider'])} calendar is connected and managed by your operator.")
    body = (
        nav_html(state, session, "Your calendar", "calendar")
        + "<p class=lead>The assistant only offers times that are free on this calendar, and every booking is added to it before the customer gets a confirmation.</p>"
        + _flash(error, notice)
        + status + connect + picker
    )
    return _page("Your calendar", body)


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
            return _business_form(state, session, error=f"Enter a business name of 1 to {NAME_MAX} characters.", values=submitted)
        contact = ""
        if submitted["business_contact"]:
            normalized = normalize_mobile(submitted["business_contact"])
            if normalized is None:
                return _business_form(state, session, error="Enter the customer phone number as digits, like 704 555 0123, or leave it blank.", values=submitted)
            contact = format_contact_number(normalized)
        mobile = normalize_mobile(submitted["owner_mobile"])
        if mobile is None:
            return _business_form(state, session, error="Enter your mobile as digits, like 704 555 0123.", values=submitted)
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
