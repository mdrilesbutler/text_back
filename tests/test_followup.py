from datetime import datetime, time, timedelta, timezone

import pytest

from text_back.calendar_stub import CalendarStub
from text_back.followup import FollowupPolicy, next_allowed_send_time, run_due_followups
from text_back.handoff import FakeHandoffNotifier
from text_back.handlers import handle_sms_event, handle_voice_event
from text_back.store import Store
from text_back.telecom import FakeTelecom


CALLER = "+15551112222"
BUSINESS_NUMBER = "+15553334444"
BUSINESS_NAME = "Oak & Pine Tree Care"
NOW = datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc)

POLICY = FollowupPolicy(
    delays_minutes=(120, 1440),
    expiry_minutes=2880,
    quiet_start=time(21, 0),
    quiet_end=time(8, 0),
    timezone_name="UTC",
)


def _missed_call(store, telecom, *, call_sid="CA-fu-1", now=NOW, policy=POLICY):
    return handle_voice_event(
        store=store,
        telecom=telecom,
        call_sid=call_sid,
        call_status="ringing",
        from_number=CALLER,
        to_number=BUSINESS_NUMBER,
        wiring_mode="forwarded",
        business_name=BUSINESS_NAME,
        followup_policy=policy,
        now=now,
    )


def _inbound_sms(store, telecom, *, body, message_sid="MSG-fu-1", now=NOW):
    return handle_sms_event(
        store=store,
        calendar=CalendarStub(timezone_name="UTC"),
        telecom=telecom,
        handoff_notifier=FakeHandoffNotifier(),
        handoff_destination="operator-queue",
        message_sid=message_sid,
        from_number=CALLER,
        to_number=BUSINESS_NUMBER,
        body=body,
        business_name=BUSINESS_NAME,
        timezone_name="UTC",
        appointment_duration_minutes=60,
        now=now,
    )


def _run(store, telecom, *, now, policy=POLICY):
    return run_due_followups(
        store=store,
        telecom=telecom,
        policy=policy,
        business_name=BUSINESS_NAME,
        business_number=BUSINESS_NUMBER,
        now=now,
    )


def _outcomes(store, event_type):
    return [
        event
        for event in store.list_outcome_events(CALLER)
        if event["event_type"] == event_type
    ]


# --- scheduling ---


def test_missed_call_with_accepted_intro_schedules_sequence():
    store, telecom = Store(), FakeTelecom()
    result = _missed_call(store, telecom)

    assert result["action"] == "sent_intro"
    sequence = store.get_followup(CALLER)
    assert sequence is not None
    assert sequence["status"] == "active"
    assert sequence["call_sid"] == "CA-fu-1"
    assert sequence["attempts_sent"] == 0
    assert sequence["next_action"] == "followup"
    expected_due = NOW + timedelta(minutes=120)
    assert datetime.fromisoformat(sequence["next_action_at"]) == expected_due


def test_no_sequence_when_intro_suppressed_for_opt_out():
    store, telecom = Store(), FakeTelecom()
    store.set_opted_out(CALLER, True)

    result = _missed_call(store, telecom)

    assert result["action"] == "suppressed"
    assert store.get_followup(CALLER) is None


def test_duplicate_voice_webhook_does_not_reset_sequence():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)
    first = store.get_followup(CALLER)

    later = NOW + timedelta(minutes=30)
    result = _missed_call(store, telecom, now=later)

    assert result["duplicate"] is True
    second = store.get_followup(CALLER)
    assert second["next_action_at"] == first["next_action_at"]
    assert second["attempts_sent"] == 0


def test_no_scheduling_without_policy():
    store, telecom = Store(), FakeTelecom()
    handle_voice_event(
        store=store,
        telecom=telecom,
        call_sid="CA-nopolicy",
        call_status="ringing",
        from_number=CALLER,
        to_number=BUSINESS_NUMBER,
        wiring_mode="forwarded",
        business_name=BUSINESS_NAME,
    )
    assert store.get_followup(CALLER) is None


# --- sending ---


def test_not_due_sends_nothing():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)
    intro_count = len(telecom.outbound)

    actions = _run(store, telecom, now=NOW + timedelta(minutes=119))

    assert actions == []
    assert len(telecom.outbound) == intro_count


