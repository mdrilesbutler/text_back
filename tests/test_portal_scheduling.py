"""Schedule page logic: defaults, save and rebuild, enforcement through the engine, exact errors, Reset.

These drive ``portal_scheduling`` directly (parse_form / save / reset_form / page_context) on an app
built with ``create_app``; the HTTP routes and template are covered once they exist.
"""
import json
import re
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from text_back import portal_scheduling as ps
from text_back import working_hours as wh
from text_back.app import create_app
from text_back.booking import SlotUnavailableError, book_appointment
from text_back.followup import run_due_followups, schedule_followup_sequence
from text_back.inbox import submit_event
from text_back.sms import enqueue_sms
from text_back.telecom import FakeTelecom

NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
BASE = "https://example.test"
CALLER = "+17045550141"
WEEKDAYS = {"mon": {"open": "08:00", "close": "17:00"}, "tue": {"open": "08:00", "close": "17:00"},
            "wed": {"open": "08:00", "close": "17:00"}, "thu": {"open": "08:00", "close": "17:00"},
            "fri": {"open": "08:00", "close": "17:00"}, "sat": None, "sun": None}
DECK = Path(__file__).resolve().parents[1] / "docs" / "notes" / "portal-c" / "copy-deck.md"


def build(tmp_path, monkeypatch):
    """A booted app on a temp database: (state, telecom, clock)."""
    monkeypatch.setenv("TEXT_BACK_OWNER_MOBILE", "+19805550123")
    monkeypatch.delenv("TEXT_BACK_TIMEZONE", raising=False)
    clock = [NOW]
    telecom = FakeTelecom()
    app = create_app(db_path=str(tmp_path / "portal.db"), telecom=telecom, public_base_url=BASE,
                     business_name="Oak & Pine Tree Care", now_provider=lambda: clock[0])
    return app.state, telecom, clock


def valid_form(**over):
    form = {"appointment_duration_minutes": "60", "timezone": "America/New_York", "hours_mode": "any",
            "quiet_hours_start": "21:00", "quiet_hours_end": "08:00",
            "followup_delay_1": "120", "followup_delay_2": "1440", "followup_expiry_minutes": "2880"}
    for day, window in WEEKDAYS.items():
        if window:
            form[f"open_{day}"] = "1"
        form[f"{day}_open"] = (window or {"open": "08:00"})["open"]
        form[f"{day}_close"] = (window or {"close": "17:00"})["close"]
    form.update(over)
    return form


def post(state, form, now=NOW):
    """parse + save like the route will: (values, errors, save_error)."""
    values, errors = ps.parse_form(form, state)
    if errors:
        return values, errors, None
    return values, errors, ps.save(state, values["_settings"], now)


def saved(state, form, now=NOW):
    values, errors, problem = post(state, form, now)
    assert not errors and problem is None, (errors, problem)
    return values


def reset(state, form, group, now=NOW):
    merged = ps.reset_form(form, group, state)
    assert merged is not None
    return post(state, merged, now)


def _deck_section(title: str) -> list[str]:
    """Every text cell of one deck section, split on the ' / ' variant separator."""
    text = DECK.read_text(encoding="utf-8")
    body = text.split(f"## {title}", 1)[1].split("\n## ", 1)[0]
    cells = []
    for line in body.splitlines():
        if line.startswith("| ") and not line.startswith("| key") and not line.startswith("|---"):
            cells.extend(part.strip() for part in line.split("|")[2].split(" / "))
    return cells


# --- words -----------------------------------------------------------------------

