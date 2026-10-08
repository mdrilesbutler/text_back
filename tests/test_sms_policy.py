import base64
import hashlib
import hmac

import pytest

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


def _sms(client, body, sid):
    params = {"MessageSid": sid, "From": "+15551112222",
              "To": "+15553334444", "Body": body}
    return client.post("/webhooks/sms", data=params,
                       headers={"X-Twilio-Signature": _sign(SMS_URL, params)})


@pytest.mark.parametrize("keyword", ["START", "unstop", "  Start  "])
def test_explicit_opt_in_restores_scheduling_without_capturing_keyword(keyword):
    client, telecom = _app()
    _sms(client, "STOP", "SM-stop")
    telecom.outbound.clear()

    response = _sms(client, keyword, "SM-opt-in")

    assert response.json()["action"] == "opt_in"
    assert not client.app.state.store.is_opted_out("+15551112222")
    assert client.app.state.store.get_conversation_fields("+15551112222") == {}
    assert len(telecom.outbound) == 1
    assert telecom.outbound[0].kind == "opt_in_ack"
    assert "Mike" in telecom.outbound[0].body
    assert "STOP" in telecom.outbound[0].body
    assert _sms(client, keyword, "SM-opt-in").json()["duplicate"] is True
    assert len(telecom.outbound) == 1

    reply = _sms(client, "tree trimming", "SM-service")
    assert reply.json()["field"] == "service"
    assert client.app.state.store.get_conversation_fields("+15551112222")["service"] == "tree trimming"


@pytest.mark.parametrize("body", ["start tree removal", "please restart", "don't start", "START STOP"])
def test_conversational_text_cannot_clear_opt_out(body):
    client, telecom = _app()
    _sms(client, "STOP", "SM-stop")
    telecom.outbound.clear()
    assert _sms(client, body, "SM-ordinary").json()["action"] == "suppressed"
    assert client.app.state.store.is_opted_out("+15551112222")
    assert telecom.outbound == []


def test_opt_in_preserves_active_handoff_and_does_not_restart_automation():
    client, telecom = _app()
    _sms(client, "human", "SM-handoff")
    handoff = client.app.state.store.active_handoff("+15551112222")
    _sms(client, "STOP", "SM-stop")
    telecom.outbound.clear()

    assert _sms(client, "UNSTOP", "SM-opt-in").json()["action"] == "opt_in"
    assert client.app.state.store.active_handoff("+15551112222") == handoff
    assert [sms.kind for sms in telecom.outbound] == ["opt_in_ack"]
    assert _sms(client, "tree trimming", "SM-service").json()["reason"] == "handoff_active"
    assert len(telecom.outbound) == 1


def test_invalid_signature_cannot_restore_opted_out_contact():
    client, telecom = _app()
    _sms(client, "STOP", "SM-stop")
    telecom.outbound.clear()
    params = {"MessageSid": "SM-forged-start", "From": "+15551112222",
              "To": "+15553334444", "Body": "START"}
    response = client.post("/webhooks/sms", data=params,
                           headers={"X-Twilio-Signature": "invalid"})
    assert response.status_code == 403
    assert client.app.state.store.is_opted_out("+15551112222")
    assert telecom.outbound == []


def test_stop_cancels_pending_opt_in_ack_even_if_customer_later_resubscribes(monkeypatch):
    from text_back.telecom import RetryableSmsError

    client, telecom = _app()
    _sms(client, "STOP", "SM-stop")
    original_send = telecom.send_sms

    def reject(**kwargs):
        raise RetryableSmsError("definitely not accepted")

    monkeypatch.setattr(telecom, "send_sms", reject)
    _sms(client, "START", "SM-start-pending")
    assert client.app.state.store.get_sms("SM-start-pending:opt_in_ack")["status"] == "pending"

    monkeypatch.setattr(telecom, "send_sms", original_send)
    _sms(client, "STOP", "SM-stop-again")
    _sms(client, "UNSTOP", "SM-start-again")

    assert client.app.state.store.get_sms("SM-start-pending:opt_in_ack")["status"] == "cancelled"
    assert [sms.kind for sms in telecom.outbound].count("opt_in_ack") == 1


def test_signed_help_webhook_uses_configured_contact(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_BUSINESS_CONTACT", "https://example.test/support")
    client, telecom = _app()
    response = _sms(client, "HELP", "SM-contact")
    assert response.json()["action"] == "help"
    assert "https://example.test/support" in telecom.outbound[0].body
    assert "Msg & data rates may apply" in telecom.outbound[0].body
