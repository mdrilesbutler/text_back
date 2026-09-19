"""Customer Google tokens refresh durably and distinguish revocation from outages."""

import json
import stat
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timedelta, timezone
from threading import Event
from urllib.parse import parse_qs, urlsplit

import pytest

from text_back.calendars.credentials import GoogleCredentials
from text_back.calendars.protocol import CalendarProviderError
from text_back.calendars.transport import FakeHttpTransport, HttpResponse


NOW = datetime(2026, 9, 17, 14, tzinfo=timezone.utc)
OLD_TOKEN = "test-expired-access-token"
NEW_TOKEN = "test-refreshed-access-token"
REFRESH_TOKEN = "test-refresh-token"
CLIENT_SECRET = "test-client-secret"


def _credentials_file(tmp_path, *, expiry=None):
    path = tmp_path / "google_token.json"
    payload = {
        "token": OLD_TOKEN,
        # Google authorized-user files may serialize UTC without an offset.
        "expiry": expiry or "2026-09-17T13:00:00",
        "refresh_token": REFRESH_TOKEN,
        "client_id": "test-client-id",
        "client_secret": CLIENT_SECRET,
        "token_uri": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/calendar"],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o600)
    return path


def _response(status=200, **payload):
    if not payload:
        payload = {"access_token": NEW_TOKEN, "expires_in": 3600, "token_type": "Bearer"}
    return HttpResponse(status=status, headers=(), body=json.dumps(payload).encode())


def _provider(path, transport):
    return GoogleCredentials(str(path), transport=transport, now_provider=lambda: NOW)


def test_expired_authorized_user_token_refreshes_with_atomic_private_persistence(tmp_path):
    path = _credentials_file(tmp_path)
    transport = FakeHttpTransport([_response()])
    provider = _provider(path, transport)

    # A reader already holding the old file must see an intact old document
    # after replacement, never an in-place truncate/rewrite.
    with path.open(encoding="utf-8") as previous_file:
        assert provider() == NEW_TOKEN
        assert json.load(previous_file)["token"] == OLD_TOKEN

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["token"] == NEW_TOKEN
    assert saved["refresh_token"] == REFRESH_TOKEN
    assert saved["client_secret"] == CLIENT_SECRET
    expiry = datetime.fromisoformat(saved["expiry"].replace("Z", "+00:00"))
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    assert expiry == NOW + timedelta(hours=1)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert provider.status() == "ready"
    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.method == "POST"
    assert request.url == "https://oauth2.googleapis.com/token"
    form = parse_qs(request.body.decode())
    assert form["grant_type"] == ["refresh_token"]
    assert form["refresh_token"] == [REFRESH_TOKEN]
    assert form["client_id"] == ["test-client-id"]
    assert form["client_secret"] == [CLIENT_SECRET]


def test_provider_refresh_token_rotation_is_saved_for_the_next_refresh(tmp_path):
    path = _credentials_file(tmp_path)
    transport = FakeHttpTransport([
        _response(access_token=NEW_TOKEN, expires_in=3600, token_type="Bearer", refresh_token="test-new-refresh")
    ])

    assert _provider(path, transport)() == NEW_TOKEN

    assert json.loads(path.read_text(encoding="utf-8"))["refresh_token"] == "test-new-refresh"


def test_web_client_migration_preserves_refresh_until_browser_reconnect(tmp_path):
    path = _credentials_file(tmp_path)
    client_path = tmp_path / "web-client.json"
    client_path.write_text(json.dumps({"web": {
        "client_id": "test-web-client-id", "client_secret": "test-web-secret",
    }}))
    transport = FakeHttpTransport([
        _response(),
        _response(access_token="test-web-access", expires_in=3600,
                  refresh_token="test-web-refresh",
                  scope="https://www.googleapis.com/auth/calendar"),
        _response(accessRole="owner"),
        _response(access_token="test-web-refreshed", expires_in=3600),
    ])
    provider = GoogleCredentials(path, client_file=client_path,
                                 transport=transport, now_provider=lambda: NOW)

    assert provider() == NEW_TOKEN
    refresh = parse_qs(transport.requests[0].body.decode())
    assert refresh["client_id"] == ["test-client-id"]
    assert refresh["client_secret"] == [CLIENT_SECRET]
    assert refresh["refresh_token"] == [REFRESH_TOKEN]

    callback = "https://recover.example/calendar/callback"
    consent = provider.authorization_url(state="test-state", challenge="test-challenge",
                                         redirect_uri=callback)
    assert parse_qs(urlsplit(consent).query)["client_id"] == ["test-web-client-id"]
    provider.reconnect(code="test-code", verifier="test-verifier",
                       redirect_uri=callback, calendar_id="primary")
    exchange = parse_qs(transport.requests[1].body.decode())
    assert exchange["client_id"] == ["test-web-client-id"]
    assert json.loads(path.read_text())["client_id"] == "test-web-client-id"

    # After reconnection, the persisted token owns the new client identity.
    assert provider.refresh(rejected_token="test-web-access") == "test-web-refreshed"
    refreshed = parse_qs(transport.requests[3].body.decode())
    assert refreshed["client_id"] == ["test-web-client-id"]
    assert refreshed["client_secret"] == ["test-web-secret"]
    assert refreshed["refresh_token"] == ["test-web-refresh"]


def test_restart_reuses_unexpired_persisted_token_without_http(tmp_path):
    path = _credentials_file(tmp_path)
    first_transport = FakeHttpTransport([_response()])
    assert _provider(path, first_transport)() == NEW_TOKEN
    restarted_transport = FakeHttpTransport()

    restarted = _provider(path, restarted_transport)

    assert restarted() == NEW_TOKEN
    assert restarted.status() == "ready"
    assert restarted_transport.requests == []


def test_concurrent_independent_instances_refresh_the_same_file_only_once(tmp_path):
    path = _credentials_file(tmp_path)
    started, release = Event(), Event()
    requests = []

    def transport(request):
        requests.append(request)
        started.set()
        assert release.wait(timeout=5), "test token endpoint was not released"
        return _response()

    first_provider = _provider(path, transport)
    second_provider = _provider(path, transport)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(first_provider)
        assert started.wait(timeout=5), "first refresh did not reach token endpoint"
        second = pool.submit(second_provider)
        try:
            second.result(timeout=0.1)
        except TimeoutError:
            pass
        finally:
            release.set()
        assert first.result(timeout=5) == NEW_TOKEN
        assert second.result(timeout=5) == NEW_TOKEN

    assert len(requests) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["token"] == NEW_TOKEN


def test_temporary_http_failure_preserves_credentials_without_marking_reauth(tmp_path):
    path = _credentials_file(tmp_path)
    original = path.read_bytes()
    transport = FakeHttpTransport([
        _response(503, error="temporarily_unavailable", error_description="test-sensitive-response"),
        _response(),
    ])
    provider = _provider(path, transport)

    with pytest.raises(CalendarProviderError) as error:
        provider()

    assert "test-sensitive-response" not in str(error.value)
    assert path.read_bytes() == original
    assert provider.status() == "ready"
    assert provider() == NEW_TOKEN
    assert len(transport.requests) == 2


def test_network_failure_preserves_credentials_and_allows_later_refresh(tmp_path):
    path = _credentials_file(tmp_path)
    original = path.read_bytes()
    attempts = []

    def transport(request):
        attempts.append(request)
        if len(attempts) == 1:
            raise CalendarProviderError("calendar HTTP transport failure (TimeoutError)")
        return _response()

    provider = _provider(path, transport)
    with pytest.raises(CalendarProviderError):
        provider()

    assert path.read_bytes() == original
    assert provider.status() == "ready"
    assert provider() == NEW_TOKEN
    assert len(attempts) == 2


def test_invalid_grant_persists_reauth_and_stops_repeated_refresh_requests(
    tmp_path, caplog, capsys
):
    path = _credentials_file(tmp_path)
    response_secret = "test-sensitive-revocation-body"
    transport = FakeHttpTransport([
        _response(400, error="invalid_grant", error_description=response_secret)
    ])
    provider = _provider(path, transport)

    with pytest.raises(CalendarProviderError) as first_error:
        provider()

    assert provider.status() == "reauth_required"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["status"] == "reauth_required"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    restarted = _provider(path, transport)
    assert restarted.status() == "reauth_required"
    with pytest.raises(CalendarProviderError) as second_error:
        restarted()
    assert len(transport.requests) == 1
    captured = capsys.readouterr()
    public_output = " ".join((str(first_error.value), str(second_error.value), caplog.text, captured.out, captured.err))
    for secret in (response_secret, OLD_TOKEN, REFRESH_TOKEN, CLIENT_SECRET):
        assert secret not in public_output


def test_static_raw_access_token_remains_compatible(tmp_path):
    path = tmp_path / "legacy-token"
    path.write_text("test-legacy-access-token\n", encoding="utf-8")
    transport = FakeHttpTransport()
    provider = _provider(path, transport)

    assert provider() == "test-legacy-access-token"
    assert provider.status() == "ready"
    assert transport.requests == []


def test_google_401_refreshes_once_and_replays_with_new_authorization(tmp_path):
    from text_back.calendars.google import GoogleCalendarProvider
    path=_credentials_file(tmp_path,expiry='2026-09-17T16:00:00+00:00')
    oauth=FakeHttpTransport([_response()])
    credentials=_provider(path,oauth)
    api=FakeHttpTransport([HttpResponse(401,(),b'{}'),HttpResponse(200,(),b'{"calendars":{"primary":{"busy":[]}}}')])
    calendar=GoogleCalendarProvider('primary',credentials,api)
    assert calendar.is_free(NOW,NOW+timedelta(hours=1))
    assert dict(api.requests[0].headers)['Authorization']=='Bearer '+OLD_TOKEN
    assert dict(api.requests[1].headers)['Authorization']=='Bearer '+NEW_TOKEN
    assert len(oauth.requests)==1
