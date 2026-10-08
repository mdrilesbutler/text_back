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
| `lead.opted_out` | inbound provider message ID | A reply matches a carrier/FCC opt-out keyword or phrase; automated texts stop |
| `lead.opted_in` | inbound provider message ID | START/UNSTOP/SUBSCRIBE, or a bare YES from an opted-out contact, re-subscribes them |
| `lead.field_captured` | inbound provider message ID | One deterministic field is persisted; metadata names the field only |
| `lead.qualified` | final inbound provider message ID | All required fields are present |
| `lead.handoff_requested` | notifier alert ID | The handoff notifier accepts the operator payload |
| `calendar.slot_checked` | requested zoned start time | The free/busy check completes; metadata records availability and check count |
| `calendar.event_created` | calendar event ID | Calendar returns a non-empty event ID |
| `appointment.confirmed` | outbound provider message ID | The confirmation transport accepts the SMS; metadata links the calendar event ID |
| `followup.sent` | outbound provider message ID | A due no-response follow-up SMS is accepted by the transport; metadata records the attempt number |
| `lead.expired` | originating call SID | The bounded sequence's expiry deadline passes with no response after the final attempt; metadata records attempts_sent |
| `handoff.alert_delivered` | transport receipt ID | The delivery transport accepts the queued operator alert; metadata records channel and attempt |
| `handoff.alert_dead_lettered` | outbox alert ID | Bounded retries exhaust without transport acceptance; metadata records channel, attempts, truncated last_error |
| `job.completed` | CRM/job ticket ID | Operator records external completion proof via `record_job_completed`; metadata may link a calendar event ID |
| `revenue.attributed` | invoice/payment reference | Operator records job value via `record_revenue_attributed` only after a matching `job.completed`; metadata stores integer `amount_cents` and `job_evidence_id` |

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

## Handoff alert delivery (src/text_back/delivery.py)

Every handoff activation enqueues exactly one row in the `handoff_deliveries`
outbox (keyed by the notifier alert ID). `run_due_deliveries` is a pure
function of (store, transport, policy, injected now) — no live cron, queue,
or network transport is wired. The default channel `disabled`
(`TEXT_BACK_HANDOFF_DELIVERY_CHANNEL`) parks rows durably with zero attempts
consumed; flipping the channel later drains the backlog. Retries follow
`TEXT_BACK_HANDOFF_DELIVERY_RETRY_MINUTES` (default `1,5,15`) and exhaustion
dead-letters the row. Delivery is at-least-once to the operator but
exactly-once in this ledger: each attempt's count and next backoff slot are
persisted before the transport is called, so a crash (or an unexpected
transport exception) mid-attempt leaves the row pending and re-runnable
rather than wedged; the `handoff.alert_delivered` idempotency key carries no
attempt number, so a crash between transport success and the status flip can
re-ping the operator without double-appending evidence. Both the delivered
and dead-letter paths append their ledger event before flipping row status,
so a crash between the two commits cannot lose evidence. Notifier alert IDs
are unique across process restarts (the outbox is file-backed), and a
colliding enqueue raises instead of silently dropping an operator alert.
Quiet hours deliberately do not apply — they protect customer SMS in the
nurture lane only, and operator alerts (including safety handoffs) are
time-critical.

## Recovered Revenue Brief (src/text_back/brief.py)

`build_brief_data`/`render_brief` are deterministic projections of this ledger
for a period. Funnel counts are unique-lead based (missed calls count raw
events); confirmed appointments list calendar + confirmation evidence IDs; the
revenue section sums only explicit `revenue.attributed` events carrying an
integer `amount_cents` and an external evidence ID (invoice/payment ref) and
says "No attributed revenue recorded" otherwise — it never estimates from
bookings. `record_outcome` accepts an optional `occurred_at` for backdated
attribution entries.

## Operator write path (`src/text_back/operator.py`)

`record_job_completed` and `record_revenue_attributed` are the only supported
way to add completion and revenue facts. They require non-empty external
evidence IDs, refuse string/boolean/negative amounts, and refuse revenue
without a matching `job.completed` for the same lead. A calendar booking is
not completion. Both writes are idempotent via stable keys. There is no HTTP
or CRM connector yet; operators call these functions (or a future approved
tooling wrapper) against the ledger.

## Not implemented yet

- derived current-state projection;
- HTTP/CRM connector for operator writes.

Future projections and reports must read this ledger without rewriting its
history. A booking is pipeline evidence, not completed work or recovered
revenue.
