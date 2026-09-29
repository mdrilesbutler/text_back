"""Inbound state and operator alerts survive interruptions without lost work."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timedelta, timezone
from threading import Event

import pytest

from text_back.calendar_stub import CalendarStub
from text_back.delivery import (
    DeliveryPolicy,
    InMemoryDeliveryTransport,
    alert_from_payload_json,
    alert_payload_json,
    run_due_deliveries,
)
from text_back.handoff import FakeHandoffNotifier, HandoffAlert
from text_back.handlers import handle_sms_event
from text_back.store import Store
from text_back.telecom import FakeTelecom, RetryableSmsError


NOW = datetime(2026, 9, 17, 14, tzinfo=timezone.utc)
CALLER = "+15551112222"
BUSINESS_NUMBER = "+15553334444"


def _inbound(store, telecom, *, message_sid, body, now=NOW):
    return handle_sms_event(
        store=store,
        telecom=telecom,
        calendar=CalendarStub(),
        handoff_notifier=FakeHandoffNotifier(),
        handoff_destination="operator-queue",
        message_sid=message_sid,
        from_number=CALLER,
        to_number=BUSINESS_NUMBER,
        body=body,
        business_name="Recovery Fixture",
        timezone_name="UTC",
        appointment_duration_minutes=60,
        now=now,
    )


def _alert():
    return HandoffAlert(
        destination="operator-queue",
        caller=CALLER,
        business_number=BUSINESS_NUMBER,
        reason="customer_requested",
        latest_message="human please",
        collected_fields={"service": "tree trimming"},
        summary="Customer requested an operator follow-up.",
    )


class RejectFirstReply(FakeTelecom):
    def __init__(self):
        super().__init__()
        self.attempts = 0

    def send_sms(self, **kwargs):
        self.attempts += 1
        if self.attempts == 1:
            raise RetryableSmsError("provider rejected the first reply")
        return super().send_sms(**kwargs)


def test_inbound_retry_after_restart_sends_reply_without_capturing_next_field(tmp_path):
    path = str(tmp_path / "inbound.db")
    store, telecom = Store(path), RejectFirstReply()
    request = dict(message_sid="SM-recover-service", body="tree trimming")

    _inbound(store, telecom, **request)
    assert store.get_conversation_fields(CALLER) == {"service": "tree trimming"}
    assert telecom.outbound == []
    store.conn.close()

    restarted = Store(path)
    _inbound(restarted, telecom, now=NOW + timedelta(minutes=5), **request)

    assert restarted.get_conversation_fields(CALLER) == {"service": "tree trimming"}
    assert [sms.kind for sms in telecom.outbound] == ["field_prompt"]
    captured = [
        event
        for event in restarted.list_outcome_events(CALLER)
        if event["event_type"] == "lead.field_captured"
    ]
    assert len(captured) == 1
    assert captured[0]["metadata"] == {"field": "service"}
    _inbound(restarted, telecom, now=NOW + timedelta(minutes=6), **request)
    assert len(telecom.outbound) == 1


def test_handoff_enqueue_failure_rolls_back_claim_and_handoff_then_retry_recovers(
    tmp_path, monkeypatch
):
    path = str(tmp_path / "handoff.db")
    store, telecom = Store(path), FakeTelecom()
    request = dict(message_sid="SM-recover-handoff", body="human please")

    def interrupted_enqueue(**kwargs):
        raise RuntimeError("simulated interruption before durable operator enqueue")

    monkeypatch.setattr(store, "enqueue_handoff_delivery", interrupted_enqueue)
    with pytest.raises(RuntimeError, match="simulated interruption"):
        _inbound(store, telecom, **request)

    assert store.active_handoff(CALLER) is None
    assert store.list_outcome_events(CALLER) == []
    assert telecom.outbound == []
    store.conn.close()

    restarted = Store(path)
    result = _inbound(restarted, telecom, now=NOW + timedelta(minutes=5), **request)

    assert result["action"] == "handoff_requested"
    alert_id = result["alert_id"]
    row = restarted.get_handoff_delivery(alert_id)
    assert row["status"] == "pending"
    alert = alert_from_payload_json(row["payload_json"])
    assert alert.caller == CALLER
    assert alert.latest_message == "human please"
    assert restarted.active_handoff(CALLER)["alert_id"] == alert_id
    assert [sms.kind for sms in telecom.outbound] == ["handoff_ack"]
    _inbound(restarted, telecom, now=NOW + timedelta(minutes=6), **request)
    assert len(restarted.due_handoff_deliveries((NOW + timedelta(minutes=6)).isoformat())) == 1
    assert len(telecom.outbound) == 1


@pytest.mark.parametrize("malformed_payload", ["[", "{}"])
def test_malformed_operator_payload_does_not_prevent_later_alert_delivery(malformed_payload):
    store, transport = Store(), InMemoryDeliveryTransport()
    store.enqueue_handoff_delivery(
        alert_id="broken-alert",
        phone=CALLER,
        payload_json=malformed_payload,
        next_attempt_at=(NOW - timedelta(minutes=1)).isoformat(),
    )
    healthy_alert = _alert()
    store.enqueue_handoff_delivery(
        alert_id="healthy-alert",
        phone=CALLER,
        payload_json=alert_payload_json(healthy_alert),
        next_attempt_at=NOW.isoformat(),
    )

    run_due_deliveries(store=store, transport=transport, policy=DeliveryPolicy(()), now=NOW)

    assert store.get_handoff_delivery("broken-alert")["status"] == "dead_letter"
    assert store.get_handoff_delivery("healthy-alert")["status"] == "delivered"
    assert transport.delivered == [healthy_alert]


def test_concurrent_runner_cannot_dead_letter_final_operator_attempt_in_flight(tmp_path):
    path = str(tmp_path / "concurrent-handoff.db")
    first_store, second_store = Store(path), Store(path)
    first_store.enqueue_handoff_delivery(
        alert_id="last-attempt",
        phone=CALLER,
        payload_json=alert_payload_json(_alert()),
        next_attempt_at=NOW.isoformat(),
    )
    started, release = Event(), Event()

    class BlockingTransport(InMemoryDeliveryTransport):
        def deliver(self, alert):
            started.set()
            assert release.wait(timeout=5), "test transport was not released"
            return super().deliver(alert)

    first_transport, second_transport = BlockingTransport(), InMemoryDeliveryTransport()
    policy = DeliveryPolicy(())
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            run_due_deliveries, store=first_store, transport=first_transport, policy=policy, now=NOW
        )
        assert started.wait(timeout=5), "first runner never reached operator transport"
        second = pool.submit(
            run_due_deliveries, store=second_store, transport=second_transport, policy=policy, now=NOW
        )
        try:
            second.result(timeout=0.1)
        except TimeoutError:
            pass
        finally:
            release.set()
        first.result(timeout=5)
        second.result(timeout=5)

    assert first_store.get_handoff_delivery("last-attempt")["status"] == "delivered"
    assert first_transport.attempts == 1
    assert second_transport.attempts == 0
    events = first_store.list_outcome_events(CALLER)
    assert [event["event_type"] for event in events] == ["handoff.alert_delivered"]
