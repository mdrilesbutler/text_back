# /client redesign, Variant A (one long Messages page) — 2026-10-20

Branch `ui/compare-a`. Comparison build only: no PR, merge or deploy. Code in
`src/text_back/client_portal.py` and `src/text_back/client_settings.py`; new tests in
`tests/test_client_portal_ui.py`. Suite: 608 passed (`.venv/bin/pytest tests/`).

## Screenshots

Every screen at 375px and 1024px, full page, 2x, rendered by Playwright Chromium against
the real app with stub telecom (`FakeTelecom`), the stub calendar and a sample messages
file (`intro` customized, email question on). Regenerate with
`.venv/bin/python docs/notes/ui-compare-a/screenshots.py <tmpdir>` from the repo root
(needs `pip install playwright && playwright install chromium` in the venv).

| File | Screen |
| --- | --- |
| 01-signin | Sign in: business name as heading, one field, one button |
| 02-enter-code | Enter code (`autocomplete=one-time-code`) |
| 03-messages | Messages tab, one long page in conversation order |
| 04-messages-editing-unsaved | Typed into a card, chip inserted, live preview, "Unsaved changes" in the save bar |
| 05-messages-rejected-save | Server rejected a save; reason on the offending card and in the top banner |
| 06-messages-saved | Saved notice |
| 07-business | Business tab |
| 08-business-confirm-new-mobile | Owner-mobile change as step 2 of 2 |
| 09-calendar-test-mode | Calendar: test mode / none |
| 10-messages-javascript-off | Messages tab with JavaScript disabled |
| 11-calendar-reconnect-needed | Calendar: reconnect needed |
| 12-calendar-could-not-be-read | Calendar: could not be read |
| 13-calendar-connected | Calendar: connected, which calendar, radio picker |

## Design choices (10 lines)

1. One long Messages page in six numbered moments (Missed call, The questions, Booking, No reply, You step in, START/HELP/STOP); re-prompts sit directly under the question they repeat, and the "also ask" toggles sit on the phone/email cards.
2. Every card leads with a phone bubble showing the text as the customer gets it: real business name, sample job/time/address, the HELP contact line, and the opt-out line appended exactly where `messages.py` appends it (same STOP-word rule, server-rendered, mirrored live in JS).
3. The count under the bubble is of the rendered text, not the template, and knows the GSM alphabet: the shipped intro's em dash makes it 3 segments, and the page says so ("symbols like — shorten each text").
4. Standard wording vs Customized is a per-card badge; "Use standard wording" is a real submit button (`name=reset`) so it works with JavaScript off, and JS turns it into an instant clear.
5. Placeholders are tappable chips that insert at the cursor; with JS off they still document what is allowed.
6. Rules are surfaced twice before Save: a collapsed "rules every message follows" at the top and a one-line amber-dot rule on the cards that have one (STOP, 911, "no booking was made", follow-up promise). Validation stays in `messages.py`.
7. A rejected save keeps everything typed, marks the offending card red with the reason, and the banner links to it; `blame()` maps the validator's message to the card, including the key-less "unbalanced braces" and "handoff acknowledgements" errors.
8. Light, warm palette with amber `#F0B429` only on primary buttons (dark text for contrast), active tab underline and focus rings; Atkinson/Plex named as system fallbacks only, no assets loaded, one inline `<style>`.
9. Mobile first: 48px tap targets, 17px body and 18px inputs (no iOS zoom), full-width amber buttons, a sticky Save bar with unsaved-changes awareness, segmented tabs, no horizontal scroll at 375px.
10. Business and Calendar kept their routes and data: fields now carry explanations, the mobile change renders as step 2 of 2, and Calendar is one status block with the four real states plus a plain "What Google will ask" card and a radio picker.

Security properties are unchanged (same handlers; headers, CSRF, code and session rules
covered by `test_client_portal.py`, `test_client_settings.py` and the new UI tests).
