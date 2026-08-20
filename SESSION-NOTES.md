# text_back — Session Notes

## 2026-08-20 — environment-backed app configuration

Added an environment loader for every documented `TEXT_BACK_*` setting.
`create_app()` now reads webhook secret, public base URL, SQLite path, and
`wiring_mode` from the process environment while preserving explicit keyword
arguments as the higher-precedence test/adapter seam. The SQLite path is wired
into `Store`, and `/health` reports only non-secret effective configuration.

### Evidence
- Focused configuration tests: 2 passed.
- Full suite: `.venv/bin/pytest tests/` — 52 passed.
- No credentials or production values added to the repository.

## 2026-08-20 — wiring_mode: attach to a client's existing number via forwarding

Added `wiring_mode` support so text_back can wire onto a client's existing
public phone number via conditional call forwarding, instead of requiring
the client to hand out our number directly. Test-first (RED confirmed
before implementation).

### Implemented
- `policy.py`: `WIRING_MODE_FORWARDED` ("forwarded"), `WIRING_MODE_MANAGED`
  ("managed"), `WIRING_MODES`.
- `app.py`: `create_app(..., wiring_mode: str = WIRING_MODE_FORWARDED)` —
  same config-flow pattern as `webhook_secret`/`public_base_url`; invalid
  values raise `ValueError`; `app.state.wiring_mode` is threaded into
  `handle_voice_event`; `/health` now reports `wiring_mode`.
- `handlers.py`: `handle_voice_event` takes `wiring_mode` as a required
  keyword argument. In `managed` mode, behavior is unchanged from before —
  only a terminal-unanswered `CallStatus` triggers the intro SMS. In
  `forwarded` mode, the terminal-status check is skipped entirely: the
  first voice webhook for a given `call_sid` triggers exactly one intro SMS
  regardless of `CallStatus`, because the carrier only ever forwards to us
  after no-answer/busy on the client's real line — an inbound call to our
  number already IS a missed call. Exactly-once delivery across
  ringing/completed webhook retries for the same call still comes from the
  existing `store.claim_event("voice", call_sid, "missed_call_intro")`
  idempotency gate (unchanged). Opt-out suppression and the
  from/to direction (text the original caller, from our number) are
  unchanged and apply in both modes.
- `.env.example`: documented `TEXT_BACK_WIRING_MODE` (forwarded/managed).
- `README.md`: new "Wiring mode" section.
- `NEXT-SESSION.md`: gotcha that "terminal status only" is a `managed`-mode
  rule; `forwarded` mode triggers on arrival.
- No LLM — deterministic mode dispatch only, per project non-goals.

### Evidence
- `.venv/bin/pytest tests/` — 50 passed (38 prior + 12 new, in
  `tests/test_wiring_mode.py`) on 2026-08-20. Existing
  `tests/test_webhooks.py` now pins `wiring_mode="managed"` explicitly
  since it documents the (unchanged) legacy/managed behavior; the app-level
  default flipped to `forwarded`.

### Not done
- No env-var loader reads `TEXT_BACK_WIRING_MODE` yet — same as the other
  `.env.example` values, which are documented but not yet parsed from the
  environment anywhere in this repo (see `__main__.py`); wiring env parsing
  is a pre-existing gap, not introduced here.

## 2026-08-20 — conversation field collection (deterministic)

Added slot-filling collection of service, location, preferred time, and name
to inbound SMS "conversation" replies. Test-first (RED confirmed before
implementation).

### Implemented
- `policy.py`: `CONVERSATION_FIELDS` (fixed order: service, location,
  preferred_time, name), `FIELD_PROMPTS`, `next_missing_field()`,
  `conversation_prompt()`, `conversation_summary_sms()`.
- `store.py`: `conversation_fields` table keyed `(phone, field)`; added
  `get_conversation_fields`, `set_conversation_field`, `clear_conversation_fields`.
- `handlers.py`: `_collect_conversation_field()` — each non-STOP/HELP,
  non-opted-out inbound SMS is treated as the verbatim answer to the next
  missing field, in fixed order. STOP/HELP/opt-out still short-circuit ahead
  of field collection (unchanged). Blank replies re-prompt the same field
  without storing an empty value. Once all four fields are collected, further
  replies neither overwrite fields nor re-prompt.
- No LLM or NLP extraction — deterministic sequencing only, per project
  non-goals.

### Evidence
- `.venv/bin/pytest tests/` — 38 passed (19 prior + 19 new) on 2026-08-20.

### Not done
- No wiring from collected fields into `booking.py` (still requires a
  parsed `datetime`, which `preferred_time` is deliberately kept as raw
  text, not parsed). No conversation reset after a booking is made.

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
