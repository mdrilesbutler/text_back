"""Client settings pages: phone details, owner mobile change, calendar connection."""
import json
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.calendars.credentials import CALENDAR_SCOPE, GoogleCredentials
from text_back.calendars.google import GoogleCalendarProvider
from text_back.calendars.transport import FakeHttpTransport, HttpResponse
from text_back.store import Store
from text_back.telecom import FakeTelecom

from test_client_portal import OWNER, BASE, code_from, csrf_of, make, sign_in

NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)


def test_business_details_are_saved_applied_and_survive_restart(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/phone")
    assert page.status_code == 200 and 'value="Oak &amp; Pine Tree Care"' in page.text
    assert "/client/calendar" in page.text and "/client/messages" in page.text  # tabs
    csrf = csrf_of(page.text)
    saved = client.post("/client/phone", data={"csrf": csrf, "business_name": "  Oak &  Pine  ", "business_contact": "980-555-0100",
                                               "owner_mobile": "(980) 555-0123"})
    assert "Saved." in saved.text
    assert client.app.state.business_name == "Oak & Pine"
    assert client.app.state.business_contact == "(980) 555-0100"
    # A fresh process on the same database comes up with the saved values, not the env defaults.
    again = create_app(db_path=str(tmp_path / "portal.db"), telecom=FakeTelecom(), public_base_url=BASE,
                       business_name="Oak & Pine Tree Care", now_provider=lambda: clock[0])
    assert again.state.business_name == "Oak & Pine" and again.state.business_contact == "(980) 555-0100"
    # Bad input is refused with the typed values kept.
    bad = client.post("/client/phone", data={"csrf": csrf, "business_name": "", "business_contact": "", "owner_mobile": OWNER})
    assert "Enter a business name" in bad.text and client.app.state.business_name == "Oak & Pine"
    bad = client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak", "business_contact": "call me", "owner_mobile": OWNER})
    assert "customer phone number" in bad.text and client.app.state.business_contact == "(980) 555-0100"
    assert client.post("/client/phone", data={"csrf": "forged", "business_name": "x", "owner_mobile": OWNER}).status_code == 400
    # The old address still lands on the page.
    assert client.post("/client/business", data={"business_name": "x"}, follow_redirects=False).status_code == 303
    moved = client.get("/client/business", follow_redirects=False)
    assert moved.status_code == 301 and moved.headers["location"] == "/client/phone"


def test_changing_the_owner_mobile_requires_a_code_texted_to_the_new_number(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/phone").text)
    page = client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak & Pine Tree Care", "business_contact": "",
                                              "owner_mobile": "980 555 0199"})
    assert "Confirm your new mobile" in page.text and "(980) 555-0199" in page.text
    code, text = code_from(telecom)
    assert text.to == "+19805550199" and "new mobile code" in text.body
    assert client.app.state.owner_mobile == OWNER  # nothing changed yet
    assert "/client/phone/confirm" in client.get("/client/phone").text  # still pending on reload
    wrong = client.post("/client/phone/confirm", data={"csrf": csrf, "code": "000000"})
    assert "not right or has expired" in wrong.text and client.app.state.owner_mobile == OWNER
    done = client.post("/client/phone/confirm", data={"csrf": csrf, "code": code})
    assert "Sign-in codes now go to (980) 555-0199" in done.text
    assert client.app.state.owner_mobile == "+19805550199"
    # Only the new number can request a sign-in code from now on.
    client.cookies.clear()
    before = len([m for m in telecom.outbound if m.kind == "login_code"])
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    assert len([m for m in telecom.outbound if m.kind == "login_code"]) == before
    sign_in(client, telecom, mobile="980 555 0199")


