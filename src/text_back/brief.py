"""Deterministic Recovered Revenue Brief generated from the outcome ledger.

The brief is a pure projection of ``outcome_events`` for a period. It never
estimates: a booking is pipeline evidence, and revenue appears only when an
explicit ``revenue.attributed`` event (with an integer ``amount_cents`` and an
external evidence ID such as an invoice number) has been recorded. When no
revenue is attributed, the brief says so instead of guessing.
"""

from __future__ import annotations

from datetime import datetime

from text_back.store import Store

FUNNEL_KEYS = (
    "missed_calls",
    "leads_contacted",
    "leads_engaged",
    "leads_qualified",
    "appointments_booked",
    "appointments_confirmed",
    "handoffs",
    "followups_sent",
    "leads_expired",
)

# event_type -> (funnel key, count unique leads instead of raw events)
_FUNNEL_MAP: dict[str, tuple[str, bool]] = {
    "call.missed": ("missed_calls", False),
    "sms.initial_sent": ("leads_contacted", True),
    "sms.customer_replied": ("leads_engaged", True),
    "lead.qualified": ("leads_qualified", True),
    "calendar.event_created": ("appointments_booked", True),
    "appointment.confirmed": ("appointments_confirmed", True),
    "lead.handoff_requested": ("handoffs", True),
    "followup.sent": ("followups_sent", True),
    "lead.expired": ("leads_expired", True),
}


def _in_period(event: dict, period_start: datetime, period_end: datetime) -> bool:
    occurred = datetime.fromisoformat(event["occurred_at"])
    if occurred.tzinfo is None:
        raise ValueError(f"outcome event {event['id']} has a naive occurred_at")
    return period_start <= occurred < period_end


def build_brief_data(
    store: Store,
    *,
    period_start: datetime,
    period_end: datetime,
) -> dict:
    """Aggregate ledger facts for the period. Raises on malformed evidence
    rather than silently misreporting."""
    events = [
        event
        for event in store.list_outcome_events()
        if _in_period(event, period_start, period_end)
    ]

    funnel: dict[str, int] = {key: 0 for key in FUNNEL_KEYS}
    seen_leads: dict[str, set[str]] = {key: set() for key in FUNNEL_KEYS}
    confirmed_appointments: list[dict] = []
    attributed: list[dict] = []
    attributed_total = 0

    for event in events:
        mapping = _FUNNEL_MAP.get(event["event_type"])
        if mapping is not None:
            key, unique_leads = mapping
            if unique_leads:
                if event["lead_id"] not in seen_leads[key]:
                    seen_leads[key].add(event["lead_id"])
                    funnel[key] += 1
            else:
                funnel[key] += 1

        if event["event_type"] == "appointment.confirmed":
            confirmed_appointments.append(
                {
                    "lead_id": event["lead_id"],
                    "calendar_event_id": event["metadata"].get("calendar_event_id", ""),
                    "confirmation_message_id": event["evidence_id"],
                    "occurred_at": event["occurred_at"],
                }
            )
        elif event["event_type"] == "revenue.attributed":
            amount = event["metadata"].get("amount_cents")
            if not isinstance(amount, int) or amount < 0:
                raise ValueError(
                    "revenue.attributed events require a non-negative integer "
                    f"amount_cents (event id {event['id']})"
                )
            attributed.append(
                {
                    "lead_id": event["lead_id"],
                    "evidence_id": event["evidence_id"],
                    "amount_cents": amount,
                    "calendar_event_id": event["metadata"].get("calendar_event_id", ""),
                    "occurred_at": event["occurred_at"],
                }
            )
            attributed_total += amount

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "funnel": funnel,
        "confirmed_appointments": confirmed_appointments,
        "attributed_revenue": attributed,
        "attributed_revenue_cents": attributed_total,
    }


def _dollars(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def render_brief(
    store: Store,
    *,
    business_name: str,
    period_start: datetime,
    period_end: datetime,
) -> str:
    """Render the plain-text brief. Deterministic for a given ledger + period."""
    data = build_brief_data(store, period_start=period_start, period_end=period_end)
    funnel = data["funnel"]

    lines = [
        f"Recovered Revenue Brief — {business_name}",
        f"Period: {data['period_start']} to {data['period_end']}",
        "",
        "Funnel (evidence-backed, unique leads unless noted)",
        f"  Missed calls (events):      {funnel['missed_calls']}",
        f"  Leads texted back:          {funnel['leads_contacted']}",
        f"  Leads who replied:          {funnel['leads_engaged']}",
        f"  Leads fully qualified:      {funnel['leads_qualified']}",
        f"  Appointments booked:        {funnel['appointments_booked']}",
        f"  Appointments confirmed:     {funnel['appointments_confirmed']}",
        f"  Human handoffs:             {funnel['handoffs']}",
        f"  Follow-up sequences used:   {funnel['followups_sent']}",
        f"  Leads expired (no reply):   {funnel['leads_expired']}",
        "",
    ]

    lines.append("Confirmed appointments")
    if data["confirmed_appointments"]:
        for appt in data["confirmed_appointments"]:
            lines.append(
                f"  {appt['occurred_at']}  lead {appt['lead_id']}  "
                f"event {appt['calendar_event_id']}  "
                f"confirmation {appt['confirmation_message_id']}"
            )
    else:
        lines.append("  None in this period.")
    lines.append("")

    lines.append("Revenue")
    if data["attributed_revenue"]:
        for item in data["attributed_revenue"]:
            linked = (
                f"  (calendar event {item['calendar_event_id']})"
                if item["calendar_event_id"]
                else ""
            )
            lines.append(
                f"  {item['occurred_at']}  {_dollars(item['amount_cents'])}  "
                f"evidence {item['evidence_id']}{linked}"
            )
        lines.append(
            f"  Total attributed: {_dollars(data['attributed_revenue_cents'])}"
        )
    else:
        lines.append(
            "  No attributed revenue recorded for this period. Bookings are "
            "pipeline evidence only; revenue appears here when a completed job "
            "is attributed with an invoice or payment reference."
        )
    lines.append("")
    lines.append(
        "Every number above is backed by a ledger event with a provider, "
        "calendar, or invoice evidence ID. Nothing is estimated."
    )
    return "\n".join(lines)
