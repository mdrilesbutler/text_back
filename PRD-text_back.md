# text_back — Product Requirements Document

Status: Local core + SignalWire adapters implemented and tested (104 tests); live Google Calendar, operator notification delivery, credentials, and deploy pending human gates
Updated: 2026-08-21
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

## Current open items (2026-08-20)

1. SignalWire Space is funded and one local voice/SMS-capable pilot number was purchased 2026-08-21 at $0.50/month under the existing $15/month approval. Exact number is config-only outside Git. Next browser gate: verify Michael's personal mobile for Platform Free Trial; do not submit a paid Brand/Campaign without reviewing its displayed fees. Michael is currently a sole proprietor and the LLC is pending.
2. Michael: Google sign-in for `mdrilesbutler@gmail.com` hit an "access blocked" page mid-flow (2026-08-20); exact error wording still unreported. Fallbacks documented in NEXT-SESSION.md.
3. After gcloud auth lands: scripted GCP setup — create project, enable `calendar-json.googleapis.com`, create service account + key to `~/.config/text_back/sa_key.json` (never git), Michael shares the pilot calendar with the SA email.
4. Code, done locally: explicit `preferred_time` values are parsed in the configured timezone and all four collected fields feed the free/busy-rechecked Calendar stub booking gate. Vague, past, nonexistent, ambiguous, and unavailable times do not produce confirmations. The local voicemail-style forwarded greeting is implemented with `<Say>` + `<Hangup>` and no retained recording.
5. Finish live SignalWire attachment and the Google Calendar adapter once credentials exist. The outbound REST adapter and inbound `X-SignalWire-Signature`/cXML boundary are implemented locally but not configured or exercised against a live account; keep confirmation gated on the Calendar event ID.
6. Deploy through Paperclip Hermes on Hostinger; real-phone end-to-end smoke test.
7. Before first client launch: replace pilot identity/calendar/phone with client-owned values; per-client 10DLC registration.
8. Connect the tested handoff payload to an approved operator delivery adapter; the current notifier is in-memory only and sends nothing externally.

## Session record — 2026-08-21 (hermes-vcn-0, Codex)

- Michael purchased one SignalWire local voice/SMS-capable pilot number at $0.50/month. No production traffic was routed and no message was sent.
- Stored the exact pilot number only in protected local config at `~/.config/text_back/pilot.env` (mode 600), preserving the catalog rule that client-specific values stay out of code and Git.
- Added a SignalWire Compatibility REST outbound-SMS adapter with HTTPS enforcement, least-secret configuration, configured-sender enforcement, provider message-ID validation, and redacted provider failures.
- Added environment selection via `TEXT_BACK_TELECOM_MODE=stub|signalwire`; SignalWire mode fails closed when required settings are missing, and `/health` exposes only the non-secret provider name.
- Added deterministic preferred-time parsing, configurable timezone/duration, and end-to-end conversation-to-Calendar-stub booking. Confirmations remain gated on an event ID; the live Google adapter is not implemented.
- Added deterministic customer-requested/safety handoff state, automation pause/resume, and concise operator alert payloads. The notifier is an in-memory stub; no operator alert was delivered.
- SignalWire's documented Platform Free Trial is the selected no-EIN proof path: one assigned SignalWire number to one verified mobile, REST API only. Personal-mobile verification is still pending.
- Evidence: `.venv/bin/pytest tests/` — 104 passed. No API token, signing key, EIN, customer message content, or production value was committed.

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
