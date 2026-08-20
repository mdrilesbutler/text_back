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
