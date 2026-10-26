"""Forwarding checks tick only from a call the carrier forwarded from the business line."""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from text_back.handlers import handle_voice_event
from text_back.portal_forwarding import checklist, save_manual_ticks
from text_back.store import Store
from text_back.telecom import FakeTelecom

NOW = datetime(2026, 10, 26, 14, 0, tzinfo=timezone.utc)
BUSINESS, TEXTING, CALLER = "+17045550123", "+17045550100", "+19805550141"


def _state(tmp_path, business_line=BUSINESS):
    store = Store(str(tmp_path / "t.db"))
    if business_line:
        store.set_setting("business_line", business_line)
    return SimpleNamespace(store=store, business_number=TEXTING, timezone_name="America/New_York")


def _call(state, sid, caller=CALLER, forwarded_from="", at=NOW - timedelta(hours=1)):
    telecom = FakeTelecom()
    handle_voice_event(store=state.store, telecom=telecom, call_sid=sid, call_status="ringing", from_number=caller,
                       to_number=TEXTING, wiring_mode="forwarded", business_name="Oak", now=at, forwarded_from=forwarded_from)
    return telecom


def _mark_sent(state, sid, at=NOW - timedelta(hours=1)):
    with state.store.transaction():
        state.store.conn.execute("UPDATE sms_outbox SET status='sent' WHERE key=?", (f"{sid}:intro",))
        state.store.record_outcome(lead_id=CALLER, event_type="sms.initial_sent", idempotency_key=f"call:{sid}:initial_sms",
                                   evidence_id=sid, occurred_at=at.isoformat())


def _words(result):
    return [(s["n"], s["state_word"]) for s in result["steps"]]


def test_direct_call_never_ticks_forwarding(tmp_path):
    state = _state(tmp_path)
    _call(state, "CA-direct"); _mark_sent(state, "CA-direct")
    result = checklist(state, NOW)
    assert _words(result) == [(1, "Not yet"), (2, "Not yet"), (3, "Not yet"), (4, "Not yet"), (5, "Not yet")]
    assert result["done_count"] == 0 and result["state_word"] == "Needs you"
    assert "Waits for check 1." in result["steps"][1]["evidence"]


def test_forwarded_call_ticks_1_2_4_with_full_dates(tmp_path):
    state = _state(tmp_path)
    _call(state, "CA-fwd", forwarded_from=BUSINESS); _mark_sent(state, "CA-fwd")
    result = checklist(state, NOW)
    assert _words(result) == [(1, "Done"), (2, "Done"), (3, "Not yet"), (4, "Done"), (5, "Not yet")]
    assert "Mon, Oct 26" in result["steps"][0]["evidence"] or "Today" in result["steps"][0]["evidence"]
    assert "0141" in result["steps"][0]["evidence"]
    assert result["done_count"] == 3


def test_a_direct_leg_and_a_forwarded_leg_to_the_same_caller_break_check_2(tmp_path):
    # Forwarded twice (or forwarded plus a direct ring): two call_sids, two first texts, one caller.
    state = _state(tmp_path)
    fwd_at = NOW - timedelta(hours=1)
    _call(state, "CA-fwd", forwarded_from=BUSINESS, at=fwd_at); _mark_sent(state, "CA-fwd", at=fwd_at)
    _call(state, "CA-direct", at=fwd_at + timedelta(minutes=2)); _mark_sent(state, "CA-direct", at=fwd_at + timedelta(minutes=2))
    step = checklist(state, NOW)["steps"][1]
    assert (step["n"], step["state_word"]) == (2, "Not yet")
    assert step["evidence"] == "2 texts went out for one call. Check that the number isn't forwarded twice."


def test_reminders_and_a_later_call_do_not_break_check_2(tmp_path):
    state = _state(tmp_path)
    fwd_at = NOW - timedelta(hours=1)
    _call(state, "CA-fwd", forwarded_from=BUSINESS, at=fwd_at); _mark_sent(state, "CA-fwd", at=fwd_at)
    with state.store.transaction():
        state.store.conn.execute("INSERT INTO sms_outbox(key,phone,from_number,body,kind,completion_json,status,next_attempt_at,created_at) "
                                 "VALUES('CA-fwd:followup:1',?,?,?,'followup','{}','sent',?,?)",
                                 (CALLER, TEXTING, "again", NOW.isoformat(), (fwd_at + timedelta(minutes=3)).isoformat()))
    _call(state, "CA-later", at=fwd_at + timedelta(minutes=11)); _mark_sent(state, "CA-later", at=fwd_at + timedelta(minutes=11))
    _call(state, "CA-other", caller="+19805550142", at=fwd_at + timedelta(minutes=1))
    _mark_sent(state, "CA-other", at=fwd_at + timedelta(minutes=1))
    assert _words(checklist(state, NOW))[1] == (2, "Done")


def test_an_unsent_first_text_is_not_yet(tmp_path):
    state = _state(tmp_path)
    _call(state, "CA-fwd", forwarded_from=BUSINESS)
    with state.store.transaction():
        state.store.conn.execute("UPDATE sms_outbox SET status='dead_letter' WHERE key='CA-fwd:intro'")
    step = checklist(state, NOW)["steps"][1]
    assert step["state_word"] == "Not yet" and step["evidence"] == "No text went out for that call yet."


def test_caller_id_check_fails_when_the_call_arrives_as_the_business_number(tmp_path):
    state = _state(tmp_path)
    _call(state, "CA-fwd", caller=BUSINESS, forwarded_from=BUSINESS); _mark_sent(state, "CA-fwd")
    result = checklist(state, NOW)
    assert _words(result)[3] == (4, "Not yet") and "caller ID" in result["steps"][3]["evidence"]


def test_manual_steps_say_you_checked_this_and_persist(tmp_path):
    state = _state(tmp_path)
    save_manual_ticks(state.store, {"answered_no_text": True, "deactivation_saved": False}, NOW)
    result = checklist(state, NOW)
    assert _words(result)[2] == (3, "You checked this") and _words(result)[4] == (5, "Not yet")
    assert result["steps"][2]["evidence"].startswith("Answer a call to your business number")  # the deck's hint; the pill says it is ticked
    save_manual_ticks(state.store, {"answered_no_text": False}, NOW)
    assert _words(checklist(state, NOW))[2] == (3, "Not yet")


def test_no_business_number_says_so_on_checks_1_and_4(tmp_path):
    state = _state(tmp_path, business_line="")
    result = checklist(state, NOW)
    assert result["steps"][0]["evidence"] == "Enter your business number first."
    assert result["steps"][3]["evidence"] == "Enter your business number first."


def test_all_done_reads_done(tmp_path):
    state = _state(tmp_path)
    _call(state, "CA-fwd", forwarded_from=BUSINESS); _mark_sent(state, "CA-fwd")
    save_manual_ticks(state.store, {"answered_no_text": True, "deactivation_saved": True}, NOW)
    result = checklist(state, NOW)
    assert result["all_done"] and result["state_word"] == "Done" and result["done_count"] == 5
