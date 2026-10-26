"""Owner portal (/client): sign-in, the shared page frame, Account and Messages.

Sign-in is passwordless. The owner enters the business mobile on file (TEXT_BACK_OWNER_MOBILE
or the saved owner mobile); if it matches, a six-digit code is texted to that number and
nothing else. A code lives ten minutes and allows five guesses; three sign-in requests per
number per 15 minutes, counted for ANY number so the notice never reveals which number is on
file. A session lasts 12 hours, or 30 days when the owner ticks "Remember this phone".

Every page is server-rendered from templates/client through portal_render.render(): one
stylesheet, one ES module, a strict CSP, CSRF on every POST, and pages that work with
JavaScript off. Every visible string is a row of docs/notes/portal-c/copy-deck.md.

Home, Schedule, Calendar and Phone live in client_settings.py and share the helpers here.
Async routes only parse the form; anything that touches SQLite, the telecom or the registry
runs in the threadpool, so the event loop never waits on I/O.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool

from text_back.messages import MessageTemplateError, write_message_file
from text_back.policy import format_contact_number
from text_back.portal_render import mount_static, render
from text_back.sms import enqueue_sms, run_due_sms

CODE_TTL = timedelta(minutes=10)
CODE_ATTEMPTS = 5
CODES_PER_WINDOW = 3
CODE_WINDOW = timedelta(minutes=15)
SESSION_TTL = timedelta(hours=12)
REMEMBER_TTL = timedelta(days=30)
SESSION_COOKIE = "text_back_client"
PENDING_COOKIE = "text_back_client_login"
HOME = "/client/home"
LOGIN = "/client/login"

# --- words (copy deck sections 1, 2, 8, 9; verbatim) ---------------------------------------
MOBILE_ERROR = "Enter your mobile as 10 digits, like 704 555 0123."
RATE_LIMITED = "We've sent three codes in the last 15 minutes. Wait a few minutes, then try again."
CODE_FAILURE = "That code isn't right, or it has expired. Check the text or send a new code."
SESSION_ENDED = "You were signed out. Sign in again to continue."
SIGNED_OUT_EVERYWHERE = "Signed out everywhere."
LOGIN_NOTICES = {"ended": SESSION_ENDED, "everywhere": SIGNED_OUT_EVERYWHERE}
REMEMBER_ON = "On. This phone stays signed in for 30 days."
REMEMBER_OFF = "Off. This phone signs out after 12 hours."
SAVED = "Saved."

NAV: tuple[tuple[str, str], ...] = (("home", "Home"), ("messages", "Messages"), ("schedule", "Schedule"),
                                    ("calendar", "Calendar"), ("phone", "Phone"))


class FormExpired(Exception):
    """A POST whose CSRF token does not match the session: answered with the HTML
    "This page expired" page (status 400). Nothing is saved."""

    def __init__(self, reload_url: str):
        super().__init__(reload_url)
        self.reload_url = reload_url


class Redirect(Exception):
    def __init__(self, target: str):
        super().__init__(target)
        self.target = target


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


def require_session(state, request: Request) -> dict:
    """The signed-in session, or a redirect to sign-in (with "You were signed out." when a
    session cookie was presented that no longer works)."""
    session = _session(state, request)
    if session:
        return session
    raise Redirect(LOGIN + ("?notice=ended" if request.cookies.get(SESSION_COOKIE) else ""))


def check_csrf(form, session, reload_url: str) -> None:
    if not hmac.compare_digest(str(form.get("csrf", "") or ""), session["csrf"]):
        raise FormExpired(reload_url)


def shell(state, session, *, title: str, nav: str | None, notice: str = "") -> dict:
    """Context every signed-in page passes to base.html.j2."""
    return {
        "title": title,
        "business_name": state.business_name,
        "nav": NAV,
        "nav_active": nav,
        "csrf": session["csrf"],
        "signed_in_with": format_contact_number(session["phone"]),
        "notice": notice,
        "tz": getattr(state, "timezone_name", "UTC") or "UTC",
        "now": _now(state),
        "tb_data": None,
    }


def _set_session_cookie(response, state, token: str, remember: bool) -> None:
    ttl = REMEMBER_TTL if remember else SESSION_TTL
    response.set_cookie(SESSION_COOKIE, token, secure=_secure(state), httponly=True, samesite="lax",
                        max_age=int(ttl.total_seconds()), path="/client")


# --- sign in -------------------------------------------------------------------

def _login_form(request: Request, state, *, error: str = "", notice: str = "") -> HTMLResponse:
    return render(request, "client/login.html.j2", title="Sign in", error=error, notice=notice)


def _verify_form(request: Request, state, *, error: str = "") -> HTMLResponse:
    # Inputs are the business name and the error only: no number, csrf, clock or
    # per-request value, so the page is identical for an unknown number and a wrong code.
    return render(request, "client/verify.html.j2", title="Check your phone", business_name=state.business_name, error=error)


def send_code(state, mobile: str, now: datetime, *, purpose: str = "sign-in") -> None:
    """Text a fresh six-digit code to ``mobile`` (at most three per 15 minutes per number)."""
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


def _request_login(state, mobile: str, now: datetime) -> str | None:
    """Record one sign-in request and text a code when ``mobile`` is on file.

    Returns the pending-login cookie value, or None when this number already asked three
    times in 15 minutes (counted for every number, known or not)."""
    with state.store.transaction():
        conn = state.store.conn
        conn.execute("DELETE FROM client_login_requests WHERE created_at<=?", ((now - CODE_WINDOW).isoformat(),))
        recent = conn.execute("SELECT count(*) FROM client_login_requests WHERE phone=? AND created_at>?",
                              (mobile, (now - CODE_WINDOW).isoformat())).fetchone()[0]
        if recent >= CODES_PER_WINDOW:
            return None
        conn.execute("INSERT INTO client_login_requests(phone,created_at) VALUES(?,?)", (mobile, now.isoformat()))
    owner = getattr(state, "owner_mobile", "") or ""
    if owner and hmac.compare_digest(mobile, owner):
        send_code(state, mobile, now)
    pending = secrets.token_urlsafe(24)
    with state.store.transaction():
        state.store.conn.execute(
            "INSERT INTO client_sessions(token_hash,csrf,phone,expires_at,created_at,pending) VALUES(?,?,?,?,?,1)",
            (_mac(state, pending), secrets.token_urlsafe(24), mobile, (now + CODE_TTL).isoformat(), now.isoformat()),
        )
    return pending


# --- Account -------------------------------------------------------------------

def account_view(state, session, *, confirm_everywhere: bool = False) -> dict:
    now = _now(state)
    with state.store.lock:
        rows = state.store.conn.execute(
            "SELECT token_hash, created_at FROM client_sessions WHERE pending=0 AND expires_at>? ORDER BY created_at DESC",
            (now.isoformat(),)).fetchall()
    others = [{"signed_in": datetime.fromisoformat(row["created_at"])} for row in rows
              if row["token_hash"] != session["token_hash"]]
    remember = bool(session.get("remember"))
    return {
        "signed_in_as": format_contact_number(session["phone"]),
        "this_device": {"signed_in": datetime.fromisoformat(session["created_at"]),
                        "until": datetime.fromisoformat(session["expires_at"])},
        "other_devices": others,
        "remember": remember,
        "remember_status": REMEMBER_ON if remember else REMEMBER_OFF,
        "confirm_everywhere": confirm_everywhere,
    }


def _account_page(request: Request, state, session, *, notice: str = "", confirm_everywhere: bool = False):
    return render(request, "client/account.html.j2",
                  **shell(state, session, title="Account", nav="account", notice=notice),
                  **account_view(state, session, confirm_everywhere=confirm_everywhere))


# --- Messages -------------------------------------------------------------------

def _messages_page(request: Request, state, session, *, notice: str = "", values=None, asked=None, error: str = "",
                   scenario: str = ""):
    from text_back import portal_messages

    view = portal_messages.page_view(state, _now(state), values=values, asked=asked, error=error)
    ids = [s.id for s in view["rail"]]
    view["scenario"] = scenario if scenario in ids else ids[0]
    tb_data = view.pop("tb_data")
    title = "Not saved · Messages" if view["error_summary"] else "Messages"
    context = shell(state, session, title=title, nav="messages", notice=notice)
    context["tb_data"] = tb_data
    savebar_initial = "error" if view["error_summary"] else ("saved" if notice else "clean")
    return render(request, "client/messages.html.j2", **context, savebar_initial=savebar_initial, **view)


def _save_messages(request: Request, state, session, form):
    from text_back import portal_messages

    if state.messages.path is None:
        return _messages_page(request, state, session)
    submitted, overrides, asked = portal_messages.read_form(form)
    before = state.messages.current()
    try:
        write_message_file(state.messages.path, overrides)
    except MessageTemplateError as exc:
        return _messages_page(request, state, session, error=str(exc), values=submitted, asked=asked)
    after = state.messages.current()  # pick up the new file right away
    notice = portal_messages.change_summary(before.templates, after.templates, set(before.fields), set(after.fields))
    return _messages_page(request, state, session, notice=notice)


# --- routes --------------------------------------------------------------------

def install_routes(app):
    state = app.state
    mount_static(app)

    @app.exception_handler(Redirect)
    async def _redirect(request: Request, exc: Redirect):
        return RedirectResponse(exc.target, status_code=303)

    def _expired(request: Request, exc: FormExpired):
        session = _session(state, request)
        if not session:
            return RedirectResponse(LOGIN, status_code=303)
        nav = exc.reload_url.split("/")[2] if exc.reload_url.count("/") >= 2 else None
        return render(request, "client/expired.html.j2", status_code=400,
                      **shell(state, session, title="This page expired", nav=nav), reload_url=exc.reload_url)

    @app.exception_handler(FormExpired)
    async def _form_expired(request: Request, exc: FormExpired):
        return await run_in_threadpool(_expired, request, exc)

    @app.get("/client", include_in_schema=False)
    @app.get("/client/", include_in_schema=False)
    def client_root(request: Request):
        return RedirectResponse(HOME if _session(state, request) else LOGIN, status_code=303)

    @app.get("/client/login", include_in_schema=False)
    def login_page(request: Request, notice: str = ""):
        if _session(state, request):
            return RedirectResponse(HOME, status_code=303)
        response = _login_form(request, state, notice=LOGIN_NOTICES.get(notice, ""))
        if request.cookies.get(SESSION_COOKIE):
            response.delete_cookie(SESSION_COOKIE, path="/client")
        return response

    @app.post("/client/login", include_in_schema=False)
    async def login(request: Request):
        form = await request.form()
        mobile = normalize_mobile(str(form.get("mobile", "") or ""))
        if mobile is None:
            return _login_form(request, state, error=MOBILE_ERROR)
        pending = await run_in_threadpool(_request_login, state, mobile, _now(state))
        if pending is None:
            return _login_form(request, state, notice=RATE_LIMITED)
        # Same answer either way so the page never confirms which number is on file.
        response = RedirectResponse("/client/verify", status_code=303)
        response.set_cookie(PENDING_COOKIE, pending, secure=_secure(state), httponly=True, samesite="lax",
                            max_age=int(CODE_TTL.total_seconds()), path="/client")
        return response

    def _pending(request: Request):
        token = request.cookies.get(PENDING_COOKIE, "")
        if not token:
            return None
        with state.store.lock:
            row = state.store.conn.execute(
                "SELECT * FROM client_sessions WHERE token_hash=? AND pending=1 AND expires_at>?",
                (_mac(state, token), _now(state).isoformat()),
            ).fetchone()
        return dict(row) if row else None

    @app.get("/client/verify", include_in_schema=False)
    def verify_page(request: Request):
        if _session(state, request):
            return RedirectResponse(HOME, status_code=303)
        if not _pending(request):
            return RedirectResponse(LOGIN, status_code=303)
        return _verify_form(request, state)

    def _verify(request: Request, form):
        pending = _pending(request)
        if not pending:
            return RedirectResponse(LOGIN, status_code=303)
        now = _now(state)
        # One message for a wrong code, an expired code, too many guesses and a
        # number that is not on file, so the page never confirms which number is.
        if not check_code(state, pending["phone"], str(form.get("code", "") or ""), now):
            return _verify_form(request, state, error=CODE_FAILURE)
        remember = str(form.get("remember", "") or "") == "1"
        token = secrets.token_urlsafe(32)
        with state.store.transaction():
            state.store.conn.execute("DELETE FROM client_sessions WHERE token_hash=?", (pending["token_hash"],))
            state.store.conn.execute(
                "INSERT INTO client_sessions(token_hash,csrf,phone,expires_at,created_at,pending,remember) VALUES(?,?,?,?,?,0,?)",
                (_mac(state, token), secrets.token_urlsafe(24), pending["phone"],
                 (now + (REMEMBER_TTL if remember else SESSION_TTL)).isoformat(), now.isoformat(), int(remember)),
            )
        response = RedirectResponse(HOME, status_code=303)
        _set_session_cookie(response, state, token, remember)
        response.delete_cookie(PENDING_COOKIE, path="/client")
        return response

    @app.post("/client/verify", include_in_schema=False)
    async def verify(request: Request):
        form = await request.form()
        return await run_in_threadpool(_verify, request, form)

    def _logout(request: Request, form):
        session = _session(state, request)
        if session and hmac.compare_digest(str(form.get("csrf", "") or ""), session["csrf"]):
            with state.store.transaction():
                state.store.conn.execute("DELETE FROM client_sessions WHERE token_hash=?", (session["token_hash"],))
        response = RedirectResponse(LOGIN, status_code=303)
        response.delete_cookie(SESSION_COOKIE, path="/client")
        return response

    @app.post("/client/logout", include_in_schema=False)
    async def logout(request: Request):
        form = await request.form()
        return await run_in_threadpool(_logout, request, form)

    # --- Account -----------------------------------------------------------------

    @app.get("/client/account", include_in_schema=False)
    def account_page(request: Request):
        session = require_session(state, request)
        return _account_page(request, state, session)

    def _remember(request: Request, form):
        session = require_session(state, request)
        check_csrf(form, session, "/client/account")
        now = _now(state)
        remember = str(form.get("remember", "") or "") == "1"
        if remember:
            expires = now + REMEMBER_TTL
        else:
            expires = min(datetime.fromisoformat(session["expires_at"]), now + SESSION_TTL)
        with state.store.transaction():
            state.store.conn.execute("UPDATE client_sessions SET remember=?, expires_at=? WHERE token_hash=?",
                                     (int(remember), expires.isoformat(), session["token_hash"]))
        session = dict(session, remember=int(remember), expires_at=expires.isoformat())
        response = _account_page(request, state, session, notice=SAVED)
        token = request.cookies.get(SESSION_COOKIE, "")
        if token:
            response.set_cookie(SESSION_COOKIE, token, secure=_secure(state), httponly=True, samesite="lax",
                                max_age=max(0, int((expires - now).total_seconds())), path="/client")
        return response

    @app.post("/client/account/remember", include_in_schema=False)
    async def account_remember(request: Request):
        form = await request.form()
        return await run_in_threadpool(_remember, request, form)

    def _signout_everywhere(request: Request, form):
        session = require_session(state, request)
        check_csrf(form, session, "/client/account")
        if str(form.get("confirm", "") or "") != "1":
            # Step one: the inline confirmation, no modal. Nothing has changed yet.
            return _account_page(request, state, session, confirm_everywhere=True)
        with state.store.transaction():
            # Every signed-in session: one owner per deployment, and sessions from before a
            # mobile change still carry the old number.
            state.store.conn.execute("DELETE FROM client_sessions WHERE pending=0")
        response = RedirectResponse(LOGIN + "?notice=everywhere", status_code=303)
        response.delete_cookie(SESSION_COOKIE, path="/client")
        return response

    @app.post("/client/account/signout-everywhere", include_in_schema=False)
    async def signout_everywhere(request: Request):
        form = await request.form()
        return await run_in_threadpool(_signout_everywhere, request, form)

    # --- Messages ----------------------------------------------------------------

    @app.get("/client/messages", include_in_schema=False)
    def messages_page(request: Request, scenario: str = ""):
        session = require_session(state, request)
        return _messages_page(request, state, session, scenario=scenario)

    def _save(request: Request, form):
        session = require_session(state, request)
        check_csrf(form, session, "/client/messages")
        return _save_messages(request, state, session, form)

    @app.post("/client/messages", include_in_schema=False)
    async def save_messages(request: Request):
        form = await request.form()
        return await run_in_threadpool(_save, request, form)
