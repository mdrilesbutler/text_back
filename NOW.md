# NOW — text_back

## STATE (as of 2026-09-28)
- App code lives on `local/tdd-core` (last pushed 2026-09-28 22:57 UTC); `main` is stale. 370 tests green (368 + 2 from PR #1).
- 2026-09-28 PR #1 MERGED into `local/tdd-core` (7107639): followup crash-safety — defect was already fixed by e4b9f5a (durable SMS outbox); PR adds crash-shaped tests pinning it. 
- Runtime on hermes-vcn-0: text-back.service active, public HTTPS via Tailscale Funnel :8443, Google Calendar + worker + Telegram alerts live, SignalWire handlers attached, TEXT_BACK_PILOT_RECIPIENTS explicitly empty. No real-phone pilot yet.
- 10DLC/Free Trial: SMS reaches only the ONE Dashboard-verified mobile. Pilot caller must be that mobile; the forwarding phone must be a different phone. Later clients need Brand + Campaign (fees).
- Canon drift: `local/tdd-core` still carries the old 83-line CLAUDE.md as live state (Codex updates it) and fails `canon_check --repo-only`. Migrating it to AGENTS.md + this NOW.md is Michael's call.
- Pilot phone roles (Michael, 2026-09-28 — do not re-ask): CLIENT phone = the client's actual number, 980-428-5452; its unanswered calls forward to the SignalWire number +17045695600, which is the TEXT number (SMS sender). The client never gets the SignalWire number as their number. Test caller = a different phone; under the Free Trial it must be the Dashboard-verified mobile to receive SMS.
- hermes-cloud = ubuntu@129.80.33.210 (key ~/.ssh/oracle); the `hermes-cloud` alias exists only on piclaw.
- Pending in Michael's browser: Google Web OAuth callback registration; Telegram alert acknowledgment.

## NOW
Run the real-phone Recover pilot on hermes-vcn-0 (`local/tdd-core` @ 7107639): client config business phone = +19804285452 (forwarded mode, conditional forward to +17045695600); TEXT_BACK_PILOT_RECIPIENTS = the test caller's mobile; restart, confirm health count 1; call 5452 from the test phone, let it go unanswered → intro text from +17045695600, qualification, provider-verified booking or async handoff, STOP, brief; record evidence.

## BLOCKED
BLOCKED · real-phone Recover pilot · Claude on Alienware denied hermes-cloud access; test caller must be a second phone that can receive trial SMS · NEED YOU: allow hermes-cloud SSH (or run from piclaw) + name the test caller phone

## OWNER
claude-wsl#21c6 · 2026-09-29T01:24Z

## NEXT
- Decide canon migration for `local/tdd-core` (collapse CLAUDE.md into AGENTS.md; state to canon-state NOW.md) — Michael's call.


