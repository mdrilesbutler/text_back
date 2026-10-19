"""Provider rejection must not consume a durable customer-message intent."""

from contextlib import suppress
from datetime import datetime, time, timedelta, timezone

from text_back.booking import book_appointment
from text_back.calendar_stub import CalendarStub
from text_back.followup import (
    FollowupPolicy,
    run_due_followups,
    schedule_followup_sequence,
)
from text_back.handlers import handle_voice_event
from text_back.store import Store
from text_back.telecom import FakeTelecom, RetryableSmsError


NOW = datetime(2026, 9, 17, 14, tzinfo=timezone.utc)
CALLER = "+15551112222"
BUSINESS_NUMBER = "+15553334444"
BUSINESS_NAME = "Recovery Fixture"
POLICY = FollowupPolicy((1, 60), 120, time(21), time(8), "UTC")


class RejectFirstSms(FakeTelecom):
    """The first request is definitely rejected before provider acceptance."""

    def __init__(self):
        super().__init__()
        self.attempts = 0

    def send_sms(self, **kwargs):
        self.attempts += 1
        if self.attempts == 1:
            raise RetryableSmsError("simulated transient rejection before acceptance")
        return super().send_sms(**kwargs)


def _outcomes(store, event_type):
    return [
        event
        for event in store.list_outcome_events(CALLER)
        if event["event_type"] == event_type
    ]


def test_initial_sms_recovers_after_provider_rejection_and_store_restart(tmp_path):
    path = str(tmp_path / "initial.db")
    store, telecom = Store(path), RejectFirstSms()
    request = dict(
        telecom=telecom,
        call_sid="CA-recover-intro",
        call_status="ringing",
        from_number=CALLER,
        to_number=BUSINESS_NUMBER,
        wiring_mode="forwarded",
        business_name=BUSINESS_NAME,
        followup_policy=POLICY,
    )

    # The first failure may propagate or be parked for retry; neither may
    # permanently consume the introduction or claim it was accepted.
    with suppress(RetryableSmsError):
        handle_voice_event(store=store, now=NOW, **request)
    assert telecom.outbound == []
    assert _outcomes(store, "sms.initial_sent") == []
    assert store.get_followup(CALLER) is None
    store.conn.close()

    restarted = Store(path)
    handle_voice_event(store=restarted, now=NOW + timedelta(minutes=5), **request)

    assert [sms.kind for sms in telecom.outbound] == ["missed_call_intro"]
    accepted = _outcomes(restarted, "sms.initial_sent")
    assert len(accepted) == 1
    assert accepted[0]["evidence_id"] == "SM-0001"
    assert restarted.get_followup(CALLER)["status"] == "active"
    handle_voice_event(store=restarted, now=NOW + timedelta(minutes=6), **request)
    assert len(telecom.outbound) == 1


def test_followup_recovers_after_provider_rejection_and_store_restart(tmp_path):
    path = str(tmp_path / "followup.db")
    store, telecom = Store(path), RejectFirstSms()
    schedule_followup_sequence(
        store=store,
        policy=POLICY,
        phone=CALLER,
        call_sid="CA-recover-followup",
        now=NOW,
    )
    request = dict(
        telecom=telecom,
        policy=POLICY,
        business_name=BUSINESS_NAME,
        business_number=BUSINESS_NUMBER,
    )

    with suppress(RetryableSmsError):
        run_due_followups(store=store, now=NOW + timedelta(minutes=1), **request)
    assert telecom.outbound == []
    assert _outcomes(store, "followup.sent") == []
    assert store.get_followup(CALLER)["attempts_sent"] == 0
    store.conn.close()

    restarted = Store(path)
    retry_at = NOW + timedelta(minutes=6)
    run_due_followups(store=restarted, now=retry_at, **request)

    assert [sms.kind for sms in telecom.outbound] == ["followup"]
    accepted = _outcomes(restarted, "followup.sent")
    assert len(accepted) == 1
    assert accepted[0]["evidence_id"] == "SM-0001"
    assert accepted[0]["metadata"]["attempt"] == 1
    assert restarted.get_followup(CALLER)["attempts_sent"] == 1
    run_due_followups(store=restarted, now=retry_at, **request)
    assert len(telecom.outbound) == 1