def test_every_user_facing_string_is_in_the_copy_deck():
    deck = _deck_section("5. Schedule")
    bracketed = [re.sub(r"\[[^\]]*\]", "{}", cell) for cell in deck]
    for text in (*ps.APPLIES.values(), ps.ANY_TIME_NOTE, ps.QUIET_LEGEND, ps.QUIET_OFF, *ps.DAY_WORDS,
                 ps.CORRUPT_HOURS, ps.ANY_TIME_WARNING, ps.ANY_TIME_BUTTON, ps.ERR_DURATION, ps.ERR_TIMEZONE,
                 ps.ERR_MODE, ps.ERR_NO_DAYS, ps.ERR_TIMES, ps.ERR_QUIET, ps.ERR_REMINDERS, ps.ERR_EXPIRY,
                 *ps.HOURS_HINTS.values(), *ps.CONSEQUENCES.values(), *ps.LABELS.values()):
        assert text in deck, text
    # The save notice names what changed (deck schedule_toast); "reminders already scheduled keep their time"
    # now sits on the Reminders card (reminder_consequence), pinned below like every other claim.
    assert ps.SAVED == "Saved. You changed “{rules}”. It applies now, including customers mid-conversation."
    assert re.sub(r"\{rules\}", "{}", ps.SAVED) in bracketed and ps.SAVED_NOTHING == "Saved."
    for banned in ("nudge", "Nudge", "give-up", "Give-up", "Close the lead"):
        for text in (ps.ERR_REMINDERS, ps.ERR_EXPIRY, *ps.LABELS.values(), *ps.CONSEQUENCES.values()):
            assert banned not in text
    # Errors with a day or a number filled in follow the deck's bracketed shapes.
    assert "{}: opening time must be before closing time." in bracketed
    assert "{}: the hours are shorter than one appointment ({} minutes)." in bracketed


def test_save_notice_names_only_the_rules_that_changed(tmp_path, monkeypatch):
    state, _, _ = build(tmp_path, monkeypatch)
    before = ps.current_values(state)
    assert ps.saved_notice(before, ps.current_values(state)) == "Saved."
    saved(state, valid_form(appointment_duration_minutes="90", quiet_hours_start="22:00", quiet_hours_end="06:00"))
    assert ps.saved_notice(before, ps.current_values(state)) == (
        "Saved. You changed “Appointment length”, “Time zone”, “Quiet hours”. It applies now, including customers "
        "mid-conversation.")  # valid_form() also moves the zone from the UTC default to New York
    again = ps.current_values(state)
    saved(state, valid_form(appointment_duration_minutes="90", quiet_hours_start="22:00", quiet_hours_end="06:00",
                            hours_mode="set"))
    assert ps.changed_rules(again, ps.current_values(state)) == ["Working hours"]
    # A reminder delay among the changes: the notice says scheduled reminders keep their time
    # (pinned to the engine by test_save_confirmation_matches_live_behaviour).
    before = ps.current_values(state)
    saved(state, valid_form(appointment_duration_minutes="90", quiet_hours_start="22:00", quiet_hours_end="06:00",
                            hours_mode="set", followup_delay_1="240"))
    assert ps.saved_notice(before, ps.current_values(state)) == (
        "Saved. You changed “If there's no reply, send a reminder after”. It applies now, including customers "
        "mid-conversation; reminders already scheduled keep their time.")


# --- defaults and the page context --------------------------------------------------

def test_page_context_shows_every_default_and_consequence(tmp_path, monkeypatch):
    state, _, _ = build(tmp_path, monkeypatch)
    values = ps.current_values(state)
    assert values["defaults"] == {
        "appointment_duration_minutes": "60 minutes", "timezone": "UTC", "working_hours": "Any day, any time",
        "quiet_hours": "9:00 PM–8:00 AM", "followup_delay_1": "2 hours", "followup_delay_2": "1 day",
        "followup_expiry_minutes": "2 days",
    }
    assert values["raw_defaults"] == {
        "appointment_duration_minutes": "60", "timezone": "UTC", "quiet_hours_start": "21:00", "quiet_hours_end": "08:00",
        "no_quiet_hours": "0", "followup_delay_1": "120", "followup_delay_2": "1440", "followup_expiry_minutes": "2880",
    }
    assert values["hours_mode"] == "any" and values["appointment_duration_minutes"] == "60"
    assert values["hours"]["mon"] == {"on": True, "open": "08:00", "close": "17:00"} and values["hours"]["sat"]["on"] is False
    assert ps.timezone_label("America/New_York") == "Eastern (New York)"

    context = ps.page_context(state, values)
    assert context["defaults"] is values["defaults"] and context["errors"] == {}
    assert [row["name"] for row in context["day_rows"]] == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    assert context["day_rows"][0]["open_options"][32] == ("08:00", "8:00 AM") and context["day_rows"][0]["close_options"][-1] == ("24:00", "midnight")
    assert ("21:00", "9:00 PM") in context["quiet_options"]
    assert context["delay1_options"][0] == ("30", "30 minutes") and ("120", "2 hours") in context["delay1_options"]
    assert ("1440", "1 day") in context["delay2_options"] and ("2880", "2 days") in context["expiry_options"]
    assert context["hours_warning"] == "" and context["hours_hints"] == ps.HOURS_HINTS
    assert set(context["consequences"]) == {"appointment_duration_minutes", "timezone", "working_hours", "quiet_hours",
                                            "followup_delay_1", "followup_delay_2", "followup_expiry_minutes"}
    assert context["consequences"]["working_hours"] == ps.HOURS_HINTS["any"]
    assert context["consequences"]["followup_delay_1"] == context["consequences"]["followup_delay_2"] == ps.CONSEQUENCES["followup_delay_1"]
    assert context["labels"] == ps.LABELS and set(ps.LABELS) == set(ps.RESET_GROUPS)
    assert context["labels"]["followup_expiry_minutes"] == "Stop waiting for a reply after"
    assert context["timezone_options"][0] == ("America/New_York", "Eastern (New York)")


