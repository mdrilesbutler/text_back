import json
import stat
import pytest
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from text_back.setup_intake import create_invitation, install_routes

ORIGIN = 'https://pilot.example'


def fixture(tmp_path):
    app = FastAPI()
    install_routes(app, directory=tmp_path, public_base_url=ORIGIN)
    link = create_invitation(tmp_path, ORIGIN)
    token = link.split('#')[1]
    return TestClient(app, base_url=ORIGIN), token


def test_intake_requires_token_and_same_origin(tmp_path):
    client, token = fixture(tmp_path)
    body = {'key': 'example-signing-key-for-test'}
    assert client.post('/operator/setup', json=body).status_code == 401
    headers = {'Authorization': 'Bearer '+token, 'Origin': 'https://other.example'}
    assert client.post('/operator/setup', json=body, headers=headers).status_code == 403
    headers = {'Authorization': 'Bearer wrong-token', 'Origin': ORIGIN}
    assert client.post('/operator/setup', json=body, headers=headers).status_code == 401
    assert not (tmp_path/'signalwire-signing-key.pending').exists()


def test_key_saved_privately_once_without_echo(tmp_path):
    client, token = fixture(tmp_path)
    headers = {'Authorization': 'Bearer '+token, 'Origin': ORIGIN}
    key = 'example-signing-key-for-test'
    response = client.post('/operator/setup', json={'key': key}, headers=headers)
    assert response.status_code == 200
    assert key not in response.text
    saved = tmp_path/'signalwire-signing-key.pending'
    assert saved.read_text() == key
    assert stat.S_IMODE(saved.stat().st_mode) == 0o600
    assert client.post('/operator/setup', json={'key': 'different-key-12345'}, headers=headers).status_code == 401
    assert saved.read_text() == key
    restarted = FastAPI()
    install_routes(restarted, directory=tmp_path, public_base_url=ORIGIN)
    with TestClient(restarted, base_url=ORIGIN) as other:
        assert other.post('/operator/setup', json={'key': key}, headers=headers).status_code == 401


def test_expiry_and_invalid_input_do_not_write(tmp_path):
    client, token = fixture(tmp_path)
    headers = {'Authorization': 'Bearer '+token, 'Origin': ORIGIN}
    for value in ['short', 'line\nbreak' * 5, {'not': 'a string'}, 'x'*513]:
        assert client.post('/operator/setup', json={'key': value}, headers=headers).status_code == 400
    assert client.post('/operator/setup', content=b'x'*4097, headers=headers).status_code == 413
    grant_path = tmp_path/'setup-invitation.json'
    grant = json.loads(grant_path.read_text())
    grant['expires_at'] = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    grant_path.write_text(json.dumps(grant))
    assert client.post('/operator/setup', json={'key': 'valid-but-expired-key'}, headers=headers).status_code == 401
    assert not (tmp_path/'signalwire-signing-key.pending').exists()


def test_form_uses_fragment_and_no_third_party_assets(tmp_path):
    client, token = fixture(tmp_path)
    response = client.get('/operator/setup')
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert "frame-ancestors 'none'" in response.headers['content-security-policy']
    assert token not in response.text
    assert 'location.hash' in response.text
    assert 'history.replaceState' in response.text


def test_existing_staged_key_is_not_overwritten(tmp_path):
    client, token = fixture(tmp_path)
    path = tmp_path/'signalwire-signing-key.pending'
    path.write_text('already-saved-key')
    headers = {'Authorization': 'Bearer '+token, 'Origin': ORIGIN}
    assert client.post('/operator/setup', json={'key': 'replacement-signing-key'}, headers=headers).status_code == 409
    assert path.read_text() == 'already-saved-key'


GOOGLE_ROUTE = '/operator/setup/google-client'


def google_client():
    return {'web': {'client_id': 'test.apps.googleusercontent.com',
                    'client_secret': 'test-client-secret',
                    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                    'token_uri': 'https://oauth2.googleapis.com/token',
                    'redirect_uris': [ORIGIN+'/calendar/callback']}}


def google_fixture(tmp_path):
    app = FastAPI()
    install_routes(app, directory=tmp_path, public_base_url=ORIGIN)
    link = create_invitation(tmp_path, ORIGIN, purpose='google-client')
    return TestClient(app, base_url=ORIGIN), link.split('#')[1]


