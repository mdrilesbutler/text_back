# AGENTS.md — text_back

## Cold resume rule
If the user says "continue project", "continue", "pick up", or equivalent, read `NEXT-SESSION.md` in this repo root completely before acting, then follow it unless a newer user instruction overrides it. Canonical checkouts: `/home/ubuntu/projects/text_back` (hermes-vcn-0) and `/home/mdriles/projects/text_back` (piclaw); use the one you are in.

## Required reading
1. `PRD-text_back.md` (labeled root PRD — there is no bare `PRD.md`)
2. `NEXT-SESSION.md`
3. `SESSION-NOTES.md`
4. `docs/ONBOARDING-FORWARDING.md` (before any number wiring or client onboarding)

## Safety and product boundaries
- Never purchase or activate telecom service, incur spend, send production messages, or route customer calls without Michael's explicit approval. Approved so far (2026-08-20): SignalWire path with a $15/month ceiling — purchases still happen only via Michael's browser.
- Never store credentials, OAuth tokens, API keys, webhook secrets, service-account keys, or customer-sensitive message content in Git or Obsidian. Keys live under `~/.config/text_back/` or the deployment secret store.
- Validate telecom webhook signatures and fail closed.
- Deterministic policy — not the language model — controls STOP/HELP, consent, booking, quiet hours, and human handoff.
- Never claim an appointment is booked without a successful Calendar event ID.
- Respect `wiring_mode` semantics: `forwarded` triggers on first voice event per call_sid; `managed` only on terminal unanswered statuses. Never mix the rules.
- Test with non-customer numbers before production traffic; the live-call verification checklist in `docs/ONBOARDING-FORWARDING.md` is mandatory at every onboarding.
- Fluxworks catalog rule: business-specific values (identity, numbers, calendar, hours) belong in config/env only — the build must be reproducible per client.
