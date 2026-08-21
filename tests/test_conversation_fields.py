import base64
import hashlib
import hmac
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.calendar_stub import CalendarStub
from text_back.handoff import FakeHandoffNotifier
from text_back.handlers import handle_sms_event
from text_back.policy import (
    CONVERSATION_FIELDS,
    conversation_prompt,
    next_missing_field,
)
from text_back.store import Store
from text_back.telecom import FakeTelecom


CALLER = "+15551112222"
BUSINESS = "+15553334444"
PREFERRED_TIME = "2026-08-25 2:00 PM"
NOW = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)


def _send(store, telecom, message_sid, body, from_number=CALLER, to_number=BUSINESS):
    return handle_sms_event(
        store=store,
        calendar=CalendarStub(),
        telecom=telecom,
        handoff_notifier=FakeHandoffNotifier(),
        handoff_destination="operator-queue",
        message_sid=message_sid,
        from_number=from_number,
        to_number=to_number,
        body=body,
        business_name="Mike",
        timezone_name="UTC",
        appointment_duration_minutes=60,
        now=NOW,
    )


# --- policy: deterministic field order and prompts -------------------------


def test_conversation_fields_order_is_service_location_preferred_time_name():
    assert CONVERSATION_FIELDS == ("service", "location", "preferred_time", "name")


def test_next_missing_field_walks_fields_in_order():
    assert next_missing_field({}) == "service"
    assert next_missing_field({"service": "tree removal"}) == "location"
    assert next_missing_field({"service": "x", "location": "y"}) == "preferred_time"
    assert (
        next_missing_field({"service": "x", "location": "y", "preferred_time": "z"})
        == "name"
    )
    assert (
        next_missing_field(
            {"service": "x", "location": "y", "preferred_time": "z", "name": "w"}
        )
        is None
    )


def test_next_missing_field_treats_blank_values_as_missing():
    assert next_missing_field({"service": "  "}) == "service"


def test_conversation_prompt_exists_for_every_field():
    for field in CONVERSATION_FIELDS:
        prompt = conversation_prompt(field)
        assert isinstance(prompt, str)
        assert prompt.strip()


# --- store: per-phone persistence -------------------------------------------


def test_store_persists_conversation_fields_across_calls():
    store = Store()
    store.set_conversation_field(CALLER, "service", "tree removal")
    assert store.get_conversation_fields(CALLER) == {"service": "tree removal"}
    store.set_conversation_field(CALLER, "location", "12 Oak St")
    assert store.get_conversation_fields(CALLER) == {
        "service": "tree removal",
        "location": "12 Oak St",
    }


def test_store_conversation_fields_isolated_per_phone():
    store = Store()
    store.set_conversation_field(CALLER, "service", "tree removal")
    assert store.get_conversation_fields("+15559998888") == {}


def test_store_set_conversation_field_overwrites_existing_value():
    store = Store()
    store.set_conversation_field(CALLER, "service", "tree removal")
    store.set_conversation_field(CALLER, "service", "stump grinding")
    assert store.get_conversation_fields(CALLER) == {"service": "stump grinding"}


def test_store_clear_conversation_fields_removes_all():
    store = Store()
    store.set_conversation_field(CALLER, "service", "tree removal")
    store.set_conversation_field(CALLER, "location", "12 Oak St")
    store.clear_conversation_fields(CALLER)
    assert store.get_conversation_fields(CALLER) == {}


# --- handler: deterministic slot-filling conversation -----------------------


def test_first_reply_captures_service_and_prompts_for_location():
    store, telecom = Store(), FakeTelecom()
    result = _send(store, telecom, "SM-1", "tree removal")
    assert result["action"] == "field_collected"
    assert result["field"] == "service"
    assert result["next_field"] == "location"
    assert store.get_conversation_fields(CALLER) == {"service": "tree removal"}
    assert len(telecom.outbound) == 1
    assert telecom.outbound[0].kind == "field_prompt"
    assert telecom.outbound[0].body == conversation_prompt("location")
    assert telecom.outbound[0].to == CALLER
    assert telecom.outbound[0].from_number == BUSINESS


def test_full_conversation_collects_all_four_fields_in_order():
    store, telecom = Store(), FakeTelecom()
    _send(store, telecom, "SM-1", "tree removal")
    _send(store, telecom, "SM-2", "12 Oak St")
    _send(store, telecom, "SM-3", PREFERRED_TIME)
    result = _send(store, telecom, "SM-4", "John Smith")

    assert result["action"] == "booked"
    assert result["fields_complete"] is True
    fields = store.get_conversation_fields(CALLER)
    assert fields == {
        "service": "tree removal",
        "location": "12 Oak St",
        "preferred_time": PREFERRED_TIME,
        "name": "John Smith",
    }
    assert len(telecom.outbound) == 4
    assert telecom.outbound[-1].kind == "booking_confirmation"
    assert "tree removal" in telecom.outbound[-1].body
    assert "12 Oak St" in telecom.outbound[-1].body
    assert "02:00 PM" in telecom.outbound[-1].body


