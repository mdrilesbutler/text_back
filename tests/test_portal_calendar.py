"""Calendar page logic (candidate C): the state card, the picker and the free-times check.

These drive ``portal_calendar`` directly (status_card / availability_card / check_availability /
page_context) on an app built with ``create_app``; the HTTP routes and template are covered once
they exist. Every owner-facing word comes from docs/notes/portal-c/copy-deck.md, section 6.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from text_back import client_settings
from text_back import portal_calendar as pc
from text_back.app import create_app
from text_back.calendars.google import GoogleCalendarProvider
from text_back.calendars.credentials import GoogleCredentials
from text_back.calendars.protocol import CalendarProviderError
from text_back.calendars.transport import FakeHttpTransport, HttpResponse
from text_back.telecom import FakeTelecom

NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)  # Monday 11:00 EDT
BASE = "https://example.test"
OWNER = "+19805550123"
SUPPORT = "+19805550100"
EASTERN = ZoneInfo("America/New_York")
WEEKDAYS = {**{d: {"open": "08:00", "close": "17:00"} for d in ("mon", "tue", "wed", "thu", "fri")}, "sat": None, "sun": None}
DECK = Path(__file__).resolve().parents[1] / "docs" / "notes" / "portal-c" / "copy-deck.md"


# --- fixtures ----------------------------------------------------------------------

def build(tmp_path, monkeypatch, *, support=""):
    """A booted app on the stub calendar: its state."""
    monkeypatch.setenv("TEXT_BACK_OWNER_MOBILE", OWNER)
    if support:
        monkeypatch.setenv("TEXT_BACK_SUPPORT_CONTACT", support)
    else:
        monkeypatch.delenv("TEXT_BACK_SUPPORT_CONTACT", raising=False)
    monkeypatch.delenv("TEXT_BACK_TIMEZONE", raising=False)
    app = create_app(db_path=str(tmp_path / "portal.db"), telecom=FakeTelecom(), public_base_url=BASE,
                     business_name="Oak & Pine Tree Care", now_provider=lambda: NOW)
    return app.state


def google_state(tmp_path, monkeypatch, *, status="ready", client_file=True, responses=(), support=""):
    """A booted app on a Google calendar whose token file says ``status``: (state, credentials, transport)."""
    monkeypatch.setenv("TEXT_BACK_OWNER_MOBILE", OWNER)
    if support:
        monkeypatch.setenv("TEXT_BACK_SUPPORT_CONTACT", support)
    else:
        monkeypatch.delenv("TEXT_BACK_SUPPORT_CONTACT", raising=False)
    token = tmp_path / "token.json"
    token.write_text(json.dumps(dict(token="access", refresh_token="refresh", client_id="c", client_secret="s",
                                     status=status, expiry="2030-01-01T00:00:00Z")))
    web = None
    if client_file:
        web = tmp_path / "web.json"
        web.write_text(json.dumps({"web": {"client_id": "web-id", "client_secret": "web-secret"}}))
    transport = FakeHttpTransport(list(responses))
    credentials = GoogleCredentials(str(token), transport=transport, now_provider=lambda: NOW, client_file=web)
    calendar = GoogleCalendarProvider("jobs@group.calendar.google.com", credentials, transport)
    app = create_app(db_path=str(tmp_path / "google.db"), telecom=FakeTelecom(), public_base_url=BASE,
                     business_name="Oak & Pine Tree Care", calendar=calendar, now_provider=lambda: NOW)
    return app.state, credentials, transport


def remember(state):
    state.store.set_setting("calendar_choices", json.dumps([
        {"id": "owner@example.test", "summary": "Personal", "accessRole": "owner", "primary": True},
        {"id": "jobs@group.calendar.google.com", "summary": "Tree jobs", "accessRole": "writer"},
    ]), now=NOW)


def set_hours(state, hours=WEEKDAYS, tz="America/New_York"):
    state.store.set_setting("timezone", tz, now=NOW)
    state.store.set_setting("working_hours", json.dumps(hours), now=NOW)
    client_settings.apply_scheduling(state)


def labels(card):
    return [button["label"] for button in card["buttons"]]


def every_string(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from every_string(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from every_string(item)


def _deck_section(title: str) -> list[str]:
    """Every text cell of one deck section, split on the ' / ' variant separator."""
    text = DECK.read_text(encoding="utf-8")
    body = text.split(f"## {title}", 1)[1].split("\n## ", 1)[0]
    cells = []
    for line in body.splitlines():
        if line.startswith("| ") and not line.startswith("| key") and not line.startswith("|---"):
            cells.extend(part.strip() for part in line.split("|")[2].split(" / "))
    return cells


# --- words -------------------------------------------------------------------------

def test_every_user_facing_string_is_in_the_copy_deck():
    deck = _deck_section("6. Calendar")
    bracketed = [re.sub(r"\[[^\]]*\]", "{}", cell) for cell in deck]
    for text in pc.DECK_STRINGS:
        shape = re.sub(r"\{[a-z_]*\}", "{}", text)
        assert text in deck or shape in bracketed, text
    # The any-time note is the Schedule page's warning, reused verbatim.
    assert pc.ANY_TIME_NOTE in _deck_section("5. Schedule")
    # Words the prompt bans on this page.
    for text in pc.DECK_STRINGS + pc.OPEN_STRINGS + (pc.ANY_TIME_NOTE,):
        assert "real read" not in text and "text_back" not in text and "SignalWire" not in text


# --- the state card ------------------------------------------------------------------

def test_not_connected_has_connect_or_a_contact_action_never_a_dead_end(tmp_path, monkeypatch):
    # (1) The Google web client is configured: Home's words, one sentence on why it matters, then Connect.
    state = build(tmp_path, monkeypatch)
    monkeypatch.setattr(client_settings, "calendar_status",
                        lambda s: {"provider": "google", "status": "none", "calendar_id": "", "can_connect": True})
    card = pc.status_card(state)
    assert card["state_word"] == "Not connected" and card["title"] == "No calendar yet"
    assert card["body"] == "No calendar of yours yet. Until you connect one, bookings go on a test calendar you can't see."
    assert card["why"] == ("Connect the Google account that owns your business calendar, so the assistant offers your "
                           "real free times and books onto your calendar.")
    assert card["buttons"] == [{"label": "Connect Google Calendar", "action": "connect", "kind": "primary",
                                "busy_label": "Opening Google…"}]
    monkeypatch.undo()

    # (2) No web client, but a support contact: the second paragraph names FluxWorks and a text action is offered.
    state = build(tmp_path, monkeypatch, support=SUPPORT)
    assert state.support_contact == SUPPORT
    card = pc.status_card(state)
    assert card["state_word"] == "Not connected" and card["title"] == "No calendar yet"
    assert card["why"].startswith("To book onto your own calendar, it has to be connected.")
    assert "Connecting from this page isn't set up for your account yet." in card["why"]
    assert "FluxWorks sets this up for you." in card["why"]
    assert card["buttons"] == [{"label": "Text FluxWorks support", "href": f"sms:{SUPPORT}", "kind": "secondary"}]

    # (3) Neither: no button, but the body still names the next step.
    state = build(tmp_path, monkeypatch)
    assert state.support_contact == ""
    card = pc.status_card(state)
    assert card["buttons"] == []
    assert card["why"].endswith("FluxWorks sets this up for you.")
    assert "sms:" not in json.dumps(card)


def test_connected_state_names_the_calendar_and_offers_reconnect(tmp_path, monkeypatch):
    state, _, _ = google_state(tmp_path, monkeypatch)
    remember(state)
    card = pc.status_card(state)
    assert card["state_word"] == "Connected" and card["title"] == "Google Calendar"
    # No "Connected as": the account's address is not stored. The picker replaces "Use a different calendar".
    assert card["body"] == "Bookings go here: Tree jobs."
    assert card["calendar_name"] == "Tree jobs"
    assert labels(card) == ["Reconnect Google Calendar"]
    assert card["buttons"][0]["action"] == "connect" and card["buttons"][0]["kind"] == "secondary"

    context = pc.page_context(state)
    picker = context["picker"]
    assert picker["legend"] == "Which calendar should the assistant use?"
    assert picker["hint"] == "Free times are checked on this calendar and new appointments are added to it."
    assert [(c["id"], c["name"], c["in_use"], c["main"]) for c in picker["choices"]] == [
        ("owner@example.test", "Personal", False, True), ("jobs@group.calendar.google.com", "Tree jobs", True, False)]
    assert picker["main_suffix"] == "(main calendar)" and picker["pill"] == "In use" and picker["button"] == "Use this calendar"
    assert picker["only"] == "" and picker["error"] == "Pick one of the calendars listed."
    assert context["consent_note"].startswith("What Google will ask:")
    assert context["availability"]["title"] == "Next free times on Tree jobs"

    # Without a connected calendar there is no picker; with a single calendar the empty state explains.
    state.store.set_setting("calendar_choices", json.dumps([{"id": "jobs@group.calendar.google.com", "summary": "Tree jobs"}]), now=NOW)
    assert pc.page_context(state)["picker"]["only"] == "This is the only calendar this account can add appointments to."
    stub = build(tmp_path, monkeypatch)
    assert pc.page_context(stub)["picker"] is None


def test_reauth_and_unreadable_states_say_what_to_do(tmp_path, monkeypatch):
    # Reconnect needed, web client configured: the body says what happened and the button reconnects.
    state, credentials, transport = google_state(tmp_path, monkeypatch, status="reauth_required")
    card = pc.status_card(state)
    assert card["state_word"] == "Reconnect needed" and card["title"] == "Google Calendar"
    assert card["body"] == ("Google disconnected the calendar, so bookings are paused until you reconnect. "
                            "Customers are told no booking was made.")
    assert card["buttons"] == [{"label": "Reconnect Google Calendar", "action": "connect", "kind": "primary",
                                "busy_label": "Opening Google…"}]
    availability = pc.availability_card(state, None)
    assert availability["button"] == "" and availability["replaced"] == "Reconnect the calendar first."
    # Checking anyway never reaches Google.
    result = pc.check_availability(state, NOW)
    assert result["error"] == "Reconnect the calendar first." and result["slots"] == [] and transport.requests == []
    assert pc.page_context(state)["picker"] is None

    # Couldn't be read: same next step.
    def broken():
        raise CalendarProviderError("unreadable")
    monkeypatch.setattr(credentials, "status", broken)
    card = pc.status_card(state)
    assert card["state_word"] == "Couldn't be read"
    assert card["body"] == "TextBack couldn't read the calendar connection. Bookings are paused until you reconnect."
    assert labels(card) == ["Reconnect Google Calendar"]
    assert pc.check_availability(state, NOW)["error"] == "Reconnect the calendar first."

    # No web client: a support contact gives a text action, otherwise the body names FluxWorks.
    state, _, _ = google_state(tmp_path, monkeypatch, status="reauth_required", client_file=False, support=SUPPORT)
    card = pc.status_card(state)
    assert card["state_word"] == "Reconnect needed" and "FluxWorks sets this up for you." in card["body"]
    assert card["buttons"] == [{"label": "Text FluxWorks support", "href": f"sms:{SUPPORT}", "kind": "secondary"}]
    state, _, _ = google_state(tmp_path, monkeypatch, status="reauth_required", client_file=False)
    card = pc.status_card(state)
    assert card["buttons"] == [] and card["body"].endswith("FluxWorks sets this up for you.")


def test_managed_providers_are_connected_and_name_the_next_step(tmp_path, monkeypatch):
    monkeypatch.setenv("TEXT_BACK_OWNER_MOBILE", OWNER)
    monkeypatch.delenv("TEXT_BACK_SUPPORT_CONTACT", raising=False)
    transport = FakeHttpTransport([])
    calendar = GoogleCalendarProvider("jobs@example.test", lambda: "static-token", transport)
    app = create_app(db_path=str(tmp_path / "managed.db"), telecom=FakeTelecom(), public_base_url=BASE,
                     business_name="Oak & Pine Tree Care", calendar=calendar, now_provider=lambda: NOW)
    state = app.state
    card = pc.status_card(state)
    assert card["state_word"] == "Connected" and card["title"] == "Google Calendar"
    assert card["body"].startswith("Bookings go here: jobs@example.test.") and "FluxWorks" in card["body"]
    assert card["buttons"] == []
    assert "static-token" not in json.dumps(pc.page_context(state))
    assert pc.page_context(state)["picker"] is None
    assert pc.availability_card(state, None)["title"] == "Next free times on jobs@example.test"

    state.support_contact = SUPPORT
    assert pc.status_card(state)["buttons"] == [{"label": "Text FluxWorks support", "href": f"sms:{SUPPORT}", "kind": "secondary"}]

    # A provider without a busy read: still connected, and the check says so instead of failing.
    class Outlook:
        provider_name = "microsoft"
        calendar_id = "work"
    state.calendar = Outlook()
    card = pc.status_card(state)
    assert card["state_word"] == "Connected" and card["title"] == "Outlook / Microsoft 365"
    availability = pc.availability_card(state, None)
    assert availability["button"] == "" and availability["replaced"] == pc.NO_CHECK
    assert pc.check_availability(state, NOW)["error"] == pc.NO_CHECK


# --- the free-times check -------------------------------------------------------------

def test_stub_card_title_says_test_calendar(tmp_path, monkeypatch):
    state = build(tmp_path, monkeypatch)
    card = pc.availability_card(state, None)
    assert card["title"] == "Test calendar, not yours"
    assert card["intro"] == "Shows how the check works. These times are not from your calendar."
    assert card["button"] == "Check free times" and card["busy_label"] == "Checking…" and card["replaced"] == ""
    assert card["slots"] == [] and card["checked"] is False
    for text in every_string(pc.page_context(state)):
        assert "real read" not in text


def test_availability_respects_working_hours(tmp_path, monkeypatch):
    state = build(tmp_path, monkeypatch)
    set_hours(state)  # Mon–Fri 8–5 Eastern, stub busy list empty
    monday_1am = datetime(2026, 10, 19, 1, 0, tzinfo=EASTERN)
    result = pc.check_availability(state, monday_1am)
    assert result["checked"] is True and result["error"] == ""
    assert result["slots"][0] == "Mon, Oct 19 · 8:00–9:00 AM"
    assert all(start.astimezone(EASTERN).hour >= 8 for start in result["starts"])
    card = pc.availability_card(state, result)
    assert card["slots"] == ["Mon, Oct 19 · 8:00–9:00 AM", "Mon, Oct 19 · 8:30–9:30 AM", "Mon, Oct 19 · 9:00–10:00 AM"]
    assert card["caption"] == "Checked just now · next 14 days · working hours Mon–Fri 8:00 AM–5:00 PM"
    assert card["note"] == "" and card["empty"] == ""
    # The card filters on the saved hours even when handed starts outside them.
    smuggled = dict(result, starts=[monday_1am.replace(hour=2)] + result["starts"])
    assert pc.availability_card(state, smuggled)["slots"][0] == "Mon, Oct 19 · 8:00–9:00 AM"


def test_any_time_hours_show_the_note(tmp_path, monkeypatch):
    state = build(tmp_path, monkeypatch)
    state.store.set_setting("timezone", "America/New_York", now=NOW)
    client_settings.apply_scheduling(state)
    monday_1am = datetime(2026, 10, 19, 1, 0, tzinfo=EASTERN)
    card = pc.availability_card(state, pc.check_availability(state, monday_1am))
    assert card["note"] == "Customers can be offered times like 1 AM. Set your hours."
    assert card["slots"][0] == "Mon, Oct 19 · 1:30–2:30 AM"
    assert card["caption"] == "Checked just now · next 14 days · working hours Any day, any time"
    assert pc.availability_card(state, None)["note"] == card["note"]  # shown before any check too
    set_hours(state)
    assert pc.availability_card(state, None)["note"] == ""


def test_stub_check_uses_the_stub_busy_list_and_the_appointment_length(tmp_path, monkeypatch):
    state = build(tmp_path, monkeypatch)
    set_hours(state, {**WEEKDAYS, **{d: {"open": "09:00", "close": "17:00"} for d in ("mon", "tue", "wed", "thu", "fri")}})
    # NOW is Monday 11:00 EDT; the stub is busy 11:30–12:30.
    state.calendar.busy.append((NOW + timedelta(minutes=30), NOW + timedelta(minutes=90)))
    result = pc.check_availability(state, NOW)
    assert result["slots"] == ["Mon, Oct 19 · 12:30–1:30 PM", "Mon, Oct 19 · 1:00–2:00 PM", "Mon, Oct 19 · 1:30–2:30 PM"]
    assert result["duration"] == 60
    # Events the stub already holds count as busy too.
    state.calendar.events["evt-1"] = {"start": NOW + timedelta(minutes=90), "end": NOW + timedelta(minutes=150), "conversation_id": "c"}
    assert pc.check_availability(state, NOW)["slots"][0] == "Mon, Oct 19 · 1:30–2:30 PM"
    state.calendar.events.clear()
    state.store.set_setting("appointment_duration_minutes", "90", now=NOW)
    client_settings.apply_scheduling(state)
    result = pc.check_availability(state, NOW)
    assert result["slots"][0] == "Mon, Oct 19 · 12:30–2:00 PM" and result["duration"] == 90
    card = pc.availability_card(state, result)
    assert card["intro"] == "Shows how the check works. These times are not from your calendar."
    assert state.store.conn.execute("SELECT count(*) FROM outcome_events").fetchone()[0] == 0


def test_no_free_time_in_the_horizon_is_said_plainly(tmp_path, monkeypatch):
    state = build(tmp_path, monkeypatch)
    state.calendar.busy.append((NOW - timedelta(days=1), NOW + timedelta(days=30)))
    result = pc.check_availability(state, NOW)
    assert result["slots"] == [] and result["checked"] is True
    assert result["empty"] == "No free 60-minute time in the next 14 days inside your working hours."
    assert pc.availability_card(state, result)["empty"] == result["empty"]
    assert pc.HORIZON_DAYS == 14


def test_ready_google_check_reads_busy_intervals_and_fails_closed(tmp_path, monkeypatch):
    busy = [{"start": "2026-10-19T15:30:00Z", "end": "2026-10-19T16:30:00Z"}]
    state, _, transport = google_state(tmp_path, monkeypatch, responses=[
        HttpResponse(200, (), json.dumps({"calendars": {"jobs@group.calendar.google.com": {"busy": busy}}}).encode()),
        HttpResponse(500, (), b"boom"),
    ])
    remember(state)
    set_hours(state)
    result = pc.check_availability(state, NOW)
    assert result["error"] == ""
    assert result["slots"] == ["Mon, Oct 19 · 12:30–1:30 PM", "Mon, Oct 19 · 1:00–2:00 PM", "Mon, Oct 19 · 1:30–2:30 PM"]
    request = transport.requests[-1]
    assert request.url.endswith("/freeBusy")
    body = json.loads(request.body)
    assert body["items"] == [{"id": "jobs@group.calendar.google.com"}]
    assert body["timeMin"] == "2026-10-19T15:00:00Z" and body["timeMax"] == "2026-11-02T15:00:00Z"
    card = pc.availability_card(state, result)
    assert card["title"] == "Next free times on Tree jobs"
    assert card["intro"] == "The first three free 60-minute times in the next 14 days, inside your working hours."
    assert card["caption"] == "Checked just now · next 14 days · working hours Mon–Fri 8:00 AM–5:00 PM"

    failed = pc.check_availability(state, NOW)
    assert failed["error"] == "Couldn't reach Google Calendar. Try again in a minute."
    assert failed["slots"] == [] and failed["checked"] is False
    card = pc.availability_card(state, failed)
    assert card["error"] == failed["error"] and card["button"] == "Check free times"
    assert "access" not in json.dumps(pc.page_context(state, failed)).replace("calendar access", "")


def test_page_context_combines_the_cards_the_picker_and_the_consent_note(tmp_path, monkeypatch):
    state = build(tmp_path, monkeypatch)
    context = pc.page_context(state)
    assert set(context) == {"card", "availability", "picker", "consent_note"}
    assert context["card"]["state_word"] == "Not connected"
    assert context["availability"]["title"] == "Test calendar, not yours"
    assert context["picker"] is None
    assert context["consent_note"] == pc.CONSENT_NOTE
    assert "(1) You pick the Google account that owns your business calendar." in context["consent_note"]
