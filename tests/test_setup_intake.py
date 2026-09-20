import json
import stat
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
