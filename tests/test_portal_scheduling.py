"""Scheduling page: defaults, save and rebuild, enforcement through the engine, D.6 errors, Reset."""
import html as html_lib
import json
import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from test_client_portal import BASE, csrf_of, make as _make, sign_in

from text_back import portal_scheduling as ps
from text_back.app import create_app
from text_back.followup import run_due_followups, schedule_followup_sequence
from text_back.inbox import submit_event
from text_back.telecom import FakeTelecom

CALLER = "+17045550141"
WEEKDAYS = {"mon": {"open": "08:00", "close": "17:00"}, "tue": {"open": "08:00", "close": "17:00"},
            "wed": {"open": "08:00", "close": "17:00"}, "thu": {"open": "08:00", "close": "17:00"},
            "fri": {"open": "08:00", "close": "17:00"}, "sat": None, "sun": None}


def make(tmp_path, monkeypatch, **kwargs):
    monkeypatch.setenv("TEXT_BACK_REGISTRATION_DIR", str(tmp_path / "no-such-dir"))
    return _make(tmp_path, monkeypatch, **kwargs)


def valid_form(csrf, **over):
    form = {"csrf": csrf, "appointment_duration_minutes": "60", "timezone": "America/New_York", "hours_mode": "any",
            "quiet_hours_start": "21:00", "quiet_hours_end": "08:00",
            "followup_delay_1": "120", "followup_delay_2": "1440", "followup_expiry_minutes": "2880"}
    for day, window in WEEKDAYS.items():
        if window:
            form[f"open_{day}"] = "1"
        form[f"{day}_open"] = (window or {"open": "08:00"})["open"]
        form[f"{day}_close"] = (window or {"close": "17:00"})["close"]
    form.update(over)
    return form


def _error_under(html, key):
    match = re.search(rf'<p class="error" id="{key}-error">.*?<span>(.*?)</span>', html, re.S)
    return html_lib.unescape(match.group(1)) if match else None


