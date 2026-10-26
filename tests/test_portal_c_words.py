"""No plumbing words, no braces and no hosts on any /client screen, in every state the fixtures reach.

The scan reads what an owner can see or hear: text nodes (hidden ones included, so a state JS reveals is
covered too), aria-label, title and placeholder values, and every string value inside a
<script type="application/json"> block (the data the page script renders). Other scripts, styles and the
icon sprite are dropped. In the JSON, the ``gsm`` and ``ext`` character tables are skipped: they are
alphabets for the length counter (the extended one holds braces), never words on screen.

One designed exception: a TextBack calendar link (``<base>/a/<ref>`` and its ``/g`` ``/o`` ``/i``
forms) is allowed in a title= value and in the JSON sample, because copy deck row ``link_labels``
says "the full link shows on tap". It is read as the words "calendar link". Any other URL or host
in those places still fails.
"""
import html
import json
import re

import pytest

from text_back import client_settings, portal_status
from text_back.calendars.protocol import CalendarProviderError
from test_client_portal import OWNER, csrf_of, make, sign_in
from test_client_settings import google_fixture

BANNED = ("SignalWire", "text_back", "campaign", "brand", "10DLC", "registration", "segment", "lead", "token",
          "webhook", "provider", "event ID", "call_sid", "nudge", "hand-off", "handoff")
HOSTS = re.compile(r"ts\.net|localhost|127\.0\.0\.1|://|(?<!\d):8\d|:8443|:8765|:8003|:8766", re.I)


JSON_SKIP = {"gsm", "ext"}
CALENDAR_LINK = re.compile(r"https?://\S+?/a/[\w-]+(?:/[goi])?(?![\w/-])")


def _designed_links(text: str) -> str:
    return CALENDAR_LINK.sub("calendar link", text)
ATTRIBUTE = re.compile(r"""(?<![\w-])(?:aria-label|placeholder|title)=(?:"([^"]*)"|'([^']*)'|([^\s>"']+))""")
JSON_BLOCK = re.compile(r"""(?is)<script\b[^>]*\btype=["']?application/json["']?[^>]*>(.*?)</script>""")


