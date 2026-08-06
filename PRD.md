# text_back — Product Requirements Document

Status: Approved project; discovery/architecture complete; implementation not started  
Updated: 2026-08-06  
Owner: Michael Riley  
Canonical path: `/home/mdriles/projects/text_back`

## Product

A production missed-call recovery and scheduling assistant for arborists, guides, and similar field-service businesses.

## Customer flow

1. A customer calls the business's programmable local number.
2. The telecom provider rings the operator's normal mobile phone.
3. If unanswered, the system texts: “Hey, sorry we missed your call—this is Mike’s scheduling assistant. What were you calling about?”
4. AI replies naturally and gathers job/service type, location, and preferred time.
5. The system checks Google Calendar availability and books the appointment.
6. It confirms the appointment by SMS.
7. STOP, HELP, consent, quiet-hour, and human-handoff rules are enforced.

## Product objective

Recover missed-call revenue without forcing the operator to adopt a new phone, app, or CRM. The system must be inexpensive, reliable, auditable, and simple enough for a small service business.

## Recommended architecture

- Application/runtime: Paperclip Hermes-operated application on Hostinger.
- Telecom: SignalWire is the current cost-first recommendation; Twilio remains the documentation/ecosystem fallback.
- Public number: programmable carrier number, not Google Voice.
- Calendar: Google Calendar through `mdrilesbutler@gmail.com` for the pilot; client-owned Google accounts in production.
- State: persistent conversation/contact/appointment records with idempotency keys and webhook-event audit history.
- AI: bounded conversational extraction and response generation; deterministic policy engine controls booking, opt-out, and escalation.
- Secrets: environment/secret store only; never repository or Obsidian.

## Requirements

### Voice and missed-call detection
- Provision one local voice/SMS-capable number.
- Forward/ring the configured operator phone.
- Send the initial text only after an unanswered/failed/no-answer disposition.
- Prevent duplicate texts from webhook retries.
- Allow configurable ring timeout and business hours.

### SMS conversation
- Maintain per-caller conversation state.
- Collect service/job type, location, preferred date/time, customer name, and any safety-critical notes.
- Ask one concise question at a time.
- Never claim an appointment is booked until Calendar returns a confirmed event ID.
- Time out or hand off uncertain, hostile, emergency, complex, or repeated-failure conversations.

### Calendar booking
- Query free/busy before offering or accepting a slot.
- Use a configurable appointment duration, travel buffer, timezone, and working hours.
- Recheck availability immediately before event creation.
- Create an event containing caller number, request summary, address/location, and conversation reference.
- Store the provider event ID and send a text confirmation.

### Compliance and human control
- STOP and standard opt-out keywords immediately suppress non-essential messaging.
- HELP returns accurate business/contact information.
- Respect A2P registration, carrier rules, consent, and quiet hours.
- Human handoff pauses AI and alerts the operator with a concise summary.
- Never send marketing content in this transactional workflow.
- Keep an audit log of inbound/outbound messages, booking actions, consent, opt-out, and handoff.

### Operations
- Health endpoint and structured logs.
- Webhook signature validation.
- Retry handling with idempotency.
- Spend guardrails and usage alerts.
- Admin configuration for business identity, phone, calendar, hours, service area, durations, and handoff destination.
- Backup and recovery appropriate to the Hostinger/Paperclip deployment.

## Acceptance criteria

- An unanswered test call produces exactly one initial SMS.
- A complete test conversation gathers the required fields without inventing information.
- Booking occurs only in a free slot and creates exactly one Google Calendar event.
- Confirmation contains the correct date, time, timezone, and business identity.
- STOP suppresses further automated conversation; HELP and human handoff work.
- Duplicate and out-of-order webhooks do not duplicate texts or appointments.
- Telecom webhook signatures are rejected when invalid.
- End-to-end production smoke test passes from a real phone after explicit paid-service approval.

## Cost decision (verified from public pricing on 2026-08-06)

SignalWire is the current recommendation:
- Local number: $0.50/month.
- Local 10DLC SMS: $0.00415 per inbound/outbound segment before carrier fees.
- Voice: $0.0066/min inbound and $0.0080/min outbound.
- Low Volume Mixed campaign: $1.50/month.
- Brand registration: $4.50 one time; listed DCA vetting: $7.50 one time.
- Example at 100 three-minute forwarded calls and 400 SMS segments: about $8.04/month before carrier fees and AI usage.

Twilio comparison:
- Local number: $1.15/month.
- SMS: $0.0083 per segment before carrier fees.
- Voice: $0.0085/min inbound and $0.0140/min outbound.
- Same example base: about $11.22/month before registration, carrier, and AI fees.

Pricing can change and must be rechecked before purchase. Sources:
- https://signalwire.com/pricing/messaging
- https://signalwire.com/pricing/voice
- https://www.twilio.com/en-us/sms/pricing/us
- https://www.twilio.com/en-us/voice/pricing/us

## Approval gates

No telecom account activation, number purchase, paid usage, production messaging, or customer traffic without Michael’s explicit approval. After approval, SignalWire/Twilio authentication and Google Calendar OAuth require Michael’s one-time browser actions. No credential values belong in project files.

## Current open items

1. Michael: approve a paid telecom provider and a spending ceiling; recommended: SignalWire, $15/month ceiling.
2. Michael: complete one-time telecom authentication/account verification when prompted.
3. Michael: complete Google Calendar OAuth for `mdrilesbutler@gmail.com` when prompted.
4. Hermes/Paperclip: implement, test, deploy, and operate the Hostinger application.
5. Before first client launch: replace pilot business identity/calendar/phone configuration with client-owned values and complete required messaging registration.

## Session record — 2026-08-06

Done:
- Confirmed the correct production flow and Google Voice exclusion.
- Compared current Twilio and SignalWire public pricing.
- Selected SignalWire as the cost-first recommendation, with Twilio as fallback.
- Created the canonical project and cold-resume documentation.

Not done:
- No carrier account, number, OAuth grant, application code, deployment, or paid service was created.

Mistakes avoided/corrections:
- Do not treat Google Voice as a programmable production telecom backend.
- Do not send the missed-call SMS merely because ringing started; wait for a terminal unanswered disposition.
- Do not let AI directly override opt-out, availability, or booking policy.
