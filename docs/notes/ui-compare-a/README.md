# /client redesign, variant A ("conversation spine") — 2026-10-22

Branch `ui/compare-a`, comparison build only: no PR, merge or deploy. The previous
variant-A look (f361093) was thrown away; its routes, security and data were kept.
Suite: 630 passed (`.venv/bin/pytest tests/`).

## Design choices (10 lines)

1. Messages reads top to bottom in the order a customer meets the texts, grouped by moment on a vertical spine that starts at the brand's red missed-call dot; START, HELP and STOP sit off the spine under "Any time", collapsed, because they can arrive at any point.
2. Every card leads with the exact text the customer gets, as a TextBack bubble on a full-bleed band: business name filled in, sample job/time/address, and the auto-added STOP line drawn with a dotted underline so the owner can tell it was added for him.
3. Card anatomy is title + state, bubble, a receipt line ("1 text · 75 characters"; amber and named when a symbol like "—" makes it bill as 2–3 texts), and one footer row: "Edit wording" against "✓ Standard wording" or "Reset". Rules, chips and help live inside the editor.
4. Brand is FluxWorks: white page, stone neutrals, #171717 ink, #166534 as the only accent, Archivo 600 headings and Source Sans 3 body at 17px, self-hosted. Status is always colour + icon + word. A dark token set lifts cards above the page.
5. Shell: full-width header with the business name and an account menu (Appearance, Sign out); bottom tab bar on phone; a 13rem left sidebar from 1024px. Messages adds a sticky phone rail with a "Show" select for seven sample conversations, which renders below the list on phone.
6. One sticky save bar for the whole form ("No unsaved changes", "2 unsaved changes", "Saved just now"), with Discard + Undo, Ctrl/Cmd+S and a leave-page guard. The toast names what changed.
7. A rejected save keeps every edit, puts a plain-language summary at the top of the list ("Take out “business line”…") with a link to the text, opens that card and repeats the reason beside the field. Validation is still only on the server.
8. Everything works with JavaScript off: native disclosures for editors and "Any time", `:has()` scenario switching, Reset posts the form ("Reset and save"), and server-rendered toasts and save-bar copy.
9. Sign in and Enter code: one field and one button, business name as heading, a card on a tinted page from 640px. The code field is one real `one-time-code` input drawn as six cells, and the enter-code page shows no part of any number.
10. Business shows a live first-text preview under the name and a two-step stepper for a new owner mobile. Calendar is one status block per state with its action inside, a radio picker only when connected, and "What Google will ask" as a disclosure.

Stack: Jinja2 templates in `src/text_back/templates/client/`, one stylesheet and one ES
module served from `/client/static/` (`portal.css` 84 KB, 17 KB gzipped; `portal.js` 620
lines), Lucide icons as an inline sprite, fonts in `static/fonts/`. Pages send a CSP with
`default-src 'self'`, so there is no inline script or style and nothing loads from another
host. The owner-only `/client/styleguide` shows every token and component in light and
dark.

## Agents and skills, and what each changed

