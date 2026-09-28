# NOW — text_back

## STATE (as of 2026-09-28)
- App code lives on `local/tdd-core` (last pushed 2026-09-28 22:57 UTC); `main` is stale. 370 tests green (368 + 2 from PR #1).
- 2026-09-28 PR #1 open (base `local/tdd-core`): followup crash-safety — defect was already fixed by e4b9f5a (durable SMS outbox); PR adds crash-shaped tests pinning it. Review: SAFE TO MERGE.
- Runtime on hermes-vcn-0: text-back.service active, public HTTPS via Tailscale Funnel :8443, Google Calendar + worker + Telegram alerts live, SignalWire handlers attached, TEXT_BACK_PILOT_RECIPIENTS explicitly empty. No real-phone pilot yet.
- 10DLC/Free Trial: SMS reaches only the ONE Dashboard-verified mobile. Pilot caller must be that mobile; the forwarding phone must be a different phone. Later clients need Brand + Campaign (fees).
- Canon drift: `local/tdd-core` still carries the old 83-line CLAUDE.md as live state (Codex updates it) and fails `canon_check --repo-only`. Migrating it to AGENTS.md + this NOW.md is Michael's call.
- Pending in Michael's browser: Google Web OAuth callback registration; Telegram alert acknowledgment.

## NOW
Run the real-phone Recover pilot per `docs/ONBOARDING-FORWARDING.md` on hermes-vcn-0 (`local/tdd-core`): set TEXT_BACK_PILOT_RECIPIENTS to the PFT-verified mobile, restart, confirm health count 1, forward from the second phone to +17045695600, missed call from the verified mobile → intro, qualification, provider-verified booking or async handoff, STOP, brief; record evidence.

## BLOCKED
BLOCKED · real-phone Recover pilot · needs PR #1 merged + device facts · NEED YOU: merge #1; confirm which mobile is verified in the SignalWire Dashboard and name a second voice phone to forward from

## OWNER
none

## NEXT
- Decide canon migration for `local/tdd-core` (collapse CLAUDE.md into AGENTS.md; state to canon-state NOW.md) — Michael's call.
