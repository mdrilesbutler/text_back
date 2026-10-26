"""Tailnet-only preview of branch ui/compare-c (candidate C) with a fake phone service.

No text message is ever sent. The latest sign-in code is shown at /preview/code.
Run from the worktree root:  .venv/bin/python docs/notes/ui-compare-c/preview.py <empty data dir> [host] [port]
Defaults: 100.124.192.46:8766 (the tailnet address; never 8000/8443/8765/8003). For a private
save-check copy, pass 127.0.0.1 and another port.

Every seeded caller goes through the real pipeline (voice webhook handler, inbound SMS handler,
worker, stub calendar) on a clock set to times earlier today, so Home, the forwarding checks and
the bookings show what the product would really record. Seeded callers carry an "Example" tag.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

DATA = Path(sys.argv[1]).resolve(); DATA.mkdir(parents=True, exist_ok=True)
HOST = sys.argv[2] if len(sys.argv) > 2 else "100.124.192.46"
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 8766
assert PORT not in (8000, 8443, 8765, 8003, 443), "that port belongs to the live service or another preview"
TZ = "America/New_York"
OWNER, BUSINESS_LINE, TEXTING = "+19805550123", "+17045550123", "+17045550100"
PUBLIC = "https://hermes-cloud.tailefb1a4.ts.net:8443"  # production-shaped link host (never this preview's host)

messages = DATA / "messages.json"
if not messages.exists():
    messages.write_text(json.dumps({
        "intro": "Hey, this is Oak & Pine Tree Care. Sorry we missed your call. What do you need done?",
        "prompt_location": "What's the address for the job?",
    }))
os.environ.update({
    "TEXT_BACK_OWNER_MOBILE": OWNER,
    "TEXT_BACK_MESSAGES_FILE": str(messages),
    "TEXT_BACK_TIMEZONE": TZ,
    "TEXT_BACK_HANDOFF_DESTINATION": "operator",
    # A fictional 555-01xx support number, so "Text FluxWorks support" shows where the product offers it (P3).
    "TEXT_BACK_SUPPORT_CONTACT": "+17045550199",
})
for key in list(os.environ):
    if key.endswith("_API_KEY"):
        os.environ.pop(key)

import uvicorn  # noqa: E402

from text_back import inbox, worker  # noqa: E402
from text_back.app import create_app  # noqa: E402
from text_back.telecom import FakeTelecom  # noqa: E402


class PreviewChatTransport:
    """Stands in for the production chat channel (Telegram) without any network: alerts are kept
    in memory. The portal words the steps-back cards from the channel name, so the preview shows
    what a production client sees."""

    channel_name = "telegram"

    def __init__(self):
        self.delivered = []

    def deliver(self, alert):
        self.delivered.append(alert)
        return f"preview-{len(self.delivered):04d}"


class TimedTelecom(FakeTelecom):
    """FakeTelecom that remembers when each text went out, for the code page. Nothing leaves the box."""

    def __init__(self):
        super().__init__(); self.sent_at = []

    def send_sms(self, **kw):
        self.sent_at.append(datetime.now(timezone.utc)); return super().send_sms(**kw)


CLOCK = [None]
telecom = TimedTelecom()
app = create_app(db_path=str(DATA / "preview.db"), telecom=telecom, public_base_url=PUBLIC,
                 business_name="Oak & Pine Tree Care", timezone_name=TZ,
                 now_provider=lambda: CLOCK[0] or datetime.now(timezone.utc),
                 delivery_transport=PreviewChatTransport(), handoff_destination="operator")
state = app.state
state.business_number = TEXTING
state.cookie_secure = False  # served over plain http on the tailnet; links keep the https host
store = state.store

EXAMPLES = {"+19805550141": "Dana Whitfield", "+19805550177": "Marcus Lee", "+19805550192": "Priya Natarajan"}
state.preview_example_phones = set(EXAMPLES)
# The forwarding checks and the texting approval on Home come from the seeded calls and settings below.
state.preview_example_setup = {"forwarding", "approval"}


def seed() -> None:
    if store.setting("preview_seeded"):
        return
    now = datetime.now(timezone.utc)
    local = now.astimezone(ZoneInfo(TZ))
    week_start = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    # Seed times earlier today, never before this week's Monday, so counts and rows share one window.
    # Before late morning the offsets shrink so seeded calls never land in the small hours.
    scale = 1 if local.hour >= 13 else 0.15
    def at(minutes_ago: int) -> datetime:
        return max(now - timedelta(minutes=int(minutes_ago * scale)), week_start.astimezone(timezone.utc) + timedelta(minutes=5))

    store.set_setting("business_line", BUSINESS_LINE, now=now)
    store.set_setting("business_contact", "(704) 555-0123", now=now)
    store.set_setting("carrier", "verizon", now=now)
    store.set_setting("texting_approval_state", "waiting", now=now)
    # One other signed-in device, so Account shows "Another device · last used …" (tagged Example).
    import secrets
    device = secrets.token_hex(32)
    used = (local - timedelta(days=3)).replace(hour=17, minute=30, second=0, microsecond=0).astimezone(timezone.utc)
    with store.transaction():
        store.conn.execute(
            "INSERT INTO client_sessions(token_hash,csrf,phone,expires_at,created_at,pending,remember,last_used_at) "
            "VALUES(?,?,?,?,?,0,1,?)", (device, secrets.token_urlsafe(24), OWNER, (now + timedelta(days=27)).isoformat(),
                                       (used - timedelta(hours=2)).isoformat(), used.isoformat()))
    store.set_setting("preview_example_session", device, now=now)
    store.set_setting("working_hours", json.dumps({d: {"open": "08:00", "close": "17:00"} for d in ("mon", "tue", "wed", "thu", "fri")}), now=now)

    def step(t: datetime, kind: str, **params) -> None:
        CLOCK[0] = t
        inbox.submit_event(state=state, kind=kind, params=params)
        for _ in range(3):
            worker.run_once(state)

    n = 0
    def sms(phone, t, body):
        nonlocal n; n += 1
        step(t, "sms", message_sid=f"SMpreview{n}", from_number=phone, to_number=TEXTING, body=body)

    # Dana: a call forwarded from the business line, then a full booking (on the stub test calendar).
    dana, t = "+19805550141", at(330)
    step(t, "voice", call_sid="CApreview1", call_status="ringing", from_number=dana, to_number=TEXTING, forwarded_from=BUSINESS_LINE)
    for i, body in enumerate(("Tree trimming", "412 Maple St, Charlotte", "Thursday at 10", "Dana Whitfield"), 1):
        sms(dana, t + timedelta(minutes=2 * i), body)
    # Marcus: asks for a call back, so the assistant steps back.
    marcus, t = "+19805550177", at(170)
    step(t, "voice", call_sid="CApreview2", call_status="ringing", from_number=marcus, to_number=TEXTING, forwarded_from=BUSINESS_LINE)
    sms(marcus, t + timedelta(minutes=3), "Stump grinding, two stumps")
    sms(marcus, t + timedelta(minutes=5), "Can you have someone call me instead?")
    # Priya: missed call, no reply yet.
    priya, t = "+19805550192", at(45)
    step(t, "voice", call_sid="CApreview3", call_status="ringing", from_number=priya, to_number=TEXTING, forwarded_from=BUSINESS_LINE)
    for phone, name in EXAMPLES.items():
        store.set_conversation_field(phone, "name", name)
    CLOCK[0] = None
    store.set_setting("preview_seeded", now.isoformat(), now=now)


seed()


# --- Preview only: a busy business (TEXT_BACK_PREVIEW_FULL=1). ---------------------------------------
# Twenty callers today through the real pipeline (forwarded calls, real replies, real bookings on the stub
# calendar), forwarding fully checked, texting approved, and a connected Google calendar shown for the
# owner. Every seeded caller, count and calendar card carries the Example tag.
FULL = os.environ.get("TEXT_BACK_PREVIEW_FULL") == "1"

FULL_CALLERS = [
    # name, job, address, outcome, extra
    ("Tom Alvarez", "Oak removal, leaning toward the garage", "1907 Laurel Ave, Charlotte", "book", "Tuesday at 9"),
    ("Grace Kim", "Hedge trimming", "54 Wren Ct, Mint Hill", "book", "Wednesday at 1pm"),
    ("Luis Ortega", "Storm limb on the roof", None, "danger", None),
    ("Hannah Brooks", "Pine removal", "720 Sharon Rd, Charlotte", "book", "Friday at 3pm"),
    ("Derek Patel", "Crown thinning on two maples", "16 Elm Row, Pineville", "texting", None),
    ("Sofia Rossi", "Stump grinding", "3301 Park Rd, Charlotte", "book", "Thursday at 2pm"),
    ("Ben Carter", "Quote for land clearing", "Hwy 51 lot, Matthews", "book", "Tuesday at 1pm"),
    ("Aisha Johnson", None, None, "waiting", None),
    ("Kevin Nguyen", "Dead ash tree", "905 Queens Rd, Charlotte", "book", "Wednesday at 9"),
    ("Rachel Green", "Trim over the driveway", "27 Cedar St, Huntersville", "stop", None),
    ("Omar Haddad", "Two pines by the fence", "412 Oak Hollow Dr, Indian Trail", "book", "Friday at 10"),
    ("Emily Chen", "Cabling a split oak", None, "texting", None),
    ("Jake Morrison", "Emergency removal, tree on the shed", "6 Bramble Way, Matthews", "book", "Tuesday at 3pm"),
    ("Nina Petrova", "Palm trimming", "118 Lakeview Dr, Cornelius", "book", "Thursday at 4pm"),
    ("Chris Owens", "Price for grinding three stumps", None, "person", None),
    ("Maya Singh", "Removal of a dead dogwood", "77 Rosewood Ln, Charlotte", "book", "Monday at 11"),
    ("Paul Becker", None, None, "waiting", None),
]


def seed_full() -> None:
    if store.setting("preview_full_seeded"):
        return
    now = datetime.now(timezone.utc)
    local = now.astimezone(ZoneInfo(TZ))
    start = local.replace(hour=7, minute=40, second=0, microsecond=0)
    if start >= local:
        start = local - timedelta(hours=1)
    span = max((local - start).total_seconds() - 900, 600)
    n = 0
    last = {}
    def step(t, kind, **params):
        CLOCK[0] = t
        inbox.submit_event(state=state, kind=kind, params=params)
        for _ in range(3):
            worker.run_once(state)
    def sms(phone, t, body):
        nonlocal n; n += 1
        step(t, "sms", message_sid=f"SMfull{n}", from_number=phone, to_number=TEXTING, body=body)
    for i, (name, job, address, outcome, when) in enumerate(FULL_CALLERS):
        phone = f"+1980555{1200 + i:04d}"
        EXAMPLES[phone] = name
        t = (start + timedelta(seconds=span * i / len(FULL_CALLERS))).astimezone(timezone.utc)
        step(t, "voice", call_sid=f"CAfull{i}", call_status="ringing", from_number=phone, to_number=TEXTING,
             forwarded_from=BUSINESS_LINE)
        t2 = t + timedelta(minutes=2)
        if outcome == "waiting":
            pass
        elif outcome == "stop":
            sms(phone, t2, job); sms(phone, t2 + timedelta(minutes=3), "STOP")
        elif outcome == "person":
            sms(phone, t2, job); sms(phone, t2 + timedelta(minutes=2), "Can you have someone call me instead?")
        elif outcome == "danger":
            sms(phone, t2, "A branch came down on a power line by our house")
        elif outcome == "texting":
            sms(phone, t2, job)
            if address:
                sms(phone, t2 + timedelta(minutes=2), address)
        else:  # book
            sms(phone, t2, job); sms(phone, t2 + timedelta(minutes=2), address)
            sms(phone, t2 + timedelta(minutes=4), when); sms(phone, t2 + timedelta(minutes=6), name)
        store.set_conversation_field(phone, "name", name)
        last[phone] = CLOCK[0]
    CLOCK[0] = None
    # Booking confirmations are queued by the worker on the real clock; date them to their conversation
    # so every caller's "Last activity" is the time of that customer's own texts.
    with store.transaction():
        for phone, t in last.items():
            store.conn.execute("UPDATE sms_outbox SET created_at=? WHERE phone=? AND created_at>?",
                               ((t + timedelta(minutes=1)).isoformat(), phone, now.isoformat()))
            store.conn.execute("UPDATE outcome_events SET occurred_at=? WHERE lead_id=? AND occurred_at>?",
                               ((t + timedelta(minutes=1)).isoformat(), phone, now.isoformat()))
    from text_back.portal_forwarding import save_manual_ticks
    save_manual_ticks(store, {"answered_no_text": True, "deactivation_saved": True}, now)
    store.set_setting("texting_approval_state", "approved", now=now)
    store.set_setting("preview_full_seeded", now.isoformat(), now=now)


if FULL:
    seed_full()
    state.preview_example_phones = set(EXAMPLES)
    state.preview_example_setup = {"forwarding", "approval", "calendar"}
    # Show the owner's calendar as connected (no Google call is ever made): bookings stay on the stub,
    # the portal reads status, picker and free times from this stand-in.
    import json as _json
    from text_back import client_settings as _cs, portal_status as _ps

    class _ShownCalendar:
        provider_name = "google"
        calendar_id = "owner@example.com"

        def __init__(self, real):
            self._real = real

        def __getattr__(self, name):
            return getattr(self._real, name)

        def busy_intervals(self, time_min, time_max):
            out = []
            for row in store.conn.execute("SELECT start, end FROM appointments"):
                a = datetime.fromisoformat(row[0]); b = datetime.fromisoformat(row[1]) if row[1] else a + timedelta(hours=1)
                out.append((a.astimezone(timezone.utc), b.astimezone(timezone.utc)))
            return out

    state.calendar = _ShownCalendar(state.calendar)
    store.set_setting("calendar_choices", _json.dumps([
        {"id": "owner@example.com", "summary": "Oak & Pine jobs", "primary": True},
        {"id": "crew@example.com", "summary": "Crew schedule"}]))
    store.set_setting("google_calendar_id", "owner@example.com")

    def _shown_status(st):
        return {"provider": "google", "status": "ready", "calendar_id": "owner@example.com", "can_connect": True}
    _cs.calendar_status = _shown_status
    _ps.calendar_status = _shown_status
state.preview_example_sessions = {store.setting("preview_example_session")} - {None}

PAGE = """<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1"><meta name=robots content=noindex>
<title>Preview code · TextBack</title><link rel=stylesheet href="/client/static/portal.css"></head><body>
<main id=main class="page auth"><div class=auth__card>{body}</div>
<p class=auth__foot>Preview only. No text message is sent.</p></main></body></html>"""


def code_page() -> bytes:
    hint = ("<p>Only <strong>980 555 0123</strong> gets a code. Any other number shows the same Enter code page, "
            "but nothing is sent, so this page will not change.</p>")
    sent = [(m, t) for m, t in zip(telecom.outbound, telecom.sent_at) if m.kind == "login_code"]
    if sent:
        msg, when = sent[-1]
        found = re.search(r"\b(\d{6})\b", msg.body)
        code = found.group(1) if found else "?"
        expired = datetime.now(timezone.utc) >= when + timedelta(minutes=10)
        stamp = when.astimezone(ZoneInfo(TZ)).strftime("%b %d, %I:%M %p").replace(" 0", " ")
        note = ("<strong>Expired.</strong> Go back to sign in and send a new code." if expired
                else "Type it on the Enter code page. It works for 10 minutes; a new code replaces it.")
        body = (f"<p>Sign-in code sent {html.escape(stamp)} Eastern</p><h1>{code[:3]} {code[3:]}</h1><p>{note}</p>{hint}"
                f"<p><a class='btn btn--primary' href=/client/{'login' if expired else 'verify'}>"
                f"{'Send a new code' if expired else 'Back to enter code'}</a></p>")
    else:
        body = f"<h1>No code yet</h1>{hint}<p><a class='btn btn--primary' href=/client/login>Go to sign in</a></p>"
    return PAGE.format(body=body).encode()


# --- Preview only: no sign-in. Every /client page opens already signed in as the demo owner. ---------------
# A fixed session row is (re)written on each request, so Sign out and Sign out everywhere just land back on Home.
import secrets as _secrets
from text_back import client_portal as _cp

_TOKEN = _secrets.token_urlsafe(32)


def _ensure_session() -> None:
    now = datetime.now(timezone.utc)
    with store.transaction():
        store.conn.execute("DELETE FROM client_sessions WHERE token_hash=?", (_cp._mac(state, _TOKEN),))
        store.conn.execute(
            "INSERT INTO client_sessions(token_hash,csrf,phone,expires_at,created_at,pending,remember) VALUES(?,?,?,?,?,0,1)",
            (_cp._mac(state, _TOKEN), "preview-csrf-" + _TOKEN[:16], OWNER, (now + timedelta(days=30)).isoformat(), now.isoformat()))


def _has_cookie(scope) -> bool:
    for name, value in scope.get("headers", []):
        if name == b"cookie" and f"{_cp.SESSION_COOKIE}={_TOKEN}".encode() in value:
            return True
    return False


async def _redirect(send, location: str, set_cookie: bool) -> None:
    headers = [(b"location", location.encode()), (b"cache-control", b"no-store")]
    if set_cookie:
        headers.append((b"set-cookie", f"{_cp.SESSION_COOKIE}={_TOKEN}; Path=/client; HttpOnly; SameSite=Lax; Max-Age=2592000".encode()))
    await send({"type": "http.response.start", "status": 303, "headers": headers})
    await send({"type": "http.response.body", "body": b""})


OPEN = os.environ.get("TEXT_BACK_PREVIEW_OPEN") == "1"  # set for the shared tailnet preview; capture tools leave it off


async def wrapper(scope, receive, send):
    if scope["type"] == "http" and OPEN:
        path = scope["path"]
        if path in ("/", "/client", "/client/", "/client/login", "/client/verify", "/preview/code"):
            _ensure_session()
            await _redirect(send, "/client/home", set_cookie=True); return
        if path.startswith("/client") and not path.startswith("/client/static"):
            _ensure_session()
            if not _has_cookie(scope):
                qs = scope.get("query_string", b"").decode()
                await _redirect(send, path + ("?" + qs if qs else ""), set_cookie=True); return
    await _wrapped(scope, receive, send)


async def _wrapped(scope, receive, send):
    if scope["type"] == "http" and scope["path"] == "/":
        await send({"type": "http.response.start", "status": 303, "headers": [(b"location", b"/client/login")]})
        await send({"type": "http.response.body", "body": b""}); return
    if scope["type"] == "http" and scope["path"] == "/preview/code":
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"text/html; charset=utf-8"), (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": code_page()}); return
    await app(scope, receive, send)


if __name__ == "__main__":
    uvicorn.run(wrapper, host=HOST, port=PORT, log_level="info")