def test_booking_confirmation_recovers_without_creating_another_event(tmp_path):
    path = str(tmp_path / "booking.db")
    store, telecom, calendar = Store(path), RejectFirstSms(), CalendarStub()
    request = dict(
        telecom=telecom,
        calendar=calendar,
        caller=CALLER,
        business_number=BUSINESS_NUMBER,
        service="tree trimming",
        location="12 Oak St",
        customer_name="Test Customer",
        business_name=BUSINESS_NAME,
        timezone_name="UTC",
        start=NOW + timedelta(days=1),
        duration_minutes=60,
        conversation_id="conversation-recover-booking",
    )

    with suppress(RetryableSmsError):
        book_appointment(store=store, now=NOW, **request)
    assert len(calendar.events) == 1
    assert telecom.outbound == []
    assert _outcomes(store, "appointment.confirmed") == []
    event_id = store.appointment_by_conversation(request["conversation_id"])["event_id"]
    store.conn.close()

    restarted = Store(path)
    result = book_appointment(store=restarted, now=NOW + timedelta(minutes=5), **request)

    assert [sms.kind for sms in telecom.outbound] == ["booking_confirmation"]
    assert result["booked"] is True
    assert result["event_id"] == event_id
    assert len(calendar.events) == 1
    assert store.appointment_by_event(event_id)["event_id"] == event_id  # the same event, no second one
    assert telecom.outbound[0].kind == "booking_confirmation"
    accepted = _outcomes(restarted, "appointment.confirmed")
    assert len(accepted) == 1
    assert accepted[0]["evidence_id"] == "SM-0001"
    assert accepted[0]["metadata"]["calendar_event_id"] == event_id
    book_appointment(store=restarted, now=NOW + timedelta(minutes=6), **request)
    assert len(telecom.outbound) == 1
    assert len(calendar.events) == 1


def test_calendar_event_survives_crash_before_local_appointment_commit(tmp_path, monkeypatch):
    store, telecom, calendar = Store(str(tmp_path/'calendar-crash.db')), FakeTelecom(), CalendarStub()
    request = dict(store=store, telecom=telecom, calendar=calendar, caller=CALLER,
        business_number=BUSINESS_NUMBER, service='trim', location='Oak', customer_name='Test',
        business_name=BUSINESS_NAME, timezone_name='UTC', start=NOW+timedelta(days=1),
        duration_minutes=60, conversation_id='crash-booking', now=NOW)
    save = store.save_appointment
    def fail(**kwargs):
        raise RuntimeError('interrupted after provider accepted')
    monkeypatch.setattr(store,'save_appointment',fail)
    with suppress(RuntimeError):
        book_appointment(**request)
    assert len(calendar.events)==1
    assert not store.appointment_by_conversation('crash-booking')
    monkeypatch.setattr(store,'save_appointment',save)
    result=book_appointment(**request)
    assert result['booked']
    assert len(calendar.events)==1
    assert len(telecom.outbound)==1


class ProcessInterrupted(BaseException):
    """Process loss: nothing after this point runs in the dying process."""


class InterruptedTelecom(FakeTelecom):
    def send_sms(self, **kwargs):
        raise ProcessInterrupted()


def _followup_request(telecom):
    return dict(telecom=telecom, policy=POLICY,
                business_name=BUSINESS_NAME, business_number=BUSINESS_NUMBER)


def test_followup_crash_after_intent_commit_sends_once_after_restart(tmp_path, monkeypatch):
    import text_back.followup as followup

    path = str(tmp_path / "followup-crash-before-send.db")
    store = Store(path)
    schedule_followup_sequence(store=store, policy=POLICY, phone=CALLER,
                               call_sid="CA-crash-before-send", now=NOW)

    def die(**kwargs):
        raise ProcessInterrupted()

    monkeypatch.setattr(followup, "run_due_sms", die)
    telecom = FakeTelecom()
    with suppress(ProcessInterrupted):
        run_due_followups(store=store, now=NOW + timedelta(minutes=1), **_followup_request(telecom))
    assert telecom.outbound == []
    assert store.get_followup(CALLER)["attempts_sent"] == 0
    store.conn.close()
    monkeypatch.undo()

    restarted = Store(path)
    later = NOW + timedelta(minutes=2)
    run_due_followups(store=restarted, now=later, **_followup_request(telecom))
    run_due_followups(store=restarted, now=later, **_followup_request(telecom))

    assert [sms.kind for sms in telecom.outbound] == ["followup"]
    accepted = _outcomes(restarted, "followup.sent")
    assert [event["metadata"]["attempt"] for event in accepted] == [1]
    assert restarted.get_followup(CALLER)["attempts_sent"] == 1


def test_followup_crash_mid_send_is_held_not_resent_or_advanced(tmp_path):
    path = str(tmp_path / "followup-crash-mid-send.db")
    store = Store(path)
    schedule_followup_sequence(store=store, policy=POLICY, phone=CALLER,
                               call_sid="CA-crash-mid-send", now=NOW)

    with suppress(ProcessInterrupted):
        run_due_followups(store=store, now=NOW + timedelta(minutes=1),
                          **_followup_request(InterruptedTelecom()))
    store.conn.close()

    restarted, telecom = Store(path), FakeTelecom()
    for minutes in (2, 5, 30, 90):
        run_due_followups(store=restarted, now=NOW + timedelta(minutes=minutes),
                          **_followup_request(telecom))

    # Acceptance is unknowable after a mid-send crash: hold, never double-text.
    assert telecom.outbound == []
    assert _outcomes(restarted, "followup.sent") == []
    assert restarted.get_followup(CALLER)["attempts_sent"] == 0
    rows = restarted.conn.execute("SELECT status FROM sms_outbox WHERE kind='followup'").fetchall()
    assert [row["status"] for row in rows] == ["unknown"]
