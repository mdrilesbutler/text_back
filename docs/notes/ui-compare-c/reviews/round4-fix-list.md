# Candidate C — round 4 fixes (every remaining judge deduction; Michael will not approve anything that still has them)

Sources: /tmp/claude-1001/-home-ubuntu-projects-text-back/530ef4b8-f397-415c-94a6-111b0523d2dc/scratchpad/final3-vs-{A,B}/judges/{claude,grok,codex}.md
(keys.json beside each says which label was C). Re-read the C items there before starting.

## c2 phone navigation
1. Account is findable in one tap on phone. Header: left the TextBack mark with the business name under it (small, wraps, never ellipsized);
   right a 44x44+ button with a person icon AND the visible word "Account" linking to /client/account (aria-current on the Account page,
   highlighted like an active tab). Keep sign out on the Account page; drop the business-name dropdown menu if it becomes redundant
   (keep "Signed in as …" on the Account page). Desktop sidebar keeps Account.
2. Messages section jumps are one tap: at the top of Messages on phone, show the five steps as a wrapped grid of 44 px buttons
   (2 or 3 per row, never clipped, no sideways scroll); once that grid scrolls away, the compact sticky "Jump to: <step>" control appears.
   Schedule and Phone & business get the same treatment (their sections as one-tap links at the top + sticky Jump to).
3. Messages is shorter on phone: inside each step, the main-path texts stay open; the branch texts (re-asks, time taken, calendar failed,
   unclear answers) sit in ONE disclosure per step, summary "If the answer is unclear · 3 texts" (count from data; titles listed in the
   summary line or right under it), open automatically when it holds a customized, unsaved or errored text and via any jump/error link.
   Reduce the spine gutter on phone (node column ≤ 32 px) so cards get more width. Target: Messages ≤ 8 phone screens at 390x844.

## c1 phone layout
4. Nothing sits under the bottom tab bar: hide the bottom tab bar while scrolling DOWN and show it on scroll UP, at the page top and at the
   page end (standard mobile pattern; instant under reduced motion; never hidden while a nav link has focus); pages end with bottom padding
   = tab bar height + 24 px so the last control always clears it. The header and the sticky Jump to stay put.
5. "Remember this device for 30 days" and similar short labels never leave one word alone on a line (text-wrap: pretty on labels/hints).

## a2 plain words (owner-facing portal copy only; customer texts are the owner's to edit)
6. Replace "the assistant"/"assistant" in owner-facing copy (Schedule, Calendar, Messages page copy, Home) with "TextBack".
   "Number in the HELP reply" → "The number customers get when they text HELP". "retried texts" → "texts TextBack sends again".
   Grep templates, portal_*.py and the copy deck for any other term Home doesn't use and align it. Update the deck rows.

## e2 finish
7. The desktop example rail never puts a hint over a bubble: remove the floating "Scroll for the rest" pill; under the phone frame (outside
   the scroll area) show a plain line "More below. Scroll the conversation." only while more is below.
8. The rail follows the page: as a Messages step scrolls into view (or a card's editor opens / gets focus), the rail scrolls its own
   thread so that step's first bubble is at the top of the rail (smooth unless reduced motion). The bubble for the card being edited
   stays highlighted.
9. Rename offer: under the first-text preview while texts still hold the old name, a muted line "This text still says “<old name>”. Update it above."

## Verify
- Suite green (tests first for every behaviour; update markup tests only where behaviour is unchanged; list them).
- Private copy: `.venv/bin/python docs/notes/ui-compare-c/preview.py <fresh dir> 127.0.0.1 8813`; never 8000/8443/8765/8003/8766.
- Capture every page at 390x844@2 and 1280x900 by scrolling (like tools/walk_c.py) and open the frames: no frame may show a heading,
  bubble, field, caption or button cut by the tab bar or any sticky bar; Messages ≤ 8 phone screens; no clipping; no sideways scroll at 320.
