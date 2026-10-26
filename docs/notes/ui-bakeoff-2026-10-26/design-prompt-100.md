# What a 100 would have taken, and the design prompt that builds it (2026-10-26)

This note works backwards from the three blind scorecards in `judges/`. It finds every point A and B
lost, and turns each one into a requirement. The paste-ready prompt at the end builds the portal
that would score 5 on all ten criteria.

## Where the points went

Best score either portal got on each criterion, per judge (1–5):

| Criterion | Claude | Grok | Codex | Who held the best | Nobody got a 5 because… |
|---|---|---|---|---|---|
| a1 orientation | 4 | 4 | 4 | tie | No page says in one line "this is working / here is the one thing left"; Messages runs 9–12 phone screens |
| a2 plain words | 4 | 4 | 4 | A | A still says "you get a lead" and shows the "follow up" rule in technical terms; B shows SignalWire, `{event_id}`, "text_back" and "Campaign in review" |
| b1 coverage | 5 | 5 | 4 | B | A has no Scheduling, Phone/forwarding or Home page, and Sign out is hidden; Codex also docked B, whose Calendar page is a dead end |
| b2 friction | 4 | 4 | 4 | tie | Calendar is a dead end on both ("Ask text_back", no contact); A's Save sits at the end of a 12-screen page |
| c1 phone layout | 4 | 4 | 4 | tie | Toasts cover the page heading; the sticky save bar covers the next field; the header truncates the business name |
| c2 phone nav | 4 | 4 | 3 | B | A has no sticky save and its desktop nav scrolls away; B's Save, Preview and nav bars together take about a fifth of the screen, with no jump links |
| d1 honesty | 3 | 3 | 4 | A | B shows unlabelled demo callers, week counts of 0 above Tuesday/Wednesday rows, and a "real read" of a test calendar offering 1 AM; A's sample shows a hand-off the real code would not make |
| d2 safety | 4 | 4 | 3 | tie | Both promise "the owner will follow up" with no evidence it happens (Codex); the diff review adds that B lets the client swap the texting number |
| e1 coherence | 5 | 5 | 4 | A | Codex: B's scheduling field spacing; A's toasts overlapping copy |
| e2 finish | 3 | 3 | 3 | tie | Dev URLs in the booking text, the business-name preview not updating, chip state not matching the field, circle vs square checks, wrong weekday, clipped preview rail |

Taking the better portal on every criterion gives 80 / 80 / 74 (mean 78). Merging A and B is
therefore not enough. The remaining 22 points sit in about 25 specific defects the judges named. The
four criteria nobody scored 5 on (orientation, honesty, phone navigation, finish) each need new
design work, not porting.

Some deductions came from the preview harness rather than the design: tailnet URLs, unlabelled seeded
callers, and a sign-in placeholder that doesn't match. A rebuild can still lose those points unless
the harness is fixed too, so the prompt covers it.

## How it runs

This is CLAUDE.md NEXT as of 2026-10-26. A new session reads NEXT and runs Part 1 below; Part 2 is
the target. The result is a third candidate, **C**, on branch `ui/compare-c`. It is fenced exactly
like A and B: no PR to main, no merge, no deploy. Michael then compares A, B and C and names the
winner, and only the winner ships. That keeps the 2026-10-26 rule that nothing from a compare branch
reaches main before he picks.

Honest limit: getting three LLM judges to give 5 on all ten criteria is a target, not a promise. The
loop stops after three rounds and reports what is left.

---

