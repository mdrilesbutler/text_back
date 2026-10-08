"""Expiring operator invitations for staging credentials without replacing them."""
import argparse
import base64
import fcntl
import hashlib
import hmac
import html
import json
import os
from pathlib import Path
import secrets
import tempfile
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse


SCRIPT = """
const token=location.hash.slice(1);
history.replaceState(null,'',location.pathname);
const form=document.querySelector('form'), status=document.querySelector('#status');
if(!token){status.textContent='Open the private save link supplied for this setup.';form.hidden=true;}
form.addEventListener('submit',async event=>{
 event.preventDefault();const button=form.querySelector('button');button.disabled=true;
 status.textContent='Saving…';
 try {
  const response=await fetch(location.pathname,{method:'POST',credentials:'omit',
   headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},
   body:JSON.stringify({key:document.querySelector('#key').value})});
  if(!response.ok){status.textContent=response.status===401?'This save link expired or was already used. Request a new link.':response.status===409?'A key is already saved. Your setup can continue.':'The key could not be saved. Check that you copied the complete Signing Key.';return;}
  document.querySelector('#key').value='';form.hidden=true;
  status.textContent='Signing key saved. Return to the conversation so setup can continue.';
 } catch {status.textContent='Connection interrupted. Try Save again.';}
 finally {button.disabled=false;}
});
"""
HTML = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Save SignalWire signing key · Recover</title>
<style>body{font:18px/1.5 system-ui,sans-serif;max-width:36rem;margin:10vh auto;padding:24px;color:#18212b;background:#f6f8fa}h1{font-size:30px}label{display:block;margin-top:24px}input,button{box-sizing:border-box;font:inherit;padding:12px;width:100%;margin:8px 0}button{background:#174f38;color:white;border:0;border-radius:6px;cursor:pointer}#status{min-height:3em}</style>
<main><h1>Save your SignalWire signing key</h1>
<p>In your existing SignalWire project, open <strong>API Credentials</strong>.
Find <strong>Signing Key</strong>, click <strong>Show</strong>, then copy it here.</p>
<form><label for="key">Signing Key</label>
<input id="key" type="password" autocomplete="off" autocapitalize="none" spellcheck="false" required minlength="16" maxlength="512">
<button type="submit">Save signing key</button></form>
<p id="status" role="status" aria-live="polite"></p></main>
<script>""" + SCRIPT + '</script></html>'

GOOGLE_SCRIPT = """
const token=location.hash.slice(1);
history.replaceState(null,'',location.pathname);
const form=document.querySelector('form'), status=document.querySelector('#status');
if(!token){status.textContent='Open the private upload link supplied for this setup.';form.hidden=true;}
form.addEventListener('submit',async event=>{
 event.preventDefault();const button=form.querySelector('button');button.disabled=true;
 try {
  const file=document.querySelector('#client').files[0];
  if(!file || file.size>32768){status.textContent='Choose the Google client JSON file (up to 32 KB).';return;}
  let client;
  try {client=JSON.parse(await file.text());}
  catch {status.textContent='That file is not valid JSON. Choose the client file downloaded from Google.';return;}
  status.textContent='Saving…';
  const response=await fetch(location.pathname,{method:'POST',credentials:'omit',
   headers:{'Content-Type':'application/json','Authorization':'Bearer '+token},
   body:JSON.stringify({client})});
  if(!response.ok){status.textContent=response.status===401?'This upload link expired or was already used. Request a new link.':response.status===409?'A client file is already saved. Your setup can continue.':response.status===400?'Use a Web application client with the exact redirect URI shown above. Download its JSON from Google.':'The file could not be saved. Try again.';return;}
  form.reset();form.hidden=true;
  status.textContent='Google client file saved privately. Return to the conversation to finish connecting your calendar.';
 } catch {status.textContent='Connection interrupted. Try Save again.';}
 finally {button.disabled=false;}
});
"""
GOOGLE_HTML = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Connect your calendar · Recover</title>
<style>body{font:18px/1.5 system-ui,sans-serif;max-width:40rem;margin:6vh auto;padding:24px;color:#18212b;background:#f6f8fa}h1{font-size:30px}label{display:block;margin-top:24px}input,button{box-sizing:border-box;font:inherit;padding:12px;width:100%;margin:8px 0}button{background:#174f38;color:white;border:0;border-radius:6px;cursor:pointer}button:disabled{opacity:.6}code{display:block;padding:12px;background:#e8eef0;overflow-wrap:anywhere}#status{min-height:3em}a{color:#174f38}</style>
<main><h1>Connect your calendar</h1>
<p>Save the Google Web application client file here. Your current calendar connection keeps working while setup is completed.</p>
<ol><li>Open <a href="https://console.cloud.google.com/auth/clients" target="_blank" rel="noopener noreferrer">Google Cloud clients</a> and select your existing project.</li>
<li>Create an OAuth client of type <strong>Web application</strong> for Recover.</li>
<li>Add this exact <strong>Authorized redirect URI</strong>:<code>__CALLBACK__</code></li>
<li>Save the client and download its JSON file immediately. Google shows the secret only when the client is created. If you already have the correct Web client JSON saved, you can upload that file instead.</li></ol>
<form><label for="client">Google Web application client JSON</label>
<input id="client" type="file" accept=".json,application/json" required>
<button type="submit">Save client file</button></form>
<p id="status" role="status" aria-live="polite"></p></main>
<script>""" + GOOGLE_SCRIPT + '</script></html>'


def _settings(purpose):
    if purpose == 'signing-key':
        return ('/operator/setup', 'setup-invitation', 'signalwire-signing-key.pending', SCRIPT, HTML, 4096)
    if purpose == 'google-client':
        return ('/operator/setup/google-client', 'google-client-invitation',
                'google-web-client.pending.json', GOOGLE_SCRIPT, GOOGLE_HTML, 32768)
    raise ValueError('Unknown setup purpose')


def _content(payload, purpose, origin):
    if purpose == 'signing-key':
        key = payload.get('key') if isinstance(payload, dict) else None
        if not isinstance(key, str) or not 16 <= len(key) <= 512 or not all(33 <= ord(c) <= 126 for c in key):
            raise HTTPException(400, 'Invalid signing key')
        return key
    client = payload.get('client') if isinstance(payload, dict) else None
    web = client.get('web') if isinstance(client, dict) else None
    if not isinstance(web, dict):
        raise HTTPException(400, 'Google Web application client required')
    for field in ('client_id', 'client_secret'):
        value = web.get(field)
        if not isinstance(value, str) or not 1 <= len(value) <= 1024 or not all(33 <= ord(c) <= 126 for c in value):
            raise HTTPException(400, 'Invalid Google client credentials')
    if not web['client_id'].endswith('.apps.googleusercontent.com'):
        raise HTTPException(400, 'Invalid Google client ID')
    redirects = web.get('redirect_uris')
    if not isinstance(redirects, list) or not all(isinstance(uri, str) for uri in redirects) or origin+'/calendar/callback' not in redirects:
        raise HTTPException(400, 'Required Google redirect URI missing')
    if web.get('auth_uri') not in ('https://accounts.google.com/o/oauth2/auth', 'https://accounts.google.com/o/oauth2/v2/auth') or web.get('token_uri') != 'https://oauth2.googleapis.com/token':
        raise HTTPException(400, 'Invalid Google OAuth endpoints')
    # Save only the known client fields. No arbitrary file paths or token data.
    return json.dumps({'web': {k: web[k] for k in
        ('client_id', 'client_secret', 'auth_uri', 'token_uri', 'redirect_uris')}})


def _write(path, content, *, new=False):
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.setup-')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if new:
            os.link(name, path)  # Atomic publication without replacing an existing key.
        else:
            os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def create_invitation(directory, public_base_url, *, purpose='signing-key'):
    route, grant_name, *_ = _settings(purpose)
    if urlsplit(public_base_url).scheme != 'https':
        raise ValueError('Setup invitations require HTTPS')
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    grant = {'token_hash': hashlib.sha256(token.encode()).hexdigest(),
             'expires_at': (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(), 'used': False}
    _write(directory/(grant_name+'.json'), json.dumps(grant))
    return public_base_url.rstrip('/')+route+'#'+token


def install_routes(app, *, directory, public_base_url):
    for purpose in ('signing-key', 'google-client'):
        _install_route(app, directory=directory, public_base_url=public_base_url, purpose=purpose)


def _install_route(app, *, directory, public_base_url, purpose):
    route, grant_name, target, script, page, max_size = _settings(purpose)
    directory = Path(directory)
    origin = public_base_url.rstrip('/')
    script_hash = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    headers = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
               'X-Content-Type-Options': 'nosniff',
               'Content-Security-Policy': "default-src 'none'; script-src 'sha256-"+script_hash+"'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"}

    @app.get(route, include_in_schema=False)
    def form():
        return HTMLResponse(page.replace('__CALLBACK__', html.escape(origin+'/calendar/callback')), headers=headers)

    @app.post(route, include_in_schema=False)
    async def save(request: Request):
        authorization = request.headers.get('authorization', '')
        if not authorization.startswith('Bearer '):
            raise HTTPException(401, 'Setup invitation required')
        if request.headers.get('origin') != origin:
            raise HTTPException(403, 'Invalid setup origin')
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > max_size:
                raise HTTPException(413, 'Setup request too large')
        try:
            payload = json.loads(body)
        except (ValueError, UnicodeError):
            payload = None
        content = _content(payload, purpose, origin)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(directory/(grant_name+'.lock'), os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, 'r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                grant = json.loads((directory/(grant_name+'.json')).read_text())
                valid = (not grant['used'] and datetime.fromisoformat(grant['expires_at']) > datetime.now(timezone.utc)
                         and hmac.compare_digest(grant['token_hash'], hashlib.sha256(authorization[7:].encode()).hexdigest()))
            except (OSError, ValueError, KeyError, TypeError):
                valid = False
            if not valid:
                raise HTTPException(401, 'Setup invitation expired or used')
            try:
                _write(directory/target, content, new=True)
            except FileExistsError:
                raise HTTPException(409, 'Credential already staged') from None
            except OSError:
                raise HTTPException(503, 'Secure storage unavailable') from None
            grant['used'] = True
            _write(directory/(grant_name+'.json'), json.dumps(grant))
        return {'saved': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--public-base-url', required=True)
    parser.add_argument('--purpose', choices=('signing-key', 'google-client'), default='signing-key')
    args = parser.parse_args()
    print(create_invitation(args.directory, args.public_base_url, purpose=args.purpose))