| Who | What it did |
| --- | --- |
| superpowers:brainstorming | Settled the direction: four directions weighed, "conversation spine" chosen ([direction.md](direction.md)). Ran its no-questions path because the brief was complete. |
| fluxworks-design | Brand tokens, Archivo + Source Sans 3 (self-hosted subsets), the phone-thread grammar the rail reuses, copy voice. |
| frontend-design, visual-design-foundations | Token scales, one signature (spine + bubble) with everything else quiet, avoiding the three AI-default looks. |
| interaction-design, responsive-design, accessibility-compliance | 150–250 ms state transitions with reduced motion, mobile-first with container queries, 44 px targets, focus and live-region rules. |
| design:design-system, design:design-critique, design:ux-copy | Component inventory behind the styleguide, the critique frame used on every screenshot pass, action-named buttons and how-to-fix errors. |
| Explore agent (very thorough) | Mapped every /client route, cookie, CSRF rule, message key, placeholder, the STOP suffix rule and the tests coupled to markup. That map became the contract nothing was allowed to break. |
| ui-designer | Wrote [design-spec.md](design-spec.md): tokens with a computed contrast table, type and spacing scales, shell, 27 components with states, screen specs, copy deck. |
| design-bridge | Wrote [implementation-plan.md](implementation-plan.md): template tree, CSS layers, JS module boundaries, stable hooks, build order. Found an existing 500 on `{a.b}` in a rejected save, now fixed. |
| frontend-developer ×5 | Phase 1: render layer, static mount, CSP, shell, sign-in, Business, Calendar, expired page. Phase 2: Messages page and all of portal.js. Phase 3: styleguide and tests. Fix rounds 1 and 2: everything the reviewers flagged. |
| anti-ui-slop-reviewer ×2 | Round 1: BLOCK (cards too dense, page 12,426 px at 375, wrapping scenario pills, Material-style rail, repeated calendar copy). Round 2: PASS on condition of two fixes (clipped sixth code cell, "connected" said three times), both applied. |
| the-agency design-ui-designer (via agency-agents) | Second opinion on the card: the full-bleed band, receipt line, single footer row, shared frame for re-prompts and the wide-card settings row. About 3,000 px saved at 375. |
| accessibility-tester | WCAG 2.2 AA audit, axe 0 violations, no blockers. Led to scroll padding so focus never hides under the tab or save bar, toasts moved off the account menu, solid fills for selected pills, a forced-colours block, and a stronger current-page cue. |
| ux-researcher | Read Messages as an arborist seeing it for the first time. Led to plain-language rejections, rule copy that says what the validator really checks, the jump row, the collapsed "Any time" group, the billing receipt wording, chip order and clearer save confirmation. |

Messages height at 375px: 12,426 px after the first build, 8,845 px after review, with
the full sample conversation included.

## For Michael (product calls, not changed here)

- The shipped default first text, first reminder and hand-off reply contain an em dash. That forces Unicode encoding, so they bill as 3, 3 and 2 texts. The cards now say so in amber; changing `DEFAULT_TEMPLATES` is a product decision.
- The hand-off check needs the literal words "follow up". "follow-up" and "text you back" are refused. The rule copy now says exactly that.
- The portal says "you get a lead" on hand-off. Leads go to the operator channel (`handoff_destination`), which is true for the pilot but needs checking per client.

## Screenshots

`screenshots.py` runs the real app twice on 127.0.0.1 with `FakeTelecom`: once on the
stub calendar and once on the Google fixture patched into its real states. It drives
Chromium and writes `<state>-<375|1024>-<light|dark>.png`, full page at 2x.

The styleguide is too tall for one capture. It is saved as `14-styleguide-00-top-*` plus
one file per section, and every section already shows a light and a dark panel. The
committed PNGs were then palette-compressed to 256 colours with Pillow, which cut them
from 64 MB to 24 MB.

```
.venv/bin/python docs/notes/ui-compare-a/screenshots.py <empty temp dir> [state,state,...]
```

| State | Screen |
| --- | --- |
| 01-signin | Sign in |
| 02-enter-code | Enter code (six-cell code field) |
| 03-messages | Messages, default |
| 04-messages-editing-unsaved | Two texts edited, a detail chip inserted, unsaved count in the save bar |
| 05-messages-rejected-save | Server refused a save: summary, card opened, reason beside the field |
| 06-messages-saved | Saved toast naming what changed, "Saved just now" |
| 07-business | Business |
| 08-business-confirm-new-mobile | New owner mobile, step 2 of 2 |
| 09-calendar-test-mode | Calendar: test mode |
| 10-messages-javascript-off | Messages with JavaScript disabled |
| 11-calendar-reconnect-needed | Calendar: reconnect needed |
| 12-calendar-could-not-be-read | Calendar: could not be read |
| 13-calendar-connected | Calendar: connected, picker |
| 14-styleguide-* | Styleguide, top plus one file per section |
| 15-page-expired | Stale form (CSRF) page |

Other notes in this folder: [direction.md](direction.md), [decisions.md](decisions.md)
(calls made on the spec's open questions), [design-spec.md](design-spec.md) and
[implementation-plan.md](implementation-plan.md).
