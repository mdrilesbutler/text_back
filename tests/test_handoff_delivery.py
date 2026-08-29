import logging
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.calendar_stub import CalendarStub
from text_back.delivery import (
    DeliveryPolicy,
    DisabledTransport,
    InMemoryDeliveryTransport,
    LogTransport,
    alert_from_payload_json,
    run_due_deliveries,
)
from text_back.handoff import FakeHandoffNotifier, HandoffAlert
from text_back.handlers import handle_sms_event
from text_back.store import Store
from text_back.telecom import FakeTelecom


CALLER = "+15551112222"
SECOND_CALLER = "+15559990000"
BUSINESS_NUMBER = "+15553334444"
DESTINATION = "operator-queue"
NOW = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)


def _send(
    *,
    store: Store,
    telecom: FakeTelecom,
    notifier,
    message_sid: str,
    body: str,
    now: datetime = NOW,
    from_number: str = CALLER,
) -> dict:
    return handle_sms_event(
        store=store,
        calendar=CalendarStub(),
        telecom=telecom,
        handoff_notifier=notifier,
        handoff_destination=DESTINATION,
        message_sid=message_sid,
        from_number=from_number,
        to_number=BUSINESS_NUMBER,
        body=body,
        business_name="Oak & Pine Tree Care",
        timezone_name="UTC",
        appointment_duration_minutes=60,
        now=now,
    )


def _activate_handoff(
    store: Store,
    notifier: FakeHandoffNotifier,
    *,
    message_sid: str = "SM-handoff",
    now: datetime = NOW,
) -> str:
    result = _send(
        store=store,
        telecom=FakeTelecom(),
        notifier=notifier,
        message_sid=message_sid,
        body="human please",
        now=now,
    )
    assert result["action"] == "handoff_requested"
    return result["alert_id"]


def test_activated_handoff_enqueues_exactly_one_pending_delivery():
    store, telecom, notifier = Store(), FakeTelecom(), FakeHandoffNotifier()
    _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-service",
        body="tree removal",
    )

    result = _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-handoff",
        body="Please have a person call me",
    )

    alert_id = result["alert_id"]
    row = store.get_handoff_delivery(alert_id)
    assert row is not None
    assert row["status"] == "pending"
    assert row["attempts"] == 0
    assert row["next_attempt_at"] == NOW.isoformat()
    assert row["phone"] == CALLER
    assert alert_from_payload_json(row["payload_json"]) == notifier.alerts[0]


def test_duplicate_handoff_webhook_enqueues_exactly_once():
    store, telecom, notifier = Store(), FakeTelecom(), FakeHandoffNotifier()

    first = _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-handoff-duplicate",
        body="human please",
    )
    second = _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-handoff-duplicate",
        body="human please",
    )

    assert second["duplicate"] is True
    rows = store.due_handoff_deliveries(NOW.isoformat())
    assert len(rows) == 1
    assert rows[0]["alert_id"] == first["alert_id"]


def test_new_handoff_after_resolution_enqueues_a_second_row():
    store, notifier = Store(), FakeHandoffNotifier()
    first_alert_id = _activate_handoff(store, notifier, message_sid="SM-first")
    assert store.resolve_handoff(CALLER) is True

    second_alert_id = _activate_handoff(store, notifier, message_sid="SM-second")

    assert first_alert_id != second_alert_id
    rows = store.due_handoff_deliveries(NOW.isoformat())
    assert {row["alert_id"] for row in rows} == {first_alert_id, second_alert_id}


