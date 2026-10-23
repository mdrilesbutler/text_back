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
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Request
from fastapi.responses import RedirectResponse
from markupsafe import Markup

from text_back.calendars.credentials import GoogleCredentials
from text_back.calendars.protocol import CalendarProviderError
from text_back.client_portal import (
    CODE_FAILURE,
    FormExpired,
    _now,
    _session,
    _shell,
    check_code,
    fill,
    normalize_mobile,
    preview_text,
    preview_values,
    send_code,
)
from text_back.policy import format_contact_number
from text_back.portal_render import render

NAME_MAX = 60
CONNECT_LINK_TTL = timedelta(minutes=15)

# Validation messages, shared by the checks and the error-to-field map so they cannot drift.
NAME_ERROR = f"Enter a business name of 1 to {NAME_MAX} characters."
CONTACT_ERROR = "Enter the customer phone number as digits, like 704 555 0123, or leave it blank."
MOBILE_ERROR = "Enter your mobile as digits, like 704 555 0123."
ERROR_FIELD = {NAME_ERROR: "business_name", CONTACT_ERROR: "business_contact", MOBILE_ERROR: "owner_mobile"}


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

def _business_form(request: Request, state, session, *, error: str = "", notice: str = "", values: dict | None = None):
    values = values or {}
    shown = {
        "business_name": values.get("business_name", state.business_name),
        "business_contact": values.get("business_contact", state.business_contact or ""),
        "owner_mobile": values.get("owner_mobile", format_contact_number(state.owner_mobile) if state.owner_mobile else ""),
    }
    sender = format_contact_number(getattr(state, "business_number", "") or "") or "the number the texts come from"
    templates = state.messages.current().templates
    name = shown["business_name"].strip() or state.business_name
    name_preview = {
        "text": preview_text("intro", templates, {**preview_values(state), "business_name": name}),
        "template": templates["intro"],
        "suffix": "" if re.search(r"\bstop\b", templates["intro"], re.IGNORECASE) else fill(templates["opt_out_suffix"], {}),
        "saved_name": state.business_name,
    }
    return render(
        request, "client/business.html.j2",
        **_shell(state, session, title="Not saved · Business" if error else "Business", nav="business", notice=notice),
        values=shown, name_max=NAME_MAX, sender=sender, name_preview=name_preview,
        error={"field": ERROR_FIELD.get(error), "message": error} if error else None,
    )


def _confirm_form(request: Request, state, session, pending_mobile: str, *, error: str = ""):
    pending_display = format_contact_number(pending_mobile)
    return render(
        request, "client/confirm_mobile.html.j2",
        **_shell(state, session, title="Confirm your new mobile", nav="business"),
        pending_display=pending_display, error=error,
        # "Send the code again" re-posts these to POST /client/business (same route, same rate limit).
        resend={"business_name": state.business_name, "business_contact": state.business_contact or "",
                "owner_mobile": pending_display},
    )


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


@dataclass(frozen=True, slots=True)
class StatusView:
    kind: str            # ready | reauth_required | unavailable | none | managed  -> data-status
    pill_variant: str    # success | warning | danger | info
    pill_icon: str
    pill_word: str
    title: str
    detail: Markup       # one sentence
    calendar: str = ""   # the calendar in use, shown only while connected


@dataclass(frozen=True, slots=True)
class Choice:
    id: str
    name: str
    main: bool
    in_use: bool


# provider id -> (display name, short name in a sentence)
PROVIDER_NAMES = {"google": ("Google Calendar", "Google"), "microsoft": ("Outlook (Microsoft 365)", "Outlook"),
                  "icloud": ("iCloud Calendar", "iCloud")}
SETUP_NOTE = "Connecting a calendar from this page is still being set up by FluxWorks."


def status_view(view: dict, label: str) -> StatusView:
    """The calendar status block for ``calendar_status()`` output; ``label`` names the calendar in use."""
    provider = view["provider"]
    if provider == "stub":
        return StatusView("none", "info", "flask-conical", "Test mode", "No calendar connected",
                          Markup("Bookings are not recorded on any calendar yet."))
    if provider != "google":
        name, short = PROVIDER_NAMES.get(provider, (provider.title(), provider.title()))
        return StatusView("managed", "success", "user-check", "Connected", f"{name} connected",
                          Markup("Your {} calendar is connected and managed by FluxWorks.").format(short))
    if view["status"] == "ready":
        return StatusView("ready", "success", "calendar-check", "Connected", "Connected to Google Calendar",
                          Markup("Free times come from this calendar and every booking is added to it."),
                          calendar=label)
    if view["status"] == "reauth_required":
        return StatusView("reauth_required", "warning", "triangle-alert", "Paused", "Reconnect needed",
                          Markup("Google has disconnected the calendar, so bookings are paused until you reconnect."))
    return StatusView("unavailable", "danger", "circle-x", "Error", "The calendar could not be read",
                      Markup("Bookings are paused until the calendar is connected again."))


