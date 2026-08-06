# AGENTS.md — text_back

## Cold resume rule
If the user says “continue project”, “continue”, “pick up”, or equivalent, read `/home/mdriles/projects/text_back/NEXT-SESSION.md` completely before acting, then follow it unless a newer user instruction overrides it.

## Required reading
1. `/home/mdriles/projects/text_back/PRD.md`
2. `/home/mdriles/projects/text_back/NEXT-SESSION.md`
3. `/home/mdriles/projects/text_back/SESSION-NOTES.md`

## Safety and product boundaries
- Never purchase or activate telecom service, incur spend, send production messages, or route customer calls without Michael’s explicit approval.
- Never store credentials, OAuth tokens, API keys, webhook secrets, or customer-sensitive message content in Git or Obsidian.
- Validate telecom webhook signatures and fail closed.
- Deterministic policy—not the language model—controls STOP/HELP, consent, booking, quiet hours, and human handoff.
- Never claim an appointment is booked without a successful Calendar event ID.
- Test with non-customer numbers before production traffic.
