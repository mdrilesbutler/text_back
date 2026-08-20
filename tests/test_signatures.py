import base64
import hashlib
import hmac

from text_back.signatures import SignatureError, verify_twilio_compat


def _sign(url: str, params: dict[str, str], token: str) -> str:
    data = url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    digest = hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def test_valid_signature_is_accepted():
    url = "https://example.test/webhooks/voice"
    params = {"CallSid": "CA123", "CallStatus": "no-answer"}
    token = "test-token"
    assert verify_twilio_compat(url, params, _sign(url, params, token), token) is True


def test_invalid_signature_is_rejected():
    url = "https://example.test/webhooks/voice"
    params = {"CallSid": "CA123"}
    try:
        verify_twilio_compat(url, params, "bogus", "test-token")
    except SignatureError as exc:
        assert "invalid" in str(exc).lower()
    else:
        raise AssertionError("expected SignatureError")


def test_missing_secret_fails_closed():
    try:
        verify_twilio_compat("https://example.test/x", {}, "sig", "")
    except SignatureError as exc:
        assert "secret" in str(exc).lower()
    else:
        raise AssertionError("expected SignatureError")
