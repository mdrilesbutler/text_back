"""Launch the actual ASGI server on a private ephemeral socket, using fakes."""
import base64
import hashlib
import hmac
import os
from pathlib import Path
import socket
import signal
import subprocess
import sys
import time

import httpx


def test_real_server_signed_request_persists_and_restarts(tmp_path):
    root=Path(__file__).resolve().parents[1]
    env={key:value for key,value in os.environ.items() if not key.startswith('TEXT_BACK_')}
    env.update(PYTHONPATH=str(root/'src'),TEXT_BACK_DB_PATH=str(tmp_path/'runtime.db'),
        TEXT_BACK_WEBHOOK_SECRET='test-runtime-signing',TEXT_BACK_PUBLIC_BASE_URL='https://runtime.test',
        TEXT_BACK_TELECOM_MODE='stub',TEXT_BACK_CALENDAR_PROVIDER='stub')
    params={'CallSid':'CA-runtime-smoke','CallStatus':'ringing','From':'+15551112222','To':'+15553334444'}
    signed='https://runtime.test/webhooks/voice'+''.join(key+params[key] for key in sorted(params))
    signature=base64.b64encode(hmac.new(b'test-runtime-signing',signed.encode(),hashlib.sha1).digest()).decode()
    for iteration in range(2):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            port=sock.getsockname()[1]
            process=subprocess.Popen([sys.executable,'-m','uvicorn','text_back.app:create_app','--factory','--fd',str(sock.fileno()),'--no-access-log'],
                pass_fds=(sock.fileno(),),env=env,cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            try:
                with httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=2,trust_env=False) as client:
                    deadline=time.monotonic()+5
                    while True:
                        try:
                            health=client.get('/health')
                            if health.status_code==200 and health.json()['worker_running']:
                                break
                        except httpx.TransportError:
                            pass
                        assert process.poll() is None,'server exited before readiness'
                        assert time.monotonic()<deadline,'server did not become ready'
                        time.sleep(0.02)
                    assert client.post('/webhooks/voice',data=params).status_code==403
                    result=client.post('/webhooks/voice',data=params,headers={'X-Twilio-Signature':signature})
                    assert result.status_code==200
                    assert result.json()['duplicate'] is bool(iteration)
                    assert client.get('/health').json()['sms_queue']['sent']==1
            finally:
                process.terminate()
                _, logs = process.communicate(timeout=10)
            assert process.returncode in (0, -signal.SIGTERM)
            assert b"Application shutdown complete" in logs
