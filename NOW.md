# NOW — text_back

## STATE (as of 2026-09-11)
- Last code commit 2026-08-29. 302 tests green on hermes-cloud (verified 2026-09-11).
- Built locally: FastAPI app, signature boundary, idempotency, STOP/HELP, slot filling, time parsing, booking gate, handoff state, outcome ledger, follow-up sequence, Revenue Brief, operator revenue write path, handoff-alert delivery outbox, calendar layer (stub/google/microsoft/icloud).
- No live webhook, message, call, deployment, or customer traffic has ever happened.
- Open defect (2026-08-29 review): `followup.py` claims the event then sends — crash between the two wedges the attempt. Same shape `delivery.py` already fixed.
- Gate (Michael): deployment shape — tunnel smoke test vs durable Caddy+domain on the VPS (deferred 2026-08-28).
- Gate (Michael): live handoff-alert channel (SMS / Telegram / email). Outbox built; channel `disabled`.
- Gate (Michael, browser): SignalWire Platform Free Trial mobile verification. Sole proprietor, LLC pending; no paid Brand/Campaign without reviewing fees.
- Not built: customer `reauth_required` flow (per-client token store, state + outcome event, reconnect-link delivery).
- Conflict: vault project note (2026-08-29) still says "if Cal.com approved" — stale; the later Google decision wins.
- 2026-09-11: canon init committed (f3d10d2); a parallel canon-sweep session stood down and committed nothing here. Grok's lane still has uncommitted UI work in `deploy/` and `docs/demo/`.

## NOW
Port the persist-attempt-before-send crash-safety pattern from `src/text_back/delivery.py` into `src/text_back/followup.py` (the `claim_event` → `send_sms` block near line 199), TDD with crash-shaped tests; full suite green; commit and push `local/tdd-core`.

## BLOCKED
none

## OWNER
claude-alienware#1095 · 2026-09-28T23:35Z

## NEXT
- (queued slices, in order)
