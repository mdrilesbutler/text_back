from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, timezone


def synchronized(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        with self.lock:
            return function(self, *args, **kwargs)
    return wrapped


class Store:
    def __init__(self, path: str = ":memory:") -> None:
        self.lock = threading.RLock()
        self._transaction_depth = 0
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
        self.conn.execute("PRAGMA busy_timeout=30000")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_events (
                source TEXT NOT NULL,
                event_id TEXT NOT NULL,
                action TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (source, event_id, action)
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                phone TEXT PRIMARY KEY,
                opted_out INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_fields (
                phone TEXT NOT NULL,
                field TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (phone, field)
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                conversation_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE,
                caller TEXT NOT NULL,
                start TEXT NOT NULL,
                location TEXT NOT NULL,
                service TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        # Appointments booked before the Schedule page lack their own end time (guarded migration).
        if "end" not in {row[1] for row in self.conn.execute("PRAGMA table_info(appointments)")}:
            self.conn.execute("ALTER TABLE appointments ADD COLUMN end TEXT")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS handoffs (
                phone TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                reason TEXT NOT NULL,
                alert_id TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outcome_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                evidence_id TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                occurred_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_outcome_events_lead_id_id
            ON outcome_events (lead_id, id)
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS followups (
                phone TEXT PRIMARY KEY,
                call_sid TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts_sent INTEGER NOT NULL DEFAULT 0,
                next_action TEXT NOT NULL,
                next_action_at TEXT NOT NULL,
                cancel_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS handoff_deliveries (
                alert_id TEXT PRIMARY KEY,
                phone TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT NOT NULL,
                receipt_id TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_handoff_deliveries_due
            ON handoff_deliveries (status, next_attempt_at)
            """
        )
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sms_outbox (
                key TEXT PRIMARY KEY, phone TEXT NOT NULL, from_number TEXT NOT NULL,
                body TEXT NOT NULL, kind TEXT NOT NULL, completion_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT NOT NULL, lease_until TEXT,
                provider_id TEXT, last_error TEXT, created_at TEXT NOT NULL
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS sms_due ON sms_outbox(status, next_attempt_at)")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS inbound_jobs (
            key TEXT PRIMARY KEY, kind TEXT NOT NULL, phone TEXT NOT NULL,
            params_json TEXT NOT NULL, received_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt_at TEXT NOT NULL)""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS calendar_reconnect_links (
            token_hash TEXT PRIMARY KEY, expires_at TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0,
            purpose TEXT NOT NULL DEFAULT 'operator')""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS calendar_oauth_states (
            state_hash TEXT PRIMARY KEY, cookie_hash TEXT NOT NULL, verifier TEXT NOT NULL,
            expires_at TEXT NOT NULL, used INTEGER NOT NULL DEFAULT 0,
            purpose TEXT NOT NULL DEFAULT 'operator')""")
        # Databases created before the client-initiated connect flow lack the purpose column.
        for table in ("calendar_reconnect_links", "calendar_oauth_states"):
            columns = {row[1] for row in self.conn.execute(f"PRAGMA table_info({table})")}
            if "purpose" not in columns:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN purpose TEXT NOT NULL DEFAULT 'operator'")
        # Owner-editable business settings (name, phones, chosen calendar); env values are the defaults.
        self.conn.execute("""CREATE TABLE IF NOT EXISTS client_settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS client_login_codes (
            phone TEXT PRIMARY KEY, code_hash TEXT NOT NULL, expires_at TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
            purpose TEXT NOT NULL DEFAULT 'sign-in')""")
        # Codes from before purposes existed were all sign-in codes; a code is only ever
        # accepted for the purpose it was texted for ('sign-in' or 'new mobile').
        if "purpose" not in {row[1] for row in self.conn.execute("PRAGMA table_info(client_login_codes)")}:
            self.conn.execute("ALTER TABLE client_login_codes ADD COLUMN purpose TEXT NOT NULL DEFAULT 'sign-in'")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS client_sessions (
            token_hash TEXT PRIMARY KEY, csrf TEXT NOT NULL, phone TEXT NOT NULL,
            expires_at TEXT NOT NULL, created_at TEXT NOT NULL, pending INTEGER NOT NULL DEFAULT 0)""")
        # Sessions created before "Remember this device for 30 days" lack the remember flag.
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(client_sessions)")}
        if "remember" not in columns:
            self.conn.execute("ALTER TABLE client_sessions ADD COLUMN remember INTEGER NOT NULL DEFAULT 0")
        # When each signed-in session last opened a page (Account: "Another device · last used …").
        if "last_used_at" not in columns:
            self.conn.execute("ALTER TABLE client_sessions ADD COLUMN last_used_at TEXT")
        # Every sign-in request, for any number, so the "three codes in 15 minutes" notice
        # reads the same whether or not the number is on file.
        self.conn.execute("""CREATE TABLE IF NOT EXISTS client_login_requests (
            phone TEXT NOT NULL, created_at TEXT NOT NULL)""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_client_login_requests ON client_login_requests(phone, created_at)")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS booking_jobs (
            key TEXT PRIMARY KEY, phone TEXT NOT NULL, payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 1,
            next_attempt_at TEXT NOT NULL)""")
        self._commit()

    def _commit(self) -> None:
        if not self._transaction_depth:
            self.conn.commit()

    @synchronized
    def setting(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM client_settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    @synchronized
    def set_setting(self, key: str, value: str | None, *, now: datetime | None = None) -> None:
        """Store an owner-editable setting; None removes it so the env default applies again."""
        if value is None:
            self.conn.execute("DELETE FROM client_settings WHERE key=?", (key,))
        else:
            stamp = (now or datetime.now(timezone.utc)).isoformat()
            self.conn.execute(
                "INSERT INTO client_settings(key,value,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, value, stamp),
            )
        self._commit()

    @contextmanager
    def transaction(self):
        """Serialize one connection and atomically commit local state + intents.

        BEGIN IMMEDIATE also serializes independent processes/connections.
        Nested calls participate in their caller's transaction.
        """
        with self.lock:
            outer = self._transaction_depth == 0
            if outer:
                self.conn.execute("BEGIN IMMEDIATE")
            self._transaction_depth += 1
            try:
                yield
            except BaseException:
                if outer:
                    self.conn.rollback()
                raise
            else:
                if outer:
                    self.conn.commit()
            finally:
                self._transaction_depth -= 1

    @synchronized
    def get_sms(self, key: str) -> dict | None:
        with self.lock:
            row = self.conn.execute("SELECT * FROM sms_outbox WHERE key = ?", (key,)).fetchone()
            return dict(row) if row else None

    @synchronized
    def claim_event(self, source: str, event_id: str, action: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.conn.execute(
                "INSERT INTO processed_events (source, event_id, action, created_at) VALUES (?, ?, ?, ?)",
                (source, event_id, action, now),
            )
            self._commit()
            return True
        except sqlite3.IntegrityError:
            return False

    @synchronized
    def set_opted_out(self, phone: str, opted_out: bool) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT INTO contacts (phone, opted_out, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET opted_out=excluded.opted_out, updated_at=excluded.updated_at
            """,
            (phone, int(opted_out), now),
        )
        self._commit()

    @synchronized
    def is_opted_out(self, phone: str) -> bool:
        row = self.conn.execute(
            "SELECT opted_out FROM contacts WHERE phone = ?", (phone,)
        ).fetchone()
        return bool(row["opted_out"]) if row else False

    @synchronized
    def get_conversation_fields(self, phone: str) -> dict[str, str]:
        rows = self.conn.execute(
            "SELECT field, value FROM conversation_fields WHERE phone = ?", (phone,)
        ).fetchall()
        return {row["field"]: row["value"] for row in rows}

    @synchronized
    def set_conversation_field(self, phone: str, field: str, value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT INTO conversation_fields (phone, field, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(phone, field) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (phone, field, value, now),
        )
        self._commit()

    @synchronized
    def clear_conversation_fields(self, phone: str) -> None:
        self.conn.execute("DELETE FROM conversation_fields WHERE phone = ?", (phone,))
        self._commit()

    @synchronized
    def delete_conversation_field(self, phone: str, field: str) -> None:
        self.conn.execute(
            "DELETE FROM conversation_fields WHERE phone = ? AND field = ?",
            (phone, field),
        )
        self._commit()

    @synchronized
    def save_appointment(
        self,
        *,
        conversation_id: str,
        event_id: str,
        caller: str,
        start: str,
        location: str,
        service: str,
        end: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT INTO appointments
                (conversation_id, event_id, caller, start, end, location, service, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, event_id, caller, start, end, location, service, now),
        )
        self._commit()

    @synchronized
    def appointment_by_event(self, event_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM appointments WHERE event_id = ?", (event_id,)
        ).fetchone()
        return dict(row) if row else None

    @synchronized
    def appointment_by_conversation(self, conversation_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM appointments WHERE conversation_id = ?", (conversation_id,)
        ).fetchone()
        return dict(row) if row else None

    @synchronized
    def request_handoff(self, phone: str, reason: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            INSERT INTO handoffs
                (phone, status, reason, alert_id, requested_at, resolved_at)
            VALUES (?, 'active', ?, '', ?, NULL)
            ON CONFLICT(phone) DO UPDATE SET
                status = 'active',
                reason = excluded.reason,
                alert_id = '',
                requested_at = excluded.requested_at,
                resolved_at = NULL
            WHERE handoffs.status = 'resolved'
            """,
            (phone, reason, now),
        )
        self._commit()
        return cursor.rowcount == 1

    @synchronized
    def set_handoff_alert_id(self, phone: str, alert_id: str) -> None:
        self.conn.execute(
            "UPDATE handoffs SET alert_id = ? WHERE phone = ? AND status = 'active'",
            (alert_id, phone),
        )
        self._commit()

    @synchronized
    def active_handoff(self, phone: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM handoffs WHERE phone = ? AND status = 'active'",
            (phone,),
        ).fetchone()
        return dict(row) if row else None

    @synchronized
    def resolve_handoff(self, phone: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            UPDATE handoffs
            SET status = 'resolved', resolved_at = ?
            WHERE phone = ? AND status = 'active'
            """,
            (now, phone),
        )
        self._commit()
        return cursor.rowcount == 1

    # --- follow-up sequences ---

    @synchronized
    def start_followup(
        self,
        *,
        phone: str,
        call_sid: str,
        next_action: str,
        next_action_at: str,
    ) -> bool:
        """Create/replace the lead's sequence unless one is already active.

        Duplicate webhooks for the same call must not reset an active sequence;
        a new missed call after cancel/expiry starts fresh.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            INSERT INTO followups
                (phone, call_sid, status, attempts_sent, next_action,
                 next_action_at, cancel_reason, created_at, updated_at)
            VALUES (?, ?, 'active', 0, ?, ?, NULL, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
                call_sid = excluded.call_sid,
                status = 'active',
                attempts_sent = 0,
                next_action = excluded.next_action,
                next_action_at = excluded.next_action_at,
                cancel_reason = NULL,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at
            WHERE followups.status != 'active'
            """,
            (phone, call_sid, next_action, next_action_at, now, now),
        )
        self._commit()
        return cursor.rowcount == 1

    @synchronized
    def get_followup(self, phone: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM followups WHERE phone = ?", (phone,)
        ).fetchone()
        return dict(row) if row else None

    @synchronized
    def due_followups(self, now_iso: str) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT * FROM followups
            WHERE status = 'active' AND next_action_at <= ?
            ORDER BY next_action_at
            """,
            (now_iso,),
        ).fetchall()
        return [dict(row) for row in rows]

    @synchronized
    def advance_followup(
        self,
        phone: str,
        *,
        attempts_sent: int,
        next_action: str,
        next_action_at: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            UPDATE followups
            SET attempts_sent = ?, next_action = ?, next_action_at = ?, updated_at = ?
            WHERE phone = ? AND status = 'active'
            """,
            (attempts_sent, next_action, next_action_at, now, phone),
        )
        self._commit()

    @synchronized
    def defer_followup(self, phone: str, next_action_at: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            UPDATE followups
            SET next_action_at = ?, updated_at = ?
            WHERE phone = ? AND status = 'active'
            """,
            (next_action_at, now, phone),
        )
        self._commit()

    @synchronized
    def cancel_followup(self, phone: str, reason: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            UPDATE followups
            SET status = 'cancelled', cancel_reason = ?, updated_at = ?
            WHERE phone = ? AND status = 'active'
            """,
            (reason, now, phone),
        )
        self._commit()
        return cursor.rowcount == 1

    @synchronized
    def expire_followup(self, phone: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            UPDATE followups
            SET status = 'expired', updated_at = ?
            WHERE phone = ? AND status = 'active'
            """,
            (now, phone),
        )
        self._commit()
        return cursor.rowcount == 1

    # --- handoff alert deliveries ---

    @synchronized
    def enqueue_handoff_delivery(
        self,
        *,
        alert_id: str,
        phone: str,
        payload_json: str,
        next_attempt_at: str,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.conn.execute(
                """
                INSERT INTO handoff_deliveries
                    (alert_id, phone, payload_json, status, attempts,
                     next_attempt_at, receipt_id, last_error, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', 0, ?, NULL, NULL, ?, ?)
                """,
                (alert_id, phone, payload_json, next_attempt_at, now, now),
            )
            self._commit()
            return True
        except sqlite3.IntegrityError:
            return False

    @synchronized
    def get_handoff_delivery(self, alert_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM handoff_deliveries WHERE alert_id = ?", (alert_id,)
        ).fetchone()
        return dict(row) if row else None

    @synchronized
    def due_handoff_deliveries(self, now_iso: str) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT * FROM handoff_deliveries
            WHERE status = 'pending' AND next_attempt_at <= ?
            ORDER BY next_attempt_at
            """,
            (now_iso,),
        ).fetchall()
        return [dict(row) for row in rows]

    @synchronized
    def begin_handoff_delivery_attempt(
        self, alert_id: str, *, attempts: int, next_attempt_at: str
    ) -> bool:
        """Persist the attempt bump BEFORE any transport call.

        The WHERE clause is the attempt lock: it succeeds only while the row
        is still pending at the prior attempt count, so a replayed or
        concurrent runner skips the row instead of double-attempting. Because
        this commits first, a crash mid-delivery leaves the row pending and
        re-runnable at ``next_attempt_at`` (true at-least-once) rather than
        wedged behind a consumed claim.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            UPDATE handoff_deliveries
            SET attempts = ?, next_attempt_at = ?, updated_at = ?
            WHERE alert_id = ? AND status = 'pending' AND attempts = ?
            """,
            (attempts, next_attempt_at, now, alert_id, attempts - 1),
        )
        self._commit()
        return cursor.rowcount == 1

    @synchronized
    def mark_handoff_delivery_delivered(
        self, alert_id: str, *, attempts: int, receipt_id: str
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            UPDATE handoff_deliveries
            SET status = 'delivered', attempts = ?, receipt_id = ?, updated_at = ?
            WHERE alert_id = ? AND status = 'pending' AND attempts = ?
            """,
            (attempts, receipt_id, now, alert_id, attempts),
        )
        self._commit()
        return cursor.rowcount == 1

    @synchronized
    def retry_handoff_delivery(
        self,
        alert_id: str,
        *,
        attempts: int,
        next_attempt_at: str,
        last_error: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            UPDATE handoff_deliveries
            SET attempts = ?, next_attempt_at = ?, last_error = ?, updated_at = ?
            WHERE alert_id = ? AND status = 'pending' AND attempts = ?
            """,
            (attempts, next_attempt_at, last_error, now, alert_id, attempts),
        )
        self._commit()

    @synchronized
    def dead_letter_handoff_delivery(
        self, alert_id: str, *, attempts: int, last_error: str
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            UPDATE handoff_deliveries
            SET status = 'dead_letter', attempts = ?, last_error = ?, updated_at = ?
            WHERE alert_id = ? AND status = 'pending' AND attempts = ?
            """,
            (attempts, last_error, now, alert_id, attempts),
        )
        self._commit()
        return cursor.rowcount == 1

    @synchronized
    def record_outcome(
        self,
        *,
        lead_id: str,
        event_type: str,
        idempotency_key: str,
        evidence_id: str,
        metadata: dict[str, object] | None = None,
        occurred_at: str | None = None,
    ) -> bool:
        if not lead_id or not event_type or not idempotency_key or not evidence_id:
            raise ValueError("outcome events require lead, type, idempotency, and evidence")
        when = occurred_at or datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"))
        try:
            self.conn.execute(
                """
                INSERT INTO outcome_events
                    (lead_id, event_type, idempotency_key, evidence_id,
                     metadata_json, occurred_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_id,
                    event_type,
                    idempotency_key,
                    evidence_id,
                    metadata_json,
                    when,
                ),
            )
            self._commit()
            return True
        except sqlite3.IntegrityError:
            return False

    @synchronized
    def list_outcome_events(self, lead_id: str | None = None) -> list[dict]:
        if lead_id is None:
            rows = self.conn.execute(
                "SELECT * FROM outcome_events ORDER BY id"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM outcome_events WHERE lead_id = ? ORDER BY id",
                (lead_id,),
            ).fetchall()
        events: list[dict] = []
        for row in rows:
            event = dict(row)
            event["metadata"] = json.loads(event.pop("metadata_json"))
            events.append(event)
        return events
