"""Durable SMS retry bounds and safety decisions at actual send time."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, time, timedelta, timezone
from threading import Event

import pytest

from text_back.followup import FollowupPolicy, schedule_followup_sequence
from text_back.sms import enqueue_sms, run_due_sms
from text_back.store import Store
from text_back.telecom import AmbiguousSmsError, FakeTelecom, RetryableSmsError


NOW = datetime(2026, 9, 17, 14, tzinfo=timezone.utc)
CALLER = "+15551112222"
BUSINESS_NUMBER = "+15553334444"
KEY = "call:CA-outbox:intro"
POLICY = FollowupPolicy((1, 60), 120, time(21), time(8), "UTC")


def _enqueue(store, *, now=NOW, key=KEY, kind="missed_call_intro", completion=None):
    return enqueue_sms(
        store=store,
        key=key,
        to=CALLER,
        from_number=BUSINESS_NUMBER,
        body="Test scheduling message. Reply STOP to opt out.",
        kind=kind,
        now=now,
        completion=completion,
    )


class RejectingTelecom(FakeTelecom):
    def __init__(self, failures):
        super().__init__()
        self.failures = failures
        self.attempts = 0

    def send_sms(self, **kwargs):
        self.attempts += 1
        if self.attempts <= self.failures:
            raise RetryableSmsError("provider rejected before accepting")
        return super().send_sms(**kwargs)


def test_definite_rejections_retry_with_backoff_and_stop_after_four_attempts():
    store, telecom = Store(), RejectingTelecom(failures=99)
    assert _enqueue(store) == KEY

    run_due_sms(store=store, telecom=telecom, now=NOW)
    assert store.get_sms(KEY)["status"] == "pending"
    assert store.get_sms(KEY)["attempts"] == 1
    run_due_sms(store=store, telecom=telecom, now=NOW + timedelta(seconds=30))
    assert telecom.attempts == 1

    for minutes, attempts in ((1, 2), (6, 3), (21, 4)):
        run_due_sms(store=store, telecom=telecom, now=NOW + timedelta(minutes=minutes))
        assert telecom.attempts == attempts

    assert store.get_sms(KEY)["status"] == "dead_letter"
    assert store.get_sms(KEY)["attempts"] == 4
    run_due_sms(store=store, telecom=telecom, now=NOW + timedelta(days=1))
    assert telecom.attempts == 4
    assert telecom.outbound == []


class ProcessInterrupted(BaseException):
    """A process loss cannot report whether the provider accepted a send."""


class InterruptedTelecom(FakeTelecom):
    def send_sms(self, **kwargs):
        raise ProcessInterrupted()


def test_restart_expires_sending_lease_to_unknown_without_resending(tmp_path):
    path = str(tmp_path / "interrupted.db")
    store = Store(path)
    _enqueue(store)

    with pytest.raises(ProcessInterrupted):
        run_due_sms(store=store, telecom=InterruptedTelecom(), now=NOW)
    assert store.get_sms(KEY)["status"] == "sending"
    assert store.get_sms(KEY)["attempts"] == 1
    store.conn.close()

    restarted, telecom = Store(path), FakeTelecom()
    run_due_sms(store=restarted, telecom=telecom, now=NOW + timedelta(seconds=119))
    assert restarted.get_sms(KEY)["status"] == "sending"
    run_due_sms(store=restarted, telecom=telecom, now=NOW + timedelta(seconds=121))
    assert restarted.get_sms(KEY)["status"] == "unknown"
    assert restarted.get_sms(KEY)["attempts"] == 1
    run_due_sms(store=restarted, telecom=telecom, now=NOW + timedelta(hours=1))
    assert telecom.outbound == []


class AcceptedButTimedOutTelecom(FakeTelecom):
    def send_sms(self, **kwargs):
        super().send_sms(**kwargs)
        raise AmbiguousSmsError("request timed out after acceptance became possible")


def test_ambiguous_timeout_is_held_unknown_and_never_blindly_retried():
    store, telecom = Store(), AcceptedButTimedOutTelecom()
    _enqueue(store)

    run_due_sms(store=store, telecom=telecom, now=NOW)

    assert store.get_sms(KEY)["status"] == "unknown"
    assert store.get_sms(KEY)["attempts"] == 1
    assert store.get_sms(KEY)["provider_id"] in (None, "")
    run_due_sms(store=store, telecom=telecom, now=NOW + timedelta(minutes=5))
    run_due_sms(store=store, telecom=telecom, now=NOW + timedelta(days=1))
    assert len(telecom.outbound) == 1
    assert store.get_sms(KEY)["attempts"] == 1


def test_concurrent_runners_send_one_provider_request(tmp_path):
    path = str(tmp_path / "concurrent.db")
    first_store, second_store = Store(path), Store(path)
    _enqueue(first_store)
    started, release = Event(), Event()

    class BlockingTelecom(FakeTelecom):
        def send_sms(self, **kwargs):
            started.set()
            assert release.wait(timeout=5), "test provider was not released"
            return super().send_sms(**kwargs)

    telecom = BlockingTelecom()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(run_due_sms, store=first_store, telecom=telecom, now=NOW)
        assert started.wait(timeout=5), "first runner never reached the provider"
        second = pool.submit(run_due_sms, store=second_store, telecom=telecom, now=NOW)
        try:
            second.result(timeout=0.1)
        except TimeoutError:
            # A serialized runner is also valid; release the first send before
            # checking both final results.
            pass
        finally:
            release.set()
        first.result(timeout=5)
        second.result(timeout=5)

    assert len(telecom.outbound) == 1
    assert first_store.get_sms(KEY)["status"] == "sent"
    assert first_store.get_sms(KEY)["attempts"] == 1
    assert first_store.get_sms(KEY)["provider_id"] == "SM-0001"


@pytest.mark.parametrize("kind", ["missed_call_intro", "opt_in_ack"])
def test_stop_received_before_retry_cancels_pending_customer_sms(kind):
    store, telecom = Store(), RejectingTelecom(failures=1)
    _enqueue(store, kind=kind)
    run_due_sms(store=store, telecom=telecom, now=NOW)
    store.set_opted_out(CALLER, True)

    run_due_sms(store=store, telecom=telecom, now=NOW + timedelta(minutes=1))

    assert store.get_sms(KEY)["status"] == "cancelled"
    assert store.get_sms(KEY)["attempts"] == 1
    assert telecom.attempts == 1
    assert telecom.outbound == []


def test_retry_entering_quiet_hours_waits_until_business_morning():
    evening = NOW.replace(hour=20, minute=59)
    morning = (NOW + timedelta(days=1)).replace(hour=8, minute=0)
    store, telecom = Store(), RejectingTelecom(failures=1)
    _enqueue(store, now=evening)
    run_due_sms(store=store, telecom=telecom, now=evening, policy=POLICY)

    run_due_sms(
        store=store, telecom=telecom, now=evening + timedelta(minutes=1), policy=POLICY
    )
    assert store.get_sms(KEY)["status"] == "pending"
    assert store.get_sms(KEY)["attempts"] == 1
    assert telecom.outbound == []
    run_due_sms(
        store=store, telecom=telecom, now=morning - timedelta(seconds=1), policy=POLICY
    )
    assert telecom.attempts == 1
    run_due_sms(store=store, telecom=telecom, now=morning, policy=POLICY)
    assert len(telecom.outbound) == 1
    assert store.get_sms(KEY)["status"] == "sent"
    assert store.get_sms(KEY)["attempts"] == 2


def test_cancelled_followup_sequence_cancels_queued_message_before_send():
    store, telecom = Store(), FakeTelecom()
    call_sid = "CA-cancel-followup"
    schedule_followup_sequence(
        store=store, policy=POLICY, phone=CALLER, call_sid=call_sid, now=NOW
    )
    key = _enqueue(
        store,
        key=f"followup:{call_sid}:1",
        kind="followup",
        now=NOW + timedelta(minutes=1),
        completion={"call_sid": call_sid},
    )
    store.cancel_followup(CALLER, "customer_replied")

    run_due_sms(store=store, telecom=telecom, now=NOW + timedelta(minutes=1))

    assert store.get_sms(key)["status"] == "cancelled"
    assert store.get_sms(key)["attempts"] == 0
    assert telecom.outbound == []


def test_signed_failed_receipt_does_not_create_confirmation_outcome():
    from text_back.sms import reconcile_sms
    store = Store()
    enqueue_sms(store=store, key='failed-confirmation', to=CALLER, from_number=BUSINESS_NUMBER,
        body='Booked event real-id', kind='booking_confirmation', now=NOW,
        completion={'event_type':'appointment.confirmed','outcome_key':'confirm:real-id'})
    class Unknown(FakeTelecom):
        def send_sms(self,**kwargs):
            raise AmbiguousSmsError('uncertain')
    run_due_sms(store=store,telecom=Unknown(),now=NOW)
    assert reconcile_sms(store=store,key='failed-confirmation',provider_id='provider-id',now=NOW,delivery_status='failed')
    assert store.get_sms('failed-confirmation')['status']=='dead_letter'
    assert not any(e['event_type']=='appointment.confirmed' for e in store.list_outcome_events())
    assert any(e['event_type']=='sms.delivery_failed' for e in store.list_outcome_events())


def test_handoff_cancels_booking_confirmation_waiting_for_retry():
    store=Store()
    enqueue_sms(store=store,key='booking-before-handoff',to=CALLER,from_number=BUSINESS_NUMBER,
        body='Booked event existing-provider-id',kind='booking_confirmation',now=NOW)
    store.request_handoff(CALLER,'customer_requested')
    telecom=FakeTelecom()
    run_due_sms(store=store,telecom=telecom,now=NOW)
    assert telecom.outbound==[]
    assert store.get_sms('booking-before-handoff')['status']=='cancelled'
