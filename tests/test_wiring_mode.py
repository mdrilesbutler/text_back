"""wiring_mode: how our number relates to the client's real phone line.

- "forwarded" (new default): our number only ever receives a call after the
  carrier's conditional call forwarding kicks in (no-answer/busy on the
  client's real line). That means the FIRST voice webhook we see for a given
  CallSid already represents a missed call — trigger the intro SMS on
  arrival, regardless of CallStatus. Idempotency (via claim_event keyed on
  call_sid) must still guarantee exactly one SMS across ringing/completed
  webhook retries for the same call.
- "managed" (current/legacy behavior): our number IS the client's number, so
  only terminal-unanswered statuses (no-answer/busy/failed/canceled)
  represent a missed call.
"""

import base64
import hashlib
import hmac

import pytest
from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.handlers import handle_voice_event
from text_back.policy import WIRING_MODE_FORWARDED, WIRING_MODE_MANAGED
from text_back.store import Store
from text_back.telecom import FakeTelecom


WEBHOOK_SECRET = "test-webhook-secret"
VOICE_URL = "https://example.test/webhooks/voice"
CALLER = "+15551112222"
BUSINESS = "+15553334444"


def _sign(url: str, params: dict[str, str]) -> str:
    data = url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    digest = hmac.new(WEBHOOK_SECRET.encode(), data.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def _client(wiring_mode: str | None = None) -> tuple[TestClient, FakeTelecom]:
    telecom = FakeTelecom()
    kwargs = dict(
        webhook_secret=WEBHOOK_SECRET,
        public_base_url="https://example.test",
        telecom=telecom,
    )
    if wiring_mode is not None:
        kwargs["wiring_mode"] = wiring_mode
    app = create_app(**kwargs)
    return TestClient(app), telecom


def _post_voice(client: TestClient, params: dict[str, str]):
    return client.post(
        "/webhooks/voice", data=params, headers={"X-Twilio-Signature": _sign(VOICE_URL, params)}
    )


def _voice_params(call_sid: str, call_status: str) -> dict[str, str]:
    return {
        "CallSid": call_sid,
        "CallStatus": call_status,
        "From": CALLER,
        "To": BUSINESS,
        "Direction": "inbound",
    }


# --- app-level default ------------------------------------------------------


def test_forwarded_is_the_default_wiring_mode():
    client, telecom = _client()  # no wiring_mode passed
    response = _post_voice(client, _voice_params("CA-default-1", "ringing"))
    assert response.status_code == 200
    assert response.json()["action"] == "sent_intro"
    assert len(telecom.outbound) == 1


def test_health_reports_configured_wiring_mode():
    default_client, _ = _client()
    assert default_client.get("/health").json()["wiring_mode"] == "forwarded"

    managed_client, _ = _client(wiring_mode="managed")
    assert managed_client.get("/health").json()["wiring_mode"] == "managed"


def test_invalid_wiring_mode_is_rejected():
    with pytest.raises(ValueError):
        create_app(wiring_mode="bogus")


# --- forwarded mode: trigger on arrival, regardless of CallStatus ----------


@pytest.mark.parametrize("call_status", ["ringing", "in-progress", "completed", "no-answer"])
def test_forwarded_mode_sends_intro_on_first_event_for_any_call_status(call_status):
    client, telecom = _client(wiring_mode=WIRING_MODE_FORWARDED)
    response = _post_voice(client, _voice_params(f"CA-fwd-{call_status}", call_status))
    assert response.status_code == 200
    assert response.json()["action"] == "sent_intro"
    assert len(telecom.outbound) == 1
    sms = telecom.outbound[0]
    assert sms.to == CALLER
    assert sms.from_number == BUSINESS
    assert sms.kind == "missed_call_intro"


def test_forwarded_mode_is_idempotent_across_ringing_then_completed_retries():
    client, telecom = _client(wiring_mode=WIRING_MODE_FORWARDED)
    call_sid = "CA-fwd-retry"

    first = _post_voice(client, _voice_params(call_sid, "ringing"))
    second = _post_voice(client, _voice_params(call_sid, "completed"))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["action"] == "sent_intro"
    assert second.json()["duplicate"] is True
    assert len(telecom.outbound) == 1


def test_forwarded_mode_suppresses_intro_for_opted_out_caller():
    store = Store()
    store.set_opted_out(CALLER, True)
    telecom = FakeTelecom()
    app = create_app(
        webhook_secret=WEBHOOK_SECRET,
        public_base_url="https://example.test",
        telecom=telecom,
        store=store,
        wiring_mode=WIRING_MODE_FORWARDED,
    )
    client = TestClient(app)
    response = _post_voice(client, _voice_params("CA-fwd-optout", "ringing"))
    assert response.status_code == 200
    assert response.json()["action"] == "suppressed"
    assert telecom.outbound == []


# --- managed mode: unchanged, terminal-unanswered only ---------------------


def test_managed_mode_ignores_non_terminal_status():
    client, telecom = _client(wiring_mode=WIRING_MODE_MANAGED)
    response = _post_voice(client, _voice_params("CA-managed-ringing", "ringing"))
    assert response.status_code == 200
    assert response.json()["action"] == "ignored"
    assert telecom.outbound == []


def test_managed_mode_sends_intro_only_on_terminal_unanswered():
    client, telecom = _client(wiring_mode=WIRING_MODE_MANAGED)
    response = _post_voice(client, _voice_params("CA-managed-noanswer", "no-answer"))
    assert response.status_code == 200
    assert response.json()["action"] == "sent_intro"
    assert len(telecom.outbound) == 1


# --- handler unit-level: wiring_mode is a required, explicit argument ------


def test_handle_voice_event_requires_explicit_wiring_mode():
    store, telecom = Store(), FakeTelecom()
    with pytest.raises(TypeError):
        handle_voice_event(  # type: ignore[call-arg]
            store=store,
            telecom=telecom,
            call_sid="CA-missing-mode",
            call_status="ringing",
            from_number=CALLER,
            to_number=BUSINESS,
        )
