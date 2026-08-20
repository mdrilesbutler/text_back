# text_back — Product Requirements Document

Status: Local core implemented and tested (50 tests); telecom + Google credentials pending human gates  
Updated: 2026-08-20  
Owner: Michael Riley  
Canonical path: `/home/ubuntu/projects/text_back` on hermes-vcn-0 (piclaw mirror: `/home/mdriles/projects/text_back`)  
Remote: `git@github.com:mdrilesbutler/text_back.git`, branch `local/tdd-core`  
Catalog: this build is the template for the **fluxworks catalog** — every business-specific value must live in config, never code, so it can be redeployed per client.

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
- Number wiring (`wiring_mode` config, added 2026-08-20): `forwarded` (default) attaches to the client's EXISTING number via carrier conditional call forwarding — any call arriving at our number is by definition missed, so the first voice event per call_sid triggers exactly one text-back. `managed` keeps the terminal-unanswered rule for ported/platform-owned numbers. Per-carrier onboarding codes and the mandatory live verification checklist live in `docs/ONBOARDING-FORWARDING.md`.
- Calendar credentials: service-account approach chosen over OAuth desktop client (2026-08-20) — fully CLI-scriptable and catalog-reproducible; the client shares their calendar with the service account's email instead of completing an OAuth consent flow.
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

## Cost refresh (2026-08-20)

Re-verified before purchase, as required. SignalWire estimate for 100 forwarded 3-min calls + 400 SMS segments, INCLUDING carrier passthrough and the Low Volume Mixed 10DLC campaign: **≈ $9.44/month** — fits the approved $15/month ceiling. One-time setup ≈ $12 (brand $4.50 + DCA vetting $7.50) plus $5 minimum account funding (stays as credit). Twilio equivalent ≈ $14.10/month. Caveats: SignalWire's live site now hides per-unit rates (number/SMS rates archive-verified from 2026 snapshots of SignalWire's own pricing pages); the $1.50/month Low Volume Mixed tier requires an **EIN** — whether SignalWire's dashboard offers a sole-proprietor tier (no EIN, $2/month at registry level) is UNVERIFIED, and Twilio verifiably does offer it. 10DLC approval takes ~1–2 weeks (brand 3–5 business days + campaign 3–5 days). New accounts start in trial mode; exiting requires a card + ≥$5 funding.

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

## Current open items (2026-08-20)

1. Michael: SignalWire signup in browser (spend approval GIVEN 2026-08-20, $15/month ceiling): create Space, add card, fund $5, buy one local number, start 10DLC brand registration. Also answer: does he have an EIN? (Decides the cheap 10DLC tier vs. possibly flipping to Twilio's sole-prop path.)
2. Michael: Google sign-in for `mdrilesbutler@gmail.com` hit an "access blocked" page mid-flow (2026-08-20); exact error wording still unreported. Fallbacks documented in NEXT-SESSION.md.
3. After gcloud auth lands: scripted GCP setup — create project, enable `calendar-json.googleapis.com`, create service account + key to `~/.config/text_back/sa_key.json` (never git), Michael shares the pilot calendar with the SA email.
4. Code, unblocked now: env-loader (config documented in `.env.example` but nothing reads the environment yet); voicemail-style greeting on forwarded calls (conditional forwarding replaces carrier voicemail); parse `preferred_time` into a slot and wire collected fields into `booking.py`.
5. Live SignalWire + Google Calendar adapters once credentials exist; keep confirmation gated on provider event ID.
6. Deploy through Paperclip Hermes on Hostinger; real-phone end-to-end smoke test.
7. Before first client launch: replace pilot identity/calendar/phone with client-owned values; per-client 10DLC registration.

## Session record — 2026-08-20 (hermes-vcn-0, Claude)

Done:
- Committed the previously uncommitted TDD core and pushed the repo to GitHub (`mdrilesbutler/text_back`).
- Conversation field collection (service → location → preferred_time → name), deterministic slot-filling, no LLM. 19 new tests.
- `wiring_mode` (`forwarded` default / `managed`) so the product attaches to a client's existing number via conditional call forwarding. 12 new tests. Suite: 50 passing.
- `docs/ONBOARDING-FORWARDING.md`: per-carrier conditional-forwarding runbook (Verizon/T-Mobile first-party-verified; AT&T/Cricket flagged UNVERIFIED) with mandatory live verification checklist.
- SignalWire pricing refresh (see Cost refresh above); fits the approved $15 ceiling.
- Installed gcloud CLI (ARM tarball) at `~/google-cloud-sdk` on hermes-vcn-0.
- Renamed `PRD.md` → `PRD-text_back.md` (labeled-PRD convention).

Mistakes made and how they were corrected:
- `gcloud auth login --no-launch-browser` crashes with EOFError under the non-interactive `!` runner — corrected by running it in the background with stdin held open via `tail -f <codefile> |`, so the verification code can be appended to the file later.
- `git commit` failed on this host (no git identity configured) — corrected with `git -c user.name="Michael Riley" -c user.email="mdriles@gmail.com" commit ...`, matching the repo's existing author.
- Google sign-in then hit "access blocked" (likely in-app webview or account/session flag) — unresolved; fallback ladder documented.
- Initial plan used an OAuth desktop client for Calendar; corrected to a service account, which is scriptable and avoids the consent-screen UI entirely.

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

## Resume prompt

The full 100%-pickup prompt lives in `NEXT-SESSION.md` § Resume prompt (rewritten every handoff — that copy is canonical). Short form: `cd ~/projects/text_back`, start the agent, say **continue project**; the AGENTS.md cold-resume rule routes it through `NEXT-SESSION.md`.
