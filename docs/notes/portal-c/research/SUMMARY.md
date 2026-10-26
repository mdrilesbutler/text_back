# Candidate C research synthesis: the 15 design decisions (2026-10-26)

Inputs: `competitors.md`, `ux-patterns.md`, `accessibility.md`, `../copy-deck.md`, the spec
(`../../ui-bakeoff-2026-10-26/design-prompt-100.md` Part 2) and the rubric (`judge-prompt.md`).
Ranked by rubric impact: the four criteria no judge gave a 5 (a1 orientation, d1 honesty, c2 phone
navigation, e2 finish) come first. Each decision names its criteria and its source section. Where the
sources disagree the ruling is in "Conflicts resolved"; anything no source could verify is marked unknown.
Confidence: high = three or more sources agree or the spec fixes it; medium = one evidence-backed source;
low = a synthesis call the mockup critique must confirm.

## The 15 decisions

1. **Home's first line is the computed system state.** `<h1>Home</h1>`, then one display-size sentence
   (>= 22 px, the largest text on the page) with exactly three variants from the copy deck:
   "Working: missed calls get a text within a minute." / "Not working yet: [N] steps left." (N = count of
   Needs-you cards) / "Set up on your side. Waiting on the phone companies to approve texting." No
   marketing line above it. (a1, d1) Sources: ux-patterns §A3; copy-deck §3 `home_status_*`;
   competitors Jobber §1 (Status block, On/Off). High.
2. **One check vocabulary on Home cards and the Phone checklist** (table below): the glyph says
   done-ness, the word says what, and a glyph never appears without its word. (a1, d1, e1, e2) Sources:
   accessibility 3.2.4 and 1.4.1; ux-patterns §A1; copy-deck `home_state_words`, `check_states`. High.
3. **Setup cards are tasks, not answer summaries.** Three cards (Calendar, Call forwarding, Texting
   approval): title, state word, one hint line without a full stop, at most one button that lands on the
   fix; the whole card is the tap target when Needs you; Waiting cards have no button and no link. Saved
   values (calendar name, carrier) live on their own pages. No card state may contradict its page
   ("Done" above "No call recorded yet" is a test failure). (a1, b2, d1) Sources: ux-patterns §A2; Part 2
   Home; competitors Goodcall §2 ("Nothing changes until you approve it"). High.
4. **Forwarding checks tick only from matching evidence.** Checks 1, 2 and 4 come from recorded calls;
   check 4 is Done when the caller's number matches neither the business line nor the texting number;
   a call placed straight to the texting number never ticks anything; checks 3 and 5 are manual and
   read "You checked this"; the heading counts "[N] of 5 done". (d1, d2) Sources: Part 2 Phone;
   copy-deck §7 Checklist; competitors GHL §4 (three-point verification), Numa §1. High; the
   plain-words claim for check 4 must be pinned to the code by a test (copy-deck Open 9).
5. **Nothing on screen is hand-written sample truth.** Example-conversation bubbles come from running
   the real policy code on scripted replies, labelled "Example conversation · nothing is sent · names
   made up"; every seeded caller carries an "Example" tag; an unconnected calendar's availability card is
   titled "Test calendar, not yours"; preview links render with the configured public base URL as
   "Add to Google Calendar ›" with the full link on tap; every date comes from a datetime through one
   helper. (d1, e2) Sources: ux-patterns §G2; Part 2 Messages, Calendar, Preview harness; copy-deck
   `rail_foot`, `home_example_tag`, `avail_title`. High.
6. **Sticky chrome is 156 px, not 170** (table below): header 56 fully sticky, jump chips 44 (Messages
   only), bottom nav 56; the Save bar (56) appears only when dirty and REPLACES the nav, so a nav tap can
   never drop changes and chrome never exceeds 156. `scroll-padding-top/bottom` equal the sticky heights
   plus 4 px so a focused field or a jump target is never covered. (c2, c1) Sources: ux-patterns §F2,
   §F5; accessibility 2.4.11, 2.4.12; Part 2 Phone layout (cap). High on the budget; medium on
   nav-replacement (see Conflicts, 2).
7. **Five labelled bottom tabs, Account behind the header name, desktop sidebar that never scrolls
   away.** Tabs: Home, Messages, Schedule, Calendar, Phone (`<nav aria-label="Pages">`,
   `aria-current="page"`, items >= 64 x 56, label >= 12 px). The business name in the header is a
   button named "Account" opening Signed in with / Account / Sign out. Desktop: same five plus Account in
   a `position: sticky` sidebar. (c2, b1, a1) Sources: ux-patterns §F1; Part 2 Pages; copy-deck §9
   `nav`, `header`, `menu`; competitors Jobber §7 (owners expect a bottom bar). High.
