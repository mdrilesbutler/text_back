"""Owner portal (/client): passwordless sign-in, sessions, Home, Account, Messages, Scheduling.
Business details and the calendar connection live in client_settings.py and
share the sign-in, page shell and code helpers defined here.

Sign-in is passwordless. The owner enters the business mobile that is on
file (TEXT_BACK_OWNER_MOBILE); if it matches, a six-digit code is texted to
that number and nothing else. The code lives ten minutes, allows five
guesses, and a browser session lasts twelve hours, or thirty days when the
owner ticks "Remember this phone". Pages are server-rendered Jinja2
templates (portal_ui.render) with no inline scripts or styles.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from text_back import portal_data, portal_messages, portal_scheduling
from text_back.messages import DEFAULT_TEMPLATES, MessageTemplateError, write_message_file
from text_back.portal_ui import render
from text_back.sms import enqueue_sms, run_due_sms

CODE_TTL = timedelta(minutes=10)
CODE_ATTEMPTS = 5
CODES_PER_WINDOW = 3
CODE_WINDOW = timedelta(minutes=15)
SESSION_TTL = timedelta(hours=12)
REMEMBER_TTL = timedelta(days=30)
SESSION_COOKIE = "text_back_client"
PENDING_COOKIE = "text_back_client_login"
CODE_FAILURE = "That code is not right or has expired. Check the text or send a new code."
REMEMBER_ON = "This phone stays signed in for 30 days."
REMEMBER_OFF = "This phone signs out after 12 hours."
HOME = "/client"
NO_MESSAGES_FILE = "Message editing isn't turned on for this account yet. Contact text_back to turn it on."

# Nav for the routes that exist in this build: (key, label, href, icon).
# Scheduling and Phone arrive in later layers; nothing here may point at a missing route.
NAV: tuple[tuple[str, str, str, str], ...] = (
    ("home", "Home", "/client", "home"),
    ("messages", "Messages", "/client/messages", "message"),
    ("scheduling", "Scheduling", "/client/scheduling", "clock"),
    ("business", "Business", "/client/business", "phone"),
    ("calendar", "Calendar", "/client/calendar", "calendar"),
)
MESSAGES_SUBTITLE = "Edit any text. Words in {braces} fill in by themselves."
SCHEDULING_SUBTITLE = "The few timing rules the assistant follows. Reset returns a rule to its default."

def nav_html(session, title: str, active: str) -> str:
    """Kept for the older string-built pages. The shell now draws the heading,
    the nav and the sign-out control, so there is nothing left to emit here."""
    return ""


def _shell(state, session, *, title: str, active: str, **ctx) -> dict:
    """Context every signed-in page passes to layout.html."""
    base = {
        "title": title,
        "active": active,
        "business_name": state.business_name,
        "csrf": session["csrf"] if session else "",
        "remember": bool(session.get("remember")) if session else False,
        "nav": list(NAV),
    }
    base.update(ctx)
    return base


def _page(title: str, body: str, *, script: str = "", session=None, active: str = "", state=None) -> HTMLResponse:
    """Bridge for the older string-built pages: the old body is shown inside the new shell.

    ``script`` is ignored: the CSP blocks inline scripts, and the shared
    portal.js handles counters through ``data-counter``.
    """
    business_name = getattr(state, "business_name", "") if state is not None else ""
    ctx = {
        "title": title,
        "active": active,
        "business_name": business_name,
        "csrf": session["csrf"] if session else "",
        "remember": bool(session.get("remember")) if session else False,
        "nav": list(NAV),
        "body": body,
    }
    return render("pages/legacy.html", **ctx)


def _now(state):
    return state.now_provider() if state.now_provider else datetime.now(timezone.utc)


def _mac(state, value: str) -> str:
    return hmac.new(state.webhook_secret.encode(), ("client-portal:" + value).encode(), hashlib.sha256).hexdigest()


def normalize_mobile(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        digits = "1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if 8 <= len(digits) <= 15 and raw.strip().startswith("+"):
        return "+" + digits
    return None


def _secure(state) -> bool:
    return str(state.public_base_url).lower().startswith("https://")


def _session(state, request: Request):
    token = request.cookies.get(SESSION_COOKIE, "")
    if not token:
        return None
    now = _now(state)
    with state.store.lock:
        # pending=0: a "code requested" row must never pass as a signed-in session.
        row = state.store.conn.execute(
            "SELECT * FROM client_sessions WHERE token_hash=? AND pending=0 AND expires_at>?", (_mac(state, token), now.isoformat())
        ).fetchone()
    return dict(row) if row else None


def _login_form(state, error: str = "", notice: str = "") -> HTMLResponse:
    return render("pages/login.html", title="Sign in", business_name=state.business_name, error=error, notice=notice)


def _verify_form(state, error: str = "") -> HTMLResponse:
    # No csrf, no nonce, no timestamp: two error responses must be byte-identical.
    remember_default = state.store.setting("remember_default") == "1"
    return render("pages/verify.html", title="Check your phone", business_name=state.business_name,
                  error=error, remember_default=remember_default)


def _messages_page(state, session, *, error: str = "", notice: str = "", drafts=None, errors=None, ask=None) -> HTMLResponse:
    """The Messages page from the current file (or the owner's rejected draft)."""
    ctx = portal_messages.page_context(state, drafts=drafts, errors=errors, ask=ask)
    if not ctx["editable"] and not error:
        error = NO_MESSAGES_FILE
    return render("pages/messages.html", **_shell(
        state, session, title="Messages", active="messages", subtitle=MESSAGES_SUBTITLE,
        error=error, notice=notice, **ctx))


def _scheduling_page(state, session, *, error: str = "", notice: str = "", values=None, errors=None) -> HTMLResponse:
    values = values if values is not None else portal_scheduling.current_values(state)
    return render("pages/scheduling.html", **_shell(
        state, session, title="Scheduling", active="scheduling", subtitle=SCHEDULING_SUBTITLE,
        error=error, notice=notice, **portal_scheduling.page_context(state, values, errors)))


def send_code(state, mobile: str, now: datetime, *, purpose: str = "sign-in") -> None:
    """Text a fresh six-digit code to ``mobile`` (rate limited per number)."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    key = f"login:{mobile}:{secrets.token_hex(8)}"
    with state.store.transaction():
        # The outbox is the durable record of codes actually texted.
        recent = state.store.conn.execute(
            "SELECT count(*) FROM sms_outbox WHERE kind='login_code' AND phone=? AND created_at>?",
            (mobile, (now - CODE_WINDOW).isoformat()),
        ).fetchone()[0]
        if recent >= CODES_PER_WINDOW:
            return
        state.store.conn.execute("DELETE FROM client_login_codes WHERE phone=?", (mobile,))
        state.store.conn.execute(
            "INSERT INTO client_login_codes(phone,code_hash,expires_at,attempts,created_at) VALUES(?,?,?,0,?)",
            (mobile, _mac(state, code), (now + CODE_TTL).isoformat(), now.isoformat()),
        )
        enqueue_sms(
            store=state.store, key=key, to=mobile, from_number=state.business_number, now=now,
            kind="login_code", body=f"{state.business_name} settings {purpose} code: {code}. It expires in 10 minutes.",
        )
    run_due_sms(store=state.store, telecom=state.telecom, now=now, policy=state.followup_policy,
                keys=[key], callback_base_url=state.public_base_url, immediate=True)
    with state.store.transaction():
        # Once handed to the carrier the code has no business sitting in the outbox.
        state.store.conn.execute(
            "UPDATE sms_outbox SET body='[sign-in code]' WHERE key=? AND status IN ('sent','unknown','dead_letter')", (key,)
        )


def check_code(state, phone: str, code: str, now: datetime) -> bool:
    """True when ``code`` is the live code for ``phone``; the code is consumed on success.
    Every failure (no code, expired, too many guesses, wrong digits) looks the same."""
    code = re.sub(r"\D", "", code or "")
    with state.store.transaction():
        row = state.store.conn.execute(
            "SELECT * FROM client_login_codes WHERE phone=? AND expires_at>?", (phone, now.isoformat())
        ).fetchone()
        if row is None or row["attempts"] >= CODE_ATTEMPTS:
            return False
        state.store.conn.execute("UPDATE client_login_codes SET attempts=attempts+1 WHERE phone=?", (phone,))
        if len(code) != 6 or not hmac.compare_digest(row["code_hash"], _mac(state, code)):
            return False
        state.store.conn.execute("DELETE FROM client_login_codes WHERE phone=?", (phone,))
        return True


def _set_session_cookie(response, state, token: str, remember: bool) -> None:
    ttl = REMEMBER_TTL if remember else SESSION_TTL
    response.set_cookie(SESSION_COOKIE, token, secure=_secure(state), httponly=True, samesite="lax",
                        max_age=int(ttl.total_seconds()), path="/client")


# --- Home ----------------------------------------------------------------------

def _calendar_card(state) -> dict:
    from text_back.client_settings import calendar_choices, calendar_status  # circular at import time

    view = calendar_status(state)
    names = {entry["id"]: entry.get("summary") or entry["id"] for entry in calendar_choices(state)}
    current = names.get(view["calendar_id"], view["calendar_id"]) or "your calendar"
    status = view["status"]
    card = {"action_href": "/client/calendar"}
    if status == "ready":
        card.update(title="Calendar connected", state="ok", state_word="Connected", detail=f"{current} \u00b7 Google", action_label="Open")
    elif status == "reauth_required":
        card.update(title="Calendar needs reconnecting", state="warn", state_word="Needs attention",
                    detail="Bookings are paused until you reconnect.", action_label="Reconnect")
    elif status == "unavailable":
        card.update(title="Calendar connection can't be read", state="err", state_word="Not working",
                    detail="Reconnect to resume bookings.", action_label="Open")
    elif status == "none":
        card.update(title="No calendar yet", state="warn", state_word="Not set up",
                    detail="Bookings aren't recorded anywhere.", action_label="Set up")
    else:
        provider = {"microsoft": "Microsoft 365", "icloud": "iCloud"}.get(view["provider"], view["provider"].title())
        card.update(title="Calendar connected", state="ok", state_word="Connected", detail=f"{provider}, managed for you", action_label="Open")
    return card


def _forwarding_card(state) -> dict:
    checklist = portal_data.forwarding_checklist(state)
    total, done = len(checklist["steps"]), checklist["done_count"]
    words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}
    if checklist["verified"]:
        return {"title": "Forwarding verified", "state": "ok", "state_word": "Verified",
                "detail": "All five checks done.", "action_label": "Open", "action_href": "/client/business"}
    left = total - done
    return {"title": f"Forwarding {done} of {total}", "state": "warn", "state_word": "Needs attention",
            "detail": f"{words.get(left, left)} check{'s' if left != 1 else ''} left.",
            "action_label": "Finish setup", "action_href": "/client/business"}


def _registration_card() -> dict | None:
    status = portal_data.registration_status()
    if status is None:
        return None
    detail = status["detail"]
    if status["state"]:
        detail = f"{detail} Status: {status['state'].replace('_', ' ').capitalize()}."
    return {"title": "Messaging registration", "state": "ok" if status["complete"] else "info",
            "state_word": status["headline"], "detail": detail}


def _home(state, session) -> HTMLResponse:
    now = _now(state)
    tz_name = state.timezone_name
    conversations = portal_data.recent_conversations(state.store, limit=10, now=now, tz_name=tz_name)
    rows = [{"id": index + 1, "cells": {
        "who": {"text": conv["display"], "sub": portal_data.format_contact_number(conv["phone"]) if conv["name"] else ""},
        "status": conv["status"], "last": conv["last_label"], "snippet": conv["snippet"] or "—"}}
        for index, conv in enumerate(conversations)]
    monday = portal_data.week_start(tz_name, now)
    return render("pages/home.html", **_shell(
        state, session, title="Home", active="home",
        calendar_card=_calendar_card(state), forwarding_card=_forwarding_card(state),
        registration_card=_registration_card(),
        week=portal_data.week_counts(state.store, tz_name, now),
        week_caption=f"Since Monday, {monday.strftime('%b %d').replace(' 0', ' ')}.",
        conversation_rows=rows,
    ))


def _account(state, session, *, notice: str = "", error: str = "") -> HTMLResponse:
    until = portal_data._parse(session["expires_at"])
    zone = portal_data._tz(state.timezone_name)
    label = until.astimezone(zone).strftime("%b %d, %Y").replace(" 0", " ") if until else "the session ends"
    return render("pages/account.html", **_shell(
        state, session, title="Account", active="",
        owner_mobile=session.get("phone", ""), signed_in_until=label, notice=notice, error=error))


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

    @app.get("/client", include_in_schema=False)
    @app.get("/client/", include_in_schema=False)
    def client_root(request: Request):
        session = _session(state, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        return _home(state, session)

    @app.get("/client/login", include_in_schema=False)
    def login_page(request: Request):
        if _session(state, request):
            return RedirectResponse(HOME, status_code=303)
        return _login_form(state)

    @app.post("/client/login", include_in_schema=False)
    async def login(request: Request):
        form = await request.form()
        mobile = normalize_mobile(str(form.get("mobile", "")))
        now = _now(state)
        if mobile is None:
            return _login_form(state, error="Enter the mobile number as digits, like 704 555 0123.")
        owner = getattr(state, "owner_mobile", "")
        if owner and hmac.compare_digest(mobile, owner):
            send_code(state, mobile, now)
        # Same answer either way so the page never confirms which number is on file.
        response = RedirectResponse("/client/verify", status_code=303)
        pending = secrets.token_urlsafe(24)
        with state.store.transaction():
            state.store.conn.execute(
                "INSERT INTO client_sessions(token_hash,csrf,phone,expires_at,created_at,pending) VALUES(?,?,?,?,?,1)",
                (_mac(state, pending), secrets.token_urlsafe(24), mobile, (now + CODE_TTL).isoformat(), now.isoformat()),
            )
        response.set_cookie(PENDING_COOKIE, pending, secure=_secure(state), httponly=True, samesite="lax",
                            max_age=int(CODE_TTL.total_seconds()), path="/client")
        return response

    def _pending(request: Request):
        token = request.cookies.get(PENDING_COOKIE, "")
        if not token:
            return None
        now = _now(state)
        with state.store.lock:
            row = state.store.conn.execute(
                "SELECT * FROM client_sessions WHERE token_hash=? AND pending=1 AND expires_at>?",
                (_mac(state, token), now.isoformat()),
            ).fetchone()
        return dict(row) if row else None

    @app.get("/client/verify", include_in_schema=False)
    def verify_page(request: Request):
        if _session(state, request):
            return RedirectResponse(HOME, status_code=303)
        if not _pending(request):
            return RedirectResponse("/client/login", status_code=303)
        return _verify_form(state)

    @app.post("/client/verify", include_in_schema=False)
    async def verify(request: Request):
        pending = _pending(request)
        if not pending:
            return RedirectResponse("/client/login", status_code=303)
        form = await request.form()
        now = _now(state)
        # One message for a wrong code, an expired code, too many guesses and a
        # number that is not on file, so the page never confirms which number is.
        if not check_code(state, pending["phone"], str(form.get("code", "")), now):
            return _verify_form(state, error=CODE_FAILURE)
        remember = str(form.get("remember", "")) == "1"
        ttl = REMEMBER_TTL if remember else SESSION_TTL
        with state.store.transaction():
            state.store.conn.execute("DELETE FROM client_sessions WHERE token_hash=?", (pending["token_hash"],))
            token = secrets.token_urlsafe(32)
            state.store.conn.execute(
                "INSERT INTO client_sessions(token_hash,csrf,phone,expires_at,created_at,pending,remember) VALUES(?,?,?,?,?,0,?)",
                (_mac(state, token), secrets.token_urlsafe(24), pending["phone"], (now + ttl).isoformat(), now.isoformat(), int(remember)),
            )
        response = RedirectResponse(HOME, status_code=303)
        _set_session_cookie(response, state, token, remember)
        response.delete_cookie(PENDING_COOKIE, path="/client")
        return response

    @app.get("/client/account", include_in_schema=False)
    def account_page(request: Request):
        session = _require(request)
        return _account(state, session)

    @app.post("/client/account", include_in_schema=False)
    @app.post("/client/account/remember", include_in_schema=False)
    async def account_remember(request: Request):
        session = _require(request)
        form = await request.form()
        if not hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
            raise HTTPException(400, "Form expired; reload the page and try again")
        now = _now(state)
        remember = str(form.get("remember", "")) == "1"
        with state.store.transaction():
            if remember:
                expires = now + REMEMBER_TTL
            else:
                current = portal_data._parse(session["expires_at"]) or now
                expires = min(current, now + SESSION_TTL)
            state.store.conn.execute(
                "UPDATE client_sessions SET remember=?, expires_at=? WHERE token_hash=?",
                (int(remember), expires.isoformat(), session["token_hash"]),
            )
            state.store.set_setting("remember_default", "1" if remember else "0", now=now)
        session = dict(session, remember=int(remember), expires_at=expires.isoformat())
        response = _account(state, session, notice=REMEMBER_ON if remember else REMEMBER_OFF)
        token = request.cookies.get(SESSION_COOKIE, "")
        if token:
            _set_session_cookie(response, state, token, remember)
        return response

    @app.get("/client/messages", include_in_schema=False)
    def messages_page(request: Request):
        session = _session(state, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        return _messages_page(state, session)

    @app.post("/client/messages", include_in_schema=False)
    async def save_messages(request: Request):
        session = _session(state, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        form = await request.form()
        if not hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
            raise HTTPException(400, "Form expired; reload the page and try again")
        if state.messages.path is None:
            return _messages_page(state, session, error=NO_MESSAGES_FILE)
        # A Reset button posts the whole form with that one field back to its default,
        # so it works without JS and never discards the owner's other edits.
        drafts, overrides, ask, reset_key = portal_messages.read_form(form)
        current = state.messages.current().templates
        base = {key: value for key, value in current.items() if value != DEFAULT_TEMPLATES[key]}
        errors = portal_messages.validate_fields(overrides, base)
        if errors:
            first = next(errors[key] for key in portal_messages.EDITABLE_KEYS if key in errors)
            return _messages_page(state, session, error=f"Not saved: {first}", drafts=drafts, errors=errors, ask=ask)
        try:
            write_message_file(state.messages.path, overrides)
        except MessageTemplateError as exc:  # the merged set is validated once more on write
            return _messages_page(state, session, error=f"Not saved: {portal_messages.owner_reason(str(exc))}",
                                  drafts=drafts, ask=ask)
        state.messages.current()  # pick up the new file right away
        return _messages_page(state, session, notice=portal_messages.RESET if reset_key else portal_messages.SAVED)

    @app.get("/client/scheduling", include_in_schema=False)
    def scheduling_page(request: Request):
        session = _require(request)
        return _scheduling_page(state, session)

    @app.post("/client/scheduling", include_in_schema=False)
    async def save_scheduling(request: Request):
        session = _require(request)
        form = await request.form()
        if not hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
            raise HTTPException(400, "Form expired; reload the page and try again")
        now = _now(state)
        reset_key = str(form.get("reset", "") or "")
        if reset_key:
            # Reset = this post with one group's fields at their defaults; everything else is kept.
            form = portal_scheduling.reset_form(form, reset_key, state)
            if form is None:
                return _scheduling_page(state, session, error="Nothing was reset. Reload the page and try again.")
        values, errors = portal_scheduling.parse_form(form, state)
        if errors:
            return _scheduling_page(state, session, error=f"Not saved: {portal_scheduling.first_error(errors)}",
                                    values=values, errors=errors)
        problem = portal_scheduling.save(state, values["_settings"], now)
        if problem:
            return _scheduling_page(state, session, error=f"Not saved: {problem}.", values=values)
        return _scheduling_page(state, session, notice=portal_scheduling.RESET if reset_key else portal_scheduling.SAVED)

    @app.post("/client/logout", include_in_schema=False)
    async def logout(request: Request):
        session = _session(state, request)
        form = await request.form()
        if session and hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
            with state.store.transaction():
                state.store.conn.execute("DELETE FROM client_sessions WHERE token_hash=?", (session["token_hash"],))
        response = RedirectResponse("/client/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE, path="/client")
        return response
