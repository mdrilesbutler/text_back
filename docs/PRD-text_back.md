# text_back — Product Requirements Document

Status: Local core + SignalWire adapters implemented and tested (148 tests); Space funded and pilot number verified live via API (no handlers attached); live Google Calendar, operator notification delivery, signing key, and deploy pending human gates
Updated: 2026-08-28
Owner: Michael Riley  
Canonical path: `/home/ubuntu/projects/text_back` on hermes-vcn-0 (piclaw mirror: `/home/mdriles/projects/text_back`)  
Remote: `git@github.com:mdrilesbutler/text_back.git`, branch `local/tdd-core`  
Catalog: this build is the template for the **fluxworks catalog** — every business-specific value must live in config, never code, so it can be redeployed per client.

## Product

A production missed-call recovery and scheduling assistant for arborists, guides, and similar field-service businesses.

## Customer flow

1. A customer calls the business's existing public number.
2. The carrier rings the operator's normal mobile phone.
3. If the operator does not answer, conditional forwarding sends the call to the client's dedicated programmable number. The first voice event for that `call_sid` is the missed-call trigger in `forwarded` mode.
4. The system sends one branded transactional SMS, such as: “Sorry we missed your call—this is {{business_name}}'s scheduling assistant. What were you calling about?”
5. A bounded conversational layer gathers job/service type, location, preferred time, and name; deterministic policy controls consent, STOP/HELP, booking, quiet hours, and handoff.
6. The system checks Google Calendar availability and books only after receiving an event ID.
7. It confirms the appointment by SMS or routes the conversation to a human.

## Product objective

Recover missed-call revenue without forcing the operator to adopt a new phone, app, or CRM. The system must be inexpensive, reliable, auditable, and simple enough for a small service business.

## Commercial / GTM model (adopted 2026-08-20)

**Canonical writeup:** `docs/gtm/KOERNER-MODEL.md`
**Seed video (Michael):** https://www.youtube.com/watch?v=g4-3AxelI_Y — *This Might Be the Easiest Way to Sell AI to Businesses* (Chris Koerner). Full captions unavailable on hermes-cloud; model is grounded in matching public Koerner playbooks (assessment ladder + speed-to-lead).

**Sell the outcome, not “AI”:** after-hours / missed-call recovery with calendar-truth booking.

| SKU | What | Starter price band |
|---|---|---|
| `TB-ASSESS` | 45-min discovery → written plan in 48h | $500–$1,000 |
| `TB-RECOVER` | Recover install (forwarded number + calendar) | $1,500–$3,000 one-time |
| `TB-CARE` | Managed monthly (monitor + recovered-leads report) | $200–$500 / mo |

Default path for field-service ICP: assessment → **text_back install** as the Stage-2 product (not a custom agent build). Templates: `docs/gtm/assessment-template.md`, `docs/gtm/leave-behind.md`.

## Recommended architecture

**Canonical product model:** `docs/PRODUCT-MODEL.md` — combines Koerner’s assessment/install/care ladder, Podium’s missed-call continuity, Hatch’s speed-to-conversion journeys, Goodcall’s structured routing, and an evidence-backed Recovered Revenue Brief modeled on Tra’s reporting structure. Competitive matrix: `docs/COMPETITOR-MATRIX.md`.

**Scope decision:** Ship **Recover** first (missed call → SMS → qualify → booked/handoff → outcome brief). **Answer** (AI voice) and **Grow** (estimate/no-show/review journeys) are later add-ons only after a real-phone Recover pilot proves conversion.

- Application/runtime: Paperclip Hermes-operated application on Hostinger.
- Telecom: SignalWire is the current cost-first recommendation; Twilio remains the documentation/ecosystem fallback.
- Public number: programmable carrier number, not Google Voice.
- Number wiring (`wiring_mode` config, added 2026-08-20): `forwarded` (default) attaches to the client's EXISTING number via carrier conditional call forwarding — any call arriving at our number is by definition missed, so the first voice event per call_sid triggers exactly one text-back. `managed` keeps the terminal-unanswered rule for ported/platform-owned numbers. Per-carrier onboarding codes and the mandatory live verification checklist live in `docs/ONBOARDING-FORWARDING.md`.
- Calendar credentials: service-account approach chosen over OAuth desktop client (2026-08-20) — fully CLI-scriptable and catalog-reproducible; the client shares their calendar with the service account's email instead of completing an OAuth consent flow.
- Calendar: Google Calendar through `mdrilesbutler@gmail.com` for the pilot; client-owned Google accounts in production.
- State: persistent conversation/contact/appointment records with idempotency keys and webhook-event audit history.
- AI: bounded conversational extraction and response generation; deterministic policy engine controls booking, opt-out, and escalation.
- Secrets: environment/secret store only; never repository or Obsidian.

## Requirements

### Voice and missed-call detection
- Provision one local voice/SMS-capable number.
- Default `forwarded` mode: attach to the client's existing number with conditional forwarding and treat the first provider voice event per `call_sid` as the already-missed call.
- Optional `managed` mode: ring the configured operator and send the initial text only after a terminal `no-answer`/`busy`/`failed`/`canceled` disposition.
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
- Handoff is ASYNC lead capture, never a live-person transfer (Michael, 2026-08-29: "they don't get a human, that's the whole point"). It pauses AI, tells the customer the owner will follow up, and queues a concise summary for the operator to act on later. Customer-facing copy never promises a person or points at the business line (enforced by `tests/test_no_live_human_copy.py`).
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

## Cost planning snapshot (2026-08-20; recheck required)

The planning estimate for 100 forwarded 3-min calls + 400 SMS segments, including the previously researched carrier passthrough and Low Volume Mixed 10DLC campaign assumptions, was **≈ $9.44/month**. That fits the approved $15/month ceiling, but it is not a purchase quote. Some unit rates came from archived 2026 snapshots, and SignalWire's current registration guide (checked 2026-08-21) lists a $4 Brand submission fee rather than the $4.50 used in the earlier estimate. Recheck the authenticated dashboard's exact funding, registration, recurring, per-segment, carrier, and voice charges immediately before any paid action; stop for renewed approval if the displayed commitment exceeds the ceiling. The prior research also found that the Low Volume Mixed path requires an **EIN**; a SignalWire sole-proprietor path remains unverified.

Current official references: [Campaign Registry registration](https://signalwire.com/docs/platform/messaging/campaign-registry/registration), [phone numbers](https://signalwire.com/docs/platform/phone-numbers), and [webhook security](https://signalwire.com/docs/compatibility-api/guides/webhook-security).

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

No telecom account activation, number purchase, paid usage, production messaging, or customer traffic without Michael’s explicit approval. The SignalWire path has a $15/month ceiling, but Michael must still perform the purchase/payment steps in his browser. Google Cloud authentication and service-account setup also require his participation. No credential values belong in project files.

