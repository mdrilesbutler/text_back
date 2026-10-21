"""Calendar page: every connection state, the picker, and the live availability check."""
from html import unescape
import json
import re
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from text_back import client_settings
from text_back.app import create_app
from text_back.calendars.google import GoogleCalendarProvider
from text_back.calendars.protocol import CalendarProviderError
from text_back.calendars.transport import FakeHttpTransport, HttpResponse
from text_back.telecom import FakeTelecom

from test_client_portal import BASE, csrf_of, make, sign_in
from test_client_settings import NOW, google_fixture

CHECK = "Check availability now"


def slots_of(html):
    return re.findall(r'<li><svg class="i" aria-hidden="true"><use href="#i-clock"></use></svg>([^<]+)</li>', html)


def connect(client, csrf):
    start = client.post("/client/calendar", data={"csrf": csrf, "action": "connect"}, follow_redirects=False)
    consent = client.get(start.headers["location"], follow_redirects=False)
    from urllib.parse import parse_qs, urlsplit
    params = parse_qs(urlsplit(consent.headers["location"]).query)
    cookie = consent.cookies.get("text_back_oauth")
    back = client.get(BASE + "/calendar/callback", params={"state": params["state"][0], "code": "code"},
                      headers={"Cookie": f"text_back_oauth={cookie}; text_back_client={client.cookies.get('text_back_client')}"},
                      follow_redirects=False)
    assert back.status_code == 303