8. **Messages gets five jump chips, sticky under the title.** Chip text equals the section h2s: Missed
   call, Questions, Booking, No reply, Steps back; the row is one 44 px line that scrolls sideways inside
   its own container (fade at the edge, keyboard reachable), the page itself never scrolls sideways; the
   active chip tracks scroll; each target h2 has `tabindex="-1"`. START/HELP/STOP is reached by scrolling;
   the example conversation by its own link, not a chip. (c2, a1) Sources: ux-patterns §F3;
   accessibility 2.1.1, 1.4.10; Part 2 Messages. High on the pattern; chip count is a ruling (Conflicts, 3).
9. **Save feedback is an in-flow status banner, never a floating toast.** One empty
   `<div role="status">` exists at load between the sticky header and the h1, content-width; after a
   save it holds "Saved. Changed: [card titles]." with a green left rule, the word Saved, and a 44 px
   Dismiss; it pushes content down, so it cannot cover the title or a field; it persists until dismissed
   or the next navigation; it never takes focus and never carries an error. There are no floating toasts
   anywhere in C. (c1, b2, d1, e1) Sources: ux-patterns §E1-E3; accessibility 4.1.3 and "Toast rule";
   Part 2 Messages (toast under the header); copy-deck `toast_saved`, `toast_dismiss`. High.
10. **Every visible string comes from the copy deck, verbatim.** Sentences <= 25 words; the only
    specialist phrase is "texting approval", explained once on its card; the banned-word render test
    covers Part 2's list plus GOV.UK's error words (please, sorry, valid, invalid, oops, error occurred,
    required field) and fails on any "{" in visible text, any `title=` on a control, and any host or port.
    (a2, e2) Sources: Part 2 Words; ux-patterns §B1, §B2; copy-deck Conventions; competitors Summary 7-8
    (the jargon to avoid). High.
11. **Errors say the fix and are server-rendered.** Validate on blur (or at 10 digits), clear the error
    per keystroke once fixed, tick only hard-format fields; wording "Enter ... like 704 555 0123" / "must
    be ..."; on a failed POST each bad field gets `aria-invalid` plus an inline message and a linked
    summary (`role="alert"`, `tabindex="-1"`) before the h1 receives focus, works with JS off; the owner's
    text is never cleared; no tooltips. (b2, a2, d2) Sources: ux-patterns §D1, §D2; accessibility 3.3.1,
    3.3.3; copy-deck `error_summary`, `reason_*`, per-field errors. High; summary heading words ruled in
    Conflicts, 5.
12. **The cost line is computed on the rendered text and names the culprit.** Render the template with
    the real business name, a 12-character first name, the real link length and the network-notice prefix
    while approval is pending; count GSM-7/UCS-2 with extension characters doubled; show "1 text · [N]
    characters" or the amber "Billed as [N] texts. The "[symbol]" symbol makes each text hold only 70
    characters. Use "[plain symbol]" instead." with a one-tap replacement for curly quotes, dashes and the
    ellipsis; updates announce at most once per second and only when the count changes. (d2, a2, e2)
    Sources: ux-patterns §G1; copy-deck `cost_*`, `trial_notice`; accessibility 4.1.3. High on the
    arithmetic; the line itself has no competitor precedent (competitors Gaps) so user-test it.
