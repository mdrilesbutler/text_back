"""Home truth: headline from setup state only; counts and rows share one window; full dates."""
import json
from datetime import datetime, timedelta, timezone

from text_back.app import create_app
from text_back.handlers import handle_voice_event
from text_back.portal_forwarding import save_manual_ticks
from text_back.portal_status import headline, setup_items, this_week
from text_back.telecom import FakeTelecom

NOW = datetime(2026, 10, 26, 18, 40, tzinfo=timezone.utc)  # Mon 2:40 PM EDT
BUSINESS, TEXTING = "+17045550123", "+17045550100"


def _app(tmp_path):
    app = create_app(db_path=str(tmp_path / "t.db"), telecom=FakeTelecom(), business_name="Oak", timezone_name="America/New_York")
    app.state.business_number = TEXTING
    app.state.store.set_setting("business_line", BUSINESS)
    return app


def _missed(state, sid, caller, at, forwarded_from="", mark_sent=True):
    handle_voice_event(store=state.store, telecom=FakeTelecom(), call_sid=sid, call_status="ringing", from_number=caller,
                       to_number=TEXTING, wiring_mode="forwarded", business_name="Oak", now=at, forwarded_from=forwarded_from)
    if mark_sent:
        with state.store.transaction():
            state.store.conn.execute("UPDATE sms_outbox SET status='sent', created_at=? WHERE key=?", (at.isoformat(), f"{sid}:intro"))
            state.store.record_outcome(lead_id=caller, event_type="sms.initial_sent", idempotency_key=f"call:{sid}:initial_sms",
                                       evidence_id=sid, occurred_at=at.isoformat())


def test_headline_says_working_only_when_nothing_needs_the_owner(tmp_path):
    state = _app(tmp_path).state
    state.store.set_setting("texting_approval_state", "waiting")
    items = setup_items(state, NOW)
    assert [i["state_word"] for i in items] == ["Needs you", "Needs you", "Waiting on phone companies"]
    assert headline(items) == "Not working yet: 2 steps left."
    assert items[0]["action_href"] == "/client/calendar" and items[1]["action_label"] == "Finish forwarding"
    assert items[1]["detail"] == "0 of 5 checks done."
    assert items[2]["action_label"] is None


def test_headline_waits_on_phone_companies_when_only_approval_is_pending(tmp_path):
    forwarding_done = [dict(key="calendar", state_word="Done"), dict(key="forwarding", state_word="Done"),
                       dict(key="approval", state_word="Waiting on phone companies")]
    assert headline(forwarding_done) == "Set up on your side. Waiting on the phone companies to approve texting."
    assert headline([dict(state_word="Done")] * 3) == "Working: missed calls get a text within a minute."
    assert headline([dict(state_word="Needs you"), dict(state_word="Done"), dict(state_word="Done")]) == "Not working yet: 1 step left."


def test_forwarding_card_is_done_only_from_forwarded_evidence(tmp_path):
    state = _app(tmp_path).state
    _missed(state, "CA1", "+19805550141", NOW - timedelta(hours=5), forwarded_from=BUSINESS)
    save_manual_ticks(state.store, {"answered_no_text": True, "deactivation_saved": True}, NOW)
    card = next(i for i in setup_items(state, NOW) if i["key"] == "forwarding")
    assert card["state_word"] == "Done" and "Today, 9:40 AM" in card["detail"]


def test_week_counts_and_rows_share_one_window(tmp_path):
    state = _app(tmp_path).state
    _missed(state, "CA-old", "+19805550199", NOW - timedelta(days=3))            # last Friday: outside the window
    _missed(state, "CA-1", "+19805550141", NOW - timedelta(hours=5), forwarded_from=BUSINESS)
    _missed(state, "CA-2", "+19805550177", NOW - timedelta(minutes=70), mark_sent=False)
    week = this_week(state, NOW)
    assert week["since_label"] == "Mon, Oct 26"
    assert week["counts"] == {"missed_calls": 2, "customers_texted": 2, "booked": 0, "stepped_back": 0}
    assert [r["phone"] for r in week["rows"]] == ["+19805550177", "+19805550141"]
    assert week["rows"][1]["last_label"] == "Today, 9:40 AM"
    assert week["rows"][0]["status"] == "Waiting for a reply" and week["rows"][1]["status"] == "Waiting for a reply"
    assert all(r["phone"] != "+19805550199" for r in week["rows"])


def test_empty_week_has_zero_counts_and_no_rows(tmp_path):
    week = this_week(_app(tmp_path).state, NOW)
    assert set(week["counts"].values()) == {0} and week["rows"] == []
