# Mockup brief (shared by directions d1 and d2)

Render every page and state of the TextBack /client owner portal as static HTML from ONE fixture,
so the two directions differ only in design. Judges will score the screenshots blind against the
existing candidate A using docs/notes/ui-bakeoff-2026-10-26/judge-prompt.md.

## Inputs (read all, in this order)
1. docs/notes/ui-bakeoff-2026-10-26/judge-prompt.md — the rubric (a1–e2). Every decision serves a criterion.
2. docs/notes/ui-bakeoff-2026-10-26/design-prompt-100.md Part 2 — the target; LOCKED rules.
3. docs/notes/portal-c/research/SUMMARY.md — the 15 decisions, shared vocabulary, sticky-chrome budget. Binding.
4. docs/notes/portal-c/copy-deck.md — every visible string, verbatim. No other words on screen.
5. docs/notes/portal-c/mockups/fixture.json (+ fixture.md) — all content and the `states` list. Render from it; never type content into templates.
6. ~/.claude/skills/fluxworks-design/SKILL.md — tokens, fonts, hard rules (white page, #171717 ink, #166534 the only accent, Archivo 600 headings, Source Sans 3 body, no invented numbers).
7. docs/notes/portal-c/mockups/_assets/portal.css — candidate A's stylesheet (layers tokens/reset/base/layout/components/pages). Build ON it: link it first, then your direction's own `dN.css` for what you change or add. Fonts are beside it (`_assets/*.woff2`). Do not edit _assets.
8. docs/notes/portal-c/research/accessibility.md — contrast floors (control borders #78716c or darker; #e7e5e4 only for dividers), focus, scroll-padding, role=status slot, one check vocabulary.

## Output (direction folder docs/notes/portal-c/mockups/dN/)
- `build.py` — renders Jinja2 templates in `dN/templates/` from `../fixture.json` to `dN/*.html` (run it with /home/ubuntu/projects/text_back-ui-c/.venv/bin/python). Templates must be plain Jinja2 so they port to the app later.
- `dN.css` — only the rules that differ from or extend portal.css. Use the same custom properties; no new hues.
- Pages: `01-sign-in.html`, `02-enter-code.html`, `03-home.html`, `04-messages.html`, `05-schedule.html`, `06-calendar.html`, `07-phone.html`, `08-account.html`.
- States: one file per entry in fixture `states`, named `NN-<page>--<state>.html` (e.g. `04-messages--edit-open.html`, `07-phone--carrier-verizon.html`, `03-home--account-menu.html`, `04-messages--saved-toast.html`, `04-messages--unsaved-bar.html`, `07-phone--invalid-mobile.html`, `06-calendar--connected.html`, `06-calendar--not-connected-no-connect.html`, `05-schedule--any-time-warning.html`, `05-schedule--custom-length.html`, `05-schedule--hours-grid.html`, `07-phone--confirm-mobile.html`, `08-account--sign-out.html`, and every save toast at phone width). Put `id="focus"` on the element the state is about so the capture tool scrolls to it.
- `README.md` — 10 lines: the direction's idea, what it borrows from A, what is new, and the one signature element.
- No JavaScript is required (states are separate files), but if you add any it must be ≤ 60 lines, inline-free (external file), and the page must read fully without it.

## Non-negotiables (judges deduct for each)
- Phone 390×844: tap targets ≥ 44 px; business name wraps (never ellipsized); sticky chrome total ≤ 156 px (header 56, Messages jump chips 44, bottom nav 56; the Save bar REPLACES the nav while there are unsaved changes); `scroll-padding-top/bottom` set on html; no sideways scroll at 320 px.
- Desktop 1280×900: sidebar `position: sticky`; the Messages preview rail scrolls its own content and never clips a bubble.
- Save/notice banner is in-flow with `role="status"`, between the header and the h1, never over the title.
- Every date is a full date from the fixture ("Mon, Oct 26, 9:12 AM"); counts equal rows; seeded callers show the "Example" tag; the example conversation carries its label.
- Chip selected state follows the field value; a custom value shows "Custom" with no chip selected.
- One check vocabulary (SUMMARY.md "Shared vocabulary") on Home cards and the Phone checklist: glyph + word, never glyph alone.
- Texting number is text, not an input, with its sentence. STOP line shown as added-for-you. Forward-all warning visible. Links in bubbles as short labels.
- No banned words (SignalWire, text_back, campaign, brand, 10DLC, registration, segment, lead, token, webhook, provider, event ID, call_sid, nudge, hand-off) and no "{" in rendered text. Grep your output.
- Every page passes: `/home/ubuntu/projects/text_back-ui-c/.venv/bin/python docs/notes/ui-compare-c/tools/capture_static.py docs/notes/portal-c/mockups/dN <scratch out dir>` with no SIDEWAYS or SMALL flags (use /tmp/claude-1001/-home-ubuntu-projects-text-back/530ef4b8-f397-415c-94a6-111b0523d2dc/scratchpad/shots-dN as the out dir). Look at the PNGs it produces (Read the image files) and fix what you see before reporting.