def _json_strings(value, key=None):
    if key in JSON_SKIP:
        return
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _json_strings(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from _json_strings(v)


def visible(page: str) -> str:
    """The words on screen, the words a screen reader speaks and the words the page script renders."""
    spoken = " ".join(_designed_links(html.unescape(next(g for g in m.groups() if g is not None)))
                      for m in ATTRIBUTE.finditer(page))
    data = " ".join(_designed_links(text) for block in JSON_BLOCK.findall(page)
                    for text in _json_strings(json.loads(html.unescape(block))))
    page = re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", " ", page)
    page = re.sub(r"(?s)<!--.*?-->", " ", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    return " ".join((html.unescape(page) + " " + spoken + " " + data).split())


def problems(page: str) -> list[str]:
    text = visible(page)
    found = [word for word in BANNED if re.search(r"(?i)(?<![\w-])" + re.escape(word) + r"(?![\w-])", text)]
    found += [f"brace at …{text[max(0, m.start() - 40):m.end() + 40]}…" for m in re.finditer(r"[{}]", text)]
    found += [f"host at …{text[max(0, m.start() - 40):m.end() + 40]}…" for m in HOSTS.finditer(text)]
    return found


def assert_clean(response, label: str):
    assert response.status_code in (200, 400), (label, response.status_code)
    assert problems(response.text) == [], label


def test_the_scan_catches_what_it_should():
    assert problems("<p>Your lead is ready</p>") == ["lead"]
    assert problems("<p>Hi {business_name}</p>")[0].startswith("brace")
    assert problems('<p>see https://hermes-cloud.tailefb1a4.ts.net:8443/a/1</p>')
    assert problems('<button aria-label="Copy the campaign code">x</button>') == ["campaign"]
    assert problems("<p>Leading the way at 8:00 AM</p><script>var lead = '{'</script><svg><path d='{'/></svg>") == []
    assert problems('<a title="Open the webhook">x</a>') == ["webhook"]
    assert problems("<a title='Your lead'>x</a>") == ["lead"]
    assert problems('<script type=application/json id=tb-data>{"sample": [{"text": "Ask the provider"}]}</script>') == ["provider"]
    assert problems('<script type=application/json>{"labels": {"x": "Hi {business_name}"}}</script>')[0].startswith("brace")
    assert problems('<script type=application/json>{"gsm": "@{}", "ext": "{}[]~", "brand": "ok"}</script>') == []
    assert problems('<span title="https://x.ts.net:8443/a/1-ab/g">Add to Google Calendar ›</span>') == []
    assert problems('<span title="https://x.ts.net:8443/health">x</span>')
    assert problems('<script type=application/json>{"sample": {"g": "https://x.ts.net:8443/a/1-ab/g"}}</script>') == []
    assert problems('<script type=application/json>{"sample": {"u": "https://x.ts.net:8443/webhooks/sms"}}</script>')


def test_signed_out_pages(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    assert_clean(client.get("/client/login"), "login")
    assert_clean(client.get("/client/login?notice=ended"), "login ended")
    assert_clean(client.get("/client/login?notice=everywhere"), "login everywhere")
    assert_clean(client.post("/client/login", data={"mobile": "12"}), "login error")
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    assert_clean(client.get("/client/verify"), "verify")
    assert_clean(client.post("/client/verify", data={"code": "000000"}), "verify error")
    for _ in range(3):
        client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    assert_clean(client.post("/client/login", data={"mobile": OWNER}), "rate limited")


def test_every_signed_in_page_and_its_states(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    app = client.app
    app.state.business_number = "+19805550100"
    for url in ("/client/home", "/client/messages", "/client/schedule", "/client/calendar", "/client/phone", "/client/account"):
        assert_clean(client.get(url), url)
    csrf = csrf_of(client.get("/client/account").text)

    # Messages: a save, then a rejected save of each kind the deck words.
    assert_clean(client.post("/client/messages", data={"csrf": csrf, "intro": "Oak here, sorry we missed you. What do you need?",
                                                       "ask_phone": "1"}), "messages saved")
    for field, typed in (("intro", "Call our business line any time"), ("handoff_ack", "Paused."),
                         ("booking_error", "Sorry, call us."), ("opt_out_suffix", "Text END"),
                         ("prompt_name", "[Job] for whom?"), ("prompt_service", "a" * 481)):
        assert_clean(client.post("/client/messages", data={"csrf": csrf, field: typed}), f"messages rejected {field}")
    app.state.store.set_setting("texting_approval_state", "approved")
    assert_clean(client.get("/client/messages"), "messages approved")

    # Schedule: any time (default), the one-tap hours, a rejected save, set hours, a reset.
    form = {"csrf": csrf, "appointment_duration_minutes": "custom", "appointment_duration_custom": "75", "timezone": "UTC",
            "hours_mode": "any", "quiet_hours_start": "21:00", "quiet_hours_end": "08:00",
            "followup_delay_1": "120", "followup_delay_2": "1440", "followup_expiry_minutes": "2880"}
    assert_clean(client.post("/client/schedule", data={**form, "suggest_hours": "1"}), "schedule suggest")
    assert_clean(client.post("/client/schedule", data={**form, "appointment_duration_custom": "7", "timezone": "Mars/Base"}),
                 "schedule rejected")
    assert_clean(client.post("/client/schedule", data={**form, "hours_mode": "set", "open_mon": "1", "mon_open": "08:00",
                                                       "mon_close": "17:00"}), "schedule set hours")
    assert_clean(client.post("/client/schedule", data={**form, "reset": "quiet_hours"}), "schedule reset")
    store = app.state.store
    store.set_setting("working_hours", "not json")
    assert_clean(client.get("/client/schedule"), "schedule corrupt hours")
    store.set_setting("working_hours", None)

    # Calendar: the stub, a check, a support contact.
    assert_clean(client.post("/client/calendar", data={"csrf": csrf, "action": "check"}), "calendar check")
    app.state.support_contact = "+19805550111"
    assert_clean(client.get("/client/calendar"), "calendar support")
    assert_clean(client.get("/client/messages"), "messages support")
    assert_clean(client.get("/client/calendar?error=access"), "calendar error access")
    assert_clean(client.get("/client/calendar?error=no_calendar"), "calendar error no calendar")

    # Phone: a rejected save, carriers, the rename offer, the confirm step, checks.
    assert_clean(client.post("/client/phone", data={"csrf": csrf, "business_name": "", "business_line": "12",
                                                    "owner_mobile": "x", "business_contact": "y", "carrier": "zz"}),
                 "phone rejected")
    for carrier in ("verizon", "tmobile", "att", "cricket", "other"):
        assert_clean(client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak & Pine Tree Care",
                                                        "owner_mobile": OWNER, "carrier": carrier,
                                                        "business_line": "980 555 0177"}), f"phone {carrier}")
    client.post("/client/messages", data={"csrf": csrf, "prompt_name": "Oak & Pine Tree Care needs your name."})
    assert_clean(client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak and Pine", "owner_mobile": OWNER}),
                 "phone rename offer")
    assert_clean(client.post("/client/phone/rename-texts", data={"csrf": csrf, "action": "update"}), "phone renamed")
    assert_clean(client.post("/client/phone/checks", data={"csrf": csrf, "check_answered_no_text": "1"}), "phone checks")
    assert_clean(client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak and Pine", "owner_mobile": "980 555 0199"}),
                 "phone confirm step")
    assert_clean(client.get("/client/phone"), "phone confirm reload")
    assert_clean(client.post("/client/phone/confirm", data={"csrf": csrf, "code": "000000"}), "phone confirm wrong")
    assert_clean(client.post("/client/phone/keep", data={"csrf": csrf}), "phone kept")

    # Account and the expired page.
    assert_clean(client.post("/client/account/signout-everywhere", data={"csrf": csrf}), "account confirm")
    assert_clean(client.post("/client/account/remember", data={"csrf": csrf, "remember": "1"}), "account remember")
    assert_clean(client.post("/client/messages", data={"csrf": "forged"}), "expired")
    assert_clean(client.get("/client/home"), "home after activity")


@pytest.mark.parametrize("view", [
    {"provider": "stub", "status": "none", "calendar_id": "", "can_connect": False},
    {"provider": "google", "status": "none", "calendar_id": "", "can_connect": True},
    {"provider": "google", "status": "ready", "calendar_id": "a@x", "can_connect": True},
    {"provider": "google", "status": "ready", "calendar_id": "a@x", "can_connect": False},
    {"provider": "google", "status": "reauth_required", "calendar_id": "a@x", "can_connect": True},
    {"provider": "google", "status": "reauth_required", "calendar_id": "a@x", "can_connect": False},
    {"provider": "google", "status": "unavailable", "calendar_id": "a@x", "can_connect": False},
    {"provider": "microsoft", "status": "managed", "calendar_id": "jobs", "can_connect": False},
    {"provider": "icloud", "status": "managed", "calendar_id": "", "can_connect": False},
], ids=lambda v: f"{v['provider']}-{v['status']}-{'connect' if v['can_connect'] else 'no-connect'}")
def test_calendar_and_home_in_every_calendar_state(tmp_path, monkeypatch, view):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    client.app.state.store.set_setting("calendar_choices", json.dumps(
        [{"id": "a@x", "summary": "Personal", "primary": True}, {"id": "b@x", "summary": "Tree jobs"}]))
    monkeypatch.setattr(client_settings, "calendar_status", lambda state: dict(view))
    monkeypatch.setattr(portal_status, "calendar_status", lambda state: dict(view))
    for support in ("", "+19805550111"):
        client.app.state.support_contact = support
        assert_clean(client.get("/client/calendar"), f"calendar {view} {support}")
        assert_clean(client.get("/client/home"), f"home {view} {support}")


def test_google_calendar_pages(tmp_path, monkeypatch):
    client, telecom, credentials, transport = google_fixture(tmp_path, monkeypatch)
    sign_in(client, telecom)
    assert_clean(client.get("/client/calendar"), "reauth")
    monkeypatch.setattr(credentials, "status", lambda: (_ for _ in ()).throw(CalendarProviderError("boom")))
    assert_clean(client.get("/client/calendar"), "unavailable")
    monkeypatch.setattr(credentials, "status", lambda: "ready")
    client_settings.remember_calendars(client.app.state, [{"id": "a@x", "summary": "Personal", "primary": True},
                                                          {"id": "b@x", "summary": "Tree jobs"}], clock_now())
    assert_clean(client.get("/client/calendar"), "ready")
    csrf = csrf_of(client.get("/client/calendar").text)
    assert_clean(client.post("/client/calendar", data={"csrf": csrf, "calendar_id": "nope"}), "picker error")
    assert_clean(client.post("/client/calendar", data={"csrf": csrf, "calendar_id": "b@x"}), "picked")


def clock_now():
    from test_client_settings import NOW
    return NOW


# --- more states: real calls on Home, every approval state, a finished checklist, no texting number ----

def _forwarded_week(app, telecom_cls=None):
    """Seed Home through the real handlers: two forwarded missed calls, replies, and one booking."""
    from datetime import timedelta

    from text_back.calendar_stub import CalendarStub
    from text_back.handlers import handle_sms_event, handle_voice_event
    from text_back.handoff import FakeHandoffNotifier
    from text_back.telecom import FakeTelecom

    state = app.state
    business, texting = "+19805550177", "+19805550100"
    state.business_number = texting
    state.store.set_setting("business_line", business)
    now = state.now_provider()
    calendar = CalendarStub()
    for i, caller in enumerate(("+19805550141", "+19805550142")):
        at = now - timedelta(hours=3 - i)
        handle_voice_event(store=state.store, telecom=FakeTelecom(), call_sid=f"CA-w{i}", call_status="ringing",
                           from_number=caller, to_number=texting, wiring_mode="forwarded", business_name="Oak",
                           now=at, forwarded_from=business)
    caller = "+19805550141"
    replies = ("Trim two oaks", "12 Elm St, Charlotte", "tomorrow at 10am", "Pat Lee")
    for n, body in enumerate(replies):
        handle_sms_event(store=state.store, calendar=calendar, telecom=FakeTelecom(), handoff_notifier=FakeHandoffNotifier(),
                         handoff_destination="ops", message_sid=f"SM-w{n}", from_number=caller, to_number=texting,
                         body=body, business_name="Oak", timezone_name="America/New_York",
                         appointment_duration_minutes=60, now=now - timedelta(hours=3) + timedelta(minutes=n + 1))
    return state


def test_home_with_recorded_forwarded_calls_and_caller_rows(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    state = _forwarded_week(client.app)
    rows = portal_status.this_week(state, state.now_provider())["rows"]
    assert len(rows) == 2 and any(r["status"].startswith("Booked") for r in rows), rows
    assert_clean(client.get("/client/home"), "home with forwarded calls")
    assert_clean(client.get("/client/phone"), "phone with forwarded calls")


@pytest.mark.parametrize("approval", ["approved", "waiting", "not_started", "needs_attention", "unknown"])
def test_home_and_messages_in_every_texting_approval_state(tmp_path, monkeypatch, approval):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    client.app.state.store.set_setting("texting_approval_state", approval)
    page = client.get("/client/home")
    assert_clean(page, f"home {approval}")
    from text_back.portal_registry import approval_words
    assert approval_words({"state": approval})["state_word"] in html.unescape(page.text)
    assert_clean(client.get("/client/messages"), f"messages {approval}")


def test_phone_with_the_forwarding_checklist_all_done(tmp_path, monkeypatch):
    from text_back.portal_forwarding import checklist, save_manual_ticks

    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    state = _forwarded_week(client.app)
    save_manual_ticks(state.store, {"answered_no_text": True, "deactivation_saved": True}, state.now_provider())
    assert checklist(state, state.now_provider())["all_done"]
    for carrier in ("", "verizon", "att"):
        state.store.set_setting("carrier", carrier or None)
        assert_clean(client.get("/client/phone"), f"phone all done {carrier}")
    assert_clean(client.get("/client/home"), "home forwarding done")


def test_pages_with_no_texting_number_assigned(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    client.app.state.business_number = ""
    for url in ("/client/home", "/client/messages", "/client/schedule", "/client/calendar", "/client/phone", "/client/account"):
        assert_clean(client.get(url), f"{url} no texting number")
    csrf = csrf_of(client.get("/client/phone").text)
    for carrier in ("verizon", "tmobile", "att", "cricket", "other"):
        assert_clean(client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak & Pine Tree Care", "owner_mobile": OWNER,
                                                        "carrier": carrier, "business_line": "980 555 0177"}),
                     f"phone no texting number {carrier}")
