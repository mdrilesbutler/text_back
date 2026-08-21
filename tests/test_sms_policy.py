import base64
import hashlib
import hmac

from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.telecom import FakeTelecom


WEBHOOK_SECRET = "test-webhook-secret"
SMS_URL = "https://example.test/webhooks/sms"
VOICE_URL = "https://example.test/webhooks/voice"


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
        business_name="Mike",
    )
    return TestClient(app), telecom


def test_stop_keyword_opts_out_and_acks():
    client, telecom = _app()
    params = {
        "MessageSid": "SM-stop-1",
        "From": "+15551112222",
        "To": "+15553334444",
        "Body": "STOP",
    }
    response = client.post(
        "/webhooks/sms",
        data=params,
        headers={"X-Twilio-Signature": _sign(SMS_URL, params)},
    )
    assert response.status_code == 200
    assert response.json()["action"] == "opt_out"
    assert len(telecom.outbound) == 1
    assert telecom.outbound[0].kind == "opt_out_ack"
    assert "stop" in telecom.outbound[0].body.lower()


def test_help_returns_business_contact_info():
    client, telecom = _app()
    params = {
        "MessageSid": "SM-help-1",
        "From": "+15551112222",
        "To": "+15553334444",
        "Body": "HELP",
    }
    response = client.post(
        "/webhooks/sms",
        data=params,
        headers={"X-Twilio-Signature": _sign(SMS_URL, params)},
    )
    assert response.status_code == 200
    assert response.json()["action"] == "help"
    assert len(telecom.outbound) == 1
    body = telecom.outbound[0].body.lower()
    assert "mike" in body
    assert telecom.outbound[0].kind == "help"


def test_stop_suppresses_later_missed_call_intro():
    client, telecom = _app()
    stop = {
        "MessageSid": "SM-stop-2",
        "From": "+15551112222",
        "To": "+15553334444",
        "Body": "stop please",
    }
    client.post("/webhooks/sms", data=stop, headers={"X-Twilio-Signature": _sign(SMS_URL, stop)})
    telecom.outbound.clear()
    voice = {
        "CallSid": "CA-after-stop",
        "CallStatus": "no-answer",
        "From": "+15551112222",
        "To": "+15553334444",
        "Direction": "inbound",
    }
    response = client.post(
        "/webhooks/voice",
        data=voice,
        headers={"X-Twilio-Signature": _sign(VOICE_URL, voice)},
    )
    assert response.status_code == 200
    assert response.json()["action"] == "suppressed"
    assert telecom.outbound == []


def test_duplicate_sms_webhook_does_not_resend_help():
    client, telecom = _app()
    params = {
        "MessageSid": "SM-help-dup",
        "From": "+15551112222",
        "To": "+15553334444",
        "Body": "HELP",
    }
    sig = _sign(SMS_URL, params)
    first = client.post("/webhooks/sms", data=params, headers={"X-Twilio-Signature": sig})
    second = client.post("/webhooks/sms", data=params, headers={"X-Twilio-Signature": sig})
    assert first.status_code == 200
    assert second.json()["duplicate"] is True
    assert len(telecom.outbound) == 1


def test_invalid_sms_signature_is_rejected():
    client, telecom = _app()
    params = {
        "MessageSid": "SM-bad",
        "From": "+15551112222",
        "To": "+15553334444",
        "Body": "HELP",
    }
    response = client.post(
        "/webhooks/sms",
        data=params,
        headers={"X-Twilio-Signature": "nope"},
    )
    assert response.status_code == 403
    assert telecom.outbound == []
