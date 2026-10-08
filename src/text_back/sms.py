"""Customer SMS outbox. Unknown acceptance is held, never blindly retried.

Intent and local transitions commit together. A send claims a row before I/O;
a crashed send expires to unknown. SignalWire callbacks can reconcile that gap.
Only a definite non-acceptance can consume the bounded retry schedule.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from functools import wraps
from urllib.parse import quote

from text_back.telecom import AmbiguousSmsError, RetryableSmsError, TelecomError

RETRY_MINUTES = (1, 5, 15)


def enqueue_sms(*, store, key, to, from_number, body, kind, now, completion=None):
    with store.transaction():
        store.conn.execute(
            """INSERT OR IGNORE INTO sms_outbox
               (key,phone,from_number,body,kind,completion_json,next_attempt_at,created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (key, to, from_number, body, kind, json.dumps(completion or {}),
             now.isoformat(), now.isoformat()),
        )
    return key


class QueuedTelecom:
    """Used only while applying an inbound event transaction."""
    def __init__(self, store, key, now):
        self.store, self.key, self.now = store, key, now
        self.keys = []

    def send_sms(self, **payload):
        key = f"{self.key}:{payload['kind']}"
        enqueue_sms(store=self.store, key=key, now=self.now, **payload)
        self.keys.append(key)
        return key


def atomic_sms_handler(function):
    """Commit inbound claim, field changes and replies before touching telecom."""
    @wraps(function)
    def wrapped(**kwargs):
        send_now = kwargs.pop('_send_now', None)
        deferred = kwargs.pop('_deferred', False)
        store, telecom = kwargs['store'], kwargs['telecom']
        # A booking called from an inbound handler shares that transaction.
        if isinstance(telecom, QueuedTelecom):
            return function(**kwargs)
        now = kwargs.get('now') or datetime.now(timezone.utc)
        key = kwargs.get('message_sid') or kwargs.get('call_sid') or kwargs.get('conversation_id')
        queued = QueuedTelecom(store, key, now)
        with store.transaction():
            result = function(**{**kwargs, 'telecom': queued, 'now': now})
        # Replay also drains previously committed replies without applying the
        # same customer's text to the next field a second time.
        with store.lock:
            keys = [r['key'] for r in store.conn.execute(
                "SELECT key FROM sms_outbox WHERE key = ? OR substr(key,1,?) = ?",
                (key, len(key) + 1, key + ':'),
            )]
        keys.extend(queued.keys)
        run_due_sms(store=store, telecom=telecom, now=send_now or now, keys=keys,
                    policy=kwargs.get('followup_policy') or getattr(store, 'sms_policy', None),
                    callback_base_url=getattr(store, 'callback_base_url', None), immediate=not deferred)
        return result
    return wrapped


def _cancelled(store, row, completion):
    phone, kind = row['phone'], row['kind']
    if kind not in ('opt_out_ack', 'help') and store.is_opted_out(phone):
        return True
    if kind not in ('opt_out_ack', 'opt_in_ack', 'help', 'handoff_ack'):
        if store.active_handoff(phone):
            return True
    if kind in ('missed_call_intro', 'followup'):
        if store.appointment_by_conversation(phone):
            return True
    if kind == 'followup':
        seq = store.get_followup(phone)
        return not seq or seq['status'] != 'active' or seq['call_sid'] != completion.get('call_sid')
    return False


def _complete(store, row, provider_id, now):
    """Caller owns a transaction; success evidence and progression are atomic."""
    current = store.get_sms(row['key'])
    if current['status'] == 'dead_letter' and current['provider_id']:
        return
    completion = json.loads(row['completion_json'])
    if completion.get('event_type'):
        store.record_outcome(
            lead_id=row['phone'], event_type=completion['event_type'],
            idempotency_key=completion['outcome_key'], evidence_id=provider_id,
            metadata=completion.get('metadata', {}), occurred_at=now.isoformat(),
        )
    if row['kind'] == 'missed_call_intro' and completion.get('delays'):
        # A reply may have arrived while the provider request was in flight.
        replied = store.conn.execute(
            "SELECT 1 FROM outcome_events WHERE lead_id=? AND event_type='sms.customer_replied' AND occurred_at>=?",
            (row['phone'], row['created_at']),
        ).fetchone()
        if not replied and not _cancelled(store, row, completion):
            store.start_followup(phone=row['phone'], call_sid=completion['call_sid'],
                                 next_action='followup', next_action_at=(now + timedelta(minutes=completion['delays'][0])).isoformat())
    if row['kind'] == 'followup':
        seq = store.get_followup(row['phone'])
        attempt = completion['metadata']['attempt']
        if seq and seq['status'] == 'active' and seq['call_sid'] == completion['call_sid'] and seq['attempts_sent'] < attempt:
            delays = completion['delays']
            more = attempt < len(delays)
            store.advance_followup(row['phone'], attempts_sent=attempt,
                                   next_action='followup' if more else 'expire',
                                   next_action_at=(now + timedelta(minutes=delays[attempt] if more else completion['expiry'])).isoformat())
    store.conn.execute("UPDATE sms_outbox SET status='sent',provider_id=?,lease_until=NULL WHERE key=?",
                       (provider_id, row['key']))


