"""Live texting-approval status for the portal, from the telecom's registry or a stored word."""
import base64
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from text_back.portal_registry import approval_words, network_notice_applies, texting_approval
from text_back.store import Store
from text_back.telecom import SignalWireTelecom, TelecomError

NOW = datetime(2026, 10, 26, 14, 0, tzinfo=timezone.utc)
SCREEN_BANNED = ("signalwire", "campaign", "brand", "10dlc", "registration", "registry")


class RegistryTelecom:
    provider_name = "signalwire"

    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, 0

    def registry_status(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


def make_state(telecom=None, store=None):
    return SimpleNamespace(telecom=telecom if telecom is not None else object(), store=store or Store(":memory:"))


@pytest.mark.parametrize(("registry", "expected"), [
    ({"brand": "approved", "campaign": "approved", "numbers": "complete"}, "approved"),
    ({"brand": "approved", "campaign": "in_review", "numbers": None}, "waiting"),
    ({"brand": "pending", "campaign": None, "numbers": None}, "waiting"),
    ({"brand": "APPROVED", "campaign": "APPROVED", "numbers": "COMPLETED"}, "approved"),
    ({"brand": None, "campaign": None, "numbers": None}, "not_started"),
])
def test_registry_result_maps_to_approved_waiting_not_started(registry, expected):
    result = texting_approval(make_state(RegistryTelecom(registry)), NOW)
    assert result["state"] == expected
    assert result["source"] == "registry"
    assert result["checked_at"] == NOW


def test_texting_approval_unknown_when_registry_unreachable():
    result = texting_approval(make_state(RegistryTelecom(error=TelecomError("boom"))), NOW)
    assert result == {"state": "unknown", "checked_at": NOW, "source": "registry"}


def test_setting_fallback_when_telecom_has_no_registry():
    store = Store(":memory:")
    assert texting_approval(make_state(store=store), NOW) == {"state": "unknown", "checked_at": None, "source": "none"}
    store.set_setting("texting_approval_state", "waiting", now=NOW)
    assert texting_approval(make_state(store=store), NOW) == {"state": "waiting", "checked_at": None, "source": "setting"}
    store.set_setting("texting_approval_state", "whatever", now=NOW)
    assert texting_approval(make_state(store=store), NOW)["state"] == "unknown"
    assert texting_approval(SimpleNamespace(), NOW)["state"] == "unknown"


def test_result_is_cached_for_ten_minutes():
    telecom = RegistryTelecom({"brand": "pending", "campaign": None, "numbers": None})
    state = make_state(telecom)
    first = texting_approval(state, NOW)
    assert first["state"] == "waiting" and telecom.calls == 1
    telecom.result = {"brand": "approved", "campaign": "approved", "numbers": "complete"}
    again = texting_approval(state, NOW + timedelta(minutes=9, seconds=59))
    assert again == first and telecom.calls == 1
    fresh = texting_approval(state, NOW + timedelta(minutes=10, seconds=1))
    assert fresh["state"] == "approved" and fresh["checked_at"] == NOW + timedelta(minutes=10, seconds=1)
    assert telecom.calls == 2
    # Going back in time (clock skew) never serves a cache from the future as current.
    assert texting_approval(state, NOW)["state"] == "approved" and telecom.calls == 3


def test_network_notice_applies_unless_approved():
    approved = make_state(RegistryTelecom({"brand": "approved", "campaign": "approved", "numbers": "complete"}))
    assert network_notice_applies(approved, NOW) is False
    for registry in ({"brand": "pending", "campaign": None, "numbers": None}, {"brand": None, "campaign": None, "numbers": None}):
        assert network_notice_applies(make_state(RegistryTelecom(registry)), NOW) is True
    assert network_notice_applies(make_state(RegistryTelecom(error=RuntimeError())), NOW) is True
    assert network_notice_applies(make_state(), NOW) is True


@pytest.mark.parametrize(("state", "word"), [
    ("approved", "Done"), ("waiting", "Waiting on phone companies"),
    ("not_started", "Not started"), ("unknown", "Waiting on phone companies"),
])
def test_approval_words_are_plain(state, word):
    words = approval_words({"state": state, "checked_at": None, "source": "registry"})
    assert words["state_word"] == word
    assert words["detail"].endswith(".") and ". " not in words["detail"], "one plain sentence"
    lowered = (words["state_word"] + " " + words["detail"]).lower()
    assert not any(banned in lowered for banned in SCREEN_BANNED), words
    assert "{" not in lowered


def test_signalwire_registry_status_uses_read_only_gets():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        assert request.method == "GET"
        expected_auth = base64.b64encode(b"project-id:secret-api-token").decode()
        assert request.headers["authorization"] == f"Basic {expected_auth}"
        path = request.url.path
        if path.endswith("/registry/beta/brands"):
            return httpx.Response(200, json={"data": [{"id": "b1", "state": "APPROVED"}]})
        if path.endswith("/registry/beta/campaigns"):
            return httpx.Response(200, json={"data": [{"id": "c1", "state": "IN_REVIEW"}]})
        if path.endswith("/registry/beta/campaigns/c1/numbers"):
            return httpx.Response(200, json={"data": [
                {"phone_number": {"number": "+15559990000"}, "state": "complete"},
                {"phone_number": {"number": "+15551234567"}, "state": "pending"},
            ]})
        return httpx.Response(404, json={})

    telecom = SignalWireTelecom(space_url="https://pilot.signalwire.com", project_id="project-id",
                                api_token="secret-api-token", allowed_from_number="+15551234567",
                                client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert telecom.registry_status() == {"brand": "approved", "campaign": "in_review", "numbers": "pending"}
    assert [m for m, _ in seen] == ["GET", "GET", "GET"]
    assert seen[0][1] == "https://pilot.signalwire.com/api/relay/rest/registry/beta/brands"
    assert seen[1][1] == "https://pilot.signalwire.com/api/relay/rest/registry/beta/campaigns"


def test_signalwire_registry_status_empty_listing_and_errors():
    def empty(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": []})

    telecom = SignalWireTelecom(space_url="https://pilot.signalwire.com", project_id="p", api_token="t",
                                allowed_from_number="+15551234567",
                                client=httpx.Client(transport=httpx.MockTransport(empty)))
    assert telecom.registry_status() == {"brand": None, "campaign": None, "numbers": None}

    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="t")

    telecom = SignalWireTelecom(space_url="https://pilot.signalwire.com", project_id="p", api_token="t",
                                allowed_from_number="+15551234567",
                                client=httpx.Client(transport=httpx.MockTransport(failing)))
    with pytest.raises(TelecomError) as excinfo:
        telecom.registry_status()
    assert "secret" not in str(excinfo.value) and "HTTP 500" in str(excinfo.value)
    assert texting_approval(SimpleNamespace(telecom=telecom, store=Store(":memory:")), NOW)["state"] == "unknown"
