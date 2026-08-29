from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone


class Store:
    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path, check_same_thread=False)
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
        self.conn.commit()

    def claim_event(self, source: str, event_id: str, action: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.conn.execute(
                "INSERT INTO processed_events (source, event_id, action, created_at) VALUES (?, ?, ?, ?)",
                (source, event_id, action, now),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

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
        self.conn.commit()

    def is_opted_out(self, phone: str) -> bool:
        row = self.conn.execute(
            "SELECT opted_out FROM contacts WHERE phone = ?", (phone,)
        ).fetchone()
        return bool(row["opted_out"]) if row else False

    def get_conversation_fields(self, phone: str) -> dict[str, str]:
        rows = self.conn.execute(
            "SELECT field, value FROM conversation_fields WHERE phone = ?", (phone,)
        ).fetchall()
        return {row["field"]: row["value"] for row in rows}

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
        self.conn.commit()

    def clear_conversation_fields(self, phone: str) -> None:
        self.conn.execute("DELETE FROM conversation_fields WHERE phone = ?", (phone,))
        self.conn.commit()

    def delete_conversation_field(self, phone: str, field: str) -> None:
        self.conn.execute(
            "DELETE FROM conversation_fields WHERE phone = ? AND field = ?",
            (phone, field),
        )
        self.conn.commit()

    def save_appointment(
        self,
        *,
        conversation_id: str,
        event_id: str,
        caller: str,
        start: str,
        location: str,
        service: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """
            INSERT INTO appointments
                (conversation_id, event_id, caller, start, location, service, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (conversation_id, event_id, caller, start, location, service, now),
        )
        self.conn.commit()

    def appointment_by_event(self, event_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM appointments WHERE event_id = ?", (event_id,)
        ).fetchone()
        return dict(row) if row else None

    def appointment_by_conversation(self, conversation_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM appointments WHERE conversation_id = ?", (conversation_id,)
        ).fetchone()
        return dict(row) if row else None

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
        self.conn.commit()
        return cursor.rowcount == 1

    def set_handoff_alert_id(self, phone: str, alert_id: str) -> None:
        self.conn.execute(
            "UPDATE handoffs SET alert_id = ? WHERE phone = ? AND status = 'active'",
            (alert_id, phone),
        )
        self.conn.commit()

    def active_handoff(self, phone: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM handoffs WHERE phone = ? AND status = 'active'",
            (phone,),
        ).fetchone()
        return dict(row) if row else None

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
        self.conn.commit()
        return cursor.rowcount == 1

    # --- follow-up sequences ---

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
        self.conn.commit()
        return cursor.rowcount == 1

    def get_followup(self, phone: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM followups WHERE phone = ?", (phone,)
        ).fetchone()
        return dict(row) if row else None

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
        self.conn.commit()

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
        self.conn.commit()

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
        self.conn.commit()
        return cursor.rowcount == 1

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
        self.conn.commit()
        return cursor.rowcount == 1

    # --- handoff alert deliveries ---

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
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_handoff_delivery(self, alert_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM handoff_deliveries WHERE alert_id = ?", (alert_id,)
        ).fetchone()
        return dict(row) if row else None

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
        self.conn.commit()
        return cursor.rowcount == 1

    def mark_handoff_delivery_delivered(
        self, alert_id: str, *, attempts: int, receipt_id: str
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            UPDATE handoff_deliveries
            SET status = 'delivered', attempts = ?, receipt_id = ?, updated_at = ?
            WHERE alert_id = ? AND status = 'pending'
            """,
            (attempts, receipt_id, now, alert_id),
        )
        self.conn.commit()
        return cursor.rowcount == 1

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
            WHERE alert_id = ? AND status = 'pending'
            """,
            (attempts, next_attempt_at, last_error, now, alert_id),
        )
        self.conn.commit()

    def dead_letter_handoff_delivery(
        self, alert_id: str, *, attempts: int, last_error: str
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        cursor = self.conn.execute(
            """
            UPDATE handoff_deliveries
            SET status = 'dead_letter', attempts = ?, last_error = ?, updated_at = ?
            WHERE alert_id = ? AND status = 'pending'
            """,
            (attempts, last_error, now, alert_id),
        )
        self.conn.commit()
        return cursor.rowcount == 1

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
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

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
