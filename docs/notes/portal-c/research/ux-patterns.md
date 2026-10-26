# Portal C research: evidence-based UX patterns for a non-technical owner on a 390 px phone

Date: 2026-10-26. Author: ux-researcher subagent (read-only; no services run, no sign-ups).
Target: `docs/notes/ui-bakeoff-2026-10-26/design-prompt-100.md` Part 2. Rubric: `judge-prompt.md` (a1–e2).
Judges' deductions this answers (from `judges/claude.md`): toasts over the page heading, sticky bars
covering the next field and eating about a fifth of the screen, 9–12-screen Messages page with no jump
links, chip state not matching the field, dead-end Calendar page, unlabelled demo data, "Done" above
"No call recorded yet", vendor words on every card.

Format per finding: **Pattern** (one sentence) · **Evidence** (source URL, quoted where possible) ·
**Rule for this portal** · **Rubric**. Anything not found is marked *unknown*; nothing is invented.
Secondary sources are labelled as such. Paywalled Baymard pages that returned only a headline are listed
under Unknowns rather than cited.

---

## A. Orientation and status (a1, d1)

### A1. One status set, descriptive words, colour never alone
**Pattern.** A setup item carries exactly one status word from a small fixed set; the word is an adjective, not a verb, and colour only reinforces it.
**Evidence.** GOV.UK Tag: "Use adjectives (descriptive words) and not verbs (action words) for the names of your tags"; "Do not use colour alone to convey information" — https://design-system.service.gov.uk/components/tag/ . GOV.UK Complete multiple tasks: 'Completed' is "black text with no background colour"; 'Cannot start yet' "should be grey text with no background colour"; "Do not use the red background colour for any status text except errors"; statuses "written in sentence case" — https://design-system.service.gov.uk/patterns/complete-multiple-tasks/ , https://design-system.service.gov.uk/components/task-list/ .
**Rule.** Home cards use exactly three states, mapped to GOV.UK's: Done = Completed (black text, no fill, no button); Needs you = Incomplete (one filled tag, the row is the link, one button); Waiting on phone companies = Cannot start yet (grey text, no fill, no button, row not linked). Red fill appears only for a real problem ("There is a problem"). Forwarding checks use the same three words in text: done / not yet / you checked. Never a state icon without its word.
**Rubric.** a1, d1, e1.

### A2. Whole-row link, one short hint, no answers in the task list
**Pattern.** Each setup task is a tappable row with a name, a status and at most one hint sentence; the list shows state, not the saved values.
**Evidence.** GOV.UK Task list: "The whole row is linked, allowing users to select anywhere within it to start the task"; hint text is "one short sentence without full stops" with no links; "The task list should not be used as a way of showing users their answers" — https://design-system.service.gov.uk/components/task-list/ .
**Rule.** Home setup cards: title + state word + one hint line (no full stop, no link inside), the card itself is the tap target when Needs you. Values (calendar name, forwarding carrier) live on their own pages, not on Home.
**Rubric.** a1, c1, b2.

### A3. The first line answers "is it working", with a step count
**Pattern.** Say the system state in one sentence and, if work remains, how many steps, because a count lets people estimate effort.
**Evidence.** NN/g progress indicators: "knowing the number of steps at least helps them form an estimate" — https://www.nngroup.com/articles/progress-indicators/ . NN/g visibility of system status: systems should "clearly communicate to users what the system's state is"; "A lack of information often equates to a lack of control" — https://www.nngroup.com/articles/visibility-system-status/ .
**Rule.** Home h1 is computed from state only: "Working: missed calls get a text within a minute." or "Not working yet: N steps left." where N equals the number of Needs you cards. No marketing line above it.
**Rubric.** a1, d1.