def test_google_client_saved_once_without_replacing_current_token(tmp_path):
    client, token = google_fixture(tmp_path)
    active = tmp_path/'google_token.json'
    active.write_text('existing-token-untouched')
    headers = {'Authorization': 'Bearer '+token, 'Origin': ORIGIN}
    payload = {'client': google_client()}
    response = client.post(GOOGLE_ROUTE, json=payload, headers=headers)
    assert response.status_code == 200
    assert 'test-client-secret' not in response.text
    saved = tmp_path/'google-web-client.pending.json'
    assert json.loads(saved.read_text()) == payload['client']
    assert stat.S_IMODE(saved.stat().st_mode) == 0o600
    assert active.read_text() == 'existing-token-untouched'
    restarted = FastAPI()
    install_routes(restarted, directory=tmp_path, public_base_url=ORIGIN)
    other = TestClient(restarted, base_url=ORIGIN)
    assert other.post(GOOGLE_ROUTE, json=payload, headers=headers).status_code == 401


def test_invitation_cannot_cross_credential_purposes(tmp_path):
    client, signing_token = fixture(tmp_path)
    google_token = create_invitation(tmp_path, ORIGIN, purpose='google-client').split('#')[1]
    assert client.post(GOOGLE_ROUTE, json={'client': google_client()}, headers={
        'Authorization': 'Bearer '+signing_token, 'Origin': ORIGIN}).status_code == 401
    assert client.post('/operator/setup', json={'key': 'valid-test-signing-key'}, headers={
        'Authorization': 'Bearer '+google_token, 'Origin': ORIGIN}).status_code == 401
    assert not (tmp_path/'google-web-client.pending.json').exists()
    assert not (tmp_path/'signalwire-signing-key.pending').exists()
    assert client.post(GOOGLE_ROUTE, json={'client': google_client()}, headers={
        'Authorization': 'Bearer '+google_token, 'Origin': ORIGIN}).status_code == 200


@pytest.mark.parametrize('change', [
    {'client_id': ''}, {'client_secret': 'line\nbreak'},
    {'redirect_uris': ['https://wrong.example/calendar/callback']},
    {'redirect_uris': ORIGIN+'/calendar/callback'},
    {'token_uri': 'https://wrong.example/token'}, {'auth_uri': 'http://accounts.google.com'},
])
def test_invalid_google_file_does_not_consume_invitation(tmp_path, change):
    client, token = google_fixture(tmp_path)
    value = google_client()
    value['web'].update(change)
    headers = {'Authorization': 'Bearer '+token, 'Origin': ORIGIN}
    assert client.post(GOOGLE_ROUTE, json={'client': value}, headers=headers).status_code == 400
    assert not (tmp_path/'google-web-client.pending.json').exists()
    assert client.post(GOOGLE_ROUTE, json={'client': google_client()}, headers=headers).status_code == 200


def test_google_intake_rejects_desktop_client_expiry_and_wrong_origin(tmp_path):
    client, token = google_fixture(tmp_path)
    headers = {'Authorization': 'Bearer '+token, 'Origin': ORIGIN}
    desktop = {'installed': google_client()['web']}
    assert client.post(GOOGLE_ROUTE, json={'client': desktop}, headers=headers).status_code == 400
    assert client.post(GOOGLE_ROUTE, content=b'x'*32769, headers=headers).status_code == 413
    assert client.post(GOOGLE_ROUTE, json={'client': google_client()}, headers={
        **headers, 'Origin': 'https://other.example'}).status_code == 403
    grant_path = tmp_path/'google-client-invitation.json'
    grant = json.loads(grant_path.read_text())
    grant['expires_at'] = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    grant_path.write_text(json.dumps(grant))
    assert client.post(GOOGLE_ROUTE, json={'client': google_client()}, headers=headers).status_code == 401
    assert not (tmp_path/'google-web-client.pending.json').exists()


def test_google_client_existing_file_and_page_privacy(tmp_path):
    client, token = google_fixture(tmp_path)
    saved = tmp_path/'google-web-client.pending.json'
    saved.write_text('previous-client')
    response = client.post(GOOGLE_ROUTE, json={'client': google_client()}, headers={
        'Authorization': 'Bearer '+token, 'Origin': ORIGIN})
    assert response.status_code == 409
    assert saved.read_text() == 'previous-client'
    page = client.get(GOOGLE_ROUTE)
    assert page.headers['cache-control'] == 'no-store'
    assert page.headers['referrer-policy'] == 'no-referrer'
    assert "frame-ancestors 'none'" in page.headers['content-security-policy']
    assert token not in page.text
    assert ORIGIN+'/calendar/callback' in page.text
    assert 'type="file"' in page.text
