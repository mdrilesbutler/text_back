"""Each appointment stores its own end time, so links sent before a length change stay right."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.booking import book_appointment
from text_back.store import Store
from text_back.telecom import FakeTelecom


class FreeCalendar:
    provider_name = "fake"
    def is_free(self, start, end): return True
    def find_event(self, **kw): return None
    def create_event(self, **kwargs): return "evt-1"


def test_booking_stores_the_end_time(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    start = datetime(2026, 10, 27, 14, 0, tzinfo=timezone.utc)
    book_appointment(calendar=FreeCalendar(), store=store, telecom=FakeTelecom(), caller="+19805550141",
                     business_number="+17045550100", service="trim", location="12 Elm St", customer_name="Dana",
                     business_name="Oak", timezone_name="America/New_York", start=start, duration_minutes=45,
                     conversation_id="+19805550141")
    row = store.appointment_by_conversation("+19805550141")
    assert datetime.fromisoformat(row["end"]) == start + timedelta(minutes=45)


def test_old_databases_gain_the_end_column(tmp_path):
    db = tmp_path / "old.db"
    Store(str(db))
    import sqlite3
    conn = sqlite3.connect(db)
    conn.execute("ALTER TABLE appointments DROP COLUMN end"); conn.commit(); conn.close()
    store = Store(str(db))
    assert "end" in {r[1] for r in store.conn.execute("PRAGMA table_info(appointments)")}


def test_calendar_links_use_the_stored_end_after_a_length_change(tmp_path):
    app = create_app(db_path=str(tmp_path / "t.db"), telecom=FakeTelecom(), public_base_url="https://example.test",
                     appointment_duration_minutes=60, business_name="Oak")
    store = app.state.store
    start = datetime(2026, 10, 27, 14, 0, tzinfo=timezone.utc)
    store.save_appointment(conversation_id="+19805550141", event_id="evt-1", caller="+19805550141",
                           start=start.isoformat(), end=(start + timedelta(minutes=45)).isoformat(),
                           location="12 Elm St", service="trim")
    app.state.appointment_duration_minutes = 120  # owner changed the length afterwards
    rowid = store.conn.execute("SELECT rowid FROM appointments").fetchone()[0]
    ref = store.calendar_links.ref(rowid, "evt-1")
    ics = TestClient(app).get(f"/a/{ref}/i").text
    assert "DTEND:20261027T144500Z" in ics


def test_legacy_rows_without_an_end_fall_back_to_the_duration(tmp_path):
    app = create_app(db_path=str(tmp_path / "t.db"), telecom=FakeTelecom(), public_base_url="https://example.test",
                     appointment_duration_minutes=60, business_name="Oak")
    store = app.state.store
    start = datetime(2026, 10, 27, 14, 0, tzinfo=timezone.utc)
    store.save_appointment(conversation_id="+19805550141", event_id="evt-1", caller="+19805550141",
                           start=start.isoformat(), location="12 Elm St", service="trim")
    rowid = store.conn.execute("SELECT rowid FROM appointments").fetchone()[0]
    ref = store.calendar_links.ref(rowid, "evt-1")
    assert "DTEND:20261027T150000Z" in TestClient(app).get(f"/a/{ref}/i").text