def test_replies_after_completion_do_not_overwrite_fields_or_reprompt():
    store, telecom = Store(), FakeTelecom()
    _send(store, telecom, "SM-1", "tree removal")
    _send(store, telecom, "SM-2", "12 Oak St")
    _send(store, telecom, "SM-3", PREFERRED_TIME)
    _send(store, telecom, "SM-4", "John Smith")
    telecom.outbound.clear()

    result = _send(store, telecom, "SM-5", "actually make it Friday")

    assert result["action"] == "conversation"
    assert result.get("fields_complete") is True
    assert telecom.outbound == []
    assert store.get_conversation_fields(CALLER)["preferred_time"] == PREFERRED_TIME


def test_blank_reply_repeats_current_prompt_without_storing_empty_value():
    store, telecom = Store(), FakeTelecom()
    result = _send(store, telecom, "SM-1", "   ")
    assert result["action"] == "field_prompt_repeated"
    assert result["field"] == "service"
    assert store.get_conversation_fields(CALLER) == {}
    assert len(telecom.outbound) == 1
    assert telecom.outbound[0].kind == "field_prompt"
    assert telecom.outbound[0].body == conversation_prompt("service")


def test_stop_takes_priority_over_field_collection_mid_conversation():
    store, telecom = Store(), FakeTelecom()
    _send(store, telecom, "SM-1", "tree removal")
    telecom.outbound.clear()

    result = _send(store, telecom, "SM-2", "STOP")

    assert result["action"] == "opt_out"
    assert store.is_opted_out(CALLER) is True
    # collected progress survives opt-out; only outbound automation is suppressed
    assert store.get_conversation_fields(CALLER) == {"service": "tree removal"}


def test_help_takes_priority_over_field_collection_mid_conversation():
    store, telecom = Store(), FakeTelecom()
    _send(store, telecom, "SM-1", "tree removal")
    telecom.outbound.clear()

    result = _send(store, telecom, "SM-2", "HELP")

    assert result["action"] == "help"
    assert telecom.outbound[0].kind == "help"


def test_opted_out_contact_is_suppressed_before_any_field_prompt():
    store, telecom = Store(), FakeTelecom()
    store.set_opted_out(CALLER, True)

    result = _send(store, telecom, "SM-1", "tree removal")

    assert result["action"] == "suppressed"
    assert telecom.outbound == []
    assert store.get_conversation_fields(CALLER) == {}


def test_fields_are_isolated_per_phone_number():
    store, telecom = Store(), FakeTelecom()
    _send(store, telecom, "SM-1", "tree removal", from_number="+15550001111")
    _send(store, telecom, "SM-2", "roof repair", from_number="+15559998888")
    assert store.get_conversation_fields("+15550001111") == {"service": "tree removal"}
    assert store.get_conversation_fields("+15559998888") == {"service": "roof repair"}


def test_duplicate_field_reply_webhook_does_not_double_prompt():
    store, telecom = Store(), FakeTelecom()
    first = _send(store, telecom, "SM-dup", "tree removal")
    second = _send(store, telecom, "SM-dup", "tree removal")
    assert first["action"] == "field_collected"
    assert second["duplicate"] is True
    assert len(telecom.outbound) == 1


# --- webhook wiring end-to-end -----------------------------------------------

WEBHOOK_SECRET = "test-webhook-secret"
SMS_URL = "https://example.test/webhooks/sms"


def _sign(url: str, params: dict[str, str]) -> str:
    data = url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    digest = hmac.new(WEBHOOK_SECRET.encode(), data.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def _app():
    telecom = FakeTelecom()
    app = create_app(
        webhook_secret=WEBHOOK_SECRET,
        public_base_url="https://example.test",
        telecom=telecom,
    )
    return TestClient(app), telecom


def test_webhook_flow_collects_first_field_end_to_end():
    client, telecom = _app()
    params = {
        "MessageSid": "SM-e2e-1",
        "From": CALLER,
        "To": BUSINESS,
        "Body": "tree removal",
    }
    response = client.post(
        "/webhooks/sms",
        data=params,
        headers={"X-Twilio-Signature": _sign(SMS_URL, params)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "field_collected"
    assert body["field"] == "service"
    assert len(telecom.outbound) == 1
    assert telecom.outbound[0].kind == "field_prompt"
