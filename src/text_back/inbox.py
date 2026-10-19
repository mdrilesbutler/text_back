"""Persist verified webhooks before processing; recover without provider replay."""
from datetime import datetime, timedelta, timezone
import json

from text_back.handlers import handle_sms_event, handle_voice_event
from text_back.policy import classify_inbound_sms


def _now(state):
    return state.now_provider() if state.now_provider else datetime.now(timezone.utc)


def submit_event(*, state, kind, params):
    now = _now(state)
    key = kind + ':' + params['message_sid' if kind == 'sms' else 'call_sid']
    with state.store.transaction():
        state.store.conn.execute('''INSERT OR IGNORE INTO inbound_jobs
            (key,kind,phone,params_json,received_at,next_attempt_at) VALUES(?,?,?,?,?,?)''',
            (key,kind,params['from_number'],json.dumps(params),now.isoformat(),now.isoformat()))
    return _process(state, key, now) or {'accepted':True, 'action':'queued'}


def _process(state, key, now):
    store=state.store
    with store.transaction():
        row=store.conn.execute('SELECT * FROM inbound_jobs WHERE key=?',(key,)).fetchone()
        if row['status']=='done':
            return {'accepted':True,'duplicate':True,'action':'noop'}
        if row['status']!='pending' or row['next_attempt_at']>now.isoformat():
            return None
        params=json.loads(row['params_json'])
        is_stop=row['kind']=='sms' and classify_inbound_sms(params['body'])=='stop'
        earlier=store.conn.execute("SELECT 1 FROM inbound_jobs WHERE phone=? AND status IN ('pending','running') AND rowid < ?",
                                  (row['phone'],store.conn.execute('SELECT rowid FROM inbound_jobs WHERE key=?',(key,)).fetchone()[0])).fetchone()
        if earlier and not is_stop:
            return None
        attempt=row['attempts']+1
        store.conn.execute("UPDATE inbound_jobs SET status='running',attempts=?,next_attempt_at=? WHERE key=?",
                           (attempt,(now+timedelta(minutes=2)).isoformat(),key))
    try:
        common=dict(store=store,telecom=state.telecom,business_name=state.business_name,
                    now=datetime.fromisoformat(row['received_at']), _send_now=now,
                    messages=state.messages.current() if getattr(state,'messages',None) else None)
        if row['kind']=='voice':
            result=handle_voice_event(**common,**params,wiring_mode=state.wiring_mode,followup_policy=state.followup_policy)
        else:
            result=handle_sms_event(**common,**params,calendar=state.calendar,
                handoff_notifier=state.handoff_notifier,handoff_destination=state.handoff_destination,
                timezone_name=state.timezone_name,appointment_duration_minutes=state.appointment_duration_minutes,
                business_contact=getattr(state,'business_contact',''))
    except Exception:
        with store.transaction():
            store.conn.execute("UPDATE inbound_jobs SET status=?,next_attempt_at=? WHERE key=?",
                ('pending' if attempt<4 else 'dead_letter',(now+timedelta(minutes=(1,5,15,15)[min(attempt-1,3)])).isoformat(),key))
        return {'accepted':True,'action':'queued' if attempt<4 else 'failed'}
    with store.transaction():
        store.conn.execute("UPDATE inbound_jobs SET status='done' WHERE key=?",(key,))
    return result


def run_due_inbound(state):
    now=_now(state)
    with state.store.transaction():
        state.store.conn.execute("UPDATE inbound_jobs SET status=CASE WHEN attempts>=4 THEN 'dead_letter' ELSE 'pending' END WHERE status='running' AND next_attempt_at<=?",(now.isoformat(),))
        keys=[r[0] for r in state.store.conn.execute("SELECT key FROM inbound_jobs WHERE status='pending' AND next_attempt_at<=? ORDER BY rowid LIMIT 20",(now.isoformat(),))]
    for key in keys:
        _process(state,key,now)
