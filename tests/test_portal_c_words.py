"""No plumbing words, no braces and no hosts on any /client screen, in every state the fixtures reach.

The scan reads what an owner can see or hear: text nodes (hidden ones included, so a state JS reveals is
covered too) plus aria-label and placeholder values. Scripts, styles and the icon sprite are dropped.
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


def visible(page: str) -> str:
    """The words on screen and the words a screen reader speaks."""
    spoken = " ".join(html.unescape(v) for v in re.findall(r'(?:aria-label|placeholder)="([^"]*)"', page))
    page = re.sub(r"(?is)<(script|style|svg)\b.*?</\1>", " ", page)
    page = re.sub(r"(?s)<!--.*?-->", " ", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    return " ".join((html.unescape(page) + " " + spoken).split())


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
    csrf = csrf_of(client.get("/client/home").text)

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