def test_stub_state_shows_test_calendar_and_a_real_check_against_the_stub_busy_list(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/calendar")
    assert page.status_code == 200 and "<h1>Calendar</h1>" in unescape(page.text)
    assert "Test calendar" in unescape(page.text) and "Bookings aren't recorded anywhere yet." in unescape(page.text)
    assert "turned on yet" in unescape(page.text) and "Connect Google Calendar" not in unescape(page.text)  # a stub cannot be connected from here
    assert CHECK in unescape(page.text) and "Available on request" in unescape(page.text)
    assert "Outlook / Microsoft 365" in unescape(page.text) and "iCloud" in unescape(page.text) and "Ask text_back to connect it." in unescape(page.text)
    assert "<button" not in unescape(page.text).split("Available on request")[1]  # the request cards have nothing to click
    assert unescape(page.text).count("<h1") == 1

    state = client.app.state
    state.store.set_setting("timezone", "America/New_York")
    state.store.set_setting("working_hours", json.dumps({**{d: {"open": "09:00", "close": "17:00"} for d in ("mon", "tue", "wed", "thu", "fri")}, "sat": None, "sun": None}))
    client_settings.apply_scheduling(state)
    # NOW is Monday 11:00 EDT; the stub is busy 11:30-12:30.
    state.calendar.busy.append((NOW + timedelta(minutes=30), NOW + timedelta(minutes=90)))
    csrf = csrf_of(unescape(page.text))
    checked = client.post("/client/calendar/availability", data={"csrf": csrf})
    assert checked.status_code == 200
    assert slots_of(unescape(checked.text)) == ["Mon, Oct 19 · 12:30–1:30 PM", "Mon, Oct 19 · 1:00–2:00 PM", "Mon, Oct 19 · 1:30–2:30 PM"]
    assert "Checked just now · next 14 days on Test calendar · 60-minute slots inside your working hours" in unescape(checked.text)
    # The appointment length and the horizon are respected; nothing was recorded as a lead event.
    state.store.set_setting("appointment_duration_minutes", "90")
    client_settings.apply_scheduling(state)
    checked = client.post("/client/calendar/availability", data={"csrf": csrf})
    assert slots_of(unescape(checked.text))[0] == "Mon, Oct 19 · 12:30–2:00 PM" and "90-minute slots" in unescape(checked.text)
    assert state.store.conn.execute("SELECT count(*) FROM outcome_events").fetchone()[0] == 0
    assert client.post("/client/calendar/availability", data={"csrf": "forged"}).status_code == 400


def test_no_free_slot_in_the_horizon_is_said_plainly(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    state = client.app.state
    state.calendar.busy.append((NOW - timedelta(days=1), NOW + timedelta(days=30)))
    checked = client.post("/client/calendar/availability", data={"csrf": csrf_of(client.get("/client/calendar").text)})
    assert "No free 60-minute slot in the next 14 days inside your working hours." in unescape(checked.text)
    assert slots_of(unescape(checked.text)) == []


def test_reauth_state_hides_the_check_and_ready_state_runs_it_against_google(tmp_path, monkeypatch):
    client, telecom, credentials, transport = google_fixture(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/calendar")
    assert "Disconnected" in unescape(page.text) and "Google has disconnected the calendar" in unescape(page.text)
    assert "Connect Google Calendar" in unescape(page.text) and "Reconnect Google Calendar" not in unescape(page.text)
    assert CHECK not in unescape(page.text) and "Reconnect first." in unescape(page.text)
    csrf = csrf_of(unescape(page.text))
    # Posting anyway never reaches Google and never 500s.
    forced = client.post("/client/calendar/availability", data={"csrf": csrf})
    assert forced.status_code == 200 and "Reconnect first." in unescape(forced.text) and len(transport.requests) == 0

    connect(client, csrf)
    page = client.get("/client/calendar")
    assert "Connected" in unescape(page.text) and "Reconnect Google Calendar" in unescape(page.text) and CHECK in unescape(page.text)
    assert "<strong>Personal</strong>" in unescape(page.text) and "Which calendar" in unescape(page.text) and "(main)" in unescape(page.text)
    busy = [{"start": "2026-10-19T15:30:00Z", "end": "2026-10-19T16:30:00Z"}]
    transport.responses.append(HttpResponse(200, (), json.dumps({"calendars": {"owner@example.test": {"busy": busy}}}).encode()))
    checked = client.post("/client/calendar/availability", data={"csrf": csrf})
    assert checked.status_code == 200
    assert slots_of(unescape(checked.text)) == ["Mon, Oct 19 · 4:30–5:30 PM", "Mon, Oct 19 · 5:00–6:00 PM", "Mon, Oct 19 · 5:30–6:30 PM"]
    request = transport.requests[-1]
    assert request.url.endswith("/freeBusy")
    body = json.loads(request.body)
    assert body["items"] == [{"id": "owner@example.test"}] and body["timeMin"] == "2026-10-19T15:00:00Z" and body["timeMax"] == "2026-11-02T15:00:00Z"
    assert "Checked just now · next 14 days on Personal · 60-minute slots inside your working hours" in unescape(checked.text)
    assert "new-access" not in unescape(checked.text)

    transport.responses.append(HttpResponse(500, (), b"boom"))
    failed = client.post("/client/calendar/availability", data={"csrf": csrf})
    assert failed.status_code == 200 and "Couldn't reach Google Calendar. Try again in a minute." in unescape(failed.text)
    assert slots_of(unescape(failed.text)) == [] and CHECK in unescape(failed.text)


def test_unavailable_and_managed_states(tmp_path, monkeypatch):
    client, telecom, credentials, transport = google_fixture(tmp_path, monkeypatch)
    sign_in(client, telecom)

    def broken():
        raise CalendarProviderError("unreadable")

    monkeypatch.setattr(credentials, "status", broken)
    page = client.get("/client/calendar")
    assert "Can't be read" in unescape(page.text) and "Reconnect to resume bookings." in unescape(page.text)
    assert "Connect Google Calendar" in unescape(page.text) and "Reconnect first." in unescape(page.text) and CHECK not in unescape(page.text)

    monkeypatch.setenv("TEXT_BACK_OWNER_MOBILE", "+19805550123")
    managed_transport = FakeHttpTransport([])
    calendar = GoogleCalendarProvider("jobs@example.test", lambda: "static-token", managed_transport)
    app = create_app(db_path=str(tmp_path / "managed.db"), telecom=FakeTelecom(), public_base_url=BASE,
                     business_name="Oak & Pine", calendar=calendar, now_provider=lambda: NOW)
    managed = TestClient(app, base_url=BASE)
    sign_in(managed, app.state.telecom)
    page = managed.get("/client/calendar")
    assert "Connected" in unescape(page.text) and "managed for you" in unescape(page.text) and CHECK in unescape(page.text)
    assert "Connect Google Calendar" not in unescape(page.text) and "Which calendar" not in unescape(page.text)
    assert "static-token" not in unescape(page.text)