def test_unknown_delivery_channel_fails_closed_at_startup(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_HANDOFF_DELIVERY_CHANNEL", "sms")
    with pytest.raises(ValueError, match="TEXT_BACK_HANDOFF_DELIVERY_CHANNEL"):
        create_app()


def test_invalid_retry_schedule_fails_closed_at_startup(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_HANDOFF_DELIVERY_RETRY_MINUTES", "5,soon")
    with pytest.raises(ValueError, match="TEXT_BACK_HANDOFF_DELIVERY_RETRY_MINUTES"):
        create_app()

    monkeypatch.setenv("TEXT_BACK_HANDOFF_DELIVERY_RETRY_MINUTES", "-1")
    with pytest.raises(ValueError):
        create_app()


def test_default_channel_is_disabled_and_health_reports_it(monkeypatch):
    monkeypatch.delenv("TEXT_BACK_HANDOFF_DELIVERY_CHANNEL", raising=False)
    monkeypatch.delenv("TEXT_BACK_HANDOFF_DELIVERY_RETRY_MINUTES", raising=False)
    app = create_app()
    client = TestClient(app)

    payload = client.get("/health").json()

    assert payload["handoff_delivery_channel"] == "disabled"


def test_disabled_channel_parks_rows_without_consuming_attempts():
    store, notifier = Store(), FakeHandoffNotifier()
    alert_id = _activate_handoff(store, notifier)
    policy = DeliveryPolicy(retry_minutes=(1, 5))

    parked = run_due_deliveries(
        store=store, transport=DisabledTransport(), policy=policy, now=NOW
    )

    assert parked == []
    row = store.get_handoff_delivery(alert_id)
    assert row["status"] == "pending"
    assert row["attempts"] == 0

    # Flipping the channel later drains the parked backlog.
    transport = InMemoryDeliveryTransport()
    drained = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW
    )
    assert [action["action"] for action in drained] == ["alert_delivered"]
    assert store.get_handoff_delivery(alert_id)["status"] == "delivered"


def test_due_runner_delivers_and_records_outcome():
    store, notifier = Store(), FakeHandoffNotifier()
    alert_id = _activate_handoff(store, notifier)
    transport = InMemoryDeliveryTransport()
    policy = DeliveryPolicy(retry_minutes=(1, 5))

    actions = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW
    )

    assert len(actions) == 1
    assert actions[0]["action"] == "alert_delivered"
    assert actions[0]["alert_id"] == alert_id
    row = store.get_handoff_delivery(alert_id)
    assert row["status"] == "delivered"
    assert row["attempts"] == 1
    assert row["receipt_id"] == actions[0]["receipt_id"]
    assert transport.delivered == [notifier.alerts[0]]
    events = [
        event
        for event in store.list_outcome_events(CALLER)
        if event["event_type"] == "handoff.alert_delivered"
    ]
    assert len(events) == 1
    assert events[0]["evidence_id"] == actions[0]["receipt_id"]
    assert events[0]["metadata"] == {"channel": "memory", "attempt": 1}
    assert events[0]["occurred_at"] == NOW.isoformat()


def test_rerun_at_same_instant_is_idempotent():
    store, notifier = Store(), FakeHandoffNotifier()
    _activate_handoff(store, notifier)
    transport = InMemoryDeliveryTransport()
    policy = DeliveryPolicy(retry_minutes=(1, 5))

    first = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW
    )
    second = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW
    )

    assert [action["action"] for action in first] == ["alert_delivered"]
    assert second == []
    assert transport.attempts == 1
    events = [
        event
        for event in store.list_outcome_events(CALLER)
        if event["event_type"] == "handoff.alert_delivered"
    ]
    assert len(events) == 1


def test_failed_delivery_schedules_backoff_retry():
    store, notifier = Store(), FakeHandoffNotifier()
    alert_id = _activate_handoff(store, notifier)
    transport = InMemoryDeliveryTransport(fail_times=1)
    policy = DeliveryPolicy(retry_minutes=(1, 5))

    first = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW
    )

    assert [action["action"] for action in first] == ["delivery_retry_scheduled"]
    assert first[0]["attempt"] == 1
    row = store.get_handoff_delivery(alert_id)
    assert row["status"] == "pending"
    assert row["attempts"] == 1
    assert row["next_attempt_at"] == (NOW + timedelta(minutes=1)).isoformat()
    assert row["last_error"]

    not_due = run_due_deliveries(
        store=store,
        transport=transport,
        policy=policy,
        now=NOW + timedelta(seconds=30),
    )
    assert not_due == []

    retried = run_due_deliveries(
        store=store,
        transport=transport,
        policy=policy,
        now=NOW + timedelta(minutes=1),
    )
    assert [action["action"] for action in retried] == ["alert_delivered"]
    events = [
        event
        for event in store.list_outcome_events(CALLER)
        if event["event_type"] == "handoff.alert_delivered"
    ]
    assert events[0]["metadata"]["attempt"] == 2