def test_due_followup_sends_records_and_schedules_next():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)

    send_time = NOW + timedelta(minutes=120)
    actions = _run(store, telecom, now=send_time)

    assert [a["action"] for a in actions] == ["followup_sent"]
    followups = [m for m in telecom.outbound if m.kind == "followup"]
    assert len(followups) == 1
    assert followups[0].to == CALLER
    assert followups[0].from_number == BUSINESS_NUMBER

    sent = _outcomes(store, "followup.sent")
    assert len(sent) == 1
    assert sent[0]["evidence_id"].startswith("SM-")
    assert sent[0]["metadata"] == {"attempt": 1}

    sequence = store.get_followup(CALLER)
    assert sequence["attempts_sent"] == 1
    assert sequence["next_action"] == "followup"
    assert datetime.fromisoformat(sequence["next_action_at"]) == send_time + timedelta(
        minutes=1440
    )


def test_followup_body_has_no_customer_content_and_supports_stop():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)
    _run(store, telecom, now=NOW + timedelta(minutes=120))

    body = [m for m in telecom.outbound if m.kind == "followup"][0].body
    assert BUSINESS_NAME in body
    assert "STOP" in body


def test_run_due_twice_at_same_instant_sends_once():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)

    send_time = NOW + timedelta(minutes=120)
    _run(store, telecom, now=send_time)
    actions = _run(store, telecom, now=send_time)

    assert actions == []
    assert len([m for m in telecom.outbound if m.kind == "followup"]) == 1
    assert len(_outcomes(store, "followup.sent")) == 1


# --- quiet hours ---


def test_due_inside_quiet_hours_defers_without_sending():
    store, telecom = Store(), FakeTelecom()
    evening = datetime(2026, 8, 25, 20, 0, tzinfo=timezone.utc)
    _missed_call(store, telecom, now=evening)

    due = evening + timedelta(minutes=120)  # 22:00, inside 21:00-08:00 quiet
    actions = _run(store, telecom, now=due)

    assert [a["action"] for a in actions] == ["followup_deferred"]
    assert [m for m in telecom.outbound if m.kind == "followup"] == []
    sequence = store.get_followup(CALLER)
    deferred_to = datetime.fromisoformat(sequence["next_action_at"])
    assert deferred_to == datetime(2026, 8, 26, 8, 0, tzinfo=timezone.utc)


def test_deferred_followup_sends_after_quiet_hours_end():
    store, telecom = Store(), FakeTelecom()
    evening = datetime(2026, 8, 25, 20, 0, tzinfo=timezone.utc)
    _missed_call(store, telecom, now=evening)
    _run(store, telecom, now=evening + timedelta(minutes=120))

    morning = datetime(2026, 8, 26, 8, 0, tzinfo=timezone.utc)
    actions = _run(store, telecom, now=morning)

    assert [a["action"] for a in actions] == ["followup_sent"]


def test_next_allowed_send_time_early_morning_moves_to_quiet_end_same_day():
    early = datetime(2026, 8, 25, 6, 30, tzinfo=timezone.utc)
    allowed = next_allowed_send_time(early, POLICY)
    assert allowed == datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc)


def test_quiet_hours_respect_business_timezone():
    policy = FollowupPolicy(
        delays_minutes=(120,),
        expiry_minutes=1440,
        quiet_start=time(21, 0),
        quiet_end=time(8, 0),
        timezone_name="America/New_York",
    )
    # 01:00 UTC == 21:00 EDT (quiet); allowed at 08:00 EDT == 12:00 UTC.
    at = datetime(2026, 8, 26, 1, 0, tzinfo=timezone.utc)
    allowed = next_allowed_send_time(at, policy)
    assert allowed == datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


# --- cancellation ---


def test_customer_reply_cancels_sequence():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)

    _inbound_sms(store, telecom, body="tree removal")

    sequence = store.get_followup(CALLER)
    assert sequence["status"] == "cancelled"
    assert sequence["cancel_reason"] == "customer_replied"
    assert _run(store, telecom, now=NOW + timedelta(days=7)) == []


def test_stop_cancels_sequence():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)

    _inbound_sms(store, telecom, body="STOP")

    assert store.get_followup(CALLER)["status"] == "cancelled"
    assert _run(store, telecom, now=NOW + timedelta(days=7)) == []


def test_opt_out_after_scheduling_cancels_at_send_time():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)
    store.set_opted_out(CALLER, True)

    actions = _run(store, telecom, now=NOW + timedelta(minutes=120))

    assert [a["action"] for a in actions] == ["followup_cancelled"]
    assert [m for m in telecom.outbound if m.kind == "followup"] == []
    assert store.get_followup(CALLER)["cancel_reason"] == "opted_out"


