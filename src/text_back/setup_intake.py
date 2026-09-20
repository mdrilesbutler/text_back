"""Optional, expiring operator invitation for staging an existing signing key."""
import argparse
import base64
import fcntl
import hashlib
import hmac
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


def create_invitation(directory, public_base_url):
    if urlsplit(public_base_url).scheme != 'https':
        raise ValueError('Setup invitations require HTTPS')
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    grant = {'token_hash': hashlib.sha256(token.encode()).hexdigest(),
             'expires_at': (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(), 'used': False}
    _write(directory/'setup-invitation.json', json.dumps(grant))
    return public_base_url.rstrip('/')+'/operator/setup#'+token


def install_routes(app, *, directory, public_base_url):
    directory = Path(directory)
    origin = public_base_url.rstrip('/')
    script_hash = base64.b64encode(hashlib.sha256(SCRIPT.encode()).digest()).decode()
    headers = {'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
               'X-Content-Type-Options': 'nosniff',
               'Content-Security-Policy': "default-src 'none'; script-src 'sha256-"+script_hash+"'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"}

    @app.get('/operator/setup', include_in_schema=False)
    def form():
        return HTMLResponse(HTML, headers=headers)

    @app.post('/operator/setup', include_in_schema=False)
    async def save(request: Request):
        authorization = request.headers.get('authorization', '')
        if not authorization.startswith('Bearer '):
            raise HTTPException(401, 'Setup invitation required')
        if request.headers.get('origin') != origin:
            raise HTTPException(403, 'Invalid setup origin')
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 4096:
                raise HTTPException(413, 'Setup request too large')
        try:
            payload = json.loads(body)
            key = payload.get('key') if isinstance(payload, dict) else None
        except (ValueError, UnicodeError):
            key = None
        if not isinstance(key, str) or not 16 <= len(key) <= 512 or not all(33 <= ord(c) <= 126 for c in key):
            raise HTTPException(400, 'Invalid signing key')
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(directory/'setup-invitation.lock', os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, 'r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                grant = json.loads((directory/'setup-invitation.json').read_text())
                valid = (not grant['used'] and datetime.fromisoformat(grant['expires_at']) > datetime.now(timezone.utc)
                         and hmac.compare_digest(grant['token_hash'], hashlib.sha256(authorization[7:].encode()).hexdigest()))
            except (OSError, ValueError, KeyError, TypeError):
                valid = False
            if not valid:
                raise HTTPException(401, 'Setup invitation expired or used')
            try:
                _write(directory/'signalwire-signing-key.pending', key, new=True)
            except FileExistsError:
                raise HTTPException(409, 'Signing key already staged') from None
            except OSError:
                raise HTTPException(503, 'Secure storage unavailable') from None
            grant['used'] = True
            _write(directory/'setup-invitation.json', json.dumps(grant))
        return {'saved': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--public-base-url', required=True)
    args = parser.parse_args()
    print(create_invitation(args.directory, args.public_base_url))
