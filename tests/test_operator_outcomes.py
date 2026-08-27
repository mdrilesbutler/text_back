from datetime import datetime, timezone

import pytest

from text_back.brief import build_brief_data
from text_back.operator import record_job_completed, record_revenue_attributed
from text_back.store import Store


LEAD = "+155****0001"
WHEN = "2026-08-10T12:00:00+00:00"
PERIOD_START = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
PERIOD_END = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)


def test_job_completed_requires_external_evidence():
    store = Store()
    with pytest.raises(ValueError):
        record_job_completed(store, lead_id=LEAD, evidence_id="")
    with pytest.raises(ValueError):
        record_job_completed(store, lead_id="", evidence_id="JOB-1")


def test_job_completed_writes_ledger_event_and_is_idempotent():
    store = Store()
    assert record_job_completed(
        store,
        lead_id=LEAD,
        evidence_id="CRM-441",
        occurred_at=WHEN,
        calendar_event_id="EV-a1",
    )
    events = store.list_outcome_events(LEAD)
    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "job.completed"
    assert event["evidence_id"] == "CRM-441"
    assert event["occurred_at"] == WHEN
    assert event["metadata"]["source"] == "operator"
    assert event["metadata"]["calendar_event_id"] == "EV-a1"
    assert record_job_completed(
        store, lead_id=LEAD, evidence_id="CRM-441", occurred_at=WHEN
    ) is False
    assert len(store.list_outcome_events(LEAD)) == 1


def test_booking_is_not_job_completion():
    store = Store()
    store.record_outcome(
        lead_id=LEAD,
        event_type="calendar.event_created",
        idempotency_key="calendar:EV-a1:created",
        evidence_id="EV-a1",
        occurred_at=WHEN,
    )
    with pytest.raises(ValueError, match="job.completed"):
        record_revenue_attributed(
            store,
            lead_id=LEAD,
            evidence_id="INV-100",
            amount_cents=45000,
        )


def test_revenue_requires_integer_cents_and_invoice_evidence():
    store = Store()
    record_job_completed(store, lead_id=LEAD, evidence_id="CRM-441", occurred_at=WHEN)
    with pytest.raises(ValueError):
        record_revenue_attributed(
            store, lead_id=LEAD, evidence_id="INV-100", amount_cents="45000"
        )
    with pytest.raises(ValueError):
        record_revenue_attributed(
            store, lead_id=LEAD, evidence_id="INV-100", amount_cents=-1
        )
    with pytest.raises(ValueError):
        record_revenue_attributed(
            store, lead_id=LEAD, evidence_id="INV-100", amount_cents=True
        )
    with pytest.raises(ValueError):
        record_revenue_attributed(
            store, lead_id=LEAD, evidence_id="", amount_cents=45000
        )


def test_revenue_requires_matching_completed_job():
    store = Store()
    record_job_completed(store, lead_id=LEAD, evidence_id="CRM-441", occurred_at=WHEN)
    with pytest.raises(ValueError, match="job.completed"):
        record_revenue_attributed(
            store,
            lead_id=LEAD,
            evidence_id="INV-100",
            amount_cents=45000,
            job_evidence_id="CRM-MISSING",
        )


def test_revenue_attributed_writes_after_completed_job_and_is_idempotent():
    store = Store()
    record_job_completed(store, lead_id=LEAD, evidence_id="CRM-441", occurred_at=WHEN)
    assert record_revenue_attributed(
        store,
        lead_id=LEAD,
        evidence_id="INV-100",
        amount_cents=45000,
        occurred_at=WHEN,
        calendar_event_id="EV-a1",
        job_evidence_id="CRM-441",
    )
    events = [e for e in store.list_outcome_events(LEAD) if e["event_type"] == "revenue.attributed"]
    assert len(events) == 1
    event = events[0]
    assert event["evidence_id"] == "INV-100"
    assert event["metadata"]["amount_cents"] == 45000
    assert event["metadata"]["job_evidence_id"] == "CRM-441"
    assert event["metadata"]["source"] == "operator"
    assert record_revenue_attributed(
        store,
        lead_id=LEAD,
        evidence_id="INV-100",
        amount_cents=45000,
        job_evidence_id="CRM-441",
    ) is False
    data = build_brief_data(store, period_start=PERIOD_START, period_end=PERIOD_END)
    assert data["attributed_revenue_cents"] == 45000
    assert data["attributed_revenue"][0]["evidence_id"] == "INV-100"