def test_chip_selected_only_when_it_equals_the_field(tmp_path, monkeypatch):
    state, _, _ = build(tmp_path, monkeypatch)
    values = ps.current_values(state)

    def chips(raw):
        values["appointment_duration_minutes"] = raw
        context = ps.page_context(state, values)
        return [c["value"] for c in context["duration_chips"] if c["selected"]], context["duration_custom"]

    assert [c["label"] for c in ps.page_context(state, values)["duration_chips"]] == ["30 min", "45 min", "60 min", "90 min", "120 min"]
    assert chips("60") == (["60"], False)
    assert chips("090") == (["90"], False)  # int(field) == preset, not string equality
    assert chips("75") == ([], True)
    assert chips("") == ([], True)
    assert chips("sixty") == ([], True)


def test_any_time_shows_the_warning_and_suggested_hours(tmp_path, monkeypatch):
    state, _, _ = build(tmp_path, monkeypatch)
    values = ps.current_values(state)
    context = ps.page_context(state, values)
    assert context["any_time_warning"] is True
    assert context["any_time_warning_text"] == "Customers can be offered times like 1 AM. Set your hours."
    assert context["any_time_button"] == "Use Mon–Fri, 8 AM–5 PM"
    assert context["suggested_hours"] == {
        "mon": {"open": "08:00", "close": "17:00"}, "tue": {"open": "08:00", "close": "17:00"},
        "wed": {"open": "08:00", "close": "17:00"}, "thu": {"open": "08:00", "close": "17:00"},
        "fri": {"open": "08:00", "close": "17:00"}, "sat": None, "sun": None,
    }
    assert wh.parse_working_hours(json.dumps(context["suggested_hours"])) == context["suggested_hours"]
    saved(state, valid_form(hours_mode="set"))
    context = ps.page_context(state, ps.current_values(state))
    assert context["any_time_warning"] is False and context["consequences"]["working_hours"] == ps.HOURS_HINTS["set"]
    # A re-rendered form that failed validation with "set" chosen does not warn either.
    values, errors = ps.parse_form(valid_form(hours_mode="set", appointment_duration_minutes="7"), state)
    assert errors and ps.page_context(state, values, errors)["any_time_warning"] is False


# --- save, rebuild, persistence ------------------------------------------------------

def test_save_persists_rebuilds_the_policy_and_survives_a_restart(tmp_path, monkeypatch):
    state, _, clock = build(tmp_path, monkeypatch)
    values = saved(state, valid_form(
        appointment_duration_minutes="90", hours_mode="set", open_sat="1", sat_open="09:00", sat_close="12:00",
        quiet_hours_start="20:00", quiet_hours_end="07:00", followup_delay_1="60", followup_delay_2="2880",
        followup_expiry_minutes="4320"))
    assert state.timezone_name == "America/New_York" and state.appointment_duration_minutes == 90
    assert state.followup_policy.delays_minutes == (60, 2880) and state.followup_policy.expiry_minutes == 4320
    assert state.followup_policy.quiet_start == time(20, 0) and state.followup_policy.quiet_end == time(7, 0)
    assert state.followup_policy.timezone_name == "America/New_York"
    assert state.store.sms_policy is state.followup_policy
    assert json.loads(state.store.setting("working_hours")) == {**WEEKDAYS, "sat": {"open": "09:00", "close": "12:00"}}
    assert values["hours_mode"] == "set" and values["hours"]["sat"] == {"on": True, "open": "09:00", "close": "12:00"}
    assert values["defaults"]["appointment_duration_minutes"] == "60 minutes"  # the default stays visible beside the saved value
    after = ps.current_values(state)
    assert after["appointment_duration_minutes"] == "90" and after["quiet_hours_start"] == "20:00"

    again = create_app(db_path=str(tmp_path / "portal.db"), telecom=FakeTelecom(), public_base_url=BASE,
                       business_name="Oak & Pine Tree Care", now_provider=lambda: clock[0])
    assert again.state.timezone_name == "America/New_York" and again.state.appointment_duration_minutes == 90
    assert again.state.followup_policy == state.followup_policy and again.state.store.sms_policy is again.state.followup_policy
    assert again.state.defaults["appointment_duration_minutes"] == 60 and again.state.defaults["timezone"] == "UTC"


