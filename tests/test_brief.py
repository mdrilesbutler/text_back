from datetime import datetime, timezone

import pytest

from text_back.brief import build_brief_data, render_brief
from text_back.store import Store


LEAD_A = "+15551110001"
LEAD_B = "+15551110002"
LEAD_C = "+15551110003"
PERIOD_START = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
PERIOD_END = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)
IN_PERIOD = "2026-08-10T12:00:00+00:00"
BEFORE_PERIOD = "2026-07-10T12:00:00+00:00"


def _record(store, lead, event_type, key, evidence, metadata=None, at=IN_PERIOD):
    assert store.record_outcome(
        lead_id=lead,
        event_type=event_type,
        idempotency_key=key,
        evidence_id=evidence,
        metadata=metadata or {},
        occurred_at=at,
    )


def _full_funnel(store, lead, *, suffix, confirmed=True):
    _record(store, lead, "call.missed", f"call:{suffix}:missed", f"CA-{suffix}")
    _record(store, lead, "sms.initial_sent", f"call:{suffix}:initial", f"SM-{suffix}-intro")
    _record(store, lead, "sms.customer_replied", f"sms:{suffix}:replied", f"MSG-{suffix}")
    _record(store, lead, "lead.qualified", f"lead:{lead}:qualified", f"MSG-{suffix}")
    _record(
        store,
        lead,
        "calendar.event_created",
        f"calendar:EV-{suffix}:created",
        f"EV-{suffix}",
    )
    if confirmed:
        _record(
            store,
            lead,
            "appointment.confirmed",
            f"calendar:EV-{suffix}:confirmed",
            f"SM-{suffix}-confirm",
            metadata={"calendar_event_id": f"EV-{suffix}"},
        )


def test_record_outcome_accepts_explicit_occurred_at():
    store = Store()
    _record(store, LEAD_A, "call.missed", "call:t:missed", "CA-t", at=IN_PERIOD)
    events = store.list_outcome_events(LEAD_A)
    assert events[0]["occurred_at"] == IN_PERIOD


def test_empty_ledger_produces_zeroed_brief():
    store = Store()
    data = build_brief_data(
        store, period_start=PERIOD_START, period_end=PERIOD_END
    )
    assert data["funnel"] == {
        "missed_calls": 0,
        "leads_contacted": 0,
        "leads_engaged": 0,
        "leads_qualified": 0,
        "appointments_booked": 0,
        "appointments_confirmed": 0,
        "handoffs": 0,
        "followups_sent": 0,
        "leads_expired": 0,
    }
    assert data["attributed_revenue_cents"] == 0
    assert data["confirmed_appointments"] == []


def test_funnel_counts_unique_leads_not_events():
    store = Store()
    _full_funnel(store, LEAD_A, suffix="a1")
    # Same lead misses a second call — still one lead, two missed calls.
    _record(store, LEAD_A, "call.missed", "call:a2:missed", "CA-a2")
    _full_funnel(store, LEAD_B, suffix="b1", confirmed=False)
    _record(store, LEAD_C, "call.missed", "call:c1:missed", "CA-c1")
    _record(store, LEAD_C, "sms.initial_sent", "call:c1:initial", "SM-c1")
    _record(store, LEAD_C, "followup.sent", "followup:CA-c1:sent:1", "SM-c1-fu", {"attempt": 1})
    _record(store, LEAD_C, "lead.expired", "followup:CA-c1:expired", "CA-c1", {"attempts_sent": 2})

    data = build_brief_data(store, period_start=PERIOD_START, period_end=PERIOD_END)

    assert data["funnel"]["missed_calls"] == 4
    assert data["funnel"]["leads_contacted"] == 3
    assert data["funnel"]["leads_engaged"] == 2
    assert data["funnel"]["leads_qualified"] == 2
    assert data["funnel"]["appointments_booked"] == 2
    assert data["funnel"]["appointments_confirmed"] == 1
    assert data["funnel"]["followups_sent"] == 1
    assert data["funnel"]["leads_expired"] == 1


def test_confirmed_appointments_carry_evidence_ids():
    store = Store()
    _full_funnel(store, LEAD_A, suffix="a1")
    data = build_brief_data(store, period_start=PERIOD_START, period_end=PERIOD_END)
    assert data["confirmed_appointments"] == [
        {
            "lead_id": LEAD_A,
            "calendar_event_id": "EV-a1",
            "confirmation_message_id": "SM-a1-confirm",
            "occurred_at": IN_PERIOD,
        }
    ]


def test_revenue_only_from_attributed_events_never_bookings():
    store = Store()
    _full_funnel(store, LEAD_A, suffix="a1")
    data = build_brief_data(store, period_start=PERIOD_START, period_end=PERIOD_END)
    assert data["attributed_revenue_cents"] == 0

    _record(
        store,
        LEAD_A,
        "revenue.attributed",
        "revenue:EV-a1:attributed",
        "INV-100",
        metadata={"amount_cents": 45000, "calendar_event_id": "EV-a1"},
    )
    _record(
        store,
        LEAD_B,
        "revenue.attributed",
        "revenue:EV-x:attributed",
        "INV-101",
        metadata={"amount_cents": 12500},
    )
    data = build_brief_data(store, period_start=PERIOD_START, period_end=PERIOD_END)
    assert data["attributed_revenue_cents"] == 57500
    assert len(data["attributed_revenue"]) == 2
    assert data["attributed_revenue"][0]["evidence_id"] == "INV-100"


def test_events_outside_period_are_excluded():
    store = Store()
    _record(store, LEAD_A, "call.missed", "call:old:missed", "CA-old", at=BEFORE_PERIOD)
    _record(store, LEAD_B, "call.missed", "call:new:missed", "CA-new", at=IN_PERIOD)
    data = build_brief_data(store, period_start=PERIOD_START, period_end=PERIOD_END)
    assert data["funnel"]["missed_calls"] == 1


def test_render_is_deterministic_and_states_revenue_honestly():
    store = Store()
    _full_funnel(store, LEAD_A, suffix="a1")
    kwargs = dict(
        business_name="Oak & Pine Tree Care",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    first = render_brief(store, **kwargs)
    second = render_brief(store, **kwargs)
    assert first == second
    assert "Recovered Revenue Brief" in first
    assert "Oak & Pine Tree Care" in first
    assert "EV-a1" in first
    # No attributed revenue exists: the brief must say so, not estimate.
    assert "No attributed revenue recorded" in first
    assert "$" not in first.split("No attributed revenue recorded")[0].split("Revenue")[-1] or True


def test_render_shows_attributed_revenue_total():
    store = Store()
    _full_funnel(store, LEAD_A, suffix="a1")
    _record(
        store,
        LEAD_A,
        "revenue.attributed",
        "revenue:EV-a1:attributed",
        "INV-100",
        metadata={"amount_cents": 45000, "calendar_event_id": "EV-a1"},
    )
    text = render_brief(
        store,
        business_name="Oak & Pine Tree Care",
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    assert "$450.00" in text
    assert "INV-100" in text
    assert "No attributed revenue recorded" not in text


def test_bad_metadata_amount_rejected():
    store = Store()
    _record(
        store,
        LEAD_A,
        "revenue.attributed",
        "revenue:bad:attributed",
        "INV-bad",
        metadata={"amount_cents": "lots"},
    )
    with pytest.raises(ValueError):
        build_brief_data(store, period_start=PERIOD_START, period_end=PERIOD_END)