### A4. No consequence without telling the owner; no silent removal
**Pattern.** Anything the system did or will do to the owner's data is stated in brief, understandable terms.
**Evidence.** NN/g: "no action with consequences to users should be taken without informing them"; explain external changes "in brief but understandable terms"; the wish-list example says state which items are unavailable and let users decide — https://www.nngroup.com/articles/visibility-system-status/ .
**Rule.** Business-name rename offers "Update 2 texts that still say 'Oak & Pine Tree Care'" instead of rewriting silently. Quiet hours list what still goes out. Schedule save states whether in-progress conversations are affected (wording pinned to code by test, per Part 2).
**Rubric.** d1, d2.

### A5. Feedback within one second; looped indicator for 2–10 s
**Pattern.** Any network action shows feedback immediately and a looped indicator if it takes more than about a second.
**Evidence.** NN/g: "Use a progress indicator for any action that takes longer than about 1.0 second"; looped indicator "reserved for actions that take between 2-10 seconds"; "Don't-click-again" warnings not recommended — https://www.nngroup.com/articles/progress-indicators/ .
**Rule.** Send code, Save, Connect Google Calendar, Check availability: button enters a busy state within 100 ms with a looped indicator and the verb ("Saving…"); never a static "Loading…" line, never a disabled button as the only feedback.
**Rubric.** b2, d1.

### A6. Confirmation states what happens next and when
**Pattern.** After an action completes, tell the owner what happened, what happens next, and who to contact.
**Evidence.** GOV.UK Confirmation pages "must include" "details of what happens next and when" and "contact details for the service" — https://design-system.service.gov.uk/patterns/confirmation-pages/ .
**Rule.** Calendar not-connected card and the Texting approval card end with a next-step sentence and a real contact action (config value), so no page is a dead end. Owner-mobile change: "We texted a code to the new number. Until you enter it, codes still go to your current mobile."
**Rubric.** b2, d2.

---

## B. Plain language (a2)

### B1. 25-word sentences, 5-sentence paragraphs, explain a specialist term once
**Pattern.** Short sentences and short words; a specialist term may be used only if explained on first use.
**Evidence.** GOV.UK Use clear language: "Try to split up sentences that are over 25 words long"; "Paragraphs should have no more than 5 sentences each"; specialist terms: "You just need to explain what they mean the first time you use them"; "Use 'buy' instead of 'purchase', 'help' instead of 'assist'"; words ending "–ion" and "–ment" make sentences longer; active voice preferred ("You need an electronic travel authorisation") — https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/writing-guidelines/clear-language/ . Reading-age figure: *unknown* (the page cites "1 in 6 adults in England have very poor literacy skills" instead).
**Rule.** Every visible string ≤ 25 words; hints one sentence; the only specialist phrase allowed is "texting approval", explained once on its card. Copy deck lint: flag any sentence over 25 words and any -ion/-ment noun that has a verb form.
**Rubric.** a2, a1.

### B2. Error words to avoid
**Pattern.** Error text says what happened and how to fix it, with no apology, no "please", no "invalid", no jargon.
**Evidence.** GOV.UK Error message: avoid "please", "sorry", "valid"/"invalid", "oops", "forbidden", "illegal", "you forgot", technical jargon such as "form post error"; avoid general messages "An error occurred", "This field is required"; use "Enter your first name" for empty fields and "must be" descriptions for wrong format — https://design-system.service.gov.uk/components/error-message/ .
**Rule.** Banned-word test extends Part 2's list with: please, sorry, invalid, valid, oops, error occurred, required field. Phone error: "Enter a mobile number with 10 digits" (empty: "Enter your mobile number").
**Rubric.** a2, b2.

---

## C. Forms on a phone (b2, c1)

### C1. One thing per page, or one visible task per screen
**Pattern.** Each page (or each screen of a long page) carries one decision, which is easier on mobile and makes errors recoverable.
**Evidence.** GOV.UK Form structure: start with "each page containing just one thing"; it helps people "use the service on a mobile device" and "recover easily from form errors"; "User research will tell you when you can merge pages together" — https://www.gov.uk/service-manual/design/form-structure . GOV.UK Question pages: "Asking just one question per question page helps users understand what you're asking them to do"; use a `<label>`/`<legend>` as the page heading — https://design-system.service.gov.uk/patterns/question-pages/ .
**Rule.** Edit-wording is its own panel/page with the text name as its h1 and one textarea; owner-mobile change is a two-step flow (new number → code), never both on one card. Schedule groups related fields under statement headings (hours, quiet hours, reminders) and each group fits one 390×844 screen without the keyboard.
**Rubric.** b2, c1, a1.