def test_save_confirmation_matches_live_behaviour(tmp_path, monkeypatch):
    """Every claim in SAVED is pinned to engine behaviour."""
    state, telecom, clock = build(tmp_path, monkeypatch)
    store = state.store
    # A customer mid-conversation: service and location given, time still to come.
    for index, body in enumerate(("tree removal", "12 Oak St")):
        submit_event(state=state, kind="sms", params=dict(
            message_sid=f"SM-mid-{index}", from_number=CALLER, to_number=state.business_number, body=body))
    # A reminder already scheduled for that caller, plus its queued text.
    schedule_followup_sequence(store=store, policy=state.followup_policy, phone=CALLER, call_sid="CA-mid", now=NOW)
    sequence_before = store.get_followup(CALLER)
    assert sequence_before["status"] == "active"
    queued_at = NOW + timedelta(hours=2)
    enqueue_sms(store=store, key="CA-mid:followup:1", to=CALLER, from_number=state.business_number,
                body="Still want a time?", kind="followup", now=queued_at)
    row_before = dict(store.conn.execute("SELECT * FROM sms_outbox WHERE key='CA-mid:followup:1'").fetchone())
    assert row_before["status"] == "pending" and row_before["next_attempt_at"] == queued_at.isoformat()
    assert state.appointment_duration_minutes == 60 and state.followup_policy.quiet_start == time(21, 0)

    saved(state, valid_form(appointment_duration_minutes="90", hours_mode="set",
                            quiet_hours_start="22:00", quiet_hours_end="06:00"))

    # "reminders already scheduled keep their time": neither the sequence nor the queued text moved.
    assert store.get_followup(CALLER)["next_action_at"] == sequence_before["next_action_at"]
    row_after = dict(store.conn.execute("SELECT * FROM sms_outbox WHERE key='CA-mid:followup:1'").fetchone())
    assert row_after["next_attempt_at"] == row_before["next_attempt_at"] and row_after["status"] == "pending"
    # Quiet hours are live in the policy the worker and the outbox read.
    assert state.followup_policy.quiet_start == time(22, 0) and state.followup_policy.quiet_end == time(6, 0)
    assert store.sms_policy is state.followup_policy

    # "Applies now, including customers mid-conversation": length and hours are live for the existing conversation.
    assert state.appointment_duration_minutes == 90
    assert json.loads(store.setting("working_hours")) == WEEKDAYS
    saturday_10am_edt = datetime(2026, 10, 24, 14, 0, tzinfo=timezone.utc)
    with pytest.raises(SlotUnavailableError, match="outside working hours"):
        book_appointment(calendar=state.calendar, store=store, telecom=telecom, caller=CALLER,
                         business_number=state.business_number, service="tree removal", location="12 Oak St",
                         customer_name="Dana", business_name=state.business_name, timezone_name=state.timezone_name,
                         start=saturday_10am_edt, duration_minutes=state.appointment_duration_minutes,
                         conversation_id=CALLER, now=NOW)
    # The conversation books once the name arrives: a Saturday asked for before the save is now turned down.
    for sid, body in (("SM-mid-sat", "2026-10-24 10:00 AM"), ("SM-mid-name", "Dana")):
        result = submit_event(state=state, kind="sms", params=dict(
            message_sid=sid, from_number=CALLER, to_number=state.business_number, body=body))
    assert result["action"] == "slot_unavailable" and telecom.outbound[-1].kind == "slot_unavailable"
    # The same conversation continues and books inside the new hours at the new length.
    result = submit_event(state=state, kind="sms", params=dict(
        message_sid="SM-mid-mon", from_number=CALLER, to_number=state.business_number, body="2026-10-26 10:00 AM"))
    assert result["action"] == "booked"
    event = state.calendar.events[store.appointment_by_conversation(CALLER)["event_id"]]
    assert event["end"] - event["start"] == timedelta(minutes=90)  # the new length, mid-conversation


