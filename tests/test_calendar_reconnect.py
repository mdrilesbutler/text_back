import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit
from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.calendars.credentials import GoogleCredentials, CALENDAR_SCOPE
from text_back.calendars.google import GoogleCalendarProvider
from text_back.calendars.transport import FakeHttpTransport, HttpResponse

NOW=datetime(2026,9,17,14,tzinfo=timezone.utc)


def fixture(tmp_path, monkeypatch):
    path=tmp_path/'token.json'
    path.write_text(json.dumps(dict(token='expired',refresh_token='old-refresh',client_id='client',client_secret='secret',status='reauth_required')))
    responses=FakeHttpTransport([
        HttpResponse(200,(),json.dumps(dict(access_token='new-access',refresh_token='new-refresh',expires_in=3600,scope=CALENDAR_SCOPE)).encode()),
        HttpResponse(200,(),json.dumps(dict(items=[dict(id='business@example.test',summary='Business',accessRole='owner',primary=True)])).encode())])
    credentials=GoogleCredentials(str(path),transport=responses,now_provider=lambda:NOW)
    calendar=GoogleCalendarProvider('business@example.test',credentials,responses)
    monkeypatch.setenv('TEXT_BACK_OPERATOR_API_KEY','test-operator-key')
    app=create_app(public_base_url='https://example.test',calendar=calendar,now_provider=lambda:NOW)
    return TestClient(app),credentials,responses


def test_reconnect_requires_admin_and_binds_callback_to_browser_and_single_use(tmp_path,monkeypatch):
    client,credentials,transport=fixture(tmp_path,monkeypatch)
    assert client.post('/operator/calendar/reconnect').status_code==401
    link=client.post('/operator/calendar/reconnect',headers={'Authorization':'Bearer test-operator-key'}).json()['url']
    response=client.get(link,follow_redirects=False)
    assert response.status_code==303
    params=parse_qs(urlsplit(response.headers['location']).query)
    assert params['access_type']==['offline']
    assert params['code_challenge_method']==['S256']
    state=params['state'][0]
    wrong=client.get('/calendar/callback',params={'state':'forged','code':'code'})
    assert wrong.status_code==400
    # TestClient's secure cookie needs HTTPS request base.
    cookie=response.cookies.get('text_back_oauth')
    good=client.get('https://example.test/calendar/callback',params={'state':state,'code':'code'},headers={'Cookie':f'text_back_oauth={cookie}'})
    assert good.status_code==200
    assert credentials.status()=='ready'
    assert credentials()=='new-access'
    assert client.get('https://example.test/calendar/callback',params={'state':state,'code':'code'},headers={'Cookie':f'text_back_oauth={cookie}'}).status_code==400
    assert len(transport.requests)==2
    assert 'new-access' not in good.text


def test_callback_without_browser_cookie_cannot_replace_credentials(tmp_path,monkeypatch):
    client,credentials,transport=fixture(tmp_path,monkeypatch)
    link=client.post('/operator/calendar/reconnect',headers={'Authorization':'Bearer test-operator-key'}).json()['url']
    response=client.get(link,follow_redirects=False)
    state=parse_qs(urlsplit(response.headers['location']).query)['state'][0]
    client.cookies.clear()
    result=client.get('/calendar/callback',params={'state':state,'code':'code'})
    assert result.status_code==400
    assert credentials.status()=='reauth_required'
    assert not transport.requests


def test_an_account_without_the_configured_calendar_cannot_replace_credentials(tmp_path,monkeypatch):
    client,credentials,transport=fixture(tmp_path,monkeypatch)
    transport.responses[1]=HttpResponse(200,(),json.dumps(dict(items=[dict(id='someone@else.test',summary='Other',accessRole='owner',primary=True)])).encode())
    link=client.post('/operator/calendar/reconnect',headers={'Authorization':'Bearer test-operator-key'}).json()['url']
    response=client.get(link,follow_redirects=False)
    state=parse_qs(urlsplit(response.headers['location']).query)['state'][0]
    cookie=response.cookies.get('text_back_oauth')
    bad=client.get('https://example.test/calendar/callback',params={'state':state,'code':'code'},headers={'Cookie':f'text_back_oauth={cookie}'})
    assert bad.status_code==400
    assert credentials.status()=='reauth_required'
