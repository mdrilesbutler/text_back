# text_back

Missed-call recovery and scheduling assistant for field-service businesses.

- Canonical requirements: `docs/PRD-text_back.md`
- **Product model:** `docs/PRODUCT-MODEL.md` (Recover first; Answer/Grow later)
- **Competitive synthesis:** `docs/COMPETITOR-MATRIX.md`
- **GTM / sales model:** `docs/gtm/KOERNER-MODEL.md` (assessment → Recover install → Care; sell recovery, not “AI”)
- **Client outcome report:** `docs/gtm/RECOVERED-REVENUE-BRIEF-TEMPLATE.md`
- Rules and how it works: `AGENTS.md`; current project state: `CLAUDE.md`

## Run locally

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest tests/
PYTHONPATH=src .venv/bin/python -m text_back   # 127.0.0.1:8000 only
```

Project state lives in `CLAUDE.md`. Finished work is pushed to `main`. Deploy: `bash scripts/deploy.sh` after a merge to `main`. Contracts: `docs/SIGNALWIRE-INTEGRATION.md`,
`docs/OUTCOME-EVENTS.md`, `docs/CALENDAR-PROVIDERS.md`.

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
  `CallSid` queues one intro SMS, regardless of `CallStatus`
  (`ringing`, `in-progress`, `completed`, etc.). Idempotency is enforced via
  the same `claim_event` mechanism keyed on `call_sid`, so carrier webhook
  retries (e.g. a `ringing` webhook followed by a `completed` webhook for
  the same call) share one durable SMS intent. Unknown provider acceptance is held for reconciliation.
- **`managed`** — our number is the client's number directly (the original/
  legacy behavior). Only a terminal-unanswered `CallStatus`
  (`no-answer`/`busy`/`failed`/`canceled`) counts as a missed call; other
  statuses (e.g. `ringing`) are ignored.

In both modes: opt-out (STOP) suppression is checked before any SMS is
sent, and the intro SMS goes to the original caller (`From` on the voice
webhook) from our number (`To`) — never to/from the client's own line.

Runtime, durable delivery, credential recovery, and pilot checks: [Recover operations](docs/RECOVER-OPERATIONS.md).
