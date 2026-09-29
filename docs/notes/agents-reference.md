# text_back — agents-reference (overflow from AGENTS.md, kept verbatim)

Moved here only because AGENTS.md has a 100-line cap. These are still LOCKED / ROADMAP facts — treat them
the same as anything in AGENTS.md itself.

## LOCKED (additional — do not re-open)
- Google OAuth for text_back is minted with the google-oauth-repair skill pattern (existing Hermes client, butler account) — re-mint in ~5 min if revoked.
- Customer calendar reauth: silent refresh; on true revocation mark the client `reauth_required` and send a reconnect link. Customers never go through the operator OAuth-repair path.
- Credential intake: browser → `~/.config/text_back/` → verified via `/health`. Never chat, git, or Obsidian.
- The live-call verification checklist in `docs/ONBOARDING-FORWARDING.md` is mandatory at every client onboarding.
- Two-lane repo protocol: Grok owns `deploy/textback-designer/` + `docs/demo/`; Claude/Codex own everything else. Every commit is `--only`-scoped to named paths, never `-a`. Lane splits are recorded here, not in dated docs files.

## ROADMAP (additional — order is locked; build only the current phase)
- v2 Answer: after-hours/overflow AI voice + directory routing.
- v3 Grow: estimate, no-show, review journeys, separately consent-scoped.
- Optional (money gate): PDF leave-behind, Stripe links for the three SKUs; a `deploy-client` skill for fluxworks.

## Gotchas
- `TEXT_BACK_SIGNALWIRE_SPACE_URL` already includes `https://`; SignalWire has no `/Balance.json`; the `!` runner is non-interactive; caller-ID passthrough on forwarded calls is proven only by the live test call.

## Note
- Old CLAUDE.md carried a "canon-allow" note for `src/text_back/handoff.py` (product code — the customer handoff
  module, not a state file) to stop it from being mistaken for a state file by name. No current lint script reads
  a "canon-allow" directive; kept here as a pointer only.