def test_retries_exhaust_to_dead_letter():
    store, notifier = Store(), FakeHandoffNotifier()
    alert_id = _activate_handoff(store, notifier)
    transport = InMemoryDeliveryTransport(fail_times=99)
    policy = DeliveryPolicy(retry_minutes=(1, 5))

    run_due_deliveries(store=store, transport=transport, policy=policy, now=NOW)
    run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW + timedelta(minutes=1)
    )
    final = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW + timedelta(minutes=6)
    )

    assert [action["action"] for action in final] == ["delivery_dead_lettered"]
    assert final[0]["attempts"] == 3
    row = store.get_handoff_delivery(alert_id)
    assert row["status"] == "dead_letter"
    assert row["attempts"] == 3
    events = [
        event
        for event in store.list_outcome_events(CALLER)
        if event["event_type"] == "handoff.alert_dead_lettered"
    ]
    assert len(events) == 1
    assert events[0]["evidence_id"] == alert_id
    assert events[0]["metadata"]["attempts"] == 3
    assert events[0]["metadata"]["last_error"]

    ledger_size = len(store.list_outcome_events(CALLER))
    fourth = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW + timedelta(minutes=7)
    )
    assert fourth == []
    assert len(store.list_outcome_events(CALLER)) == ledger_size


def test_empty_retry_schedule_means_single_attempt():
    store, notifier = Store(), FakeHandoffNotifier()
    alert_id = _activate_handoff(store, notifier)
    transport = InMemoryDeliveryTransport(fail_times=99)
    policy = DeliveryPolicy(retry_minutes=())

    actions = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW
    )

    assert [action["action"] for action in actions] == ["delivery_dead_lettered"]
    assert actions[0]["attempts"] == 1
    assert store.get_handoff_delivery(alert_id)["status"] == "dead_letter"


def test_log_transport_delivers_deterministically_and_masks_pii(caplog):
    alert = HandoffAlert(
        destination=DESTINATION,
        caller=CALLER,
        business_number=BUSINESS_NUMBER,
        reason="customer_requested",
        latest_message="human please",
        collected_fields={"service": "tree removal"},
        summary="Handoff (customer_requested) for +15551112222.",
    )
    transport = LogTransport()

    with caplog.at_level(logging.INFO, logger="text_back.delivery"):
        first = transport.deliver(alert)
    second = transport.deliver(alert)

    assert first.startswith("log-")
    assert first == second
    assert DESTINATION in caplog.text
    assert "customer_requested" in caplog.text
    assert "***2222" in caplog.text
    # Logs outlive the store's PII boundary: no full phone number, no
    # customer content, no collected fields in the process log.
    assert CALLER not in caplog.text
    assert alert.latest_message not in caplog.text
    assert "tree removal" not in caplog.text
    assert alert.summary not in caplog.text


def test_quiet_hours_do_not_defer_operator_alerts():
    # 2026-08-22T03:30Z is 23:30 on 2026-08-21 in America/New_York — inside the
    # default 21:00-08:00 quiet window. Quiet hours protect customer SMS only
    # (docs/PRODUCT-MODEL.md, "No infinite nurture" scope); operator alerts are
    # time-critical and must go out immediately, even at 2am.
    late_night = datetime(2026, 8, 22, 3, 30, tzinfo=timezone.utc)
    store, notifier = Store(), FakeHandoffNotifier()
    alert_id = _activate_handoff(store, notifier, now=late_night)
    transport = InMemoryDeliveryTransport()
    policy = DeliveryPolicy(retry_minutes=(1, 5))

    actions = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=late_night
    )

    assert [action["action"] for action in actions] == ["alert_delivered"]
    assert store.get_handoff_delivery(alert_id)["status"] == "delivered"


