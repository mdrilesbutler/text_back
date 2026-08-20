# text_back

Missed-call recovery and scheduling assistant for field-service businesses.

Canonical requirements: `PRD.md`
Cold resume: `NEXT-SESSION.md`
Session history: `SESSION-NOTES.md`
Local implementation plan: `IMPLEMENTATION-PLAN.md`

## Current state (2026-08-14, hermes-cloud)

Local core exists and is tested on this host. No production number, no paid telecom, no Google OAuth.

```bash
cd /home/ubuntu/projects/text_back
.venv/bin/pytest tests/
.venv/bin/python -m text_back   # 127.0.0.1:8000 only
```

Covered locally: webhook signature fail-closed, missed-call intro (both wiring modes), idempotent retries, STOP/HELP policy, Calendar stub booking with event-id gate.

Human gates remaining: paid telecom approval + number; Google Calendar OAuth for `mdrilesbutler@gmail.com`.

## Wiring mode

`wiring_mode` controls how our number relates to the client's real phone
line. It is a `create_app()` config value (see `.env.example` for the
`TEXT_BACK_WIRING_MODE` env var, wired the same way as the other app
settings) with two values:

- **`forwarded`** (default) — the client keeps their existing public number
  and sets up conditional call forwarding to our number for no-answer/busy.
  Because the carrier only ever connects a call to us *after* the client's
  own line already went unanswered, an inbound call to our number already
  IS a missed call. The first voice webhook we receive for a given
  `CallSid` triggers exactly one intro SMS, regardless of `CallStatus`
  (`ringing`, `in-progress`, `completed`, etc.). Idempotency is enforced via
  the same `claim_event` mechanism keyed on `call_sid`, so carrier webhook
  retries (e.g. a `ringing` webhook followed by a `completed` webhook for
  the same call) still send exactly one SMS.
- **`managed`** — our number is the client's number directly (the original/
  legacy behavior). Only a terminal-unanswered `CallStatus`
  (`no-answer`/`busy`/`failed`/`canceled`) counts as a missed call; other
  statuses (e.g. `ringing`) are ignored.

In both modes: opt-out (STOP) suppression is checked before any SMS is
sent, and the intro SMS goes to the original caller (`From` on the voice
webhook) from our number (`To`) — never to/from the client's own line.
