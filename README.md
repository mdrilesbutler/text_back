# text_back

Missed-call recovery and scheduling assistant for field-service businesses.

- Canonical requirements: `PRD-text_back.md`
- **Product model:** `docs/PRODUCT-MODEL.md` (Recover first; Answer/Grow later)
- **Competitive synthesis:** `docs/COMPETITOR-MATRIX.md`
- **GTM / sales model:** `docs/gtm/KOERNER-MODEL.md` (assessment → Recover install → Care; sell recovery, not “AI”)
- **Client outcome report:** `docs/gtm/RECOVERED-REVENUE-BRIEF-TEMPLATE.md`
- Cold resume: `NEXT-SESSION.md`
- Session history: `SESSION-NOTES.md`
- Local implementation plan: `IMPLEMENTATION-PLAN.md`

## Current state (2026-08-21, hermes-vcn-0)

Local core and a SignalWire Compatibility REST outbound-SMS adapter exist and
are tested on this host. The product path is assessment → **Recover install**
(`TB-RECOVER`) → Care; Answer voice and Grow journeys wait until a real-phone
Recover pilot proves conversion. Michael purchased one pilot number and the
protected Compatibility API credentials now verify against it. An enabled
localhost-only pilot service runs in safe `stub` mode; no live handler, message,
or customer call is active because the Project signing key, approved public
HTTPS deployment, Google Calendar adapter, and operator notifier remain gated.

```bash
cd /home/ubuntu/projects/text_back
.venv/bin/pytest tests/
.venv/bin/python -m text_back   # 127.0.0.1:8000 only
```

Covered locally: environment-backed configuration, guarded SignalWire outbound
REST and inbound Compatibility boundaries, provider-specific fail-closed
webhook signatures, valid cXML responses, a forwarded-call greeting,
missed-call intro (both wiring modes), idempotent retries, STOP/HELP policy,
deterministic field collection, and Calendar stub booking with event-ID gate.
See `docs/SIGNALWIRE-INTEGRATION.md` for the protected configuration contract.

Booking accepts explicit local times such as `2026-08-25 2:00 PM` or
`tomorrow at 2 PM`, applies `TEXT_BACK_TIMEZONE`, rejects vague/past/DST-unsafe
values, rechecks free/busy, and uses the configurable appointment duration.
The in-process Calendar stub is test-only; a live Google Calendar adapter is
still required before customer traffic.

Deterministic handoff recognizes explicit requests for a person and a bounded
set of safety terms. It persists an active pause, suppresses further automated
collection and missed-call intros, and builds a concise operator payload with
the caller, reason, latest message, and fields collected so far. The notifier
is currently an in-memory stub; external operator delivery is not implemented.

An append-only outcome ledger now backs lifecycle claims with call SIDs,
provider message IDs, handoff alert IDs, requested slots, and calendar event
IDs. It never treats a booking as completed work or revenue. See
`docs/OUTCOME-EVENTS.md` for the event/evidence contract.

Human gates remaining: verify Michael's personal mobile for SignalWire Platform
Free Trial; add credentials through the protected deployment/local secret
store; expose an approved HTTPS deployment and attach its webhook URLs; and
complete Google Cloud authentication/service-account setup for the pilot
calendar. No live SignalWire callback or REST request has been exercised.

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