# --- crash-safety and restart regressions ---


class _FixedIdNotifier:
    """Returns the same alert ID every time, simulating an ID collision."""

    provider_name = "stub"

    def notify(self, alert: HandoffAlert) -> str:
        return "collide-0001"


class _BuggyForCallerTransport:
    """Raises a NON-DeliveryError exception for one caller (a transport bug)."""

    channel_name = "memory"

    def __init__(self, buggy_caller: str) -> None:
        self.buggy_caller = buggy_caller
        self.delivered: list[HandoffAlert] = []

    def deliver(self, alert: HandoffAlert) -> str:
        if alert.caller == self.buggy_caller:
            raise KeyError("transport bug")
        self.delivered.append(alert)
        return f"mem-{len(self.delivered):04d}"


def test_crash_after_attempt_persisted_retries_instead_of_wedging():
    # The attempt bump is committed BEFORE the transport call; a process
    # death mid-delivery must leave the row re-runnable at its backoff slot,
    # never wedged in pending forever.
    store, notifier = Store(), FakeHandoffNotifier()
    alert_id = _activate_handoff(store, notifier)
    policy = DeliveryPolicy(retry_minutes=(1, 5))
    assert store.begin_handoff_delivery_attempt(
        alert_id, attempts=1, next_attempt_at=(NOW + timedelta(minutes=1)).isoformat()
    )

    transport = InMemoryDeliveryTransport()
    assert (
        run_due_deliveries(store=store, transport=transport, policy=policy, now=NOW)
        == []
    )
    actions = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW + timedelta(minutes=1)
    )

    assert [action["action"] for action in actions] == ["alert_delivered"]
    row = store.get_handoff_delivery(alert_id)
    assert row["status"] == "delivered"
    assert row["attempts"] == 2


def test_crash_during_final_attempt_dead_letters_with_evidence():
    # All scheduled attempts were persisted but the final one never completed
    # (crash). The next run must produce durable dead-letter evidence, not
    # skip the row silently.
    store, notifier = Store(), FakeHandoffNotifier()
    alert_id = _activate_handoff(store, notifier)
    policy = DeliveryPolicy(retry_minutes=())
    assert store.begin_handoff_delivery_attempt(
        alert_id, attempts=1, next_attempt_at=NOW.isoformat()
    )

    transport = InMemoryDeliveryTransport()
    actions = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW + timedelta(minutes=1)
    )

    assert [action["action"] for action in actions] == ["delivery_dead_lettered"]
    assert transport.attempts == 0  # schedule exhausted; no extra transport call
    assert store.get_handoff_delivery(alert_id)["status"] == "dead_letter"
    events = [
        event
        for event in store.list_outcome_events(CALLER)
        if event["event_type"] == "handoff.alert_dead_lettered"
    ]
    assert len(events) == 1
    assert events[0]["metadata"]["last_error"]


def test_crash_between_delivered_ledger_and_status_flip_stays_exactly_once():
    # Documented at-least-once: the crash re-pings the operator on the next
    # run, but the attempt-free idempotency key blocks a second ledger row.
    store, notifier = Store(), FakeHandoffNotifier()
    alert_id = _activate_handoff(store, notifier)
    policy = DeliveryPolicy(retry_minutes=(1, 5))
    assert store.begin_handoff_delivery_attempt(
        alert_id, attempts=1, next_attempt_at=(NOW + timedelta(minutes=1)).isoformat()
    )
    store.record_outcome(
        lead_id=CALLER,
        event_type="handoff.alert_delivered",
        idempotency_key=f"handoff_delivery:{alert_id}:delivered",
        evidence_id="mem-0001",
        metadata={"channel": "memory", "attempt": 1},
        occurred_at=NOW.isoformat(),
    )

    transport = InMemoryDeliveryTransport()
    actions = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW + timedelta(minutes=1)
    )

    assert [action["action"] for action in actions] == ["alert_delivered"]
    assert transport.attempts == 1  # operator was re-pinged (at-least-once)
    assert store.get_handoff_delivery(alert_id)["status"] == "delivered"
    events = [
        event
        for event in store.list_outcome_events(CALLER)
        if event["event_type"] == "handoff.alert_delivered"
    ]
    assert len(events) == 1


