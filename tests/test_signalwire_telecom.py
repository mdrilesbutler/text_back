import base64

import httpx
import pytest

from text_back.telecom import SignalWireTelecom, TelecomError


SPACE_URL = "https://pilot.signalwire.com"
PROJECT_ID = "project-id"
API_TOKEN = "secret-api-token"


def test_signalwire_telecom_sends_compatibility_rest_sms():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url == (
            "https://pilot.signalwire.com/api/laml/2010-04-01/"
            "Accounts/project-id/Messages"
        )
        expected_auth = base64.b64encode(
            f"{PROJECT_ID}:{API_TOKEN}".encode()
        ).decode()
        assert request.headers["authorization"] == f"Basic {expected_auth}"
        assert request.headers["content-type"].startswith(
            "application/x-www-form-urlencoded"
        )
        assert request.content.decode() == (
            "To=%2B15557654321&From=%2B15551234567&Body=Pilot+test"
        )
        return httpx.Response(201, json={"sid": "SM-live-1", "status": "queued"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    telecom = SignalWireTelecom(
        space_url=f"{SPACE_URL}/",
        project_id=PROJECT_ID,
        api_token=API_TOKEN,
        allowed_from_number="+15551234567",
        client=client,
    )
    assert API_TOKEN not in repr(telecom)

    message_sid = telecom.send_sms(
        to="+15557654321",
        from_number="+15551234567",
        body="Pilot test",
        kind="missed_call_intro",
    )

    assert message_sid == "SM-live-1"


def test_signalwire_telecom_rejects_non_https_space_url():
    with pytest.raises(ValueError, match="HTTPS"):
        SignalWireTelecom(
            space_url="http://pilot.signalwire.com",
            project_id=PROJECT_ID,
            api_token=API_TOKEN,
            allowed_from_number="+15551234567",
        )


def test_signalwire_telecom_raises_redacted_error_for_http_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad token"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    telecom = SignalWireTelecom(
        space_url=SPACE_URL,
        project_id=PROJECT_ID,
        api_token=API_TOKEN,
        allowed_from_number="+15551234567",
        client=client,
    )

    with pytest.raises(TelecomError) as exc_info:
        telecom.send_sms(
            to="+15557654321",
            from_number="+15551234567",
            body="Pilot test",
            kind="missed_call_intro",
        )

    message = str(exc_info.value)
    assert "401" in message
    assert API_TOKEN not in message
    assert "bad token" not in message


def test_signalwire_telecom_requires_provider_message_id():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"status": "queued"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    telecom = SignalWireTelecom(
        space_url=SPACE_URL,
        project_id=PROJECT_ID,
        api_token=API_TOKEN,
        allowed_from_number="+15551234567",
        client=client,
    )

    with pytest.raises(TelecomError, match="message ID"):
        telecom.send_sms(
            to="+15557654321",
            from_number="+15551234567",
            body="Pilot test",
            kind="missed_call_intro",
        )


def test_signalwire_telecom_rejects_an_unconfigured_sender():
    telecom = SignalWireTelecom(
        space_url=SPACE_URL,
        project_id=PROJECT_ID,
        api_token=API_TOKEN,
        allowed_from_number="+15551234567",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(500)
            )
        ),
    )

    with pytest.raises(TelecomError, match="not the configured"):
        telecom.send_sms(
            to="+15557654321",
            from_number="+15559876543",
            body="Pilot test",
            kind="missed_call_intro",
        )
