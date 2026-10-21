import base64

import httpx
import pytest

from text_back.telecom import FakeTelecom, NumberLookup, SignalWireTelecom, TelecomError


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


def _lookup_telecom(handler):
    return SignalWireTelecom(space_url=SPACE_URL, project_id=PROJECT_ID, api_token=API_TOKEN,
                             allowed_from_number="+15551234567", client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_lookup_number_reads_incoming_phone_numbers_with_basic_auth():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"incoming_phone_numbers": [
            {"phone_number": "+15551234567", "voice_url": "https://x.example/webhooks/voice",
             "sms_url": "https://x.example/webhooks/sms", "verification_status": "verified"},
        ]})

    result = _lookup_telecom(handler).lookup_number("+15551234567")
    assert seen["method"] == "GET"
    assert seen["url"] == "https://pilot.signalwire.com/api/laml/2010-04-01/Accounts/project-id/IncomingPhoneNumbers?PhoneNumber=%2B15551234567"
    assert seen["auth"] == "Basic " + base64.b64encode(f"{PROJECT_ID}:{API_TOKEN}".encode()).decode()
    assert result == NumberLookup(True, "+15551234567", "https://x.example/webhooks/voice", "https://x.example/webhooks/sms", "verified")


def test_lookup_number_not_owned_when_the_list_is_empty_or_another_number():
    empty = _lookup_telecom(lambda request: httpx.Response(200, json={"incoming_phone_numbers": []}))
    assert empty.lookup_number("+15551234567") == NumberLookup(False)
    other = _lookup_telecom(lambda request: httpx.Response(200, json={"incoming_phone_numbers": [{"phone_number": "+15550000000"}]}))
    assert other.lookup_number("+15551234567").owned is False
    bare = _lookup_telecom(lambda request: httpx.Response(200, json={"incoming_phone_numbers": [{"phone_number": "+15551234567"}]}))
    assert bare.lookup_number("+15551234567") == NumberLookup(True, "+15551234567", "", "", "")


def test_lookup_number_raises_telecom_error_on_http_failure_and_network_failure():
    with pytest.raises(TelecomError, match="HTTP 500"):
        _lookup_telecom(lambda request: httpx.Response(500, text="boom")).lookup_number("+15551234567")

    def down(request):
        raise httpx.ConnectError("down")

    with pytest.raises(TelecomError, match="ConnectError"):
        _lookup_telecom(down).lookup_number("+15551234567")
    with pytest.raises(TelecomError, match="valid JSON"):
        _lookup_telecom(lambda request: httpx.Response(200, text="<html>")).lookup_number("+15551234567")


def test_fake_telecom_answers_lookups_from_its_owned_numbers_and_records_them():
    fake = FakeTelecom()
    assert fake.lookup_number("+15551234567") == NumberLookup(False)
    fake.owned_numbers["+15551234567"] = {"voice_url": "v", "sms_url": "s"}
    assert fake.lookup_number("+15551234567") == NumberLookup(True, "+15551234567", "v", "s", "")
    assert fake.lookups == ["+15551234567", "+15551234567"]