### C2. Labels above the field, never inside it
**Pattern.** Visible labels sit above full-width fields; placeholders are not labels.
**Evidence.** Baymard (18-site mobile study): left labels leave a field that "will often not be wide enough to display the user's entire input"; labels above let fields span the full width — https://baymard.com/blog/mobile-form-usability-label-position . NN/g placeholders: "Disappearing placeholder text strains users' short-term memory"; "Users may mistake a placeholder for data that was automatically filled in"; "Not all screen readers read placeholder text aloud"; hints "should also be persistent and placed outside of the field" — https://www.nngroup.com/articles/form-design-placeholders/ . NN/g mobile checklist item 2: "Is the label above it?"; item 4: "Have you removed any placeholder from inside the field?" — https://www.nngroup.com/articles/mobile-input-checklist/ .
**Rule.** All labels above; hints as a persistent line under the label. Sign-in: label "Your mobile number", hint "10 digits", empty or format-only placeholder, never a real number (this also satisfies Part 2's "never prefill a real number").
**Rubric.** c1, b2, d2.

### C3. Right keyboard, no autocorrect on names, accept any format
**Pattern.** Each field opens the keyboard for its data, turns autocorrect/autocapitalize off where dictionaries fail, and accepts the owner's formatting.
**Evidence.** Baymard: "54% of mobile sites fail to invoke optimized touch keyboards for either phone, ZIP code, or credit card form fields"; autocorrect neglected by 79%; disable it for names, address lines, emails; the attributes are "type, inputmode, and pattern" — https://baymard.com/blog/mobile-touch-keyboards . NN/g checklist items 11, 12, 14: "What is the right keyboard for this field?"; don't autocorrect names/emails; "Do you allow users to enter it in whatever format they like?" — https://www.nngroup.com/articles/mobile-input-checklist/ .
**Rule.** Phone fields: `type=tel inputmode=tel autocomplete=tel`, accept "(980) 555-0123", "980.555.0123", "+1 980 555 0123", normalise on blur, show the normalised form. Business name: `autocapitalize=words autocorrect=off`. Minutes: `inputmode=numeric`, 4-ch wide with the unit beside it. Email: `type=email autocapitalize=off autocorrect=off`.
**Rubric.** c1, b2, e2.

### C4. Fields sized to their values; owner text wraps
**Pattern.** A field is wide enough to show its whole typical value, and owner-entered text is never ellipsized.
**Evidence.** NN/g checklist item 5: "Is the field big enough so that most possible field values are visible?"; item 6: "Is the field visible in both orientations when the keyboard is displayed?" — https://www.nngroup.com/articles/mobile-input-checklist/ . Baymard: unseen input meant "Many subjects ultimately just decided to delete their original input and retype it" — https://baymard.com/blog/mobile-form-usability-label-position .
**Rule.** Text inputs full width at 390 px; business name in header wraps to two lines (`overflow-wrap:anywhere`, no `text-overflow:ellipsis`); textarea for a text grows to fit its content (no inner scroll), so the bubble preview and the field agree.
**Rubric.** c1, e2.

### C5. Show the default, make every entry revertible, no form-wide Reset
**Pattern.** Each rule shows its default as just-in-time instruction and has a per-item way back to it; there is no page-wide Reset button.
**Evidence.** NN/g defaults: a representative default shows users "how to complete a field"; users "rarely utilize fancy customization features" — https://www.nngroup.com/articles/the-power-of-defaults/ . NN/g Reset: "This button almost never helps users, but often hurts them"; acceptable when it "can offer a quick way home to safe grounds" (restoring defaults); for radios/menus "include an explicit option for the default choice" or "you do trap users" — https://www.nngroup.com/articles/reset-and-cancel-buttons/ . GOV.UK Button: "Avoid using multiple default buttons on a single page"; disabled buttons "have poor contrast and can confuse some users, so avoid them if possible" — https://design-system.service.gov.uk/components/button/ .
**Rule.** Every rule shows "Default: …" under its field and a per-rule "Reset to default" link (per-text "Reset to standard wording" on Messages). No global Reset. Quick-pick chips always include the default value; the chip whose value equals the field value is selected, custom selects none and shows "Custom". One primary Save per page, left-aligned on desktop, never disabled (clicking with nothing changed shows "Nothing to save yet").
**Rubric.** b2, d2, e2.

### C6. Check before you commit, change links, keep the owner's input
**Pattern.** Before a consequential save, the owner sees what will change, can jump back to change any item, and the transaction is explicitly incomplete until confirmed.
**Evidence.** GOV.UK Check answers: "make it clear the transaction will not be complete until a user confirms their information is correct"; "You should provide a 'Change' link next to each section"; the submit button names its action — https://design-system.service.gov.uk/patterns/check-answers/ . GOV.UK Error message: do not clear fields; keep passing and failing answers — https://design-system.service.gov.uk/components/error-message/ .
**Rule.** The sticky Save bar is a one-line check-answers: "2 texts changed · Save texts" with a disclosure listing each changed item as a jump link. Unsaved items carry an "Unsaved" badge until saved. On any validation failure the owner's text stays in place.
**Rubric.** d2, b2.

---

## D. Errors and validation (b2, d2)

### D1. Validate on leaving the field; re-validate per keystroke once in error; show success for hard fields only
**Pattern.** Inline validation fires on blur (or when the input reaches full length), an existing error clears the moment the input is fixed, and positive ticks appear only where format matters.
**Evidence.** Baymard: "the validity of each field input should be checked when the user leaves the field"; "should not be checked before the user has had a chance to fully type a correct input"; an existing error "must live update on a keystroke level, disappearing the moment users enter a valid input"; "Use 'positive inline validation' for all fields"; 31% of sites have none — https://baymard.com/blog/inline-form-validation . NN/g form errors: "Ideally, all validation should be inline"; "Don't Validate Fields Before Input is Complete"; avoid success messages on simple requirements; never tooltips for errors; a summary "shouldn't be used as the only form of error indication" — https://www.nngroup.com/articles/errors-forms-design-guidelines/ .
**Rule.** Phone and email: validate on blur or at 10 digits; tick on success; error clears per keystroke. Free-text (business name, wording): no tick, only the cost line. No tooltip errors anywhere.
**Rubric.** b2, c1.

### D2. Error summary at the top for multi-field pages, linked to each field, same wording inline
**Pattern.** When a save fails on more than one field, a summary before the h1 takes focus and links to each field; the inline message repeats it with a hidden "Error:" prefix and red border.
**Evidence.** GOV.UK Error summary: "Always show an error summary when there is a validation error, even if there's only one"; "You must link the errors in the error summary to the answer they relate to"; heading "There is a problem"; focus moves to it on load — https://design-system.service.gov.uk/components/error-summary/ . GOV.UK Error message: red text after hint, red border, hidden "Error:" prefix — https://design-system.service.gov.uk/components/error-message/ .
**Rule.** Schedule and Phone pages: on failed save render "There is a problem" summary before the h1 with one link per failing field, move focus to it, and keep the inline message identical. Messages page: a failing text gets the summary link that scrolls to that text's card (with scroll-padding, see F3).
**Rubric.** b2, c2.

---

## E. Feedback after save: inline status line, not a floating toast (b2, c1, d1)

### E1. A save confirmation is a response to the owner's own act, so it is passive, but a passive toast is easily missed and must never carry errors
**Pattern.** Confirm a save with a lightweight message that does not need dismissal, and never use a toast for an error or for anything the owner must act on.
**Evidence.** NN/g indicators/validations/notifications: a notification that "was the direct result of a user action" is "less important to require the user to take action to acknowledge it"; "Passive notifications can easily be missed"; a toast "would be a bad way to implement an error message, be it validation or otherwise" — https://www.nngroup.com/articles/indicators-validations-notifications/ . Carbon: toasts "cover content on the screen so they should always be easily dismissed"; default timeout five seconds; users must be able to reach the content elsewhere after it disappears — https://carbondesignsystem.com/components/notification/usage/ . NN/g toast-specific article: *unknown* (not found on nngroup.com).
**Rule.** Save success is an in-flow banner, not an overlay: it pushes content down, so it can never cover the heading or a field (the judges' c1 deduction). Errors never appear as toasts. Floating toasts are allowed only for events the owner did not trigger on this page (e.g. "Code expired") and then they are dismissible, ≤ 2 lines, bottom-anchored above the nav, and repeated in page state.
**Rubric.** c1, b2, d1.

### E2. Place the success banner immediately before the h1, same width, with a text heading, removed on navigation
**Pattern.** Success feedback sits between header and page title, in the content column, says "Saved" in text, and disappears when the owner leaves the page.
**Evidence.** GOV.UK Notification banner: "Position a notification banner immediately before the page h1"; "should be the same width as the page's other content"; "Use the green version ... to confirm that something they're expecting to happen has happened"; "Remove a green notification banner when the user moves to a new page"; use a heading such as "Success" so colour is not the only signal; "Use notification banners sparingly"; never with an error summary on the same page — https://design-system.service.gov.uk/components/notification-banner/ .
**Rule.** After save: banner before h1, text "Saved. Changed: Question 2, the location." (names the change, per Part 2), green left rule plus the word "Saved", in flow, persists until navigation. Never shown together with an error summary. Max one banner per page.
**Rubric.** b2, c1, e1.

### E3. role=status for success, role=alert for errors, container present before content
**Pattern.** The success line is a polite live region; errors use alert; neither moves focus except the error summary.
**Evidence.** WCAG 2.2 Understanding 4.1.3: success/results use "ARIA22: Using role=status to present status messages"; errors use "ARIA19: Using ARIA role=alert or Live Regions to Identify Errors"; example "Your form was successfully submitted." — https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html . MDN: role=status "has an implicit aria-live value of polite and an implicit aria-atomic value of true"; "Do not give focus to the status when its content updates" — https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/status_role . Requirement that the live-region container exist in the DOM before text is injected: *not stated on the MDN page* (common practice, unverified here).
**Rule.** Render an empty `<div role="status">` before the h1 on every page at load; fill it on save. Cost line changes ("Billed as 3 texts") update a `role=status` region too. Error summary gets focus; nothing else does.
**Rubric.** b2, c1 (and the accessibility-tester's lane).

---

## F. Phone navigation and sticky chrome (c2, c1)

### F1. Visible bottom tabs beat a hamburger when there are ≤ 5 destinations
**Pattern.** Top-level destinations stay visible in a labelled tab bar; hidden navigation costs discoverability and time.
**Evidence.** NN/g hamburger study: on mobile hidden navigation was used in 57% of cases vs 86% for combo; participants "15% slower" with hidden nav on mobile; content discoverability dropped by more than 20%; "If a site has four or fewer top-level links, show them as visible links" — https://www.nngroup.com/articles/hamburger-menus/ . NN/g mobile navigation patterns: "If your site has more than 5 options, it's hard to fit them in a tab or navigation bar"; labelled icons are "a recommended best practice in most cases"; hamburger makes options "least discoverable" — https://www.nngroup.com/articles/mobile-navigation-patterns/ . Android navigation bar: "Three to five destinations of equal importance" — https://developer.android.com/develop/ui/compose/components/navigation-bar . Apple HIG tab-bar page and Material 3 spec: *unknown* (JS-rendered; not readable here).
**Rule.** Bottom bar with exactly five labelled items: Home, Messages, Schedule, Calendar, Phone (Part 2's list). Account/Sign out behind the business name in the header, which is a labelled button ("Account"), since it is a sixth, rarely used destination. Desktop: same five plus Account in a `position:sticky` sidebar that never scrolls away.
**Rubric.** c2, b1, a1.

### F2. Sticky chrome budget: content-to-chrome ratio, not pixel folklore
**Pattern.** Every sticky element costs content on every page; keep text readable, then minimise height, and judge the result by content-to-chrome ratio.
**Evidence.** NN/g sticky headers: "Sticky headers inherently take up space on the screen that could be used for content"; "start with readable text sizes for your header elements and minimize the vertical height from there"; a 13:1 content-to-header ratio is called a reasonable tradeoff, 2:1 "miserly"; tap targets "a minimum of 1cm × 1 cm"; partially persistent (reappear on scroll-up) headers are the common mobile pattern, triggered "by the user scrolling up by a few pixels", slide 300–400 ms, opaque background — https://www.nngroup.com/articles/sticky-headers/ . Bar heights from Apple/Material primary pages: *unknown* here; Part 2 fixes the total at ≤ 170 px.
**Rule.** Budget on an 844 px viewport: header 56 + bottom nav 56 + jump chips 44 = 156 px (ratio ≈ 4.4:1). The Save bar (56) appears only when dirty and REPLACES the bottom nav while dirty (Save · Discard), so sticky chrome never exceeds 156 px and a nav tap cannot silently drop changes. Header may be partially persistent (hide on scroll-down, return on a few px of scroll-up); chips and nav are fully sticky. Judges saw B at ≈ 1/5 of the screen (≈ 169 px) and docked it; C stays at ≤ 156.
**Rubric.** c2, c1.

### F3. Jump links at the top of long content, labelled, matching the destination heading, never covered
**Pattern.** On a page of 9+ screens, in-page links act as a table of contents; they must be distinguishable from navigation, mirror the heading text, show current location, and the target heading must land visibly below any sticky bar.
**Evidence.** NN/g in-page links: "the benefit of using jump links increases as screen size decreases"; on mobile links "should always appear at the top of content"; "In-page links need to be differentiated from other links"; match link text to the destination heading to "reassure users that they have been moved to the appropriate content"; sticky elements must not cover the heading; sticky tables of contents "should show the user's current location"; do not put them in the navigation area — https://www.nngroup.com/articles/in-page-links/ . MDN scroll-padding-top: excludes "regions of the scrollport that are obscured by other content (such as fixed-positioned toolbars or sidebars)" — https://developer.mozilla.org/en-US/docs/Web/CSS/scroll-padding-top .
**Rule.** Messages: a chip row directly under the h1, label "On this page", sticky with the header; max 5 chips (Missed call, Questions, Booking, No reply, Steps back) whose text equals the section h2s; active chip tracks scroll position; `html { scroll-padding-top: <header+chips> px; scroll-padding-bottom: <save bar> px }`; chips are not in the bottom nav. The "Required by phone companies" section is reached by scrolling, not a chip.
**Rubric.** c2, a1.

### F4. Collapse rarely changed content, keep structure visible, don't trap Back
**Pattern.** Secondary content collapses so the page's structure fits a glance; expansion must not read as a new page.
**Evidence.** NN/g mobile accordions: accordions "conserve space on mobile"; an expanded-by-default first accordion "prevented users from getting a quick glance (without scrolling) at the structure of the page"; users who think expansion navigated "press Back"; keep the page from scrolling on expand or make Back collapse it — https://www.nngroup.com/articles/mobile-accordions/ .
**Rule.** START/HELP/STOP under a native `<details>` ("Required by phone companies. Most businesses never change these.") collapsed by default; expanding does not scroll or push history. Carrier codes on Phone: one `<details>` per carrier, only the picked carrier open.
**Rubric.** c2, a1.

### F5. Where a fixed Save bar goes when the keyboard is up
**Pattern.** Mobile browsers now shrink only the visual viewport when the keyboard opens, so a fixed bottom bar is hidden behind the keyboard while typing; the field, not the bar, must stay visible.
**Evidence.** Chrome 108+: "Chrome on Android will no longer resize the Layout Viewport, and instead resize only the Visual Viewport", matching Safari iOS; "Elements that use position: fixed remain in place and can be obscured by the OSK"; `interactive-widget=resizes-content` restores layout resizing (Chromium only, not iOS) — https://developer.chrome.com/blog/viewport-resize-behavior . MDN viewport meta: default `resizes-visual`; `resizes-content` lets "the page's layout adapt to the presence of the virtual keyboard" — https://developer.mozilla.org/en-US/docs/Web/HTML/Guides/Viewport_meta_element . NN/g checklist item 6: "Is the field visible in both orientations when the keyboard is displayed?" — https://www.nngroup.com/articles/mobile-input-checklist/ .
**Rule.** Accept that the Save bar is behind the keyboard while typing (Save is not needed mid-edit); do not set `resizes-content` (on Android it would stack bar + keyboard and halve the field area). On focus, `scrollIntoView({block:'center'})` the field; `scroll-padding-bottom` = Save bar height so the focused field is never under the bar once the keyboard closes. Edit-wording panels put the textarea in the top half of the screen so the bubble preview stays visible above the keyboard.
**Rubric.** c1, c2.

### F6. Tap targets: physical size first
**Pattern.** Targets are at least 1 cm square with spacing, because small targets cause slips.
**Evidence.** NN/g touch targets: "its minimum size should be 1cm × 1cm (0.4in x 0.4in)"; about 2 mm spacing "the often-recommended minimum"; "the fat fingers are not the real culprit; the blame should lie on the tiny targets" — https://www.nngroup.com/articles/touch-target-size/ . WCAG 2.2 target-size numbers: accessibility-tester's lane.
**Rule.** Chips, Reset links, nav items, Change links: ≥ 44 × 44 CSS px with ≥ 8 px gaps (Part 2's number, consistent with NN/g's 1 cm at typical phone density); Reset links get padding, not just underlined text.
**Rubric.** c1.

---

## G. SMS preview editor and cost line (d2, a2, e2)

### G1. Segment arithmetic and the characters that double the bill
**Pattern.** A text is billed per segment: 160 chars (153 when split) in GSM-7, 70 (67) once any Unicode character is present; one such character re-encodes the whole message.
**Evidence.** Twilio glossary: GSM-7 160 single / 153 per segment; UCS-2 70 / 67; "This reduces the single message character limit from 160 to 70" for a curly quote; Smart Encoding converts curly quotes to straight — https://www.twilio.com/docs/glossary/what-sms-character-limit . Sent docs: curly quotes, en and em dashes and the ellipsis trigger Unicode; "Unicode applies to the entire body, not just the non-GSM character"; GSM extension chars `\ | ^ € { } [ ] ~` each "counts as two characters" ("Balance: {amount}" "actually costs 19") — https://docs.sent.dm/start/concepts/sms-encoding-and-length . Courier counter: "Watch the segment count, since carriers bill per segment" — https://www.courier.com/tools/sms-segment-counter . Postscript/Attentive public docs on this: *unknown* (not located). Internal evidence: the 2026-10-19 intro SMS billed as 2 segments because of the "[SignalWire Free Trial]" prefix (CLAUDE.md STATE).
**Rule.** The cost line is computed on the rendered text (inserts substituted with the longest realistic values: the real business name, a 12-char first name, the real link length, and the network-notice prefix while registration is incomplete), using GSM-7/UCS-2 rules with extension chars counted twice. Output: "1 text" or amber "Billed as N texts — the '—' symbol makes texts shorter. Use '-' instead." naming the first culprit character and offering a one-tap replacement for — – “ ” ‘ ’ … . Braces never reach the owner (chips), so `{`/`}` double-cost cannot be typed by accident; if an owner pastes one, name it too.
**Rubric.** d2, a2, e2.

### G2. The preview is the message
**Pattern.** What the owner sees in the bubble is byte-for-byte what will be sent, produced by the real renderer, with sample data labelled.
**Evidence.** Judges' d1 deductions (hand-written sample hand-off; "Booked" chip while no calendar). NN/g system status: communicate "what the system's state is" honestly — https://www.nngroup.com/articles/visibility-system-status/ . GOV.UK Check answers: the user confirms the actual values — https://design-system.service.gov.uk/patterns/check-answers/ .
**Rule.** Bubble text = `render(template, sample_context)` from the policy module; label "Example conversation · nothing is sent · names made up"; link shown as "Add to Google Calendar ›" with the configured public base URL on tap; the count in G1 runs on this same rendered string.
**Rubric.** d1, d2.

---

## Unknowns (not found; do not cite as fact)
- NN/g article specifically on toast notifications: not found on nngroup.com (404 at the expected path; search returned only vendor pages). E1 relies on NN/g's indicators/validations/notifications article and Carbon.
- Baymard "mobile form field design", "mobile touch keyboard types", "form field usability": pages returned only a paywall headline; Baymard evidence here is limited to the three blog posts that rendered (label position, touch keyboards 2015 benchmark, inline validation, 8 input-field recommendations).
- Apple HIG tab-bar height and Material 3 navigation-bar height (49 pt / 80 dp are commonly cited): primary pages are JS-rendered and unreadable here. The 56 px figures in F2 are design choices within Part 2's 170 px cap, not platform citations.
- GOV.UK reading-age target: the current guidance gives a literacy statistic, not a reading age.
- Whether a `role=status` container must pre-exist in the DOM: not stated on MDN's role page (treated as practice, not rule).
- Postscript/Attentive public documentation on segment warnings: not located; Twilio glossary + Sent docs + Courier used instead.
- Baymard field-width-matches-expected-input rule: not in any page that rendered; covered by NN/g checklist item 5 instead.

## Rules we adopt (ranked by rubric impact)
1. Save confirmation is an in-flow `role=status` banner immediately before the h1, naming the change; never an overlay, never over a heading or field. (c1, b2, d1) — E1–E3
2. Sticky chrome ≤ 156 px: header 56 + nav 56 + chips 44; the Save bar replaces the nav while dirty; `scroll-padding-top/bottom` equal the sticky heights. (c2, c1) — F2, F3, F5
3. Five labelled bottom tabs (Home, Messages, Schedule, Calendar, Phone); Account behind the header name; desktop sidebar `position:sticky`. (c2, b1, a1) — F1
4. Home h1 is computed state ("Working…" / "Not working yet: N steps left"); cards use exactly Done / Needs you / Waiting on phone companies with GOV.UK tag styling and one button max. (a1, d1) — A1–A3
5. Jump chips under the Messages title, max 5, text equals the section headings, active chip tracks scroll, not inside the nav. (c2, a1) — F3
6. Every rule shows "Default: …" and a per-item Reset; no page-wide Reset; chip state derives from the field value, custom shows "Custom". (b2, d2, e2) — C5
7. Cost line computed on the rendered text incl. prefix and inserts; names the culprit character and offers one-tap replacement. (d2, a2, e2) — G1
8. Errors: validate on blur, clear per keystroke, "Enter…/must be…" wording, GOV.UK banned words, error summary before h1 linked to fields; never toasts or tooltips. (b2, a2) — B2, D1, D2
9. Labels above, hint lines outside the field, no placeholder labels; `tel`/`numeric`/`email` keyboards, autocorrect off on names and emails, any phone format accepted. (c1, b2) — C2, C3
10. Every string ≤ 25 words, short words, "texting approval" explained once; banned-word render test. (a2) — B1
11. No dead ends: every not-done card ends with a next step and a real contact action; consequential changes are stated before save (rename offer, quiet-hours exceptions, mid-conversation effect). (b2, d2) — A4, A6, C6
12. Secondary content (START/HELP/STOP, carrier codes) in collapsed `<details>` that neither scrolls nor pushes history; owner text wraps, never ellipsizes; all targets ≥ 44 px. (c2, c1, e2) — F4, C4, F6
