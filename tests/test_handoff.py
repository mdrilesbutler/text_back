import base64
import hashlib
import hmac
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.calendar_stub import CalendarStub
from text_back.handoff import FakeHandoffNotifier
from text_back.handlers import handle_sms_event, handle_voice_event
from text_back.policy import classify_handoff_request
from text_back.store import Store
from text_back.telecom import FakeTelecom


CALLER = "+15551112222"
BUSINESS_NUMBER = "+15553334444"
DESTINATION = "operator-queue"
NOW = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)
WEBHOOK_SECRET = "test-webhook-secret"
SMS_URL = "https://example.test/webhooks/sms"


def _send(
    *,
    store: Store,
    telecom: FakeTelecom,
    notifier: FakeHandoffNotifier,
    message_sid: str,
    body: str,
) -> dict:
    return handle_sms_event(
        store=store,
        calendar=CalendarStub(),
        telecom=telecom,
        handoff_notifier=notifier,
        handoff_destination=DESTINATION,
        message_sid=message_sid,
        from_number=CALLER,
        to_number=BUSINESS_NUMBER,
        body=body,
        business_name="Oak & Pine Tree Care",
        timezone_name="UTC",
        appointment_duration_minutes=60,
        now=NOW,
    )


@pytest.mark.parametrize(
    "body",
    [
        "Can I talk to a human?",
        "I need a person",
        "Please have someone call me",
        "representative please",
    ],
)
def test_explicit_handoff_phrases_are_deterministic(body):
    assert classify_handoff_request(body) == "customer_requested"


@pytest.mark.parametrize(
    "body",
    [
        "This is an emergency",
        "A tree hit a power line",
        "Someone is injured",
        "There is immediate danger",
    ],
)
def test_safety_phrases_take_the_safety_handoff_path(body):
    assert classify_handoff_request(body) == "safety"


def test_unrelated_word_does_not_false_trigger_handoff():
    assert classify_handoff_request("personal tree trimming") is None


def test_handoff_pauses_collection_and_emits_one_operator_payload():
    store, telecom, notifier = Store(), FakeTelecom(), FakeHandoffNotifier()
    _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-service",
        body="tree removal",
    )
    telecom.outbound.clear()

    result = _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-handoff",
        body="Please have a person call me",
    )

    assert result["action"] == "handoff_requested"
    assert result["reason"] == "customer_requested"
    handoff = store.active_handoff(CALLER)
    assert handoff is not None
    assert handoff["alert_id"] == result["alert_id"]
    assert len(notifier.alerts) == 1
    alert = notifier.alerts[0]
    assert alert.destination == DESTINATION
    assert alert.caller == CALLER
    assert alert.business_number == BUSINESS_NUMBER
    assert alert.reason == "customer_requested"
    assert alert.collected_fields == {"service": "tree removal"}
    assert alert.latest_message == "Please have a person call me"
    assert "tree removal" in alert.summary
    assert telecom.outbound[-1].kind == "handoff_ack"
    assert store.get_conversation_fields(CALLER) == {"service": "tree removal"}


def test_active_handoff_suppresses_later_automated_collection():
    store, telecom, notifier = Store(), FakeTelecom(), FakeHandoffNotifier()
    _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-handoff",
        body="human please",
    )
    telecom.outbound.clear()

    result = _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-after-handoff",
        body="12 Oak St",
    )

    assert result["action"] == "suppressed"
    assert result["reason"] == "handoff_active"
    assert store.get_conversation_fields(CALLER) == {}
    assert telecom.outbound == []
    assert len(notifier.alerts) == 1


def test_duplicate_handoff_webhook_does_not_duplicate_alert_or_ack():
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

    assert first["action"] == "handoff_requested"
    assert second["duplicate"] is True
    assert len(notifier.alerts) == 1
    assert len(telecom.outbound) == 1


