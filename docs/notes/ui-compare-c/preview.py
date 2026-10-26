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


async def wrapper(scope, receive, send):
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