def test_keeping_the_current_mobile_cancels_the_pending_change(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/phone").text)
    client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak", "business_contact": "", "owner_mobile": "980 555 0199"})
    assert "Kept your current mobile" in client.post("/client/phone/confirm", data={"csrf": csrf, "cancel": "1"}).text
    assert "Confirm your new mobile" not in client.get("/client/phone").text
    assert client.app.state.owner_mobile == OWNER


def google_fixture(tmp_path, monkeypatch, *, client_file=True):
    monkeypatch.setenv("TEXT_BACK_OWNER_MOBILE", OWNER)
    monkeypatch.delenv("TEXT_BACK_MESSAGES_FILE", raising=False)
    token = tmp_path / "token.json"
    token.write_text(json.dumps(dict(token="expired", refresh_token="old", client_id="c", client_secret="s", status="reauth_required")))
    web = None
    if client_file:
        web = tmp_path / "web.json"
        web.write_text(json.dumps({"web": {"client_id": "web-id", "client_secret": "web-secret"}}))
    transport = FakeHttpTransport([
        HttpResponse(200, (), json.dumps(dict(access_token="new-access", refresh_token="new-refresh", expires_in=3600, scope=CALENDAR_SCOPE)).encode()),
        HttpResponse(200, (), json.dumps(dict(items=[
            dict(id="owner@example.test", summary="Personal", accessRole="owner", primary=True),
            dict(id="jobs@group.calendar.google.com", summary="Tree jobs", accessRole="writer"),
            dict(id="holidays", summary="Holidays", accessRole="reader"),
        ])).encode()),
    ])
    credentials = GoogleCredentials(str(token), transport=transport, now_provider=lambda: NOW, client_file=web)
    calendar = GoogleCalendarProvider("old-calendar@example.test", credentials, transport)
    telecom = FakeTelecom()
    app = create_app(db_path=str(tmp_path / "settings.db"), telecom=telecom, public_base_url=BASE, business_name="Oak & Pine",
                     calendar=calendar, now_provider=lambda: NOW)
    return TestClient(app, base_url=BASE), telecom, credentials, transport


def test_owner_connects_google_and_picks_the_calendar(tmp_path, monkeypatch):
    client, telecom, credentials, transport = google_fixture(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/calendar")
    assert "disconnected" in page.text and "Connect Google Calendar" in page.text
    csrf = csrf_of(page.text)
    start = client.post("/client/calendar", data={"csrf": csrf, "action": "connect"}, follow_redirects=False)
    assert start.status_code == 303 and start.headers["location"].startswith(BASE + "/calendar/connect?token=")
    consent = client.get(start.headers["location"], follow_redirects=False)
    assert consent.status_code == 303
    params = parse_qs(urlsplit(consent.headers["location"]).query)
    assert params["client_id"] == ["web-id"] and params["redirect_uri"] == [BASE + "/calendar/callback"]
    assert params["scope"] == [CALENDAR_SCOPE]
    cookie = consent.cookies.get("text_back_oauth")
    back = client.get(BASE + "/calendar/callback", params={"state": params["state"][0], "code": "code"},
                      headers={"Cookie": f"text_back_oauth={cookie}; text_back_client={client.cookies.get('text_back_client')}"},
                      follow_redirects=False)
    assert back.status_code == 303 and back.headers["location"] == "/client/calendar"
    assert credentials.status() == "ready"
    # The old calendar was not writable by this account, so the main calendar is used until the owner picks.
    assert client.app.state.calendar.calendar_id == "owner@example.test"
    page = client.get("/client/calendar")
    assert "Google Calendar is connected" in page.text and "<strong>Personal</strong>" in page.text
    assert "Tree jobs" in page.text and "Holidays" not in page.text  # reader-only calendars are not offered
    chosen = client.post("/client/calendar", data={"csrf": csrf, "calendar_id": "jobs@group.calendar.google.com"})
    assert "now uses Tree jobs" in chosen.text
    assert client.app.state.calendar.calendar_id == "jobs@group.calendar.google.com"
    assert "Pick one of the calendars" in client.post("/client/calendar", data={"csrf": csrf, "calendar_id": "holidays"}).text
    assert "new-access" not in page.text and "new-refresh" not in chosen.text
    # The choice survives a restart.
    again = create_app(db_path=str(tmp_path / "settings.db"), telecom=FakeTelecom(), public_base_url=BASE, business_name="Oak & Pine",
                       calendar=GoogleCalendarProvider("old-calendar@example.test", credentials, transport), now_provider=lambda: NOW)
    assert again.state.calendar.calendar_id == "jobs@group.calendar.google.com"


def test_denied_consent_returns_to_the_settings_page_with_an_explanation(tmp_path, monkeypatch):
    client, telecom, credentials, transport = google_fixture(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/calendar").text)
    start = client.post("/client/calendar", data={"csrf": csrf, "action": "connect"}, follow_redirects=False)
    consent = client.get(start.headers["location"], follow_redirects=False)
    state = parse_qs(urlsplit(consent.headers["location"]).query)["state"][0]
    cookie = consent.cookies.get("text_back_oauth")
    back = client.get(BASE + "/calendar/callback", params={"state": state, "error": "access_denied"},
                      headers={"Cookie": f"text_back_oauth={cookie}"}, follow_redirects=False)
    assert back.status_code == 303 and "did+not+grant" in back.headers["location"]
    assert credentials.status() == "reauth_required" and not transport.requests
    assert "did not grant" in client.get(back.headers["location"]).text


def test_without_a_web_client_the_page_explains_and_connect_is_refused(tmp_path, monkeypatch):
    client, telecom, credentials, transport = google_fixture(tmp_path, monkeypatch, client_file=False)
    sign_in(client, telecom)
    page = client.get("/client/calendar")
    assert "turned on yet" in page.text and "Connect Google Calendar" not in page.text
    refused = client.post("/client/calendar", data={"csrf": csrf_of(page.text), "action": "connect"})
    assert "not set up" in refused.text
    assert client.get("/client/calendar", follow_redirects=False).status_code == 200
    client.cookies.clear()
    assert client.get("/client/calendar", follow_redirects=False).headers["location"] == "/client/login"


def test_settings_table_helpers(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    assert store.setting("business_name") is None and store.setting("x", "d") == "d"
    store.set_setting("business_name", "Oak")
    store.set_setting("business_name", "Pine")
    assert store.setting("business_name") == "Pine"
    store.set_setting("business_name", None)
    assert store.setting("business_name") is None
