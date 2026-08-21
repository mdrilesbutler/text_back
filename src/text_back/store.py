from __future__ import annotations

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
