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

## How to use it

Run it from `main` once Michael has named the winner and it has shipped (CLAUDE.md NEXT: changes come
after the winner, from main). The prompt is written to reach the same end state from either base:
- **If A ships:** most of the work is porting B's three pages and fixing the shared defects.
- **If B ships:** most of the work is the language and honesty rules.

Its acceptance test is the same three-judge panel, run on the new portal against the one that
shipped.

---

```text
Build the TextBack client portal (/client) that scores 5 on every criterion of the bake-off rubric in
docs/notes/ui-bakeoff-2026-10-26/judge-prompt.md. Read that rubric, the three scorecards in
docs/notes/ui-bakeoff-2026-10-26/judges/, and docs/notes/ui-bakeoff-2026-10-26.md before you design
anything. Every requirement below comes from a point a judge took off. Work from main in a branch;
deliver through the normal CLAUDE.md path (PR, independent review, canon/review, merge, deploy),
one PR per layer: (1) shell + Home + Account, (2) Messages, (3) Scheduling, (4) Phone & forwarding,
(5) Calendar, (6) preview harness + evidence + judge run. Use the fluxworks-design skill for every
visual decision (light, plain, one green accent, Archivo + Source Sans). Product name on screen:
TextBack. The owner is non-technical, on a phone, between jobs.

## Never break (LOCKED in CLAUDE.md)
- The texting number is read-only in the portal. Show it with "Set up by FluxWorks. It can't be
  changed here." No swap, no edit, no port.
- Customers never get a live human. No copy that promises a call-back from a person the system does
  not actually notify.
- STOP/HELP/consent/quiet hours/booking truth stay with deterministic policy. The opt-out wording is
  editable but the word STOP stays and cannot be removed.
- No booking is claimed without a calendar event ID. Business specifics live in config/client_settings,
  never in code.
- Do not touch deploy/textback-designer/, docs/demo/, credentials, 443 or 8443 outside the deploy step.

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
   change the backend default yourself. Save confirmation: "Saved. New conversations use these hours."
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

## Evidence and acceptance
1. Run docs/notes/ui-bakeoff-2026-10-26/tools/walk.py (update PAGES) at 1280×900 and 390×844@2,
   scroll captures. Also capture the states judges said they could not see: Account page, an open
   "Edit wording" panel, the working-hours editor, carrier codes, every save toast at phone width,
   the unsaved-changes bar, an invalid phone number error, and both calendar states.
2. Run the same three-judge blind panel (tools/build_packs.py + tools/run_judges.sh; CLI logins
   only, every *_API_KEY unset, never an API key) on the new portal against the one now on main.
3. Target: 5 from all three judges on all ten criteria. For any criterion under 5, open the files
   that judge cited, fix the cause, and rerun, at most three rounds. Report the final scorecards
   and every remaining deduction as either a design fix still owed or a harness or evidence limit.
   Keep the panel blind: never tell a judge which portal is new.
4. .venv/bin/pytest tests/ green, canon check clean, /client verified on 8443 after deploy.
```
