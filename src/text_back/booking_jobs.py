"""Persisted retries for calendar outages after qualification."""
import json
from datetime import datetime, timedelta, timezone

from text_back.booking import BookingError, SlotUnavailableError, book_appointment
from text_back.sms import QueuedTelecom, run_due_sms
from text_back.policy import slot_unavailable_sms


def _messages(state):
    source = getattr(state, 'messages', None)
    return source.current() if source else None


def queue_booking(store, payload, now):
    key=payload['conversation_id']+':'+payload['start'].isoformat()
    encoded={**payload,'start':payload['start'].isoformat()}
    store.conn.execute('''INSERT OR IGNORE INTO booking_jobs(key,phone,payload_json,next_attempt_at)
        VALUES(?,?,?,?)''',(key,payload['caller'],json.dumps(encoded),(now+timedelta(minutes=1)).isoformat()))
    return key


def finish_booking_job(store,key):
    store.conn.execute("UPDATE booking_jobs SET status='done' WHERE key=?",(key,))


def run_due_bookings(state):
    store=state.store
    now=state.now_provider() if state.now_provider else datetime.now(timezone.utc)
    with store.transaction():
        rows=[dict(r) for r in store.conn.execute("SELECT * FROM booking_jobs WHERE status IN ('pending','running') AND next_attempt_at<=? ORDER BY next_attempt_at LIMIT 20",(now.isoformat(),))]
    for candidate in rows:
        key=candidate['key']
        with store.transaction():
            row=dict(store.conn.execute('SELECT * FROM booking_jobs WHERE key=?',(key,)).fetchone())
            if row['status'] not in ('pending','running') or row['next_attempt_at']>now.isoformat():
                continue
            if store.is_opted_out(row['phone']) or store.active_handoff(row['phone']):
                store.conn.execute("UPDATE booking_jobs SET status='cancelled' WHERE key=?",(key,))
                continue
            credentials=getattr(state.calendar,'token_provider',None)
            if hasattr(credentials,'status') and credentials.status()=='reauth_required':
                store.conn.execute("UPDATE booking_jobs SET next_attempt_at=? WHERE key=?",((now+timedelta(minutes=1)).isoformat(),key))
                continue
            attempt=row['attempts']+1
            store.conn.execute("UPDATE booking_jobs SET status='running',attempts=?,next_attempt_at=? WHERE key=?",
                (attempt,(now+timedelta(minutes=2)).isoformat(),key))
        payload=json.loads(row['payload_json'])
        payload['start']=datetime.fromisoformat(payload['start'])
        try:
            if attempt>4 or payload['start']<=now:
                raise BookingError('booking retry window exhausted')
            book_appointment(store=store,calendar=state.calendar,telecom=state.telecom,now=now,_deferred=True,
                messages=_messages(state),**payload)
        except SlotUnavailableError:
            with store.transaction():
                store.delete_conversation_field(row['phone'],'preferred_time')
                queued=QueuedTelecom(store,key,now)
                queued.send_sms(to=row['phone'],from_number=payload['business_number'],kind='slot_unavailable',body=slot_unavailable_sms(payload['business_name'],_messages(state)))
                finish_booking_job(store,key)
            run_due_sms(store=store,telecom=state.telecom,now=now,policy=state.followup_policy,keys=queued.keys)
        except Exception:
            with store.transaction():
                if attempt>=4 or payload['start']<=now:
                    # Persist the operator lead and terminal job transition together.
                    from text_back.handlers import _request_handoff
                    queued=QueuedTelecom(store,key,now)
                    _request_handoff(store=store,telecom=queued,handoff_notifier=state.handoff_notifier,
                        handoff_destination=state.handoff_destination,from_number=row['phone'],to_number=payload['business_number'],
                        body='Calendar booking could not be completed after retries.',reason='calendar_unavailable',acknowledge_customer=True,now=now,
                        business_name=payload['business_name'],messages=_messages(state))
                    store.conn.execute("UPDATE booking_jobs SET status='dead_letter' WHERE key=?",(key,))
                else:
                    store.conn.execute("UPDATE booking_jobs SET status='pending',next_attempt_at=? WHERE key=?",
                        ((now+timedelta(minutes=(1,5,15)[attempt-1])).isoformat(),key))
        else:
            with store.transaction():
                finish_booking_job(store,key)
