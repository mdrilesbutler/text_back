import base64
import hashlib
import hmac
from typing import ClassVar
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.calendar_stub import CalendarStub
from text_back.store import Store
from text_back.telecom import FakeTelecom


WEBHOOK_SECRET = "test-signalwire-signing-key"
PUBLIC_BASE_URL = "https://recover.example.test"
VOICE_URL = f"{PUBLIC_BASE_URL}/webhooks/voice"
SMS_URL = f"{PUBLIC_BASE_URL}/webhooks/sms"
CALLER = "+15551112222"
BUSINESS_NUMBER = "+15553334444"


class FakeSignalWireTelecom(FakeTelecom):
    """No-network test double that selects the live SignalWire boundary."""

    provider_name: ClassVar[str] = "signalwire"


def _sign(url: str, params: dict[str, str]) -> str:
    data = url + "".join(f"{key}{value}" for key, value in sorted(params.items()))
    digest = hmac.new(WEBHOOK_SECRET.encode(), data.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def _client(
    *,
    business_name: str = "Mike",
    wiring_mode: str = "forwarded",
    store: Store | None = None,
) -> tuple[TestClient, FakeSignalWireTelecom]:
    telecom = FakeSignalWireTelecom()
    app = create_app(
        webhook_secret=WEBHOOK_SECRET,
        public_base_url=PUBLIC_BASE_URL,
        telecom=telecom,
        wiring_mode=wiring_mode,
        business_name=business_name,
        store=store,
        # Explicit injection: SignalWire mode refuses the env-default stub
        # calendar at startup, exactly like env validation elsewhere.
        calendar=CalendarStub(),
    )
    return TestClient(app), telecom


def _voice_params(call_sid: str = "CA-signalwire-1") -> dict[str, str]:
    return {
        "CallSid": call_sid,
        "CallStatus": "ringing",
        "From": CALLER,
        "To": BUSINESS_NUMBER,
        "Direction": "inbound",
    }


def test_signalwire_voice_requires_signalwire_signature_header_before_side_effects():
    client, telecom = _client()
    params = _voice_params()

    response = client.post(
        "/webhooks/voice",
        data=params,
        headers={"X-Twilio-Signature": _sign(VOICE_URL, params)},
    )

    assert response.status_code == 403
    assert telecom.outbound == []


def test_signalwire_forwarded_voice_returns_cxml_greeting_and_sends_one_intro():
    client, telecom = _client(business_name="Oak & Pine Tree Care")
    params = _voice_params()

    response = client.post(
        "/webhooks/voice",
        data=params,
        headers={"X-SignalWire-Signature": _sign(VOICE_URL, params)},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    root = ElementTree.fromstring(response.text)
    assert root.tag == "Response"
    assert [child.tag for child in root] == ["Say", "Hangup"]
    assert "Oak & Pine Tree Care" in (root.findtext("Say") or "")
    assert len(telecom.outbound) == 1
    assert telecom.outbound[0].kind == "missed_call_intro"
    assert "Oak & Pine Tree Care" in telecom.outbound[0].body


def test_signalwire_duplicate_voice_webhook_returns_cxml_without_resending():
    client, telecom = _client()
    params = _voice_params("CA-signalwire-duplicate")
    headers = {"X-SignalWire-Signature": _sign(VOICE_URL, params)}

    first = client.post("/webhooks/voice", data=params, headers=headers)
    second = client.post("/webhooks/voice", data=params, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert ElementTree.fromstring(second.text).tag == "Response"
    assert len(telecom.outbound) == 1


def test_signalwire_managed_ringing_keeps_terminal_status_policy_and_empty_cxml():
    client, telecom = _client(wiring_mode="managed")
    params = _voice_params("CA-signalwire-managed-ringing")

    response = client.post(
        "/webhooks/voice",
        data=params,
        headers={"X-SignalWire-Signature": _sign(VOICE_URL, params)},
    )

    assert response.status_code == 200
    root = ElementTree.fromstring(response.text)
    assert root.tag == "Response"
    assert list(root) == []
    assert telecom.outbound == []


def test_signalwire_sms_returns_empty_cxml_response_after_policy_side_effect():
    client, telecom = _client()
    params = {
        "MessageSid": "SM-signalwire-help",
        "From": CALLER,
        "To": BUSINESS_NUMBER,
        "Body": "HELP",
    }

    response = client.post(
        "/webhooks/sms",
        data=params,
        headers={"X-SignalWire-Signature": _sign(SMS_URL, params)},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    root = ElementTree.fromstring(response.text)
    assert root.tag == "Response"
    assert list(root) == []
    assert len(telecom.outbound) == 1
    assert telecom.outbound[0].kind == "help"


def test_signalwire_handoff_pause_does_not_promise_a_followup_text():
    store = Store()
    assert store.request_handoff(CALLER, "customer_requested") is True
    client, telecom = _client(store=store)
    params = _voice_params("CA-signalwire-paused")

    response = client.post(
        "/webhooks/voice",
        data=params,
        headers={"X-SignalWire-Signature": _sign(VOICE_URL, params)},
    )

    assert response.status_code == 200
    say_text = ElementTree.fromstring(response.text).findtext("Say") or ""
    assert "text you" not in say_text.lower()
    assert telecom.outbound == []


def _assert_no_work(client, telecom):
    store = client.app.state.store
    assert telecom.outbound == []
    assert store.conn.execute("SELECT count(*) FROM inbound_jobs").fetchone()[0] == 0
    assert store.conn.execute("SELECT count(*) FROM sms_outbox").fetchone()[0] == 0


def test_forwarded_caller_outside_allowlist_hears_greeting_without_text_promise(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_PILOT_RECIPIENTS", "+15559990000")
    client, telecom = _client(business_name="Oak & Pine Tree Care")
    params = _voice_params("CA-outside-allowlist")

    response = client.post(
        "/webhooks/voice",
        data=params,
        headers={"X-SignalWire-Signature": _sign(VOICE_URL, params)},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    root = ElementTree.fromstring(response.text)
    assert [child.tag for child in root] == ["Say", "Hangup"]
    say_text = root.findtext("Say") or ""
    assert "Oak & Pine Tree Care" in say_text
    assert "text" not in say_text.lower()
    _assert_no_work(client, telecom)


def test_forwarded_caller_outside_empty_allowlist_hears_greeting_without_text_promise(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_PILOT_RECIPIENTS", "")
    client, telecom = _client(business_name="Oak & Pine Tree Care")
    params = _voice_params("CA-empty-allowlist")

    response = client.post(
        "/webhooks/voice",
        data=params,
        headers={"X-SignalWire-Signature": _sign(VOICE_URL, params)},
    )

    assert response.status_code == 200
    say_text = ElementTree.fromstring(response.text).findtext("Say") or ""
    assert "Oak & Pine Tree Care" in say_text
    assert "text" not in say_text.lower()
    _assert_no_work(client, telecom)


def test_managed_caller_outside_allowlist_still_gets_empty_cxml(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_PILOT_RECIPIENTS", "+15559990000")
    client, telecom = _client(wiring_mode="managed")
    params = _voice_params("CA-managed-outside")

    response = client.post(
        "/webhooks/voice",
        data=params,
        headers={"X-SignalWire-Signature": _sign(VOICE_URL, params)},
    )

    assert response.status_code == 200
    assert response.text == "<Response />"
    _assert_no_work(client, telecom)


def test_sms_outside_allowlist_still_gets_empty_cxml(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_PILOT_RECIPIENTS", "+15559990000")
    client, telecom = _client()
    params = {"MessageSid": "SM-outside", "From": CALLER, "To": BUSINESS_NUMBER, "Body": "hello"}

    response = client.post(
        "/webhooks/sms",
        data=params,
        headers={"X-SignalWire-Signature": _sign(SMS_URL, params)},
    )

    assert response.status_code == 200
    assert response.text == "<Response />"
    _assert_no_work(client, telecom)