def test_safety_handoff_ack_directs_immediate_danger_to_emergency_services():
    store, telecom, notifier = Store(), FakeTelecom(), FakeHandoffNotifier()

    result = _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-safety",
        body="A tree hit a power line and there is immediate danger",
    )

    assert result["reason"] == "safety"
    assert "911" in telecom.outbound[-1].body
    assert notifier.alerts[0].reason == "safety"


def test_stop_and_help_policy_remain_available_during_handoff():
    store, telecom, notifier = Store(), FakeTelecom(), FakeHandoffNotifier()
    _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-handoff",
        body="human please",
    )
    telecom.outbound.clear()

    help_result = _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-help",
        body="HELP",
    )
    stop_result = _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-stop",
        body="STOP",
    )

    assert help_result["action"] == "help"
    assert stop_result["action"] == "opt_out"
    assert [message.kind for message in telecom.outbound] == ["help", "opt_out_ack"]
    assert store.is_opted_out(CALLER) is True


def test_resolved_handoff_allows_automation_and_a_later_new_handoff():
    store, telecom, notifier = Store(), FakeTelecom(), FakeHandoffNotifier()
    _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-service",
        body="tree removal",
    )
    _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-first-handoff",
        body="human please",
    )

    assert store.resolve_handoff(CALLER) is True
    assert store.active_handoff(CALLER) is None
    resumed = _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-resumed",
        body="12 Oak St",
    )
    second_handoff = _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-second-handoff",
        body="representative please",
    )

    assert resumed["action"] == "field_collected"
    assert resumed["field"] == "location"
    assert second_handoff["action"] == "handoff_requested"
    assert len(notifier.alerts) == 2
    assert store.active_handoff(CALLER) is not None


def test_sms_webhook_routes_handoff_to_configured_notifier():
    store, telecom, notifier = Store(), FakeTelecom(), FakeHandoffNotifier()
    app = create_app(
        webhook_secret=WEBHOOK_SECRET,
        public_base_url="https://example.test",
        store=store,
        telecom=telecom,
        handoff_notifier=notifier,
        handoff_destination=DESTINATION,
    )
    client = TestClient(app)
    params = {
        "MessageSid": "SM-webhook-handoff",
        "From": CALLER,
        "To": BUSINESS_NUMBER,
        "Body": "Please have a human call me",
    }
    signed_data = SMS_URL + "".join(
        f"{key}{value}" for key, value in sorted(params.items())
    )
    signature = base64.b64encode(
        hmac.new(WEBHOOK_SECRET.encode(), signed_data.encode(), hashlib.sha1).digest()
    ).decode()

    response = client.post(
        "/webhooks/sms",
        data=params,
        headers={"X-Twilio-Signature": signature},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "handoff_requested"
    assert len(notifier.alerts) == 1
    assert notifier.alerts[0].destination == DESTINATION
    assert store.active_handoff(CALLER) is not None


def test_active_handoff_suppresses_new_missed_call_intro():
    store, telecom = Store(), FakeTelecom()
    assert store.request_handoff(CALLER, "customer_requested") is True

    result = handle_voice_event(
        store=store,
        telecom=telecom,
        call_sid="CA-during-handoff",
        call_status="ringing",
        from_number=CALLER,
        to_number=BUSINESS_NUMBER,
        wiring_mode="forwarded",
        business_name="Oak & Pine Tree Care",
    )

    assert result["action"] == "suppressed"
    assert result["reason"] == "handoff_active"
    assert telecom.outbound == []


def test_opted_out_customer_can_request_handoff_without_automated_ack():
    store, telecom, notifier = Store(), FakeTelecom(), FakeHandoffNotifier()
    store.set_opted_out(CALLER, True)

    result = _send(
        store=store,
        telecom=telecom,
        notifier=notifier,
        message_sid="SM-opted-out-handoff",
        body="human please",
    )

    assert result["action"] == "handoff_requested"
    assert len(notifier.alerts) == 1
    assert telecom.outbound == []
    assert store.active_handoff(CALLER) is not None