def test_active_handoff_cancels_at_send_time():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)
    store.request_handoff(CALLER, "customer_requested")

    actions = _run(store, telecom, now=NOW + timedelta(minutes=120))

    assert [a["action"] for a in actions] == ["followup_cancelled"]
    assert store.get_followup(CALLER)["cancel_reason"] == "handoff_active"
    assert [m for m in telecom.outbound if m.kind == "followup"] == []


def test_booked_appointment_cancels_at_send_time():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)
    store.save_appointment(
        conversation_id=CALLER,
        event_id="EV-1",
        caller=CALLER,
        start="2026-08-27T10:00:00+00:00",
        location="12 Elm St",
        service="tree removal",
    )

    actions = _run(store, telecom, now=NOW + timedelta(minutes=120))

    assert [a["action"] for a in actions] == ["followup_cancelled"]
    assert store.get_followup(CALLER)["cancel_reason"] == "booked"
    assert [m for m in telecom.outbound if m.kind == "followup"] == []


# --- ceiling and expiry ---


def test_ceiling_reached_then_lead_expires_with_evidence():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)

    first_send = NOW + timedelta(minutes=120)
    _run(store, telecom, now=first_send)
    second_send = first_send + timedelta(minutes=1440)
    actions = _run(store, telecom, now=second_send)

    assert [a["action"] for a in actions] == ["followup_sent"]
    sequence = store.get_followup(CALLER)
    assert sequence["attempts_sent"] == 2
    assert sequence["next_action"] == "expire"
    expiry_due = second_send + timedelta(minutes=2880)
    assert datetime.fromisoformat(sequence["next_action_at"]) == expiry_due

    actions = _run(store, telecom, now=expiry_due)
    assert [a["action"] for a in actions] == ["lead_expired"]
    sequence = store.get_followup(CALLER)
    assert sequence["status"] == "expired"

    expired = _outcomes(store, "lead.expired")
    assert len(expired) == 1
    assert expired[0]["evidence_id"] == "CA-fu-1"
    assert expired[0]["metadata"] == {"attempts_sent": 2}

    assert len([m for m in telecom.outbound if m.kind == "followup"]) == 2
    assert _run(store, telecom, now=expiry_due + timedelta(days=30)) == []


def test_reply_after_final_attempt_cancels_before_expiry():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)
    first_send = NOW + timedelta(minutes=120)
    _run(store, telecom, now=first_send)
    second_send = first_send + timedelta(minutes=1440)
    _run(store, telecom, now=second_send)

    _inbound_sms(store, telecom, body="sorry, still interested", now=second_send + timedelta(hours=1))

    assert store.get_followup(CALLER)["status"] == "cancelled"
    actions = _run(store, telecom, now=second_send + timedelta(minutes=2880))
    assert actions == []
    assert _outcomes(store, "lead.expired") == []


def test_new_missed_call_after_expiry_starts_fresh_sequence():
    store, telecom = Store(), FakeTelecom()
    _missed_call(store, telecom)
    first_send = NOW + timedelta(minutes=120)
    _run(store, telecom, now=first_send)
    second_send = first_send + timedelta(minutes=1440)
    _run(store, telecom, now=second_send)
    expiry_due = second_send + timedelta(minutes=2880)
    _run(store, telecom, now=expiry_due)

    later = expiry_due + timedelta(days=1)
    result = _missed_call(store, telecom, call_sid="CA-fu-2", now=later)

    assert result["action"] == "sent_intro"
    sequence = store.get_followup(CALLER)
    assert sequence["status"] == "active"
    assert sequence["call_sid"] == "CA-fu-2"
    assert sequence["attempts_sent"] == 0


# --- config ---


def test_followup_policy_from_environment(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_FOLLOWUP_DELAYS_MINUTES", "60,240,1440")
    monkeypatch.setenv("TEXT_BACK_FOLLOWUP_EXPIRY_MINUTES", "4320")
    monkeypatch.setenv("TEXT_BACK_QUIET_HOURS_START", "20:30")
    monkeypatch.setenv("TEXT_BACK_QUIET_HOURS_END", "07:00")
    monkeypatch.setenv("TEXT_BACK_TIMEZONE", "America/New_York")

    from text_back.config import load_config

    config = load_config()
    policy = FollowupPolicy.from_config(config)
    assert policy.delays_minutes == (60, 240, 1440)
    assert policy.expiry_minutes == 4320
    assert policy.quiet_start == time(20, 30)
    assert policy.quiet_end == time(7, 0)
    assert policy.timezone_name == "America/New_York"


def test_invalid_followup_config_rejected(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_FOLLOWUP_DELAYS_MINUTES", "60,-5")
    from text_back.config import load_config

    config = load_config()
    with pytest.raises(ValueError):
        FollowupPolicy.from_config(config)