```text
TEXTBACK /client — CANDIDATE C, THE 100-POINT PORTAL
Goal: find the design that scores 5 on all ten criteria of the bake-off rubric from all three judges,
prove it on mockups BEFORE writing app code, then build it. Every requirement in Part 2 comes from a
point a judge took off. Read first, in this order: docs/notes/ui-bakeoff-2026-10-26/judge-prompt.md
(the rubric), judges/{claude,grok,codex}.md (with judges/label-key.json to know which letter was A),
docs/notes/ui-bakeoff-2026-10-26.md (walkthrough, diff review, defects), then this file.

FENCE (overrides the CLAUDE.md delivery rule for this item only)
- Work in a new worktree: git worktree add ../text_back-ui-c -b ui/compare-c main, with its own .venv.
  You may copy code from origin/ui/compare-a and origin/ui/compare-b INTO ui/compare-c (A's Messages
  page and visual system; B's Scheduling, Phone and Home pages and their backend). Never merge either
  compare branch, never open a PR from ui/compare-c, never deploy, never edit runtime config or
  credentials. Push ui/compare-c to origin as a plain branch when done.
- The only main-bound change is a small docs PR updating CLAUDE.md STATE/NEXT at the end.
- No LLM API keys, ever. Judges and agents run on CLI subscription logins (claude, grok, codex) with
  every *_API_KEY unset. If the Claude CLI's default model refuses (out of credits), add --model opus.

PART 1 — PROCESS

Step 0. Skills first. Run
  python3 ~/.agents/skills/recommend-skills/scripts/recommend_skills.py "design and build a 100-point client portal" --limit 8
and follow the CORE matches. Then superpowers:brainstorming (constrained by Part 2; do not re-open
LOCKED items) and superpowers:writing-plans. Load fluxworks-design before any visual decision. Use
superpowers:test-driven-development during the build and superpowers:verification-before-completion
before calling any step done.

Step 1. Research, in parallel subagents (one Agent call each, all in the same message). Each writes
docs/notes/portal-c/research/<topic>.md with source links. No invented facts: anything not found is
marked unknown.
  a. competitive-analyst: owner-facing settings and setup screens of the missed-call and
     field-service tools in docs/COMPETITOR-MATRIX.md, plus Jobber, Housecall Pro, Podium, Hatch,
     Numa and GoHighLevel's missed-call text-back. Use the tavily and firecrawl plugins and WebSearch
     for docs, help-center screenshots and public demos; use the playwright plugin on public pages
     only (no sign-ups, no forms, no logins). Extract how they show "is it working", setup
     checklists, message editors, forwarding setup and plain-language patterns. Note what to copy and
     what to avoid.
  b. ux-researcher: evidence-based patterns for non-technical owners on phones. Sources: the GOV.UK
     Design System (task list, check answers, plain English, error messages), NN/g and Baymard on
     mobile forms, sticky actions, toasts vs inline confirmation, and SMS-preview editors. Map each
     finding to a rubric criterion (a1–e2).
  c. accessibility-tester (with the accessibility-compliance and wcag-audit-patterns skills): the
     WCAG 2.2 AA bar for this portal at 390 px. Cover target size, focus, contrast, error
     identification, status messages (role=status) and reduced motion.
  d. Copy, using design:ux-copy plus the ai-writing-auditor agent: rewrite every visible string in A
     and B to the Part 2 word rules. Output docs/notes/portal-c/copy-deck.md, page by page: every
     label, hint, toast, empty state and error. Check it against the LOCKED customer-copy rules and
     tests/test_no_live_human_copy.py.
  Then knowledge-synthesizer merges a–d into docs/notes/portal-c/research/SUMMARY.md: the top 15
  decisions, each tied to a rubric criterion and a source.

Step 2. Design to 100 on mockups (no app code yet).
  - ui-designer (with the frontend-design, fluxworks-design, design:design-system,
    interaction-design, responsive-design and visual-design-foundations skills) produces TWO
    directions as static HTML mockups of every page and state in Part 2. Both are built from one
    fixture file so the content is identical, in docs/notes/portal-c/mockups/{d1,d2}/. Use the copy
    deck verbatim.
  - Capture both at 1280x900 and 390x844@2 with scroll captures (adapt
    docs/notes/ui-bakeoff-2026-10-26/tools/walk.py), including every state listed in Step 4.
  - Critique before judging: run design:design-critique, design:accessibility-review and the
    anti-ui-slop-reviewer agent on both directions, and fix what they find.
  - Judge with the unchanged blind panel (tools/build_packs.py and tools/run_judges.sh, adapted to
    take any two folders): d1 vs A's screenshots and d2 vs A's. Keep the judge prompt identical to
    judge-prompt.md and never tell a judge which portal is new.
  - Loop: for every criterion under 5, open the files that judge cited, fix the mockup and re-judge.
    Combine d1 and d2 where the scores show each wins somewhere. At most three rounds. The winning
    mockup and its scorecards go in docs/notes/portal-c/design/. This is "the design that gets a 100".

Step 3. Build it on ui/compare-c, one commit per layer, tests first:
(1) shell, nav, Home, Account; (2) Messages; (3) Schedule; (4) Phone & forwarding; (5) Calendar;
(6) preview harness. Port from A and B where Part 2 says so; otherwise build to the mockup. Agents per
layer: fastapi-developer for routes, data and policy hooks; frontend-developer for templates and CSS;
test-automator for the banned-word render test and the evidence-matching checklist tests. After each
layer, run the reviewer agent (or the code-review skill) on the diff, fix its findings, and get
.venv/bin/pytest tests/ green.

Step 4. Verify the real build.
  - Start C's preview on the tailnet the way A and B run: port 8766, stub telecom, temp database,
    codes at /preview/code, sign in with 980 555 0123, limit 3 codes per 15 minutes. Run it from a
    scratchpad and never touch 8000, 8443, 8765 or 8003.
  - Walk every page at both widths. Capture the Account page, an open edit-wording panel, the
    working-hours editor, carrier codes, every save toast at phone width, the unsaved-changes bar, an
    invalid phone number error, and both calendar states.
  - Save smoke on a private localhost copy (adapt tools/smoke.py): every form persists after reload.
  - ui-ux-tester walks the six owner jobs end to end at phone width; accessibility-tester and
    anti-ui-slop-reviewer run on the live preview. Fix and re-walk.
  - Final panel, blind, same rubric: C vs A and C vs B (two runs, three judges each). Up to three fix
    rounds for anything under 5.

Step 5. Stop and report.
  - Commit evidence to ui/compare-c under docs/notes/ui-compare-c/. Keep the PNGs few and small; the
    full set stays reproducible from the tools. Push the branch.
  - Docs PR to main (CLAUDE.md only). STATE gains the C line (branch, sha, preview URL, scores). NEXT
    becomes "Michael names the winner among A, B, C; ship it", with the deferred items unchanged.
    Review it with canon_review.sh, merge it, and end on clean main.
  - Tell Michael: the C preview URL, per-judge scores for C vs A and C vs B, what still scored under 5
    and why, and anything that needs his decision (link domain, hand-off destination). No menus.

PART 2 — TARGET (what a 5 on every criterion requires)

Product name on screen: TextBack. The owner is non-technical, on a phone, between jobs.

## Never break (LOCKED in CLAUDE.md)
- The texting number is read-only in the portal. Show it with "Set up by FluxWorks. It can't be
  changed here." No swap, no edit, no port.
- Customers never get a live human. No copy that promises a call-back from a person the system does
  not actually notify.
- STOP/HELP/consent/quiet hours/booking truth stay with deterministic policy. The opt-out wording is
  editable but the word STOP stays and cannot be removed.
- No booking is claimed without a calendar event ID. Business specifics live in config/client_settings,
  never in code.
- Do not touch deploy/textback-designer/, docs/demo/, credentials, the live service (127.0.0.1:8000,
  private 443, public 8443) or the A and B previews (8765, 8003).

## Pages (all six owner jobs, findable in one tap)
Phone: bottom nav with Home, Messages, Schedule, Calendar, Phone; Account (with Sign out) behind the
business name in the header. Desktop: the same items in a sidebar that stays fixed while the page
scrolls (A's sidebar scrolled away and left an empty rail).

1. Home — answers "Is TextBack working?" in the first line, from real state only:
   "Working: missed calls get a text within a minute." or "Not working yet: 2 steps left."
   Below: one card per setup item (Calendar, Call forwarding, Texting approval), each with one state
   word (Done / Needs you / Waiting on phone companies) and at most one button that goes straight to
   the fix. Then "This week" counts and "This week's callers" — both the SAME window, so a 0 count
   never sits above rows. Every row shows a full date from a real datetime ("Fri, Oct 23, 2:40 PM");
   never hand-write a weekday.
2. Messages — keep A's conversation spine: texts in the order a customer gets them, rendered as
   bubbles, step headings (Missed call → Questions → Booking → No reply → Steps back), per-text
   "Customized"/"Standard wording" badge with Reset, cost line in plain words ("1 text" / amber
   "Billed as 3 texts — the "—" symbol makes texts shorter. Use "-" instead."), START/HELP/STOP
   collapsed under "Required by phone companies. Most businesses never change these."
   Add:
   - Jump chips under the title, sticky with the title, so 9+ screens never need blind scrolling.
   - A sticky Save bar that appears only with unsaved changes, says what changed ("2 texts
     changed"), and never covers the field being edited (scroll-padding-bottom = bar height).
   - Inserts are chips with plain labels ("Business name", "Calendar links", "Customer's first
     name"). No braces anywhere on screen, no {event_id}, no {invite_line}. Show only the inserts
     that text can use.
   - The sample conversation is produced by running the real policy code on scripted customer
     replies, never hand-written, so it cannot show a hand-off or a parse the product would not
     make. Label: "Example conversation · nothing is sent · names made up".
   - Links in previews render with the configured public base URL, never a tailnet/preview host,
     and as a short tappable label in the bubble ("Add to Google Calendar ›") with the full link
     on tap. Raise to Michael (do not build): the production host is itself a long ts.net:8443
     address; a short branded link domain needs his decision and spend.
   - The hand-off text's rule, in plain words: "This text must tell the customer someone will
     follow up." Directly under it, the true destination from config: "These go to <who actually
     receives them>." Never "you get a lead" unless the owner does.
   - Toast after save names the change ("Saved. Changed: Question 2, the location") and sits
     under the header, never over the page title or intro.
3. Schedule — port B's page: appointment length with quick-pick chips (the chip matching the field
   value is selected; a custom value selects none and says "Custom"), time zone, working hours,
   quiet hours, reminder timing ("If there's no reply, send a reminder after [2 hours]"). Every rule
   shows "Default: …" and Reset. Quiet hours say what still goes out (the first text, live replies,
   STOP/HELP). If working hours are "any time", show a warning: "Customers can be offered times
   like 1 AM. Set your hours." plus a one-tap "Mon–Fri, 8 AM–5 PM" the owner can accept. Do not
   change the backend default yourself. Every consequence line and save confirmation must match what
   the code actually does. B applies scheduling settings live, so first establish which settings
   affect conversations already in progress, then word the confirmation to match. Example: "Saved.
   Applies now, including customers mid-conversation; reminders already scheduled keep their time."
   Add a test that pins each claim to the behaviour.
   When porting B's backend, also fix the diff-review items in docs/notes/ui-bakeoff-2026-10-26.md:
   run find_event recovery BEFORE the working-hours check, so narrowing hours mid-retry can never
   orphan a created calendar event (with a test); drive the registration card from live status,
   not submit-time files; and fix the calendar-link end time.
4. Calendar — connected: name, account, "Bookings go here", change button. Not connected: one
   sentence on why it matters plus the Connect button when the Google Web client is configured, or a
   real contact action ("Text FluxWorks support", from a config value; add one if none exists) when
   it isn't. No dead ends. "Check availability" shows the next free times only inside working hours
   and labels a test or unconnected calendar in the card title ("Test calendar, not yours"), never
   "a real read".
5. Phone — business line, texting number (read-only, see LOCKED), owner mobile (code to the NEW
   number first; "Keep my current mobile" escape; A's flow), HELP number, business name. When the
   business name changes and any customized text still contains the old name literally, offer
   "Update 2 texts that still say 'Oak & Pine Tree Care'". Forwarding: carrier picker with codes,
   the warning "Only forward busy and unanswered calls — forwarding every call stops answered calls
   from reaching you", and a checklist where each tick comes only from matching evidence. A direct
   call to the texting number never ticks "forwarding works". If the app cannot tell, the step is a
   manual tick labelled "You checked this". One check style: done / not yet / you checked, all in
   text, not only shape. No step may contradict another (e.g. "Done" above "No call recorded yet").
6. Account — sign-in mobile (links to Phone to change it), remembered devices with "Sign out
   everywhere", and Sign out.
Sign in: label "Your mobile number", neutral placeholder, never prefill a real number (a public page
must not reveal the owner's mobile), same page for unknown numbers (existing behaviour).

## Words (a2) — banned on every client screen, with the replacement
SignalWire → (nothing; it's plumbing) · "[SignalWire Free Trial] tag" → "Until phone companies
approve your business for texting, each text starts with a short network notice." shown only while
that is true, from stored registration state · text_back → TextBack · campaign / brand / 10DLC /
registration → "texting approval" · segment → text · lead → "customer details" · token / {braces} →
insert chips · webhook / provider / event ID / call_sid → never · nudge → reminder · hand-off →
"when the assistant steps back". Add a test that renders every /client page and fails on any banned
word or a "{" in visible text.

## Phone layout and finish (c1, c2, e2)
- 390 px: tap targets ≥ 44 px; owner-entered text (business name) wraps to two lines, never
  ellipsized; all sticky chrome together ≤ 170 px of the 844 px screen.
- Desktop: the preview rail scrolls its own content and never clips a bubble or a label.
- Every date from a datetime and formatted by one helper. Every chip state from the field value.
- No dev text, test suffixes, hosts or ports in any rendered string.

## Preview harness (so judges score the design, not the harness)
Seeded callers and conversations carry a visible "Example" tag. The link host is a production-
shaped public base URL. Seed dates are computed relative to today. Registration state, forwarding
evidence and calendar state are seeded consistently with each other. The sign-in placeholder and
the owner mobile agree with the Account page.

## Evidence the judges must see
Capture every state in Step 4. Judges lowered their confidence for states they could not see:
the account menu, opened editors, the hours grid and carrier codes.
```
