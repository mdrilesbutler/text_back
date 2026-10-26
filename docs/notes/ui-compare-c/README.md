# /client candidate C ("Spine") — 2026-10-26

Branch `ui/compare-c` (worktree ~/projects/text_back-ui-c), pushed as a plain branch: no PR, no merge, no deploy.
Built from `docs/notes/ui-bakeoff-2026-10-26/design-prompt-100.md`. Suite: 960 passed (main: 594).

Preview (tailnet only, fake telecom, demo data, dies on reboot): http://100.124.192.46:8766. Sign in with
980 555 0123 and read the code at /preview/code (3 codes per 15 minutes, 10 per day). Start it again with
`.venv/bin/python docs/notes/ui-compare-c/preview.py <empty dir>` from the worktree.

## Final blind panel (same rubric and judges as the A/B bake-off, CLI logins, every *_API_KEY unset)

| Round | vs | Claude | Grok | Codex | C mean | Other's mean | Verdicts |
|---|---|---|---|---|---|---|---|
| 1 | A | 90 | 88 | 86 | 88.0 | 59.3 | C 3–0 |
| 1 | B | 88 | 92 | 84 | 88.0 | 58.0 | C 3–0 |
| 2 | A | 90 | 88 | 86 | 88.0 | 59.3 | C 3–0 |
| 2 | B | 92 | 86 | 84 | 87.3 | 56.0 | C 3–0 |
| 3 | A | 90 | 92 | 86 | **89.3** | 60.0 | C 3–0 |
| 3 | B | 92 | 90 | 90 | **90.7** | 59.3 | C 3–0 |

Round 3 per criterion for C (Claude/Grok/Codex): vs A a1 5/5/5, a2 4/4/4, b1 5/5/5, b2 5/5/4, c1 4/4/4, c2 4/4/4,
d1 5/5/4, d2 5/5/5, e1 4/5/4, e2 4/4/4; vs B a1 5/5/5, a2 4/4/4, b1 5/5/5, b2 5/4/5, c1 4/4/4, c2 4/4/4,
d1 5/5/5, d2 5/5/4, e1 5/5/5, e2 4/4/4. Scorecards: `final-round{1,2,3}-vs-{A,B}/` (raw, under blind labels).

Still under 5 after the three allowed fix rounds, from the round-3 scorecards:
- a2 plain words (4 from all): a few words remain that Home doesn't use ("assistant", "HELP reply", "retried texts").
- c1 phone layout (4 from all): at some scroll stops a field or caption sits just above the bottom tab bar.
- c2 phone navigation (4 from all): Messages is still about ten phone screens; "Jump to" costs a tap; Account has no tab.
- e2 finish (4 from all): the rail's "Scroll for the rest" pill can sit over a bubble; one faded leftover line in the rail.

## How it was built
Research (competitors, UX patterns, WCAG 2.2 bar, copy deck) → two mockup directions → critique → three blind
mockup rounds (scores in `docs/notes/portal-c/design/README.md`; d1 won, 84.7 → 89.3) → TDD build in layers
(shell/Home/Account, Messages, Schedule, Phone & business, Calendar, harness) with a reviewer after each → verification
(ui-ux-tester, accessibility-tester, anti-ui-slop-reviewer, capture + save checks) → fix pass → final panel × 3.

Ported from B with its ship blockers fixed: texting number read-only; forwarding checks tick only from a call the
carrier forwarded from the business line (ForwardedFrom); find_event recovery before the working-hours check;
each appointment stores its end time; texting approval read live (read-only registry GETs); save notices that match
behaviour (pinned by tests). From A: render layer, CSP, CSRF, fonts, Messages conversation spine.

## Product calls made on C (C only; they reach main only if Michael picks C)
- Default customer texts drop the possessive and the em dash ("the scheduling assistant for {business_name}"), so a
  name like "Arborists" reads right and the first text and first reminder bill as 1 text, not 3. Steps-back texts say
  "we'll follow up" instead of "the owner will". Time examples say "Friday at 4pm" instead of a fixed date.
- Hand-off details still go to the FluxWorks operator channel; the portal says so and that FluxWorks passes them on.
- TEXT_BACK_SUPPORT_CONTACT (new, empty by default) drives "Text FluxWorks support" where FluxWorks does the setup.

## Evidence here
`screens/` (17 compressed first screens and states), `audit-report.json` (every page and 42 states at both widths:
no sideways scroll, no target under 44 px, no console errors, no failed requests), `smoke.json` (23/23 save checks on
private copies), `reviews/verification-fix-list.md`, and `tools/` (walk_c.py, smoke_c.py, capture_static.py,
build_packs.py, run_judges.sh, scores.py, preview_connected.py). The full PNG set is reproducible with the tools.

Built at 1232628.
