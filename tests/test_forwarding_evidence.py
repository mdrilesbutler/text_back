"""A forwarded call carries ForwardedFrom from the carrier; a direct call to the texting number does not.

The owner portal ticks "Forwarding works" only from this recorded evidence, never from a direct call.
"""
import json
from datetime import datetime, timezone

from text_back.handlers import handle_voice_event
from text_back.store import Store
from text_back.telecom import FakeTelecom


def _missed(store, call_sid, **kw):
    handle_voice_event(store=store, telecom=FakeTelecom(), call_sid=call_sid, call_status="ringing",
                       from_number="+19805550141", to_number="+17045550100", wiring_mode="forwarded",
                       business_name="Oak", now=datetime(2026, 10, 26, 13, 12, tzinfo=timezone.utc), **kw)
    row = store.conn.execute("SELECT metadata_json FROM outcome_events WHERE event_type='call.missed' AND evidence_id=?",
                             (call_sid,)).fetchone()
    return json.loads(row[0])


def test_forwarded_call_records_the_line_it_was_forwarded_from(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    assert _missed(store, "CA1", forwarded_from="+17045550123")["forwarded_from"] == "+17045550123"


def test_direct_call_records_an_empty_forwarded_from(tmp_path):
    store = Store(str(tmp_path / "t.db"))
    assert _missed(store, "CA2")["forwarded_from"] == ""
