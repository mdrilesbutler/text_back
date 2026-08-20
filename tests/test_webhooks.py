import base64
import hashlib
import hmac

from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.telecom import FakeTelecom


WEBHOOK_SECRET = "test-webhook-secret"
PUBLIC_URL = "https://example.test/webhooks/voice"


def _sign(url: str, params: dict[str, str], token: str = WEBHOOK_SECRET) -> str:
    data = url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    digest = hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def _client(telecom: FakeTelecom | None = None) -> tuple[TestClient, FakeTelecom]:
    telecom = telecom or FakeTelecom()
    # This suite documents "managed" wiring_mode behavior specifically: our
    # number is the client's own number, so only terminal-unanswered call
    # statuses represent a missed call. See test_wiring_mode.py for
    # "forwarded" mode (the app-level default), where the first voice event
    # for a call_sid triggers regardless of call_status.
    app = create_app(
        webhook_secret=WEBHOOK_SECRET,
        public_base_url="https://example.test",
        telecom=telecom,
        wiring_mode="managed",
    )
    return TestClient(app), telecom


def _post_voice(client: TestClient, params: dict[str, str], signature: str | None = None):
    headers = {}
    if signature is not None:
        headers["X-Twilio-Signature"] = signature
    return client.post("/webhooks/voice", data=params, headers=headers)


def test_invalid_voice_signature_is_rejected_before_side_effects():
    client, telecom = _client()
    params = {
        "CallSid": "CA-invalid",
        "CallStatus": "no-answer",
        "From": "+15551112222",
        "To": "+15553334444",
        "Direction": "inbound",
    }
    response = _post_voice(client, params, signature="not-valid")
    assert response.status_code == 403
    assert telecom.outbound == []


def test_no_answer_sends_exactly_one_initial_sms():
    client, telecom = _client()
    params = {
        "CallSid": "CA-missed-1",
        "CallStatus": "no-answer",
        "From": "+15551112222",
        "To": "+15553334444",
        "Direction": "inbound",
    }
    response = _post_voice(client, params, signature=_sign(PUBLIC_URL, params))
    assert response.status_code == 200
    assert len(telecom.outbound) == 1
    sms = telecom.outbound[0]
    assert sms.to == "+15551112222"
    assert sms.from_number == "+15553334444"
    assert sms.kind == "missed_call_intro"
    assert "missed your call" in sms.body.lower()


def test_ringing_does_not_send_sms():
    client, telecom = _client()
    params = {
        "CallSid": "CA-ringing-1",
        "CallStatus": "ringing",
        "From": "+15551112222",
        "To": "+15553334444",
        "Direction": "inbound",
    }
    response = _post_voice(client, params, signature=_sign(PUBLIC_URL, params))
    assert response.status_code == 200
    assert telecom.outbound == []


def test_duplicate_no_answer_webhook_does_not_resend():
    client, telecom = _client()
    params = {
        "CallSid": "CA-dup-1",
        "CallStatus": "no-answer",
        "From": "+15551112222",
        "To": "+15553334444",
        "Direction": "inbound",
    }
    sig = _sign(PUBLIC_URL, params)
    first = _post_voice(client, params, signature=sig)
    second = _post_voice(client, params, signature=sig)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert len(telecom.outbound) == 1


def test_missing_voice_signature_is_rejected():
    client, telecom = _client()
    params = {
        "CallSid": "CA-nosig",
        "CallStatus": "no-answer",
        "From": "+15551112222",
        "To": "+15553334444",
        "Direction": "inbound",
    }
    response = client.post("/webhooks/voice", data=params)
    assert response.status_code == 403
    assert telecom.outbound == []