def test_saved_quiet_hours_defer_a_follow_up_through_the_engine(tmp_path, monkeypatch):
    state, telecom, _ = build(tmp_path, monkeypatch)
    # 13:00-14:00 Eastern is not quiet under the UTC 21:00-08:00 default, so a deferral proves the save took.
    saved(state, valid_form(quiet_hours_start="13:00", quiet_hours_end="14:00"))
    intro_at = datetime(2026, 10, 20, 15, 30, tzinfo=timezone.utc)  # 11:30 EDT; first reminder due 13:30 EDT
    schedule_followup_sequence(store=state.store, policy=state.followup_policy, phone=CALLER, call_sid="CA-sched", now=intro_at)
    due = intro_at + timedelta(minutes=120)
    actions = run_due_followups(store=state.store, telecom=telecom, policy=state.followup_policy,
                                business_name=state.business_name, business_number=state.business_number, now=due)
    assert actions == [{"action": "followup_deferred", "phone": CALLER,
                        "deferred_to": datetime(2026, 10, 20, 14, 0, tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc).isoformat()}]
    assert not [m for m in telecom.outbound if m.kind == "followup"]


def test_saved_timezone_changes_how_a_preferred_time_is_read(tmp_path, monkeypatch):
    state, telecom, _ = build(tmp_path, monkeypatch)
    saved(state, valid_form(timezone="America/Chicago"))
    for index, body in enumerate(("tree removal", "12 Oak St", "2026-10-26 2:00 PM", "Dana")):
        result = submit_event(state=state, kind="sms", params=dict(
            message_sid=f"SM-tz-{index}", from_number=CALLER, to_number=state.business_number, body=body))
    assert result["action"] == "booked"
    event = state.calendar.events[result["event_id"]]
    assert event["start"].utcoffset() == timedelta(hours=-5)  # CDT, not UTC
    assert "2:00 PM CDT" in telecom.outbound[-1].body


def test_saved_hours_leave_bookings_already_made_as_they_are(tmp_path, monkeypatch):
    """APPLIES["working_hours"]: "Bookings already made stay as they are"."""
    state, telecom, _ = build(tmp_path, monkeypatch)
    saturday = datetime(2026, 10, 24, 14, 0, tzinfo=timezone.utc)
    book_appointment(calendar=state.calendar, store=state.store, telecom=telecom, caller=CALLER,
                     business_number=state.business_number, service="tree removal", location="12 Oak St",
                     customer_name="Dana", business_name=state.business_name, timezone_name="America/New_York",
                     start=saturday, duration_minutes=60, conversation_id=CALLER, now=NOW)
    booked = dict(state.store.appointment_by_conversation(CALLER))
    saved(state, valid_form(hours_mode="set"))  # Saturday is now closed
    assert dict(state.store.appointment_by_conversation(CALLER)) == booked
    assert booked["event_id"] in state.calendar.events


def test_saved_quiet_hours_hold_a_reminder_scheduled_before_the_save(tmp_path, monkeypatch):
    """APPLIES["quiet_hours"]: "Applies right away to reminders not yet sent"."""
    state, telecom, _ = build(tmp_path, monkeypatch)
    intro_at = datetime(2026, 10, 20, 15, 30, tzinfo=timezone.utc)  # 11:30 EDT; first reminder due 13:30 EDT
    schedule_followup_sequence(store=state.store, policy=state.followup_policy, phone=CALLER, call_sid="CA-pre", now=intro_at)
    saved(state, valid_form(quiet_hours_start="13:00", quiet_hours_end="14:00"))  # after it was scheduled
    actions = run_due_followups(store=state.store, telecom=telecom, policy=state.followup_policy,
                                business_name=state.business_name, business_number=state.business_number,
                                now=intro_at + timedelta(minutes=120))
    assert [a["action"] for a in actions] == ["followup_deferred"]
    assert not [m for m in telecom.outbound if m.kind == "followup"]


