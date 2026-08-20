# text_back — local test-first implementation plan

Updated: 2026-08-14 (hermes-cloud)
Scope: local app only. No number purchase, no production SMS, no Google OAuth.

## Tracer bullets (vertical)

1. Health endpoint (`GET /health`).
2. Webhook signature fail-closed (missing/invalid rejected before parse).
3. Terminal unanswered call → exactly one initial SMS (not on ringing/initiated).
4. Webhook retries: same event id → no second SMS (idempotency).
5. Inbound SMS: STOP suppresses further automated outbound; HELP returns business info.
6. Policy engine owns STOP/HELP/consent/quiet-hours/handoff — not an LLM.
7. Calendar stub: free/busy, recheck, create event, persist provider event ID before confirmation text.
8. Booking confirmation text only after a real stub event ID exists.

## Non-goals this slice

- Paid SignalWire/Twilio account or number.
- Live Google Calendar OAuth.
- Hostinger/Paperclip deploy.
- Customer traffic or LLM-driven extraction.

## Design

- FastAPI + SQLite (file or `:memory:` in tests).
- Provider adapter: `FakeTelecom` in tests; SignalWire Compatibility (Twilio-signed) adapter later.
- Side effects keyed by `provider_event_id` + action.
- Calendar is an in-process stub with explicit free/busy windows.

## Human gates (stop here)

- Michael: approve paid telecom + spend ceiling (recommended SignalWire, $15/mo).
- Michael: browser auth for carrier + Google Calendar OAuth for `mdrilesbutler@gmail.com`.