def test_unexpected_transport_exception_retries_row_and_continues_run():
    # A transport bug (non-DeliveryError) must burn one attempt with backoff,
    # not wedge the row or abort processing of later due rows.
    store, notifier = Store(), FakeHandoffNotifier()
    first_id = _activate_handoff(store, notifier)
    second = _send(
        store=store,
        telecom=FakeTelecom(),
        notifier=notifier,
        message_sid="SM-second-caller",
        body="human please",
        from_number=SECOND_CALLER,
    )
    assert second["action"] == "handoff_requested"
    policy = DeliveryPolicy(retry_minutes=(1, 5))
    transport = _BuggyForCallerTransport(CALLER)

    actions = run_due_deliveries(
        store=store, transport=transport, policy=policy, now=NOW
    )

    assert sorted(action["action"] for action in actions) == [
        "alert_delivered",
        "delivery_retry_scheduled",
    ]
    row = store.get_handoff_delivery(first_id)
    assert row["status"] == "pending"
    assert row["attempts"] == 1
    assert "transport bug" in row["last_error"]
    assert row["next_attempt_at"] == (NOW + timedelta(minutes=1)).isoformat()
    assert store.get_handoff_delivery(second["alert_id"])["status"] == "delivered"


def test_restart_with_fresh_notifier_still_enqueues_second_leads_handoff(tmp_path):
    # Alert IDs key the durable outbox; a restart (fresh notifier) must never
    # collide with a previous life's row and silently drop a new lead's alert.
    db_path = str(tmp_path / "text_back.db")

    # Life 1: caller A activates a handoff; row parks in the file-backed outbox.
    store_life1 = Store(db_path)
    first = _send(
        store=store_life1,
        telecom=FakeTelecom(),
        notifier=FakeHandoffNotifier(),
        message_sid="SM-life1",
        body="human please",
    )
    assert first["action"] == "handoff_requested"

    # Life 2: process restart — fresh Store on the same file, fresh notifier.
    store_life2 = Store(db_path)
    second = _send(
        store=store_life2,
        telecom=FakeTelecom(),
        notifier=FakeHandoffNotifier(),
        message_sid="SM-life2",
        body="human please",
        from_number=SECOND_CALLER,
    )

    assert second["action"] == "handoff_requested"
    assert second["alert_id"] != first["alert_id"]
    rows = store_life2.due_handoff_deliveries(NOW.isoformat())
    assert {row["alert_id"] for row in rows} == {first["alert_id"], second["alert_id"]}
    phones = {row["alert_id"]: row["phone"] for row in rows}
    assert phones[second["alert_id"]] == SECOND_CALLER
    requested = [
        event
        for event in store_life2.list_outcome_events(SECOND_CALLER)
        if event["event_type"] == "lead.handoff_requested"
    ]
    assert len(requested) == 1


def test_colliding_alert_id_raises_instead_of_silently_dropping():
    store = Store()
    assert store.enqueue_handoff_delivery(
        alert_id="collide-0001",
        phone="+15550001111",
        payload_json="{}",
        next_attempt_at=NOW.isoformat(),
    )

    with pytest.raises(RuntimeError, match="collide-0001"):
        _send(
            store=store,
            telecom=FakeTelecom(),
            notifier=_FixedIdNotifier(),
            message_sid="SM-collide",
            body="human please",
        )