def test_set_hours_are_enforced_on_the_next_booking(tmp_path, monkeypatch):
    state, telecom, _ = build(tmp_path, monkeypatch)
    saved(state, valid_form(hours_mode="set"))
    for index, body in enumerate(("tree removal", "12 Oak St", "2026-10-24 10:00 AM", "Dana")):  # a Saturday
        result = submit_event(state=state, kind="sms", params=dict(
            message_sid=f"SM-wh-{index}", from_number=CALLER, to_number=state.business_number, body=body))
    assert result["action"] == "slot_unavailable" and telecom.outbound[-1].kind == "slot_unavailable"
    result = submit_event(state=state, kind="sms", params=dict(
        message_sid="SM-wh-mon", from_number=CALLER, to_number=state.business_number, body="2026-10-26 10:00 AM"))
    assert result["action"] == "booked"


def test_any_day_any_time_deletes_the_key(tmp_path, monkeypatch):
    state, _, _ = build(tmp_path, monkeypatch)
    saved(state, valid_form(hours_mode="set"))
    assert state.store.setting("working_hours")
    values = saved(state, valid_form(hours_mode="any"))
    assert state.store.setting("working_hours") is None and values["hours_mode"] == "any"


# --- validation ----------------------------------------------------------------------

def test_each_validation_error_is_exact_and_nothing_is_stored(tmp_path, monkeypatch):
    state, _, _ = build(tmp_path, monkeypatch)
    store = state.store
    untouched = ps.RESET_GROUPS["quiet_hours"] + ("appointment_duration_minutes", "timezone", "working_hours",
                                                 "followup_delays_minutes", "followup_expiry_minutes")

    def errors_of(**over):
        values, errors, problem = post(state, valid_form(**over))
        assert errors and problem is None and "_settings" not in values
        assert all(store.setting(key) is None for key in untouched)
        return values, errors

    assert errors_of(appointment_duration_minutes="7")[1] == {"appointment_duration_minutes": ps.ERR_DURATION}
    assert errors_of(appointment_duration_minutes="63")[1] == {"appointment_duration_minutes": ps.ERR_DURATION}
    values, errors = errors_of(timezone="Mars/Olympus")
    assert errors == {"timezone": ps.ERR_TIMEZONE}
    assert ("Mars/Olympus", "Mars/Olympus (current)") in ps.page_context(state, values, errors)["timezone_options"]  # kept for correction
    assert errors_of(hours_mode="")[1] == {"hours_mode": ps.ERR_MODE}
    nobody = valid_form(hours_mode="set")
    for day in WEEKDAYS:
        nobody.pop(f"open_{day}", None)
    assert ps.parse_form(nobody, state)[1] == {"hours": ps.ERR_NO_DAYS}
    assert errors_of(hours_mode="set", mon_open="08:07")[1] == {"hours_mon": ps.ERR_TIMES}
    assert errors_of(hours_mode="set", mon_open="17:00", mon_close="08:00")[1] == {"hours_mon": "Monday: opening time must be before closing time."}
    assert errors_of(hours_mode="set", mon_close="08:30")[1] == {"hours_mon": "Monday: the hours are shorter than one appointment (60 minutes)."}
    values, errors = errors_of(hours_mode="set", sun_open="08:07", open_sun="1")
    assert errors == {"hours_sun": ps.ERR_TIMES} and ps.page_context(state, values, errors)["day_rows"][6]["error"] == ps.ERR_TIMES
    assert errors_of(quiet_hours_start="21:07")[1] == {"quiet_hours": ps.ERR_QUIET}
    assert errors_of(followup_delay_1="2")[1] == {"followup_delay_1": ps.ERR_REMINDERS}  # only the bad one is marked
    assert errors_of(followup_delay_2="30000")[1] == {"followup_delay_2": ps.ERR_REMINDERS}
    assert errors_of(followup_expiry_minutes="30")[1] == {"followup_expiry_minutes": ps.ERR_EXPIRY}
    assert errors_of(followup_expiry_minutes="43201")[1] == {"followup_expiry_minutes": ps.ERR_EXPIRY}
    _, errors = errors_of(appointment_duration_minutes="7", timezone="Nowhere")
    assert ps.first_error(errors) == ps.ERR_DURATION  # the first reason in page order
    assert ps.first_error({"hours_tue": ps.ERR_TIMES, "quiet_hours": ps.ERR_QUIET}) == ps.ERR_TIMES


