"""Operator-only writes for completed jobs and attributed revenue.

These facts never come from SMS, bookings, or the language model. An operator
supplies external evidence (CRM job ticket, invoice, payment reference). A
booking remains pipeline; revenue is recorded only after a completed job.
"""

from __future__ import annotations

from text_back.store import Store


def _require_text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


def record_job_completed(
    store: Store,
    *,
    lead_id: str,
    evidence_id: str,
    occurred_at: str | None = None,
    calendar_event_id: str | None = None,
) -> bool:
    """Append ``job.completed`` from operator/CRM evidence. Idempotent."""
    lead_id = _require_text(lead_id, "lead_id")
    evidence_id = _require_text(evidence_id, "evidence_id")
    metadata: dict[str, object] = {"source": "operator"}
    if calendar_event_id:
        metadata["calendar_event_id"] = calendar_event_id
    return store.record_outcome(
        lead_id=lead_id,
        event_type="job.completed",
        idempotency_key=f"job:{lead_id}:{evidence_id}:completed",
        evidence_id=evidence_id,
        metadata=metadata,
        occurred_at=occurred_at,
    )


def record_revenue_attributed(
    store: Store,
    *,
    lead_id: str,
    evidence_id: str,
    amount_cents: int,
    occurred_at: str | None = None,
    calendar_event_id: str | None = None,
    job_evidence_id: str | None = None,
) -> bool:
    """Append ``revenue.attributed`` only after a matching ``job.completed``.

    ``amount_cents`` must be a non-negative int. ``evidence_id`` is the
    invoice or payment reference. Bookings are not accepted as completion.
    """
    lead_id = _require_text(lead_id, "lead_id")
    evidence_id = _require_text(evidence_id, "evidence_id")
    if type(amount_cents) is not int or amount_cents < 0:
        raise ValueError("amount_cents must be a non-negative integer")

    jobs = [
        event
        for event in store.list_outcome_events(lead_id)
        if event["event_type"] == "job.completed"
    ]
    if job_evidence_id:
        jobs = [event for event in jobs if event["evidence_id"] == job_evidence_id]
    if not jobs:
        raise ValueError(
            "revenue.attributed requires a job.completed event for this lead"
        )

    metadata: dict[str, object] = {
        "amount_cents": amount_cents,
        "source": "operator",
        "job_evidence_id": jobs[-1]["evidence_id"],
    }
    if calendar_event_id:
        metadata["calendar_event_id"] = calendar_event_id
    return store.record_outcome(
        lead_id=lead_id,
        event_type="revenue.attributed",
        idempotency_key=f"revenue:{lead_id}:{evidence_id}:attributed",
        evidence_id=evidence_id,
        metadata=metadata,
        occurred_at=occurred_at,
    )
