# Outcome event ledger

`outcome_events` is the append-only evidence ledger for Recover. It records
facts after their supporting provider or calendar action succeeds; it is not a
mutable lead-status table and it does not infer revenue.

Each row contains:

- monotonic local `id` and UTC `occurred_at`;
- `lead_id` (currently the caller's E.164 number);
- controlled `event_type`;
- globally unique `idempotency_key` so webhook retries do not append twice;
- non-empty `evidence_id` from the call, message, handoff, slot, or calendar;
- small JSON metadata containing policy facts, not raw message bodies.

## Implemented events

| Event | Evidence ID | Recorded when |
|---|---|---|
| `call.missed` | provider call SID | Forwarded call arrives, or managed call reaches a terminal-unanswered status |
| `sms.initial_sent` | outbound provider message ID | Missed-call intro transport accepts the message |
| `sms.customer_replied` | inbound provider message ID | A unique inbound SMS is accepted, including STOP/HELP |
| `lead.field_captured` | inbound provider message ID | One deterministic field is persisted; metadata names the field only |
| `lead.qualified` | final inbound provider message ID | All required fields are present |
| `lead.handoff_requested` | notifier alert ID | The handoff notifier accepts the operator payload |
| `calendar.slot_checked` | requested zoned start time | The free/busy check completes; metadata records availability and check count |
| `calendar.event_created` | calendar event ID | Calendar returns a non-empty event ID |
| `appointment.confirmed` | outbound provider message ID | The confirmation transport accepts the SMS; metadata links the calendar event ID |

The booking code records `calendar.event_created` before persistence and
`appointment.confirmed` only after the confirmation transport succeeds. A
booking or message failure therefore cannot appear as confirmed evidence.

## Not implemented yet

- `followup.sent`, `lead.expired`, `job.completed`, and `revenue.attributed`;
- operator/CRM evidence for completion and job value;
- a derived current-state projection and Recovered Revenue Brief.

Future projections and reports must read this ledger without rewriting its
history. A booking is pipeline evidence, not completed work or recovered
revenue.
