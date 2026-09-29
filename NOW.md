# NOW — text_back

## STATE (as of 2026-09-28)
- App code lives on `local/tdd-core` (last pushed 2026-09-28 22:57 UTC); `main` is stale. 370 tests green (368 + 2 from PR #1).
- 2026-09-28 PR #1 MERGED into `local/tdd-core` (7107639): followup crash-safety — defect was already fixed by e4b9f5a (durable SMS outbox); PR adds crash-shaped tests pinning it. 
- Runtime on hermes-vcn-0: text-back.service active, public HTTPS via Tailscale Funnel :8443, Google Calendar + worker + Telegram alerts live, SignalWire handlers attached, TEXT_BACK_PILOT_RECIPIENTS explicitly empty. No real-phone pilot yet.
- 10DLC/Free Trial: SMS reaches only the ONE Dashboard-verified mobile. Pilot caller must be that mobile; the forwarding phone must be a different phone. Later clients need Brand + Campaign (fees).
- Canon drift: `local/tdd-core` still carries the old 83-line CLAUDE.md as live state (Codex updates it) and fails `canon_check --repo-only`. Migrating it to AGENTS.md + this NOW.md is Michael's call.
- Pilot phone roles (Michael, 2026-09-28 — do not re-ask): client/test phone = 980-428-5452 (PFT-verified mobile); text number = SignalWire pilot number +17045695600. Call the SignalWire number directly from 5452; no separate forwarding phone.
- hermes-cloud = ubuntu@129.80.33.210 (key ~/.ssh/oracle); the `hermes-cloud` alias exists only on piclaw.
- Pending in Michael's browser: Google Web OAuth callback registration; Telegram alert acknowledgment.

## NOW
Run the real-phone Recover pilot on hermes-vcn-0 (`local/tdd-core`, pull 7107639 first): set TEXT_BACK_PILOT_RECIPIENTS=+19804285452, restart, confirm health count 1; from 5452 call +17045695600 unanswered → intro text, qualification, provider-verified booking or async handoff, STOP, brief; record evidence.

## BLOCKED
BLOCKED · real-phone Recover pilot · Claude on Alienware denied production access to hermes-cloud · NEED YOU: allow hermes-cloud SSH for the pilot, or run it from piclaw/hermes-cloud

## OWNER
claude-alienware#487c · 2026-09-29T00:56Z

## NEXT
- Decide canon migration for `local/tdd-core` (collapse CLAUDE.md into AGENTS.md; state to canon-state NOW.md) — Michael's call.