def test_save_rejects_a_policy_the_engine_would_refuse_before_writing(tmp_path, monkeypatch):
    state, _, _ = build(tmp_path, monkeypatch)
    before = state.followup_policy
    # parse_form never lets a zero delay through; save() still refuses it before any write.
    problem = ps.save(state, {"followup_delays_minutes": "0,1440", "followup_expiry_minutes": "4320"}, NOW)
    assert problem == "followup delays must be positive minutes"
    assert state.followup_policy is before and state.store.setting("followup_expiry_minutes") is None
    assert state.store.setting("followup_delays_minutes") is None
    assert ps.save(state, {"followup_delays_minutes": "", "followup_expiry_minutes": ""}, NOW) is None  # blank = default
    assert state.followup_policy == before and state.store.setting("followup_delays_minutes") is None


# --- reset ---------------------------------------------------------------------------

def test_no_quiet_hours_stores_an_empty_window_and_reset_restores_each_default(tmp_path, monkeypatch):
    state, _, _ = build(tmp_path, monkeypatch)
    store = state.store
    values = saved(state, valid_form(no_quiet_hours="1", appointment_duration_minutes="45",
                                     followup_delay_1="60", followup_delay_2="2880"))
    assert state.followup_policy.quiet_start == state.followup_policy.quiet_end == time(0, 0)
    assert values["no_quiet_hours"] is True and store.setting("quiet_hours_start") == "00:00"
    # Reset posts the whole form with one group at its defaults; the page's other values ride along.
    page = dict(no_quiet_hours="1", appointment_duration_minutes="45", followup_delay_1="60", followup_delay_2="2880")
    values, errors, problem = reset(state, valid_form(**page), "appointment_duration_minutes")
    assert not errors and problem is None
    assert store.setting("appointment_duration_minutes") is None and state.appointment_duration_minutes == 60
    assert state.followup_policy.delays_minutes == (60, 2880) and values["followup_delay_1"] == "60"  # the rest kept
    page["appointment_duration_minutes"] = "60"
    reset(state, valid_form(**page), "followup_delay_1")
    assert store.setting("followup_delays_minutes") == "120,2880" and state.followup_policy.delays_minutes == (120, 2880)
    page["followup_delay_1"] = "120"
    reset(state, valid_form(**page), "followup_delay_2")
    assert store.setting("followup_delays_minutes") is None and state.followup_policy.delays_minutes == (120, 1440)
    page["followup_delay_2"] = "1440"
    values, _, _ = reset(state, valid_form(**page), "quiet_hours")
    assert state.followup_policy.quiet_start == time(21, 0) and values["no_quiet_hours"] is False
    assert store.setting("quiet_hours_start") is None and store.setting("quiet_hours_end") is None
    saved(state, valid_form(timezone="America/Chicago", followup_expiry_minutes="4320"))
    reset(state, valid_form(timezone="America/Chicago", followup_expiry_minutes="4320"), "timezone")
    assert store.setting("timezone") is None and state.timezone_name == "UTC" and state.followup_policy.expiry_minutes == 4320
    reset(state, valid_form(followup_expiry_minutes="4320"), "followup_expiry_minutes")
    assert store.setting("followup_expiry_minutes") is None and state.followup_policy.expiry_minutes == 2880
    assert ps.reset_form(valid_form(), "bogus", state) is None


def test_reset_keeps_the_other_unsaved_edits_on_the_page(tmp_path, monkeypatch):
    state, _, _ = build(tmp_path, monkeypatch)
    store = state.store
    saved(state, valid_form(quiet_hours_start="22:00", quiet_hours_end="07:00"))
    assert state.followup_policy.quiet_start == time(22, 0)
    # Unsaved edits (90 minutes, set hours) plus Reset on quiet hours: everything is saved, quiet hours at default.
    _, errors, problem = reset(state, valid_form(appointment_duration_minutes="90", hours_mode="set",
                                                 quiet_hours_start="22:00", quiet_hours_end="07:00"), "quiet_hours")
    assert not errors and problem is None
    assert state.followup_policy.quiet_start == time(21, 0) and state.followup_policy.quiet_end == time(8, 0)
    assert state.appointment_duration_minutes == 90 and store.setting("working_hours")
    # Reset on working hours with a bad length elsewhere: nothing is written, the error shows, Reset's value stays on the page.
    values, errors, _ = reset(state, valid_form(appointment_duration_minutes="7", hours_mode="set"), "working_hours")
    assert errors == {"appointment_duration_minutes": ps.ERR_DURATION} and values["hours_mode"] == "any"
    assert store.setting("working_hours") and state.appointment_duration_minutes == 90
    # Saving a value equal to its default leaves no row behind, the same as Reset.
    saved(state, valid_form(appointment_duration_minutes="60", hours_mode="any"))
    assert store.setting("appointment_duration_minutes") is None and store.setting("working_hours") is None


