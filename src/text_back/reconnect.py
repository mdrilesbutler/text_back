"""Customer calendar reconnection, separated from host/operator OAuth repair."""
import asyncio
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from text_back.calendars.credentials import GoogleCredentials
from text_back.calendars.protocol import CalendarProviderError
from text_back.delivery import enqueue_handoff_alert
from text_back.handoff import HandoffAlert


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _now(state):
    return state.now_provider() if state.now_provider else datetime.now(timezone.utc)


def _credentials(state):
    credentials = getattr(state.calendar, 'token_provider', None)
    if not isinstance(credentials, GoogleCredentials):
        raise HTTPException(409, 'Google calendar reconnection is unavailable')
    return credentials


def create_link(state, purpose='operator', ttl=timedelta(days=1)):
    """Single-use link that starts Google consent. purpose='operator' reconnects the
    configured calendar; purpose='client' lets the signed-in owner connect any
    account and pick a calendar afterwards (see client_settings)."""
    token = secrets.token_urlsafe(32)
    now = _now(state)
    with state.store.transaction():
        state.store.conn.execute('INSERT INTO calendar_reconnect_links(token_hash,expires_at,purpose) VALUES(?,?,?)',
            (_hash(token),(now+ttl).isoformat(),purpose))
    return state.public_base_url+'/calendar/connect?token='+token


def maintain_credentials(state):
    credentials = getattr(state.calendar, 'token_provider', None)
    if not isinstance(credentials, GoogleCredentials):
        return
    now = _now(state)
    if state.calendar_check_at and now < state.calendar_check_at:
        return
    state.calendar_check_at = now + timedelta(minutes=1)
    try:
        credentials()
    except CalendarProviderError:
        if credentials.status() != 'reauth_required':
            raise
    if credentials.status() != 'reauth_required':
        return
    with state.store.transaction():
        active=state.store.conn.execute('SELECT 1 FROM calendar_reconnect_links WHERE used=0 AND expires_at>?',(now.isoformat(),)).fetchone()
        if active:
            return
        url=create_link(state)
        alert_id='calendar-reauth:'+secrets.token_hex(16)
        enqueue_handoff_alert(store=state.store, alert_id=alert_id, now=now,
            alert=HandoffAlert(destination=state.handoff_destination, caller='calendar-owner',
                business_number=state.business_number,reason='calendar_reauth_required',latest_message='',
                collected_fields={},summary='Reconnect your business calendar to resume booking: '+url))


def install_routes(app):
    def authorize(request):
        configured=app.state.operator_api_key
        if not configured or not hmac.compare_digest(request.headers.get('Authorization',''), 'Bearer '+configured):
            raise HTTPException(401,'Operator authentication required')

    @app.get('/operator/handoffs')
    def operator_handoffs(request: Request):
        authorize(request)
        import json
        with app.state.store.lock:
            rows=app.state.store.conn.execute('SELECT alert_id,status,payload_json FROM handoff_deliveries ORDER BY created_at DESC LIMIT 100').fetchall()
        return {'alerts':[{'alert_id':row['alert_id'],'status':row['status'],'alert':json.loads(row['payload_json'])} for row in rows]}

    @app.post('/operator/calendar/reconnect')
    def reconnect_link(request: Request):
        configured=app.state.operator_api_key
        supplied=request.headers.get('Authorization','')
        if not configured or not hmac.compare_digest(supplied,'Bearer '+configured):
            raise HTTPException(401,'Operator authentication required')
        _credentials(app.state)
        return {'url':create_link(app.state)}

    @app.get('/calendar/connect')
    def connect(token: str):
        state=app.state
        credentials=_credentials(state)
        now=_now(state)
        oauth_state=secrets.token_urlsafe(32)
        verifier=secrets.token_urlsafe(48)
        cookie=secrets.token_urlsafe(32)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        # Validate OAuth client configuration before consuming the invitation.
        try:
            url=credentials.authorization_url(state=oauth_state,challenge=challenge,redirect_uri=state.public_base_url+'/calendar/callback')
        except CalendarProviderError:
            raise HTTPException(503,'Calendar connection is not configured') from None
        with state.store.transaction():
            link=state.store.conn.execute('SELECT purpose FROM calendar_reconnect_links WHERE token_hash=? AND used=0 AND expires_at>?',(_hash(token),now.isoformat())).fetchone()
            if link is None:
                raise HTTPException(400,'Connection link expired or already used')
            state.store.conn.execute('UPDATE calendar_reconnect_links SET used=1 WHERE token_hash=?',(_hash(token),))
            state.store.conn.execute('INSERT INTO calendar_oauth_states(state_hash,cookie_hash,verifier,expires_at,purpose) VALUES(?,?,?,?,?)',
                (_hash(oauth_state),_hash(cookie),verifier,(now+timedelta(minutes=15)).isoformat(),link['purpose']))
        response=RedirectResponse(url,status_code=303,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
        response.set_cookie('text_back_oauth',cookie,secure=True,httponly=True,samesite='lax',max_age=900,path='/calendar/callback')
        return response

    @app.get('/calendar/callback')
    async def callback(request: Request, state: str='', code: str='', error: str=''):
        app_state=app.state
        now=_now(app_state)
        cookie=request.cookies.get('text_back_oauth','')
        with app_state.store.transaction():
            row=app_state.store.conn.execute('SELECT * FROM calendar_oauth_states WHERE state_hash=? AND used=0 AND expires_at>?',(_hash(state),now.isoformat())).fetchone()
            if not row or not cookie or not hmac.compare_digest(row['cookie_hash'],_hash(cookie)):
                raise HTTPException(400,'Calendar connection session expired or invalid')
            app_state.store.conn.execute('UPDATE calendar_oauth_states SET used=1 WHERE state_hash=?',(_hash(state),))
        owner_flow = row['purpose'] == 'client'
        if error or not code:
            if owner_flow:
                return _back_to_settings(app_state, error='access')  # client_settings.CALENDAR_ERRORS
            raise HTTPException(400,'Calendar permission was not granted; request a new connection link')
        try:
            # The owner may connect any account and pick a calendar next; the operator
            # path must keep the configured calendar.
            calendars = await asyncio.to_thread(_credentials(app_state).reconnect,code=code,verifier=row['verifier'],
                redirect_uri=app_state.public_base_url+'/calendar/callback',
                calendar_id=None if owner_flow else app_state.calendar.calendar_id)
        except CalendarProviderError:
            if owner_flow:
                return _back_to_settings(app_state, error='no_calendar')
            raise HTTPException(400,'Calendar connection could not be verified; request a new link') from None
        with app_state.store.transaction():
            app_state.store.conn.execute("UPDATE handoff_deliveries SET status='cancelled' WHERE alert_id LIKE 'calendar-reauth:%' AND status='pending'")
        if owner_flow:
            from text_back.client_settings import remember_calendars
            remember_calendars(app_state, calendars, now)
            return _back_to_settings(app_state)
        response=HTMLResponse('<h1>Calendar connected</h1><p>Your scheduling assistant can book appointments again. You can close this page.</p>',headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
        response.delete_cookie('text_back_oauth',path='/calendar/callback')
        return response

    def _back_to_settings(app_state, error=''):
        from urllib.parse import urlencode
        target='/client/calendar'+('?'+urlencode({'error':error}) if error else '')
        response=RedirectResponse(target,status_code=303,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
        response.delete_cookie('text_back_oauth',path='/calendar/callback')
        return response
