from datetime import datetime, timezone
import time

from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.sms import enqueue_sms
from text_back.store import Store
from text_back.telecom import FakeTelecom

NOW = datetime(2026, 9, 17, 14, tzinfo=timezone.utc)


def test_lifespan_drains_persisted_backlog_and_stops(tmp_path):
    path = str(tmp_path / 'worker.db')
    store = Store(path)
    enqueue_sms(store=store, key='persisted', to='+15551112222', from_number='+15553334444', body='Test', kind='field_prompt', now=NOW)
    store.conn.close()
    telecom = FakeTelecom()
    app = create_app(db_path=path, telecom=telecom, now_provider=lambda: NOW, worker_interval_seconds=0.01)
    with TestClient(app) as client:
        deadline = time.monotonic() + 2
        while not telecom.outbound and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(telecom.outbound) == 1
        assert client.get('/health').json()['worker_running'] is True
    assert app.state.worker_task.done()
    restarted = Store(path)
    assert restarted.get_sms('persisted')['status'] == 'sent'


def test_worker_isolates_lane_failure(monkeypatch):
    import text_back.worker as worker
    from text_back.delivery import InMemoryDeliveryTransport
    from text_back.handoff import HandoffAlert
    from text_back.delivery import enqueue_handoff_alert
    app = create_app(telecom=FakeTelecom(), now_provider=lambda: NOW, delivery_transport=InMemoryDeliveryTransport())
    enqueue_handoff_alert(store=app.state.store, alert_id='a', now=NOW,
        alert=HandoffAlert('queue','+15551112222','+15553334444','safety','help',{},'help'))
    def broken(**kwargs):
        raise RuntimeError('do not leak customer content')
    monkeypatch.setattr(worker, 'run_due_followups', broken)
    worker.run_once(app.state)
    assert app.state.store.get_handoff_delivery('a')['status'] == 'delivered'
    assert app.state.worker_errors == ['followups']
