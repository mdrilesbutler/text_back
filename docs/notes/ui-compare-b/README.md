# /client portal — comparison build B

Branch `ui/compare-b`. Not merged, not deployed. The IA document is
[client-portal-design.md](client-portal-design.md); the screenshots in
`screenshots/` are every page at 375px and 1024px, rendered from this branch
with demo data (TestClient render, headless Chromium).

## Design choices (10 lines)

1. Server-rendered Jinja2 with one stylesheet and ~360 lines of plain JS: no build step, `scripts/deploy.sh` unchanged, CSP with no inline code.
2. Hatch-style calm shell: phone gets five bottom tabs, desktop a 240px sidebar; one accent (green) used only for the active item and primary action; status is always colour + icon + word.
3. Home is a status board first (Calendar · Forwarding · Messaging registration), then this week's four numbers, then the last ten conversations; nothing on it is a control that leads nowhere (Customers is design-only, so it is not in the nav).
4. Messages keeps the engine's single source of truth (`messages.json`): "Standard wording" until the owner overrides a text, Reset per field, fill-in chips with human labels, and a live phone-frame preview of the whole conversation that counts real SMS segments (GSM-7/UCS-2, opt-out line, trial tag).
5. STOP is locked into the opt-out line with the carrier reason shown; every rejection is inline, per field, in owner language (no keys, no engine words).
6. Scheduling shows only what the engine enforces; working hours were not enforced before, so they are now checked in `booking.book_appointment` before free/busy, and "Any day, any time" (the old behaviour) is the default.
7. Every setting defaults to the environment value and is stored in `client_settings`; saving rebuilds the follow-up policy in place, so nothing needs a restart.
8. Phone has three typed numbers with Verify beside each; the texting number must already be owned by the account with handlers pointing at text_back, and there is no buy/port/pick path anywhere.
9. Forwarding instructions come straight from `docs/ONBOARDING-FORWARDING.md` with the texting number substituted and copy buttons; the five-step checklist ticks steps 1, 2 and 4 from recorded calls and leaves 3 and 5 to the owner, rolling up to the Home card.
10. Sign-in stays passwordless; "Remember this phone for 30 days" is a verify-screen checkbox plus an Account toggle, backed by one guarded column migration.

## Not built in this session (by brief)

Customers page: specified in the IA document (table, drawer, status derivation, `customers` table with migration and backfill); components for it are in `/client/styleguide`.