def _calendar_page(request: Request, state, session, *, error: str = "", notice: str = "", picker_error: str = ""):
    view = calendar_status(state)
    choices = calendar_choices(state)
    names = {entry["id"]: entry.get("summary") or entry["id"] for entry in choices}
    current = view["calendar_id"]
    status = status_view(view, names.get(current, current))
    google = view["provider"] == "google"
    connect = None
    if google and view["can_connect"]:
        # Connect/Reconnect sits inside the status block either way. Not connected: Connect is primary and
        # "What Google will ask" starts open. Connected: Reconnect is secondary and the explanation starts closed.
        ready = status.kind == "ready"
        connect = {"verb": "Reconnect" if ready else "Connect", "primary": not ready}
    picker = None
    only_calendar = ""
    if status.kind == "ready":  # the picker only makes sense while the calendar is connected
        if len(choices) > 1:
            picker = tuple(Choice(entry["id"], names[entry["id"]], bool(entry.get("primary")), entry["id"] == current)
                           for entry in choices)
        elif len(choices) == 1:
            only_calendar = names[choices[0]["id"]]
    return render(
        request, "client/calendar.html.j2",
        **_shell(state, session, title="Calendar", nav="calendar", notice=notice,
                 page_error=error or (picker_error if picker is None else "")),
        status=status, connect=connect, setup_note=SETUP_NOTE if not view["can_connect"] and view["provider"] in ("google", "stub") else "",
        picker=picker,
        only_calendar=only_calendar, picker_error=picker_error if picker is not None else "",
    )


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

    async def _checked_form(request: Request, session, reload_url: str):
        form = await request.form()
        if not hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
            raise FormExpired(reload_url)
        return form

    @app.get("/client/business", include_in_schema=False)
    def business_page(request: Request):
        session = _require(request)
        pending = state.store.setting("owner_mobile_pending")
        if pending:
            return _confirm_form(request, state, session, pending)
        return _business_form(request, state, session)

    @app.post("/client/business", include_in_schema=False)
    async def save_business(request: Request):
        session = _require(request)
        form = await _checked_form(request, session, "/client/business")
        now = _now(state)
        submitted = {key: str(form.get(key, "")).strip() for key in ("business_name", "business_contact", "owner_mobile")}
        name = " ".join(submitted["business_name"].split())
        if not name or len(name) > NAME_MAX:
            return _business_form(request, state, session, error=NAME_ERROR, values=submitted)
        contact = ""
        if submitted["business_contact"]:
            normalized = normalize_mobile(submitted["business_contact"])
            if normalized is None:
                return _business_form(request, state, session, error=CONTACT_ERROR, values=submitted)
            contact = format_contact_number(normalized)
        mobile = normalize_mobile(submitted["owner_mobile"])
        if mobile is None:
            return _business_form(request, state, session, error=MOBILE_ERROR, values=submitted)
        state.store.set_setting("business_name", name, now=now)
        state.store.set_setting("business_contact", contact, now=now)
        state.business_name = name
        state.business_contact = contact
        if mobile != state.owner_mobile:
            state.store.set_setting("owner_mobile_pending", mobile, now=now)
            send_code(state, mobile, now, purpose="new mobile")
            return _confirm_form(request, state, session, mobile)
        return _business_form(request, state, session, notice="Saved.")

    @app.post("/client/business/confirm", include_in_schema=False)
    async def confirm_mobile(request: Request):
        session = _require(request)
        form = await _checked_form(request, session, "/client/business")
        now = _now(state)
        pending = state.store.setting("owner_mobile_pending")
        if not pending:
            return _business_form(request, state, session)
        if str(form.get("cancel", "")):
            state.store.set_setting("owner_mobile_pending", None)
            return _business_form(request, state, session, notice="Kept your current mobile.")
        if not check_code(state, pending, str(form.get("code", "")), now):
            return _confirm_form(request, state, session, pending, error=CODE_FAILURE)
        state.store.set_setting("owner_mobile", pending, now=now)
        state.store.set_setting("owner_mobile_pending", None)
        state.owner_mobile = pending
        return _business_form(request, state, session, notice=f"Saved. Sign-in codes now go to {format_contact_number(pending)}.")

    @app.get("/client/business/keep", include_in_schema=False)
    def keep_mobile(request: Request):
        session = _require(request)
        state.store.set_setting("owner_mobile_pending", None)
        return _business_form(request, state, session, notice="Kept your current mobile.")

    @app.get("/client/calendar", include_in_schema=False)
    def calendar_page(request: Request, error: str = ""):
        session = _require(request)
        return _calendar_page(request, state, session, error=error[:200])

    @app.post("/client/calendar", include_in_schema=False)
    async def calendar_action(request: Request):
        session = _require(request)
        form = await _checked_form(request, session, "/client/calendar")
        now = _now(state)
        if str(form.get("action", "")) == "connect":
            if not calendar_status(state)["can_connect"]:
                return _calendar_page(request, state, session, error="Connecting a calendar is not set up for this account yet.")
            from text_back.reconnect import create_link
            return RedirectResponse(create_link(state, "client", CONNECT_LINK_TTL), status_code=303,
                                    headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})
        chosen = str(form.get("calendar_id", ""))
        choices = {entry["id"]: entry for entry in calendar_choices(state)}
        if chosen not in choices:
            return _calendar_page(request, state, session, picker_error="Pick one of the calendars listed.")
        use_calendar(state, chosen, now)
        return _calendar_page(request, state, session, notice=f"The assistant now uses {choices[chosen].get('summary') or chosen}.")
