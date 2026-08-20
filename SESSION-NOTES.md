# text_back — Session Notes

## 2026-08-14 — hermes-cloud local TDD core

Built and verified locally on `hermes-vcn-0`. No paid telecom, number, OAuth, or production SMS.

### Implemented
- FastAPI app with `GET /health`, `POST /webhooks/voice`, `POST /webhooks/sms`
- Twilio-compatible signature verification; missing/invalid signatures return 403
- Terminal unanswered (`no-answer`/`busy`/`failed`/`canceled`) sends exactly one intro SMS
- Ringing/initiated does not text
- Idempotency via SQLite `(source, event_id, action)`
- Deterministic STOP/HELP policy; STOP suppresses later missed-call intros
- Calendar stub: free/busy, recheck, persist event ID, confirmation only after event ID
- Opt-out blocks booking confirmation

### Evidence
- `.venv/bin/pytest tests/` — 19 passed on 2026-08-14

### External actions not taken
No number purchased, paid service activated, credentials stored, OAuth grant created, production traffic sent, or Hostinger deploy.

## 2026-08-06 — Project creation

Michael approved `text_back` as a legitimate project under `/home/mdriles/projects`.

### Decisions
- Build a missed-call text-back and Google Calendar scheduling product for arborists, guides, and similar field services.
- Host and operate the application through Paperclip Hermes on Hostinger.
- Use a programmable carrier number; do not use Google Voice.
- Use `mdrilesbutler@gmail.com` for the pilot Google Calendar integration.
- Prefer SignalWire on cost; keep Twilio as fallback.
- Recommended initial telecom cap: $15/month with no purchase until Michael explicitly approves.

### Pricing snapshot
SignalWire’s public pricing produced an estimated base of $8.04/month for 100 calls at three forwarded minutes each plus 400 SMS segments, before carrier fees and AI use. Listed setup fees for a low-volume 10DLC campaign total approximately $12. Pricing must be refreshed before purchase.

### Compliance baseline
Transactional scheduling only. Enforce STOP/HELP, quiet hours, consent, carrier registration, deterministic booking rules, signature validation, idempotency, and human handoff.

### External actions not taken
No number purchased, paid service activated, credentials stored, OAuth grant created, production traffic sent, or deployment performed.