def test_corrupt_saved_hours_warn_and_fail_open(tmp_path, monkeypatch):
    state, telecom, _ = build(tmp_path, monkeypatch)
    state.store.set_setting("working_hours", "{nope")
    values = ps.current_values(state)
    assert values["hours_corrupt"] is True and values["hours_mode"] == "any"
    context = ps.page_context(state, values)
    assert context["hours_warning"] == ps.CORRUPT_HOURS and context["any_time_warning"] is True
    saturday_10am_edt = datetime(2026, 10, 24, 14, 0, tzinfo=timezone.utc)
    result = book_appointment(calendar=state.calendar, store=state.store, telecom=telecom, caller=CALLER,
                              business_number=state.business_number, service="tree removal", location="12 Oak St",
                              customer_name="Dana", business_name=state.business_name, timezone_name="America/New_York",
                              start=saturday_10am_edt, duration_minutes=60, conversation_id=CALLER, now=NOW)
    assert result["booked"] is True  # every time counts as open until the owner saves again
    saved(state, valid_form(hours_mode="set"))
    assert ps.current_values(state)["hours_corrupt"] is False


def test_humanize_minutes():
    assert ps.humanize_minutes(30) == "30 minutes" and ps.humanize_minutes(60) == "1 hour"
    assert ps.humanize_minutes(120) == "2 hours" and ps.humanize_minutes(90) == "1 hour 30 minutes"
    assert ps.humanize_minutes(1440) == "1 day" and ps.humanize_minutes(2880) == "2 days"
    assert ps.humanize_minutes(1) == "1 minute"


# --- the reminder count is the policy's, never silently changed by a save -----------------

def test_one_default_reminder_shows_and_saves_only_reminder_1(tmp_path, monkeypatch):
    monkeypatch.setenv("TEXT_BACK_FOLLOWUP_DELAYS_MINUTES", "120")
    state, _, _ = build(tmp_path, monkeypatch)
    assert state.followup_policy.delays_minutes == (120,)
    values = ps.current_values(state)
    assert values["reminder_count"] == 1
    saved(state, valid_form(followup_delay_1="240", followup_delay_2="1440"))
    assert state.followup_policy.delays_minutes == (240,)
    assert state.store.setting("followup_delays_minutes") == "240"
    page = ps.page_context(state, ps.current_values(state))
    assert page["reminder_count"] == 1


def test_one_reminder_ignores_a_bad_posted_second_delay(tmp_path, monkeypatch):
    monkeypatch.setenv("TEXT_BACK_FOLLOWUP_DELAYS_MINUTES", "120")
    state, _, _ = build(tmp_path, monkeypatch)
    form = valid_form(followup_delay_1="120")
    form.pop("followup_delay_2")
    saved(state, form)
    assert state.followup_policy.delays_minutes == (120,)
    assert state.store.setting("followup_delays_minutes") is None  # equal to the default: no row


def test_three_reminders_keep_the_third_after_the_two_edited_ones(tmp_path, monkeypatch):
    monkeypatch.setenv("TEXT_BACK_FOLLOWUP_DELAYS_MINUTES", "120,1440,2880")
    monkeypatch.setenv("TEXT_BACK_FOLLOWUP_EXPIRY_MINUTES", "10080")
    state, _, _ = build(tmp_path, monkeypatch)
    assert ps.current_values(state)["reminder_count"] == 3
    saved(state, valid_form(followup_delay_1="60", followup_delay_2="720", followup_expiry_minutes="10080"))
    assert state.followup_policy.delays_minutes == (60, 720, 2880)
    assert state.store.setting("followup_delays_minutes") == "60,720,2880"


def test_two_reminders_are_unchanged(tmp_path, monkeypatch):
    state, _, _ = build(tmp_path, monkeypatch)
    assert ps.current_values(state)["reminder_count"] == 2
    saved(state, valid_form(followup_delay_1="60", followup_delay_2="720"))
    assert state.followup_policy.delays_minutes == (60, 720)


def test_one_reminder_page_renders_without_the_second_field(tmp_path, monkeypatch):
    from test_client_portal import make, sign_in

    monkeypatch.setenv("TEXT_BACK_FOLLOWUP_DELAYS_MINUTES", "120")
    client, telecom, _, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/schedule").text
    assert "name=followup_delay_1" in page and "name=followup_delay_2" not in page
