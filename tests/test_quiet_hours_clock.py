"""Clock-driven quiet-hours tests.

Deterministic: every test passes an explicit UTC ``now`` through the injected
clock seams (``next_allowed_send_time`` and ``run_due_followups``); no frozen
wall clock, no sleeps. Complements tests/test_followup.py, which covers the
basic UTC defer-then-send path — here we pin the exact window boundaries in
the business timezone, a non-overnight window, DST transition days in
America/New_York, and how quiet hours interact with expiry.
"""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from text_back.followup import (
    FollowupPolicy,
    next_allowed_send_time,
    run_due_followups,
    schedule_followup_sequence,
)
from text_back.store import Store
from text_back.telecom import FakeTelecom


CALLER = "+15551112222"
BUSINESS_NUMBER = "+15553334444"
BUSINESS_NAME = "Oak & Pine Tree Care"
EASTERN = ZoneInfo("America/New_York")

# Overnight quiet window 21:00 -> 08:00 in the business timezone.
ET_POLICY = FollowupPolicy(
    delays_minutes=(180,),
    expiry_minutes=2880,
    quiet_start=time(21, 0),
    quiet_end=time(8, 0),
    timezone_name="America/New_York",
)


def _utc(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _schedule(store, *, now, call_sid="CA-qh-1", policy=ET_POLICY):
    schedule_followup_sequence(
        store=store,
        policy=policy,
        phone=CALLER,
        call_sid=call_sid,
        now=now,
    )


def _run(store, telecom, *, now, policy=ET_POLICY):
    return run_due_followups(
        store=store,
        telecom=telecom,
        policy=policy,
        business_name=BUSINESS_NAME,
        business_number=BUSINESS_NUMBER,
        now=now,
    )


def _followup_sends(telecom):
    return [m for m in telecom.outbound if m.kind == "followup"]


# --- overnight window boundaries, exact minutes in business tz ---
# August 2026: America/New_York is EDT (UTC-4).


def test_exactly_2100_local_is_quiet():
    # 21:00 EDT Aug 25 == 01:00 UTC Aug 26 -> next 08:00 EDT == 12:00 UTC Aug 26.
    at = _utc(2026, 8, 26, 1, 0)
    assert next_allowed_send_time(at, ET_POLICY) == _utc(2026, 8, 26, 12, 0)


def test_2059_local_is_allowed():
    # 20:59 EDT Aug 25 == 00:59 UTC Aug 26 -> unchanged.
    at = _utc(2026, 8, 26, 0, 59)
    assert next_allowed_send_time(at, ET_POLICY) == at


def test_exactly_0800_local_is_allowed():
    # 08:00 EDT == 12:00 UTC -> quiet end is exclusive of the window.
    at = _utc(2026, 8, 25, 12, 0)
    assert next_allowed_send_time(at, ET_POLICY) == at


def test_0759_local_defers_exactly_one_minute_to_quiet_end():
    # 07:59 EDT == 11:59 UTC -> 08:00 EDT same day == 12:00 UTC.
    at = _utc(2026, 8, 25, 11, 59)
    assert next_allowed_send_time(at, ET_POLICY) == _utc(2026, 8, 25, 12, 0)


def test_run_due_at_quiet_start_defers_but_one_minute_earlier_sends():
    # Same boundary exercised through the full run_due_followups path.
    schedule_time = _utc(2026, 8, 25, 22, 0)  # 18:00 EDT
    due = schedule_time + timedelta(minutes=180)  # 21:00 EDT == 01:00 UTC Aug 26

    quiet_store, quiet_telecom = Store(), FakeTelecom()
    _schedule(quiet_store, now=schedule_time)
    actions = _run(quiet_store, quiet_telecom, now=due)
    assert [a["action"] for a in actions] == ["followup_deferred"]
    assert _followup_sends(quiet_telecom) == []

    open_store, open_telecom = Store(), FakeTelecom()
    _schedule(open_store, now=schedule_time - timedelta(minutes=1))
    actions = _run(open_store, open_telecom, now=due - timedelta(minutes=1))
    assert [a["action"] for a in actions] == ["followup_sent"]
    assert len(_followup_sends(open_telecom)) == 1


# --- non-overnight window (start < end on the same day) ---


DAYTIME_POLICY = FollowupPolicy(
    delays_minutes=(60,),
    expiry_minutes=1440,
    quiet_start=time(12, 0),
    quiet_end=time(13, 0),
    timezone_name="America/New_York",
)


def test_non_overnight_window_boundaries():
    # 11:59 EDT == 15:59 UTC -> allowed (before window).
    before = _utc(2026, 8, 25, 15, 59)
    assert next_allowed_send_time(before, DAYTIME_POLICY) == before

    # 12:00 EDT == 16:00 UTC -> quiet, defer to 13:00 EDT == 17:00 UTC.
    at_start = _utc(2026, 8, 25, 16, 0)
    assert next_allowed_send_time(at_start, DAYTIME_POLICY) == _utc(2026, 8, 25, 17, 0)

    # 12:59 EDT -> still quiet, same quiet end.
    last_minute = _utc(2026, 8, 25, 16, 59)
    assert next_allowed_send_time(last_minute, DAYTIME_POLICY) == _utc(2026, 8, 25, 17, 0)

    # 13:00 EDT == 17:00 UTC -> allowed (window end exclusive).
    at_end = _utc(2026, 8, 25, 17, 0)
    assert next_allowed_send_time(at_end, DAYTIME_POLICY) == at_end


def test_zero_length_window_never_quiet():
    policy = FollowupPolicy(
        delays_minutes=(60,),
        expiry_minutes=1440,
        quiet_start=time(9, 0),
        quiet_end=time(9, 0),
        timezone_name="America/New_York",
    )
    at = _utc(2026, 8, 25, 13, 0)  # 09:00 EDT, exactly the degenerate boundary
    assert next_allowed_send_time(at, policy) == at


# --- deferral lands exactly at quiet-end (business tz, full run path) ---


def test_deferral_lands_exactly_at_quiet_end_in_business_tz():
    store, telecom = Store(), FakeTelecom()
    schedule_time = _utc(2026, 8, 25, 23, 0)  # 19:00 EDT
    _schedule(store, now=schedule_time)

    due = schedule_time + timedelta(minutes=180)  # 22:00 EDT == 02:00 UTC Aug 26
    actions = _run(store, telecom, now=due)

    assert [a["action"] for a in actions] == ["followup_deferred"]
    quiet_end_utc = _utc(2026, 8, 26, 12, 0)  # 08:00 EDT
    assert actions[0]["deferred_to"] == quiet_end_utc.isoformat()
    sequence = store.get_followup(CALLER)
    assert datetime.fromisoformat(sequence["next_action_at"]) == quiet_end_utc

    # One minute before quiet end: still nothing due... it was deferred to 12:00.
    assert _run(store, telecom, now=quiet_end_utc - timedelta(minutes=1)) == []
    assert _followup_sends(telecom) == []

    # Exactly at quiet end: the send happens.
    actions = _run(store, telecom, now=quiet_end_utc)
    assert [a["action"] for a in actions] == ["followup_sent"]
    assert len(_followup_sends(telecom)) == 1


# --- DST transition days in America/New_York ---


def test_spring_forward_day_defers_across_skipped_hour():
    # 2026-03-08: clocks jump 02:00 EST -> 03:00 EDT.
    # 01:30 EST == 06:30 UTC, inside quiet hours.
    at = _utc(2026, 3, 8, 6, 30)
    assert at.astimezone(EASTERN).utcoffset() == timedelta(hours=-5)

    allowed = next_allowed_send_time(at, ET_POLICY)

    # Quiet end 08:00 is EDT after the jump: 08:00 EDT == 12:00 UTC.
    assert allowed == _utc(2026, 3, 8, 12, 0)
    allowed_local = allowed.astimezone(EASTERN)
    assert allowed_local.time() == time(8, 0)
    assert allowed_local.utcoffset() == timedelta(hours=-4)
    # Only 5.5 real hours elapse for a 6.5-hour wall-clock gap: one hour skipped.
    assert allowed - at == timedelta(hours=5, minutes=30)


def test_spring_forward_evening_quiet_start_shifts_in_utc():
    # Before the jump (Mar 7) 21:00 EST == 02:00 UTC; after (Mar 8) 21:00 EDT == 01:00 UTC.
    before_jump = _utc(2026, 3, 8, 1, 30)  # 20:30 EST Mar 7 -> allowed
    assert next_allowed_send_time(before_jump, ET_POLICY) == before_jump
    after_jump = _utc(2026, 3, 9, 1, 30)  # 21:30 EDT Mar 8 -> quiet
    assert next_allowed_send_time(after_jump, ET_POLICY) == _utc(2026, 3, 9, 12, 0)


def test_fall_back_day_both_0130_local_times_defer_to_same_quiet_end():
    # 2026-11-01: clocks fall back 02:00 EDT -> 01:00 EST; 01:30 happens twice.
    first_0130 = _utc(2026, 11, 1, 5, 30)  # 01:30 EDT (first occurrence)
    second_0130 = _utc(2026, 11, 1, 6, 30)  # 01:30 EST (second occurrence)
    assert first_0130.astimezone(EASTERN).time() == time(1, 30)
    assert second_0130.astimezone(EASTERN).time() == time(1, 30)

    quiet_end_utc = _utc(2026, 11, 1, 13, 0)  # 08:00 EST after the fall-back
    assert next_allowed_send_time(first_0130, ET_POLICY) == quiet_end_utc
    assert next_allowed_send_time(second_0130, ET_POLICY) == quiet_end_utc


def test_fall_back_evening_quiet_start_shifts_in_utc():
    # After the fall-back, 21:00 EST == 02:00 UTC next day.
    allowed_evening = _utc(2026, 11, 2, 1, 59)  # 20:59 EST Nov 1 -> allowed
    assert next_allowed_send_time(allowed_evening, ET_POLICY) == allowed_evening
    quiet_evening = _utc(2026, 11, 2, 2, 0)  # 21:00 EST Nov 1 -> quiet
    assert next_allowed_send_time(quiet_evening, ET_POLICY) == _utc(2026, 11, 2, 13, 0)


# --- quiet hours vs. expiry ---


def test_expiry_during_quiet_hours_is_not_deferred():
    # Expiry is bookkeeping, not a customer-facing send: it processes even
    # inside the quiet window and sends no SMS.
    policy = FollowupPolicy(
        delays_minutes=(60,),
        expiry_minutes=600,
        quiet_start=time(21, 0),
        quiet_end=time(8, 0),
        timezone_name="America/New_York",
    )
    store, telecom = Store(), FakeTelecom()
    schedule_time = _utc(2026, 8, 25, 16, 0)  # 12:00 EDT
    _schedule(store, now=schedule_time, policy=policy)

    send_time = schedule_time + timedelta(minutes=60)  # 13:00 EDT, allowed
    actions = _run(store, telecom, now=send_time, policy=policy)
    assert [a["action"] for a in actions] == ["followup_sent"]

    expiry_due = send_time + timedelta(minutes=600)  # 23:00 EDT, inside quiet
    assert expiry_due.astimezone(EASTERN).time() == time(23, 0)
    actions = _run(store, telecom, now=expiry_due, policy=policy)

    assert [a["action"] for a in actions] == ["lead_expired"]
    assert store.get_followup(CALLER)["status"] == "expired"
    assert len(_followup_sends(telecom)) == 1  # no extra send during quiet hours

    expired = [
        e
        for e in store.list_outcome_events(CALLER)
        if e["event_type"] == "lead.expired"
    ]
    assert len(expired) == 1
    assert expired[0]["metadata"] == {"attempts_sent": 1}


def test_quiet_deferral_of_final_attempt_pushes_expiry_from_actual_send():
    # The expiry clock starts at the moment the deferred final attempt actually
    # sends (quiet end), not at the originally scheduled due time.
    store, telecom = Store(), FakeTelecom()
    schedule_time = _utc(2026, 8, 25, 23, 0)  # 19:00 EDT
    _schedule(store, now=schedule_time)

    original_due = schedule_time + timedelta(minutes=180)  # 22:00 EDT, quiet
    actions = _run(store, telecom, now=original_due)
    assert [a["action"] for a in actions] == ["followup_deferred"]

    quiet_end_utc = _utc(2026, 8, 26, 12, 0)  # 08:00 EDT
    actions = _run(store, telecom, now=quiet_end_utc)
    assert [a["action"] for a in actions] == ["followup_sent"]

    sequence = store.get_followup(CALLER)
    assert sequence["next_action"] == "expire"
    expected_expiry = quiet_end_utc + timedelta(minutes=ET_POLICY.expiry_minutes)
    assert datetime.fromisoformat(sequence["next_action_at"]) == expected_expiry

    actions = _run(store, telecom, now=expected_expiry)
    assert [a["action"] for a in actions] == ["lead_expired"]
    assert len(_followup_sends(telecom)) == 1
