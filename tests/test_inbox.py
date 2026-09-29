from datetime import datetime, timedelta, timezone
import pytest

from text_back.app import create_app
from text_back.inbox import submit_event, run_due_inbound
from text_back.telecom import FakeTelecom
from text_back.store import Store

NOW = datetime(2026,9,17,14,tzinfo=timezone.utc)
PARAMS = dict(message_sid='inbox-1',from_number='+15551112222',to_number='+15553334444',body='tree trimming')


def test_committed_inbox_recovers_after_handler_crash_without_webhook_retry(tmp_path, monkeypatch):
    import text_back.inbox as inbox
    path = str(tmp_path/'inbox.db')
    app = create_app(db_path=path,telecom=FakeTelecom(),now_provider=lambda: NOW)
    real = inbox.handle_sms_event
    monkeypatch.setattr(inbox,'handle_sms_event',lambda **kw: (_ for _ in ()).throw(RuntimeError('injected')))
    submit_event(state=app.state, kind='sms', params=PARAMS)
    app.state.store.conn.close()
    monkeypatch.setattr(inbox,'handle_sms_event',real)
    restarted=create_app(db_path=path,telecom=FakeTelecom(),now_provider=lambda: NOW+timedelta(minutes=2))
    run_due_inbound(restarted.state)
    assert restarted.state.store.get_conversation_fields(PARAMS['from_number']) == {'service':'tree trimming'}
    assert len(restarted.state.telecom.outbound)==1
