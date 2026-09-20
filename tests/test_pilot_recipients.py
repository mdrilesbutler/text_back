import base64
import hashlib
import hmac

import httpx
import pytest
from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.config import load_config
from text_back.telecom import SignalWireTelecom, TelecomError


def sign(url, params):
    raw = url + ''.join(k+v for k,v in sorted(params.items()))
    return base64.b64encode(hmac.new(b'test-key', raw.encode(), hashlib.sha1).digest()).decode()


@pytest.mark.parametrize('allowlist', ['', '+15551112222'])
@pytest.mark.parametrize('kind', ['voice', 'sms'])
def test_unapproved_inbound_does_not_create_work(monkeypatch, allowlist, kind):
    monkeypatch.setenv('TEXT_BACK_PILOT_RECIPIENTS', allowlist)
    app = create_app(webhook_secret='test-key', public_base_url='https://pilot.example')
    params = {'From': '+15559998888', 'To': '+15553334444'}
    params.update({'CallSid': 'CA-test', 'CallStatus': 'ringing'} if kind=='voice'
                  else {'MessageSid': 'SM-test', 'Body': 'hello'})
    with TestClient(app) as client:
        response = client.post('/webhooks/'+kind, data=params,
            headers={'X-Twilio-Signature': sign('https://pilot.example/webhooks/'+kind, params)})
        assert response.status_code == 200
        assert response.text == '<Response />'
        assert app.state.telecom.outbound == []
        assert app.state.store.conn.execute('SELECT count(*) FROM inbound_jobs').fetchone()[0] == 0
        assert app.state.store.conn.execute('SELECT count(*) FROM sms_outbox').fetchone()[0] == 0


def test_allowed_recipient_still_gets_intro(monkeypatch):
    monkeypatch.setenv('TEXT_BACK_PILOT_RECIPIENTS', '+15551112222')
    app = create_app(webhook_secret='test-key', public_base_url='https://pilot.example')
    params = {'From': '+15551112222', 'To': '+15553334444', 'CallSid': 'CA-allowed', 'CallStatus': 'ringing'}
    with TestClient(app) as client:
        assert client.post('/webhooks/voice', data=params,
            headers={'X-Twilio-Signature': sign('https://pilot.example/webhooks/voice', params)}).status_code == 200
        assert len(app.state.telecom.outbound) == 1


def test_transport_blocks_queued_unapproved_sends_before_http():
    requests = []
    client = httpx.Client(transport=httpx.MockTransport(lambda req: requests.append(req)))
    telecom = SignalWireTelecom(space_url='https://pilot.signalwire.com', project_id='project',
        api_token='token', allowed_from_number='+15553334444', client=client,
        allowed_to_numbers=('+15551112222',))
    with pytest.raises(TelecomError, match='approved pilot'):
        telecom.send_sms_with_callback(to='+15559998888', from_number='+15553334444',
            body='never send', kind='followup', callback_url='https://pilot.example/status')
    assert requests == []


def test_invalid_recipient_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv('TEXT_BACK_PILOT_RECIPIENTS', '555-111-2222')
    with pytest.raises(ValueError, match='E.164'):
        load_config()
