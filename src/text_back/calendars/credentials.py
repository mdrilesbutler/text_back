"""Google authorized-user credentials with serialized refresh and atomic writes."""
from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from urllib.parse import urlencode

from text_back.calendars.protocol import CalendarProviderError
from text_back.calendars.transport import HttpRequest, urllib_transport

TOKEN_URL = 'https://oauth2.googleapis.com/token'
CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar'


class GoogleCredentials:
    def __init__(self, path, *, transport=urllib_transport, now_provider=None, client_file=None):
        self.path = Path(path)
        self.transport = transport
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self.client_file = client_file

    def _read(self):
        try:
            raw = self.path.read_text().strip()
            if not raw:
                raise ValueError()
            if raw.startswith('{'):
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError()
                return data
            return {'token': raw, 'legacy': True}
        except (OSError, ValueError):
            raise CalendarProviderError('calendar credentials unavailable') from None

    @contextmanager
    def _locked(self):
        try:
            fd = os.open(str(self.path) + '.lock', os.O_CREAT | os.O_RDWR, 0o600)
        except OSError:
            raise CalendarProviderError('calendar credential lock unavailable') from None
        with os.fdopen(fd, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def _write(self, data):
        name = None
        try:
            fd, name = tempfile.mkstemp(dir=self.path.parent, prefix='.google-')
            with os.fdopen(fd, 'w') as output:
                json.dump(data, output)
                output.flush()
                os.fsync(output.fileno())
            os.replace(name, self.path)
            directory = os.open(self.path.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            raise CalendarProviderError('calendar credential persistence failed') from None
        finally:
            if name and os.path.exists(name):
                os.unlink(name)

    def status(self):
        return self._read().get('status', 'ready')

    def _client(self, data, *, for_refresh=False):
        if self.client_file and not for_refresh:
            try:
                client = json.loads(Path(self.client_file).read_text())
                data = client.get('web') or client.get('installed') or client
            except (OSError, ValueError):
                raise CalendarProviderError('Google OAuth client unavailable') from None
        if not data.get('client_id') or not data.get('client_secret'):
            raise CalendarProviderError('Google OAuth client configuration required')
        return {k: data[k] for k in ('client_id', 'client_secret')}

    def __call__(self):
        return self.refresh()

    def refresh(self, rejected_token=None):
        with self._locked():
            data = self._read()
            if data.get('status') == 'reauth_required':
                raise CalendarProviderError('calendar reauth_required')
            token = data.get('token') or data.get('access_token')
            if data.get('legacy'):
                if rejected_token:
                    raise CalendarProviderError('calendar static token requires replacement')
                return token
            try:
                expiry = datetime.fromisoformat(data.get('expiry', '').replace('Z', '+00:00'))
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
            except ValueError:
                expiry = self.now_provider()
            if token and expiry > self.now_provider() + timedelta(seconds=60) and (not rejected_token or token != rejected_token):
                return token
            if not data.get('refresh_token'):
                data['status'] = 'reauth_required'
                self._write(data)
                raise CalendarProviderError('calendar reauth_required')
            # Refresh tokens belong to the client that issued them. A configured
            # Web client takes over only after a successful browser reconnect.
            payload = self._token_request({**self._client(data, for_refresh=True), 'grant_type':'refresh_token', 'refresh_token':data['refresh_token']}, data)
            self._save_token(data, payload)
            return payload['access_token']

    def _token_request(self, form, current=None):
        response = self.transport(HttpRequest('POST', TOKEN_URL,
            (('Content-Type','application/x-www-form-urlencoded'),), urlencode(form).encode()))
        try:
            payload = json.loads(response.body)
        except ValueError:
            raise CalendarProviderError('Google OAuth response malformed') from None
        if not isinstance(payload, dict):
            raise CalendarProviderError('Google OAuth response malformed')
        if response.status != 200:
            if response.status == 400 and payload.get('error') == 'invalid_grant' and current is not None:
                current['status'] = 'reauth_required'
                self._write(current)
                raise CalendarProviderError('calendar reauth_required')
            raise CalendarProviderError(f'Google OAuth returned HTTP {response.status}')
        if not isinstance(payload.get('access_token'), str) or not payload['access_token']:
            raise CalendarProviderError('Google OAuth access token missing')
        if not isinstance(payload.get('expires_in'), (int, float)) or payload['expires_in'] <= 0:
            raise CalendarProviderError('Google OAuth expiry missing')
        return payload

    def _save_token(self, data, payload):
        data.update(token=payload['access_token'], expiry=(self.now_provider()+timedelta(seconds=payload['expires_in'])).isoformat(), status='ready')
        if payload.get('refresh_token'):
            data['refresh_token'] = payload['refresh_token']
        self._write(data)

    def authorization_url(self, *, state, challenge, redirect_uri):
        client = self._client(self._read())
        return 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(dict(
            client_id=client['client_id'], redirect_uri=redirect_uri, response_type='code',
            scope=CALENDAR_SCOPE, access_type='offline', prompt='consent', state=state,
            code_challenge=challenge, code_challenge_method='S256'))

    def reconnect(self, *, code, verifier, redirect_uri, calendar_id=None):
        """Exchange the browser consent code and save the new credentials.

        Returns the calendars the account can write to, as
        ``[{"id", "summary", "primary"}]``. With ``calendar_id`` given (the
        operator reconnect path) the configured calendar must be among them, so
        an unrelated account can never replace this client's credentials. With
        ``calendar_id=None`` (the owner connecting from the settings page) any
        account with at least one writable calendar is accepted and the caller
        picks the calendar from the returned list.
        """
        with self._locked():
            data = self._read()
            client = self._client(data)
            payload = self._token_request({**client, 'grant_type':'authorization_code', 'code':code,
                                          'redirect_uri':redirect_uri, 'code_verifier':verifier})
            if not payload.get('refresh_token') or CALENDAR_SCOPE not in payload.get('scope', '').split():
                raise CalendarProviderError('Google Calendar offline access was not granted')
            calendars = self._writable_calendars(payload['access_token'])
            if calendar_id is not None and calendar_id not in {entry['id'] for entry in calendars}:
                raise CalendarProviderError('Google account cannot write the configured calendar')
            if not calendars:
                raise CalendarProviderError('Google account has no calendar it can write to')
            data.update(client)
            data.pop('legacy', None)
            self._save_token(data, payload)
            return calendars

    def _writable_calendars(self, access_token):
        """List the account's calendars with owner/writer access (bounded pagination, no secrets in errors)."""
        calendars = []
        page_token = None
        for _ in range(10):
            query = {'minAccessRole': 'writer', 'maxResults': '250'}
            if page_token:
                query['pageToken'] = page_token
            response = self.transport(HttpRequest('GET', 'https://www.googleapis.com/calendar/v3/users/me/calendarList?' + urlencode(query),
                (('Authorization', 'Bearer ' + access_token),)))
            try:
                body = json.loads(response.body)
            except ValueError:
                raise CalendarProviderError('Google calendar verification failed') from None
            if response.status != 200 or not isinstance(body, dict) or not isinstance(body.get('items'), list):
                raise CalendarProviderError('Google calendar list could not be read')
            for item in body['items']:
                if not isinstance(item, dict) or not isinstance(item.get('id'), str):
                    continue
                if item.get('accessRole') not in ('owner', 'writer') or item.get('deleted'):
                    continue
                calendars.append({'id': item['id'], 'summary': str(item.get('summaryOverride') or item.get('summary') or item['id']),
                                  'primary': bool(item.get('primary'))})
            page_token = body.get('nextPageToken')
            if not page_token:
                break
        return calendars
