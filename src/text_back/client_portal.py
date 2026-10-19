"""Client settings page: the business owner signs in and edits message copy.

Sign-in is passwordless. The owner enters the business mobile that is on
file (TEXT_BACK_OWNER_MOBILE); if it matches, a six-digit code is texted to
that number and nothing else. The code lives ten minutes, allows five
guesses, and a browser session lasts twelve hours. Everything is
server-rendered HTML with no external assets.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from text_back.messages import (
    DEFAULT_TEMPLATES,
    PLACEHOLDERS,
    MessageTemplateError,
    write_message_file,
)
from text_back.sms import enqueue_sms, run_due_sms

CODE_TTL = timedelta(minutes=10)
CODE_ATTEMPTS = 5
CODES_PER_WINDOW = 3
CODE_WINDOW = timedelta(minutes=15)
SESSION_TTL = timedelta(hours=12)
SESSION_COOKIE = "text_back_client"
PENDING_COOKIE = "text_back_client_login"

# Order and wording of the settings form. (key, label, when it is sent)
FIELDS = (
    ("intro", "First text after a missed call", "Sent the moment a call goes unanswered."),
    ("prompt_service", "Question 1: the job", "Asked after the caller replies."),
    ("prompt_location", "Question 2: the location", ""),
    ("prompt_preferred_time", "Question 3: day and time", ""),
    ("prompt_name", "Question 4: the name", ""),
    ("preferred_time_reprompt", "When the time could not be understood", ""),
    ("slot_unavailable", "When the calendar slot is taken", ""),
    ("booking_confirmation", "Booking confirmation", "Sent only after the calendar event exists."),
    ("booking_error", "When the calendar failed", "Must say no booking was made."),
    ("followup_1", "First follow-up (no reply)", "Sent after the first follow-up delay."),
    ("followup_2", "Last follow-up (no reply)", ""),
    ("handoff_ack", "When the owner needs to step in", "Must promise a follow-up."),
    ("handoff_ack_safety", "Safety hand-off", "Must mention 911 and promise a follow-up."),
    ("opt_in", "Reply to START", ""),
    ("help", "Reply to HELP", ""),
    ("opt_out_ack", "Reply to STOP", ""),
    ("opt_out_suffix", "Opt-out line", "Added to the first text, follow-ups, START and HELP replies when they leave out the word STOP. Must mention STOP."),
)

STYLE = (
    "body{font:17px/1.5 system-ui,sans-serif;max-width:44rem;margin:4vh auto;padding:0 20px 40px;color:#18212b;background:#f6f8fa}"
    "h1{font-size:1.5rem;margin:0 0 .5rem}h2{font-size:1.05rem;margin:1.6rem 0 .3rem}"
    "label{display:block;font-weight:600;margin-top:1.2rem}small{color:#5b6773;display:block}"
    "input,textarea{width:100%;box-sizing:border-box;font:inherit;padding:10px;border:1px solid #c5ccd3;border-radius:6px;background:#fff;margin-top:6px}"
    "textarea{min-height:5.5rem}button{font:inherit;font-weight:600;padding:10px 18px;border:0;border-radius:6px;background:#1b5e9e;color:#fff;cursor:pointer;margin-top:1rem}"
    ".err{background:#fde8e8;border:1px solid #f3b4b4;padding:12px;border-radius:6px}.ok{background:#e6f4ea;border:1px solid #a9d8b4;padding:12px;border-radius:6px}"
    ".def{color:#5b6773;font-size:.92rem;margin:.3rem 0 0}.count{font-size:.85rem;color:#5b6773;text-align:right}nav{display:flex;justify-content:space-between;align-items:center}"
    "nav form{margin:0}nav button{background:#e8ecf0;color:#18212b;margin:0;padding:6px 12px}"
)

COUNT_SCRIPT = (
    "document.querySelectorAll('textarea').forEach(function(t){var c=document.createElement('div');c.className='count';"
    "function u(){var n=(t.value||t.placeholder).length;c.textContent=n+' characters, '+Math.max(1,Math.ceil(n/160))+' text segment'+(n>160?'s':'');}"
    "t.after(c);t.addEventListener('input',u);u();});"
)


def _page(title: str, body: str, *, script: str = "") -> HTMLResponse:
    doc = (
        "<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{STYLE}</style></head><body><main>{body}</main>"
        + (f"<script>{script}</script>" if script else "")
        + "</body></html>"
    )
    return HTMLResponse(doc, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY"})


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
        row = state.store.conn.execute(
            "SELECT * FROM client_sessions WHERE token_hash=? AND expires_at>?", (_mac(state, token), now.isoformat())
        ).fetchone()
    return dict(row) if row else None


def _login_form(error: str = "", notice: str = "") -> HTMLResponse:
    msg = f"<p class=err>{html.escape(error)}</p>" if error else (f"<p class=ok>{html.escape(notice)}</p>" if notice else "")
    return _page(
        "Sign in",
        "<h1>Scheduling assistant settings</h1>"
        "<p>Enter the business mobile number on file. We'll text you a sign-in code.</p>"
        f"{msg}<form method=post action=/client/login><label for=mobile>Business mobile</label>"
        "<input id=mobile name=mobile type=tel autocomplete=tel inputmode=tel required maxlength=24>"
        "<button type=submit>Text me a code</button></form>",
    )


def _verify_form(error: str = "") -> HTMLResponse:
    msg = f"<p class=err>{html.escape(error)}</p>" if error else ""
    return _page(
        "Enter code",
        "<h1>Check your phone</h1><p>Enter the six-digit code we just texted. It expires in ten minutes.</p>"
        f"{msg}<form method=post action=/client/verify><label for=code>Sign-in code</label>"
        "<input id=code name=code inputmode=numeric autocomplete=one-time-code pattern='[0-9]{6}' required maxlength=6>"
        "<button type=submit>Sign in</button></form><p><a href=/client/login>Send a new code</a></p>",
    )


def _messages_form(state, session, *, error: str = "", notice: str = "") -> HTMLResponse:
    source = state.messages
    current = source.current().templates
    editable = source.path is not None
    msg = f"<p class=err>{html.escape(error)}</p>" if error else (f"<p class=ok>{html.escape(notice)}</p>" if notice else "")
    if not editable:
        msg += "<p class=err>Message editing is not set up for this account yet. Ask your operator to enable it.</p>"
    rows = []
    for key, label, hint in FIELDS:
        value = current[key] if current[key] != DEFAULT_TEMPLATES[key] else ""
        allowed = " ".join("{" + p + "}" for p in sorted(PLACEHOLDERS[key]))
        rows.append(
            f"<label for=f_{key}>{html.escape(label)}</label>"
            + (f"<small>{html.escape(hint)}</small>" if hint else "")
            + (f"<small>You can use: {html.escape(allowed)}</small>" if allowed else "")
            + f"<textarea id=f_{key} name={key} maxlength=480 placeholder=\"{html.escape(DEFAULT_TEMPLATES[key], quote=True)}\""
            + ("" if editable else " disabled")
            + f">{html.escape(value)}</textarea>"
            + "<p class=def>Leave blank to use the standard wording shown in grey.</p>"
        )
    body = (
        "<nav><h1>Your messages</h1><form method=post action=/client/logout>"
        f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'><button type=submit>Sign out</button></form></nav>"
        f"<p>These are the texts <strong>{html.escape(state.business_name)}</strong>'s scheduling assistant sends. "
        "Edit any of them; {business_name} and the other bracketed words are filled in automatically.</p>"
        + msg
        + "<form method=post action=/client/messages>"
        + f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'>"
        + "".join(rows)
        + ("<button type=submit>Save messages</button>" if editable else "")
        + "</form>"
    )
    return _page("Your messages", body, script=COUNT_SCRIPT)


def install_routes(app):
    state = app.state

    def send_code(mobile: str, now: datetime) -> None:
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
                kind="login_code", body=f"{state.business_name} settings sign-in code: {code}. It expires in 10 minutes.",
            )
        run_due_sms(store=state.store, telecom=state.telecom, now=now, policy=state.followup_policy,
                    keys=[key], callback_base_url=state.public_base_url, immediate=True)

    @app.get("/client", include_in_schema=False)
    @app.get("/client/", include_in_schema=False)
    def client_root(request: Request):
        return RedirectResponse("/client/messages" if _session(state, request) else "/client/login", status_code=303)

    @app.get("/client/login", include_in_schema=False)
    def login_page(request: Request):
        if _session(state, request):
            return RedirectResponse("/client/messages", status_code=303)
        return _login_form()

    @app.post("/client/login", include_in_schema=False)
    async def login(request: Request):
        form = await request.form()
        mobile = normalize_mobile(str(form.get("mobile", "")))
        now = _now(state)
        if mobile is None:
            return _login_form(error="Enter the mobile number as digits, like 704 555 0123.")
        owner = getattr(state, "owner_mobile", "")
        if owner and hmac.compare_digest(mobile, owner):
            send_code(mobile, now)
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
            return RedirectResponse("/client/messages", status_code=303)
        if not _pending(request):
            return RedirectResponse("/client/login", status_code=303)
        return _verify_form()

    @app.post("/client/verify", include_in_schema=False)
    async def verify(request: Request):
        pending = _pending(request)
        if not pending:
            return RedirectResponse("/client/login", status_code=303)
        form = await request.form()
        code = re.sub(r"\D", "", str(form.get("code", "")))
        now = _now(state)
        with state.store.transaction():
            row = state.store.conn.execute(
                "SELECT * FROM client_login_codes WHERE phone=? AND expires_at>?", (pending["phone"], now.isoformat())
            ).fetchone()
            if row is None or row["attempts"] >= CODE_ATTEMPTS:
                return _verify_form(error="That code has expired. Send a new one.")
            state.store.conn.execute("UPDATE client_login_codes SET attempts=attempts+1 WHERE phone=?", (pending["phone"],))
            if len(code) != 6 or not hmac.compare_digest(row["code_hash"], _mac(state, code)):
                return _verify_form(error="That code is not right. Check the text and try again.")
            state.store.conn.execute("DELETE FROM client_login_codes WHERE phone=?", (pending["phone"],))
            state.store.conn.execute("DELETE FROM client_sessions WHERE token_hash=?", (pending["token_hash"],))
            token = secrets.token_urlsafe(32)
            state.store.conn.execute(
                "INSERT INTO client_sessions(token_hash,csrf,phone,expires_at,created_at,pending) VALUES(?,?,?,?,?,0)",
                (_mac(state, token), secrets.token_urlsafe(24), pending["phone"], (now + SESSION_TTL).isoformat(), now.isoformat()),
            )
        response = RedirectResponse("/client/messages", status_code=303)
        response.set_cookie(SESSION_COOKIE, token, secure=_secure(state), httponly=True, samesite="lax",
                            max_age=int(SESSION_TTL.total_seconds()), path="/client")
        response.delete_cookie(PENDING_COOKIE, path="/client")
        return response

    @app.get("/client/messages", include_in_schema=False)
    def messages_page(request: Request):
        session = _session(state, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        return _messages_form(state, session)

    @app.post("/client/messages", include_in_schema=False)
    async def save_messages(request: Request):
        session = _session(state, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        form = await request.form()
        if not hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
            raise HTTPException(400, "Form expired; reload the page and try again")
        if state.messages.path is None:
            return _messages_form(state, session, error="Message editing is not set up for this account yet.")
        submitted = {key: str(form.get(key, "")).strip() for key, _, _ in FIELDS}
        overrides = {key: value for key, value in submitted.items() if value}
        try:
            write_message_file(state.messages.path, overrides)
        except MessageTemplateError as exc:
            return _messages_form(state, session, error=f"Not saved: {exc}")
        state.messages.current()  # pick up the new file right away
        return _messages_form(state, session, notice="Saved. New conversations use these messages from now on.")

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