13. **Every rule shows its default and has its own Reset; chip state derives from the field.** "Default:
    ..." under each Schedule rule and per-text "Reset" on Messages; no page-wide Reset; quick-pick chips
    are visually-hidden radios, the chip equal to the field value is selected, any other value selects
    none and shows "Custom"; one primary Save per page, never disabled (nothing changed -> "Nothing to
    save yet"). (b2, d2, e2) Sources: ux-patterns §C5; Part 2 Schedule; copy-deck `duration_chips`,
    `schedule_reset`; accessibility 1.3.1, 4.1.2; competitors Hatch §5 (inherit/custom). High.
14. **Consequences are stated before or at the save, and the locked rules show as reasons.** Rename
    offers "Update [N] texts that still say '[old name]'" instead of rewriting silently; quiet hours list
    what still goes out; the Schedule banner's claim about mid-conversation effect is pinned to the code
    by a test; owner-mobile change is a two-step flow with "Keep my current mobile"; the forward-all
    warning is always visible and the conditional codes come first; the texting number is read-only
    with "Set up by FluxWorks. It can't be changed here."; STOP stays. (d2, d1) Sources: ux-patterns §A4,
    §A6, §C6; Part 2 Never break, Schedule, Phone; copy-deck `rename_offer`, `card_quiet`,
    `schedule_toast`, `forwarding_warning`, `texting_number`; competitors Podium §6, HCP §3, Goodcall §4
    (invert the *72-first ordering). High.
15. **No page is a dead end, and no promise outruns config.** The Calendar not-connected and Messages
    not-enabled cards end with a real next step driven by `TEXT_BACK_SUPPORT_CONTACT` (see Open items);
    the steps-back card shows the true destination from config ("These go to the FluxWorks operator." or
    "These go nowhere yet. ..."); "Connected as [account]" is dropped because it is not stored. (b2, d2,
    d1) Sources: ux-patterns §A6; Part 2 Calendar, Messages; copy-deck `cal_no_connect`,
    `rule_steps_back_destination`, Open 1-4; competitors Summary 10 (nobody shows "is it working" in one
    line and no dead ends: C's opening). High.

Build constraints carried from accessibility.md that the mockups must also obey (c1, e2): control
boundaries use #78716c (the brief's #e7e5e4 is 1.2:1 and decorative only); every tappable control is
>= 44 x 44 CSS px with >= 8 px gaps; one focus ring (2 px solid #166534, 2 px offset); labels above
fields with persistent hints, no placeholder labels, `tel`/`numeric`/`email` keyboards, autocorrect off
on names and emails; the sign-in code is ONE `<input maxlength="6" autocomplete="one-time-code">` with
decorative cells; owner text wraps and is never ellipsized; no horizontal scroll at 320 px.

## Shared vocabulary (Home cards and the Phone checklist)

| Word | Glyph | Colour role | When used |
|---|---|---|---|
| Done | filled circle with a tick, #166534 | word in ink #171717, no fill, no button | Home card complete from evidence; Phone check with matching evidence |
| Needs you | empty circle, 2 px border #78716c | filled tag: #fffbeb background, #92400e text (6.84:1); the card is the link and holds the one button | Home only: an owner action is pending (connect, reconnect, finish forwarding) |
| Waiting on phone companies | empty circle, 2 px border #78716c | muted text #57534e, no fill, no button, card not linked | Home only: Texting approval card while approval is pending |
| Not yet | empty circle, 2 px border #78716c | muted text #57534e | Phone checklist step with no evidence yet |
| You checked this | tick inside a dashed circle, #57534e | muted text #57534e | Phone checklist manual steps (3 answered-call, 5 turn-off code) after the owner ticks |

Rules: the empty circle always means "not done", the word says why; Done and You checked this use
different glyphs so a manual tick never looks like evidence; red (#b91c1c) appears only in error text and
the error summary, never as a card state; the caller status pills on Home (Booked, Texting, Waiting for a
reply, Assistant stepped back, No reply, Asked us to stop) are a separate vocabulary and reuse none of
these glyphs. In forced-colours mode the glyphs redraw with CanvasText and the word carries the state.

## Sticky chrome at 390 x 844

| Element | Height | Present | Notes |
|---|---|---|---|
| Header: TextBack wordmark, business name (button "Account") | 56 px | every page, fully sticky, opaque | name wraps to two lines at 14/18 px inside the 56; verify with a 40-character name |
| Jump chips "On this page" | 44 px | Messages only, sticky under the header | one row, sideways scroll in its own container; chips >= 44 px tall, 8 px gaps |
| Status banner slot (`role="status"`) | 0 (in flow) | every page, between header and h1 | grows when filled; never sticky, never fixed |
| Bottom nav | 56 px + `env(safe-area-inset-bottom)` | every page while nothing is unsaved | five items >= 64 px wide, label >= 12 px, never clipped |
| Save bar: "[N] texts changed" · Save · Discard | 56 px + safe-area | replaces the bottom nav while dirty | same slot and height as the nav; buttons last in DOM order |
| Total sticky | 156 px Messages, 112 px other pages | cap from Part 2 is 170 | ratio about 4.4:1 content to chrome on Messages |
| `scroll-padding-top` | 104 px Messages, 60 px other pages | header + chips + 4 px ring allowance | |
| `scroll-padding-bottom` | 56 px + safe-area + 16 px | one bar is visible at a time, so no sum | updated by JS when the Save bar appears |

Safe-area inset is 0 in the 844 px Playwright viewport and in Safari's in-browser mode (it adds height
only when installed to the home screen). The 56 px figures are design choices, not platform citations.

## Conflicts resolved

1. **Chrome budget 156 vs 170.** ux-patterns §F2 budgets 156; Part 2 and accessibility 2.4.11 cap at
   170. Adopt 156 as the design value; 170 stays the test ceiling.
2. **Save bar replaces the nav (ux-patterns §F2) vs nav + Save bar stacked (accessibility 2.4.11's
   padding sum).** Replacement wins: it keeps chrome at 156 and makes a lost-changes nav tap impossible;
   the padding formula collapses to one bar. Risk (low confidence): a judge may read a vanished nav as
   broken; this and the amber Needs-you tag are the two calls the critique round checks first.
3. **Jump chips: five (ux-patterns §F3) vs seven in copy-deck `messages_jump`.** Five; the deck row
   drops "START, HELP, STOP" and "Example conversation". Seven chips cannot fit one 44 px row at 390.
4. **Check vocabulary: Home (Done / Needs you / Waiting) vs Phone (Done / Not yet / You checked
   this).** Both sets stay as words; they share glyphs by done-ness, as the table above fixes. The
   GOV.UK styling in ux-patterns §A1 (Done = plain text, Incomplete = one filled tag, Cannot start = grey)
   is adopted; the filled tag is amber, not the green accent, so "needs action" never reads as "good".
   accessibility.md proposed the green tint #dcfce7 for Done pills; Done takes no fill at all. Low-medium.
5. **Error summary heading: "There is a problem" (ux-patterns §D2) vs "Fix 2 things to save"
   (accessibility 3.3.1) vs the deck's "Not saved. ..." lines.** The deck wins on words: Messages uses
   `error_summary` as written; Schedule and Phone use a new deck row `error_summary_fields` = "Not saved.
   [N] things need a change." with one link per field and `error_summary_kept` as the second line.
6. **Save confirmation: "toast" (Part 2, copy deck keys) vs in-flow banner (ux-patterns §E) vs
   dismissible, never auto-removed (accessibility).** One component: the in-flow status banner of
   decision 9. The deck keeps its `toast_*` keys; the word "toast" never appears on screen. ux-patterns
   §E1 allowed floating toasts for events not triggered on the page; accessibility forbids fixed toasts;
   the stricter rule wins and such events become page notices (`session_ended`, `expired`).
7. **Cost line wording: Part 2's "Billed as 3 texts — the "—" symbol ..." vs the deck's "makes each
   text hold only 70 characters".** The deck: it states the reason and does not itself contain the em
   dash it warns about.
8. **Header: partially persistent (ux-patterns §F2 "may") vs fixed heights for the focus-obscured
   test.** Fully sticky; the budget already fits and the elementsFromPoint test needs a fixed geometry.
9. **Home h1: computed sentence (ux-patterns §A3) vs "Home" (copy deck, accessibility 2.4.2 title rule).**
   h1 stays "Home"; the status sentence is the first content line in display type (decision 1).

## Copy deck open items, resolved (session lead's builder decisions)

1. Support contact: new config value `TEXT_BACK_SUPPORT_CONTACT`, empty by default. When empty, the
   Calendar not-connected card reads "Connecting from this page isn't set up for your account yet.
   FluxWorks sets it up for you." with no button and no "[reply time]" string anywhere; when set, the
   "Text FluxWorks support" button appears with the contact under it. `messages_not_enabled` follows
   the same rule (synthesis extension, confirm): "Message editing isn't turned on for this account yet.
   FluxWorks turns this on when your account is set up."
2. Chat destination label: "the FluxWorks operator" (`rule_steps_back_destination` = "These go to the
   FluxWorks operator."; rail pill "Customer's details sent to the FluxWorks operator"). The deck's
   "ask FluxWorks how they'll reach you" sentence is not promised; add it only on Michael's word.
3. No destination configured (channel off or "unconfigured"): "These go nowhere yet. FluxWorks turns
   this on when your account is set up." The "log" channel wording is unknown; keep the deck's
   `destination_log` until ruled.
4. "Connected as [account]" is dropped; `cal_connected` body is "Bookings go here: [calendar name]."
5. Account devices show "This phone" / "Another device" with the signed-in and last-used dates only.
6. Time zone shows "Default: [the configured default]", rendered from the runtime default; whether
   onboarding sets a per-client default so it never reads UTC is unknown.
7. Short branded link domain: raised to Michael, not built; bubbles show the label, taps show the
   configured public base URL.
8. Forwarding check 4 compares the caller's number against the business line and the texting number;
   `check_4` evidence text becomes "The text went to the caller's number, not your business number or
   the texting number."
9. `home_approval_detail` "has filed" depends on reading approval state live from the registry (the
   diff-review fix); until that is confirmed in code, the card may only show the pending/not-started
   lines the state proves. Unknown.

## Still unknown (do not design as fact)

- Carrier codes: GHL and Numa disagree for AT&T; all codes are unverified until checked against the
  carrier; AT&T and Cricket keep the `code_unverified` warning (competitors Gaps).
- No competitor is confirmed to show a segment count, preview or reset; the cost line and "Reset to
  standard wording" have no external precedent (competitors Gaps).
- Dark-theme contrast ratios and the focus ring on the TextBack bubble: unknown until C's tokens exist
  (accessibility Palette, 2.4.13).
- Competitor phone layouts were unreadable; c1/c2 rest on ux-patterns and accessibility only.
- Where the example conversation lives on the phone (separate view reached by a link, with "Back to
  editing") is a mockup call; the desktop rail scrolls its own content (Part 2).
