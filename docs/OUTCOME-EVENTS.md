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
| `followup.sent` | outbound provider message ID | A due no-response follow-up SMS is accepted by the transport; metadata records the attempt number |
| `lead.expired` | originating call SID | The bounded sequence's expiry deadline passes with no response after the final attempt; metadata records attempts_sent |

The booking code records `calendar.event_created` before persistence and
`appointment.confirmed` only after the confirmation transport succeeds. A
booking or message failure therefore cannot appear as confirmed evidence.

## Follow-up sequence (src/text_back/followup.py)

A bounded no-response sequence is scheduled only after an accepted intro SMS
(provider evidence exists). `run_due_followups` is a pure function of
(store, telecom, policy, injected now) — no live cron, queue, or provider
send is wired. Configured by `TEXT_BACK_FOLLOWUP_DELAYS_MINUTES` (default
`120,1440`), `TEXT_BACK_FOLLOWUP_EXPIRY_MINUTES` (default `2880`), and
`TEXT_BACK_QUIET_HOURS_START`/`END` (default `21:00`/`08:00`, business
timezone). Sends due inside quiet hours defer to quiet-end. The sequence
cancels immediately on any customer reply, STOP/opt-out, successful booking,
or active handoff, and re-running the processor at the same instant is
idempotent via `claim_event`. Follow-up bodies contain no customer content.

## Recovered Revenue Brief (src/text_back/brief.py)

`build_brief_data`/`render_brief` are deterministic projections of this ledger
for a period. Funnel counts are unique-lead based (missed calls count raw
events); confirmed appointments list calendar + confirmation evidence IDs; the
revenue section sums only explicit `revenue.attributed` events carrying an
integer `amount_cents` and an external evidence ID (invoice/payment ref) and
says "No attributed revenue recorded" otherwise — it never estimates from
bookings. `record_outcome` accepts an optional `occurred_at` for backdated
attribution entries.

## Not implemented yet

- `job.completed`;
- operator/CRM evidence capture for completion and job value (the
  `revenue.attributed` write path is manual/operator-driven for now);
- a derived current-state projection.

Future projections and reports must read this ledger without rewriting its
history. A booking is pipeline evidence, not completed work or recovered
revenue.