def reconcile_sms(*, store, key, provider_id, now, delivery_status="sent"):
    with store.transaction():
        row = store.get_sms(key)
        if not row or row['attempts'] == 0:
            return False
        if row['provider_id'] and row['provider_id'] != provider_id:
            return False
        if delivery_status in ('failed', 'undelivered'):
            store.conn.execute("UPDATE sms_outbox SET status='dead_letter',provider_id=?,lease_until=NULL,last_error='provider delivery failed' WHERE key=?", (provider_id, key))
            store.cancel_followup(row['phone'], 'sms_delivery_failed')
            store.record_outcome(lead_id=row['phone'], event_type='sms.delivery_failed',
                idempotency_key=f'sms:{key}:failed', evidence_id=provider_id,
                metadata={'kind':row['kind']}, occurred_at=now.isoformat())
            return True
        if delivery_status not in ('queued','sending','sent','delivered'):
            return False
        if row['status'] != 'sent':
            _complete(store, row, provider_id, now)
        return True


def run_due_sms(*, store, telecom, now, policy=None, keys=None, callback_base_url=None, immediate=False):
    from text_back.followup import next_allowed_send_time
    actions = []
    with store.transaction():
        store.conn.execute("UPDATE sms_outbox SET status='unknown',last_error='send interrupted' WHERE status='sending' AND lease_until<=?", (now.isoformat(),))
        rows = [dict(r) for r in store.conn.execute(
            "SELECT * FROM sms_outbox WHERE status='pending' AND next_attempt_at<=? ORDER BY created_at,key", (now.isoformat(),))]
    for candidate in rows:
        key = candidate['key']
        if keys is not None and key not in keys:
            continue
        with store.transaction():
            row = store.get_sms(key)
            if row['status'] != 'pending' or row['next_attempt_at'] > now.isoformat():
                continue
            try:
                completion = json.loads(row['completion_json'])
                if not isinstance(completion, dict):
                    raise ValueError('invalid completion')
            except (ValueError, TypeError):
                store.conn.execute("UPDATE sms_outbox SET status='dead_letter',last_error='invalid completion' WHERE key=?", (key,))
                continue
            if _cancelled(store, row, completion):
                store.conn.execute("UPDATE sms_outbox SET status='cancelled' WHERE key=?", (key,))
                continue
            # Customer-initiated immediate replies and STOP/HELP are allowed;
            # nurture sends and every delayed retry respect quiet hours.
            if policy and row['kind'] not in ('help', 'opt_out_ack') and (not immediate or row['attempts'] or row['kind'] == 'followup' or now > datetime.fromisoformat(row['created_at']) + timedelta(seconds=5)):
                allowed = next_allowed_send_time(now, policy)
                if allowed > now:
                    store.conn.execute("UPDATE sms_outbox SET next_attempt_at=? WHERE key=?", (allowed.isoformat(), key))
                    continue
            attempt = row['attempts'] + 1
            store.conn.execute("UPDATE sms_outbox SET status='sending',attempts=?,lease_until=? WHERE key=?",
                               (attempt, (now + timedelta(minutes=2)).isoformat(), key))
        try:
            payload = dict(to=row['phone'], from_number=row['from_number'], body=row['body'], kind=row['kind'])
            callback_base_url = callback_base_url or getattr(store, 'callback_base_url', None)
            if callback_base_url and hasattr(telecom, 'send_sms_with_callback'):
                receipt = telecom.send_sms_with_callback(**payload, callback_url=f"{callback_base_url}/webhooks/sms-status?key={quote(key, safe='')}")
            else:
                receipt = telecom.send_sms(**payload)
            if not isinstance(receipt, str) or not receipt:
                raise AmbiguousSmsError('provider receipt missing')
        except Exception as exc:
            # Unknown exceptions may occur AFTER acceptance. Never assume that
            # a timeout or programming error authorizes a duplicate text.
            retry = isinstance(exc, RetryableSmsError)
            status = 'pending' if retry and attempt <= len(RETRY_MINUTES) else 'dead_letter' if isinstance(exc, TelecomError) and not isinstance(exc, AmbiguousSmsError) else 'unknown'
            with store.transaction():
                store.conn.execute("""UPDATE sms_outbox SET status=?,next_attempt_at=?,last_error=?,lease_until=NULL
                                      WHERE key=? AND status='sending' AND attempts=?""",
                                   (status, (now + timedelta(minutes=RETRY_MINUTES[attempt-1] if status == 'pending' else 0)).isoformat(), type(exc).__name__, key, attempt))
                if status == 'dead_letter' and row['kind'] in ('followup', 'missed_call_intro'):
                    store.cancel_followup(row['phone'], 'sms_retry_exhausted')
            actions.append({'action': status, 'key': key})
            continue
        with store.transaction():
            _complete(store, row, receipt, now)
        actions.append({'action': 'sent', 'key': key})
    return actions