def test_page_shows_every_default_and_needs_a_session(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    assert client.get("/client/scheduling", follow_redirects=False).headers["location"] == "/client/login"
    sign_in(client, telecom)
    html = client.get("/client/scheduling").text
    assert "<h1>Scheduling</h1>" in html and html.count("<h1") == 1
    for text in ("Default: 60 minutes", "Default: UTC", "Default: Any day, any time", "Default: 9:00 PM–8:00 AM",
                 "Default: 2 hours", "Default: 1 day", "Default: 2 days"):
        assert text in html, text
    for title in ("Appointments", "Working hours", "Quiet hours", "Nudges"):
        assert f"<h2>{title}</h2>" in html
    assert 'value="any" checked' in html and "Monday opening time" in html
    assert html.count('name="reset"') == 7 and ">Save</button>" in html
    for name in ("Appointment length", "Time zone", "Working hours", "Quiet hours", "First nudge", "Last nudge", "Close the lead"):
        assert f'aria-label="Reset {name}"' in html, name  # every Reset says what it resets
    assert 'data-default="60"' in html and 'data-default="UTC"' in html and 'data-default="2880"' in html
    assert 'name=no_quiet_hours value=1 data-default="0"' in html
    # One hours hint, swapped by JS; the radios carry the description, the day switches say what they open.
    assert html.count('id="hours_mode-hint"') == 1 and "hours_set-hint" not in html and "radiogroup" not in html
    assert ps.HOURS_HINTS["any"] in html and html.count('aria-describedby="hours_mode-hint"') == 2
    assert 'aria-label="Open on Monday"' in html and 'aria-label="Open on Sunday"' in html
    assert "Reset returns a rule to its default." in html and "Blank means" not in html
    assert "A nudge that is already scheduled keeps its time." in html and "Nudges and retried texts wait until quiet hours end." in html
    assert client.post("/client/scheduling", data={"csrf": "forged"}).status_code == 400


def test_save_persists_rebuilds_the_policy_and_survives_a_restart(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/scheduling").text)
    saved = client.post("/client/scheduling", data=valid_form(
        csrf, appointment_duration_minutes="90", hours_mode="set", open_sat="1", sat_open="09:00", sat_close="12:00",
        quiet_hours_start="20:00", quiet_hours_end="07:00", followup_delay_1="60", followup_delay_2="2880",
        followup_expiry_minutes="4320"))
    html = saved.text
    assert ps.SAVED in html and "aria-invalid" not in html
    state = client.app.state
    assert state.timezone_name == "America/New_York" and state.appointment_duration_minutes == 90
    assert state.followup_policy.delays_minutes == (60, 2880) and state.followup_policy.expiry_minutes == 4320
    assert state.followup_policy.quiet_start == time(20, 0) and state.followup_policy.quiet_end == time(7, 0)
    assert state.followup_policy.timezone_name == "America/New_York"
    assert state.store.sms_policy is state.followup_policy
    assert json.loads(state.store.setting("working_hours")) == {**WEEKDAYS, "sat": {"open": "09:00", "close": "12:00"}}
    assert 'value="set" checked' in html and 'name=open_sat value=1 checked' in html
    assert "Default: 60 minutes" in html  # the default stays visible beside the saved value
    assert client.get("/health").json()["appointment_duration_minutes"] == 90

    again = create_app(db_path=str(tmp_path / "portal.db"), telecom=FakeTelecom(), public_base_url=BASE,
                       business_name="Oak & Pine Tree Care", now_provider=lambda: clock[0])
    assert again.state.timezone_name == "America/New_York" and again.state.appointment_duration_minutes == 90
    assert again.state.followup_policy == state.followup_policy and again.state.store.sms_policy is again.state.followup_policy


def test_saved_quiet_hours_defer_a_follow_up_through_the_engine(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/scheduling").text)
    # 13:00-14:00 Eastern is not quiet under the UTC 21:00-08:00 default, so a deferral proves the save took.
    assert ps.SAVED in client.post("/client/scheduling", data=valid_form(csrf, quiet_hours_start="13:00", quiet_hours_end="14:00")).text
    state = client.app.state
    intro_at = datetime(2026, 10, 20, 15, 30, tzinfo=timezone.utc)  # 11:30 EDT; first nudge due 13:30 EDT
    schedule_followup_sequence(store=state.store, policy=state.followup_policy, phone=CALLER, call_sid="CA-sched", now=intro_at)
    due = intro_at + timedelta(minutes=120)
    actions = run_due_followups(store=state.store, telecom=telecom, policy=state.followup_policy,
                                business_name=state.business_name, business_number=state.business_number, now=due)
    assert actions == [{"action": "followup_deferred", "phone": CALLER,
                        "deferred_to": datetime(2026, 10, 20, 14, 0, tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc).isoformat()}]
    assert not [m for m in telecom.outbound if m.kind == "followup"]


def test_saved_timezone_changes_how_the_engine_reads_a_preferred_time(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/scheduling").text)
    assert ps.SAVED in client.post("/client/scheduling", data=valid_form(csrf, timezone="America/Chicago")).text
    state = client.app.state
    for index, body in enumerate(("tree removal", "12 Oak St", "2026-10-26 2:00 PM", "Dana")):
        result = submit_event(state=state, kind="sms", params=dict(
            message_sid=f"SM-tz-{index}", from_number=CALLER, to_number=state.business_number, body=body))
    assert result["action"] == "booked"
    event = state.calendar.events[result["event_id"]]
    assert event["start"].utcoffset() == timedelta(hours=-5)  # CDT, not UTC
    assert "2:00 PM CDT" in telecom.outbound[-1].body


def test_set_hours_from_the_page_are_enforced_on_the_next_booking(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/scheduling").text)
    assert ps.SAVED in client.post("/client/scheduling", data=valid_form(csrf, hours_mode="set")).text
    state = client.app.state
    for index, body in enumerate(("tree removal", "12 Oak St", "2026-10-24 10:00 AM", "Dana")):  # a Saturday
        result = submit_event(state=state, kind="sms", params=dict(
            message_sid=f"SM-wh-{index}", from_number=CALLER, to_number=state.business_number, body=body))
    assert result["action"] == "slot_unavailable" and telecom.outbound[-1].kind == "slot_unavailable"
    result = submit_event(state=state, kind="sms", params=dict(
        message_sid="SM-wh-mon", from_number=CALLER, to_number=state.business_number, body="2026-10-26 10:00 AM"))
    assert result["action"] == "booked"


def test_any_day_any_time_deletes_the_key(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/scheduling").text)
    client.post("/client/scheduling", data=valid_form(csrf, hours_mode="set"))
    assert client.app.state.store.setting("working_hours")
    html = client.post("/client/scheduling", data=valid_form(csrf, hours_mode="any")).text
    assert client.app.state.store.setting("working_hours") is None and 'value="any" checked' in html


def test_each_validation_error_is_exact_and_nothing_is_stored(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/scheduling").text)
    store = client.app.state.store

    def post(**over):
        html = client.post("/client/scheduling", data=valid_form(csrf, **over)).text
        assert "Not saved: " in html and 'aria-invalid="true"' in html
        assert all(store.setting(key) is None for key in ps.RESET_GROUPS["quiet_hours"] + ("appointment_duration_minutes", "timezone", "working_hours"))
        return html

    assert _error_under(post(appointment_duration_minutes="7"), "appointment_duration_minutes") == ps.ERR_DURATION
    assert _error_under(post(appointment_duration_minutes="63"), "appointment_duration_minutes") == ps.ERR_DURATION
    assert _error_under(post(timezone="Mars/Olympus"), "timezone") == ps.ERR_TIMEZONE
    assert "Mars/Olympus (current)" in post(timezone="Mars/Olympus")  # the typed value is kept for correction
    assert _error_under(post(hours_mode=""), "hours_mode") == ps.ERR_MODE
    assert 'id="hours_mode-set" value="set" data-default="0" aria-invalid="true" aria-describedby="hours_mode-hint hours_mode-error"' in post(hours_mode="")
    nobody = valid_form(csrf, hours_mode="set")
    for day in WEEKDAYS:
        nobody.pop(f"open_{day}", None)
    assert ps.ERR_NO_DAYS in client.post("/client/scheduling", data=nobody).text
    assert _error_under(post(hours_mode="set", mon_open="08:07"), "hours_mon") == ps.ERR_TIMES
    assert 'aria-label="Open on Monday" aria-describedby="hours_mon-error"' in post(hours_mode="set", mon_open="08:07")
    assert _error_under(post(hours_mode="set", mon_open="17:00", mon_close="08:00"), "hours_mon") == "Monday: opening time must be before closing time."
    assert _error_under(post(hours_mode="set", mon_close="08:30"), "hours_mon") == "Monday: the hours are shorter than one appointment (60 minutes)."
    assert _error_under(post(quiet_hours_start="21:07"), "quiet_hours") == ps.ERR_QUIET
    assert _error_under(post(followup_delay_1="2"), "followup_delay_1") == ps.ERR_NUDGES
    assert _error_under(post(followup_delay_1="2"), "followup_delay_2") is None  # only the bad one is marked
    assert _error_under(post(followup_delay_2="30000"), "followup_delay_2") == ps.ERR_NUDGES
    assert _error_under(post(followup_delay_2="30000"), "followup_delay_1") is None
    assert _error_under(post(followup_expiry_minutes="30"), "followup_expiry_minutes") == ps.ERR_EXPIRY
    html = post(appointment_duration_minutes="7", timezone="Nowhere")
    assert "Not saved: " + ps.ERR_DURATION in html  # the first reason in page order


def test_no_quiet_hours_stores_an_empty_window_and_reset_restores_each_default(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/scheduling").text)
    html = client.post("/client/scheduling", data=valid_form(csrf, no_quiet_hours="1", appointment_duration_minutes="45",
                                                             followup_delay_1="60", followup_delay_2="2880")).text
    state = client.app.state
    assert state.followup_policy.quiet_start == state.followup_policy.quiet_end == time(0, 0)
    assert "name=no_quiet_hours value=1 checked" in html
    # Reset posts the whole form with one group at its defaults; the page's other values ride along.
    page = dict(no_quiet_hours="1", appointment_duration_minutes="45", followup_delay_1="60", followup_delay_2="2880")
    html = client.post("/client/scheduling", data=valid_form(csrf, reset="appointment_duration_minutes", **page)).text
    assert ps.RESET in html and state.store.setting("appointment_duration_minutes") is None and state.appointment_duration_minutes == 60
    assert state.followup_policy.delays_minutes == (60, 2880) and 'value="60"' in html  # the rest of the page kept
    page["appointment_duration_minutes"] = "60"
    client.post("/client/scheduling", data=valid_form(csrf, reset="followup_delay_1", **page))
    assert state.store.setting("followup_delays_minutes") == "120,2880" and state.followup_policy.delays_minutes == (120, 2880)
    page["followup_delay_1"] = "120"
    client.post("/client/scheduling", data=valid_form(csrf, reset="followup_delay_2", **page))
    assert state.store.setting("followup_delays_minutes") is None and state.followup_policy.delays_minutes == (120, 1440)
    page["followup_delay_2"] = "1440"
    html = client.post("/client/scheduling", data=valid_form(csrf, reset="quiet_hours", **page)).text
    assert state.followup_policy.quiet_start == time(21, 0) and "name=no_quiet_hours value=1 checked" not in html
    assert state.store.setting("quiet_hours_start") is None
    assert "Nothing was reset" in client.post("/client/scheduling", data=valid_form(csrf, reset="bogus")).text


def test_reset_keeps_the_other_unsaved_edits_on_the_page(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/scheduling").text)
    state = client.app.state
    # Unsaved edits (90 minutes, set hours) plus Reset on quiet hours: everything is saved, quiet hours at default.
    client.post("/client/scheduling", data=valid_form(csrf, quiet_hours_start="22:00", quiet_hours_end="07:00"))
    assert state.followup_policy.quiet_start == time(22, 0)
    html = client.post("/client/scheduling", data=valid_form(csrf, reset="quiet_hours", appointment_duration_minutes="90",
                                                             hours_mode="set", quiet_hours_start="22:00", quiet_hours_end="07:00")).text
    assert ps.RESET in html and state.followup_policy.quiet_start == time(21, 0) and state.followup_policy.quiet_end == time(8, 0)
    assert state.appointment_duration_minutes == 90 and state.store.setting("working_hours")
    # Reset on working hours with a bad length elsewhere: nothing is written, the error shows, Reset's value is kept on the page.
    html = client.post("/client/scheduling", data=valid_form(csrf, reset="working_hours", appointment_duration_minutes="7", hours_mode="set")).text
    assert "Not saved: " + ps.ERR_DURATION in html and 'value="any" checked' in html
    assert state.store.setting("working_hours") and state.appointment_duration_minutes == 90
    # Saving a value equal to its default leaves no row behind, the same as Reset.
    client.post("/client/scheduling", data=valid_form(csrf, appointment_duration_minutes="60", hours_mode="any"))
    assert state.store.setting("appointment_duration_minutes") is None and state.store.setting("working_hours") is None


def test_corrupt_saved_hours_warn_and_fail_open(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    client.app.state.store.set_setting("working_hours", "{nope")
    html = client.get("/client/scheduling").text
    assert ps.CORRUPT_HOURS in html_lib.unescape(html) and 'value="any" checked' in html


def test_humanize_minutes():
    assert ps.humanize_minutes(30) == "30 minutes" and ps.humanize_minutes(60) == "1 hour"
    assert ps.humanize_minutes(120) == "2 hours" and ps.humanize_minutes(90) == "1 hour 30 minutes"
    assert ps.humanize_minutes(1440) == "1 day" and ps.humanize_minutes(2880) == "2 days"
