# Candidate C — verification fix list (from ui-ux-tester, accessibility-tester, anti-ui-slop-reviewer, capture/smoke)

Screenshots referenced live under the scratchpad: uxt/, a11y/shots/, slop-build/, final-c/.

## Product calls already made by the session lead (implement as written)
- P1 Default customer texts on C avoid the possessive and the em dash (both fix real defects: "Arborists's", and 2–3x billing):
  intro → "Hey, sorry we missed your call. This is the scheduling assistant for {business_name}. What were you calling about?"
  followup_1 → "Hi again from the scheduling assistant for {business_name}. Still happy to get you on the calendar. What job do you need done?"
  followup_2 → "Last check-in from the scheduling assistant for {business_name}. Reply with the job you need and we'll set a time."
  booking_confirmation → "Booked: {service} on {when} at {location}. This is the scheduling assistant for {business_name}. {invite_line} {calendar_links}"
  opt_in → "You're subscribed to scheduling texts from {business_name}. Msg & data rates may apply. Reply HELP for help or STOP to opt out."
  help → "This is the scheduling assistant for {business_name}. Reply with the job type, location, and a time that works. Anything we can't handle by text, the owner follows up on.{contact_line} Msg & data rates may apply."
  prompt_service → drop "e.g.": "What's the job you need done? For example: tree removal, trimming or stump grinding."
  Keep test_no_live_human_copy and every validator rule green; update tests that pin the old defaults. Record in the deck.
- P2 Home headline counts only setup items that are NOT harness-flagged examples; the headline carries no Example tag. Example cards keep their own tag.
- P3 Calendar with no web client: state word "Waiting on FluxWorks" (clock glyph), not counted in "steps left"; body "FluxWorks connects your calendar for you." plus "Text FluxWorks support" (sms:) when TEXT_BACK_SUPPORT_CONTACT is set. The preview harness sets TEXT_BACK_SUPPORT_CONTACT to +17045550199 (fictional 555-01xx range).
- P4 Stepped-back callers on Home show the caller's number with "Call" (tel:) and "Text" (sms:) links, 44 px each. Other rows stay as they are.
- P5 Sample conversation values match the approved mockup: "Tree trimming", "412 Maple St, Charlotte", "Dana Whitfield", "Thursday at 10".

## Major
- M1 Every portal POST that succeeds answers 303 to its GET page with the notice carried as a one-time flash (signed cookie or a short-lived row keyed to the session; CSRF-safe; never reflect arbitrary text — the flash holds a notice id + safe params, rendered server-side). Back and reload must not re-post. Rejected saves still render in place (no redirect) so typed text is kept.
- M2 Quiet hours with equal start and end: refuse with an inline error "Start and end can't be the same time. To turn quiet hours off, use the switch." Turning quiet hours Off then On restores the last custom times.
- M3 Forwarding code rows: below 480 px the code sits on its own line and Copy below it (or a 44x44 icon button), ≥ 12 px gap, the full code always visible at 320 px. Copy also works without navigator.clipboard (fallback: select the code text + document.execCommand('copy')); show Copy on plain http too.
- M7 Business name field: a live line under it when the name contains a symbol that makes texts bill as 70-character texts (reuse bill_info logic): "This name has a [symbol], which makes each text hold only 70 characters." Also refuse "{", "}", "<", ">" in the business name with a plain error, and wrap unbroken long names (overflow-wrap: anywhere) so the page never scrolls sideways.
- M8 Without JavaScript: a Save button at the end of every Messages step section (same form); "Reset and save"/"Replace … and save" stay labelled as saves.
- A11y F1 Desktop Messages at 150–200 % text: breakpoints in em; the list column has a minimum width (e.g. grid-template-columns: minmax(22rem,1fr) minmax(0,26rem)); below that the rail drops under the list. The rail never covers a field.
- A11y F2 Phone at 150–200 % text: the header wraps (business name never broken mid-word), nav labels cap at a size that fits or wrap to two lines, .qset/.msg__foot/.msg__receipt wrap, Reset never overlaps "Edit wording", the unsaved header's count never overlaps Discard.
- Bug (capture agent): after a rejected Phone save, changed_labels compares the raw posted business line with the stored E.164; normalise phone values before comparing. Regression test: a rejected save touching only the mobile lists exactly one change.

## Minor and finish
- m1 Insert chip adds a space before/after when needed so "[Business name]What" can't happen.
- m2 Replace — with - inserts " - " when the dash had no spaces around it.
- m3 Discard (JS and no-JS) scrolls the notice into view (or keeps the user where they are and shows the notice in a sticky-visible place).
- m4 Account remember save notice names the change: "Saved. This device now stays signed in for 30 days." / "...signs out after 12 hours."
- m5 Plain Sign out lands on login with "You signed out."
- m6 Sign-out-everywhere confirm scrolls into view with ≥ 72 px clear above the bottom nav; the confirm button reads "Yes, sign out everywhere".
- m7 After the owner mobile changes, Account's "Signed in as" shows the new number (read the current owner mobile), and the notice says other devices stay signed in.
- m8/m9 Rate-limit and verify copy allow for a typo: "If you don't get a text within a minute, check the number and send a new code." Keep the typed number on the rate-limit page; link back to Enter code.
- m10 Schedule notice "applies" wording per rule must match the rule notes; drop "including customers mid-conversation" from rules where existing bookings stay as they are; no self-contradiction for reminders.
- m11 Schedule Reset stays local until Save (JS), like Messages; no-JS label "Reset and save".
- m13 Custom length errors are the portal's inline error, not the browser bubble (novalidate on the form; server validation already exists).
- m14 After the one-tap hours (no JS too) land at the hours rule (#working-hours).
- m15 Changing the business number explains the reset: "Checks start again because the business number changed."
- m16 Check 5 with carrier Other reads "Ask your carrier how to turn off forwarding, and write it down."
- m17 "Leave them" gives a notice "Kept the texts as they are."
- m18 Rename offer buttons follow the count: "Update it" / "Leave it" for one text.
- m20 HELP number: accept only 10-digit US numbers (plus optional +1), error otherwise.
- m21 Ticked checkboxes show a check glyph (not a solid square).
- m22 Home "Finish forwarding" links to /client/phone#checks.
- m23 Jump label tracks the step on screen accurately (adjust rootMargin; update on scroll end too).
- m25 With the on-screen keyboard open (visual viewport height < 500 px), hide the bottom nav (visualViewport resize) so fields aren't crowded.
- m26 Skip link first, then header, then main content; bottom nav after main in DOM order (keep visual position with CSS).
- m27 /client/* 404 renders a plain portal page "That page doesn't exist." with a link Home (no JSON).
- m28 Expired-form page keeps the typed wording on Messages where possible (re-render with the posted values and a fresh token, notice "This page was open a long time. Check your changes and press Save again.").
- m29 A question switch counts as "1 setting changed"; notice "Saved. You turned on “Email address”."
- m30 Jargon: count label "Assistant stepped back" → "Asked for a person"; "[Contact number sentence]" chip label → "[Your HELP number]"; remove "FluxWorks operator" anywhere.
- m31 "Your business number never changes" → "This is the number customers call. TextBack never changes it."
- m32 Booking confirmation billing warning offers the honest note (links make it long) and no fix button.
- m34 Mobile change: notice "Code sent to (xxx) xxx-xxxx. Your mobile changes after you enter it." (not "Saved").
- m36 No-JS: a tapped length chip wins over an untouched number box; if both changed, the error says to pick one.
- a11y F3 Announce cost changes only when the number of texts changes (announce(..., {channel:'count', debounce:1000})).
- a11y F4 OTP input: a 2 px focus outline on the active cell / whole field.
- a11y F5 Jump links move focus to the step's h2 (id on the h2, tabindex=-1).
- a11y F6 After "Check free times", land on #availability and focus its heading.
- a11y F7 The notice's Dismiss button sits outside the live text node.
- a11y F8 Error summary links: display:block, no negative margins.
- a11y F9 Insert chip names "Insert Business name"; "Edit wording: …" without the stray space; receipt separator "STOP line added for you · 1 text"; jump menu closes on Escape; page titles "<Page> · <business name> · TextBack"; forced-colors borders on .savebar and .msg.
- Finish: free-time slots don't overlap (step = appointment length, or say "Starts at 1:30, 2:00, 2:30 PM" with the length once); time ranges never break (nw); free-time rows not styled as buttons; desktop rail last item clear of the fade; confirm-new-mobile spacing between code boxes and button and equal button widths; device rows use a device icon (not a phone) and "Remembered devices" lists only remembered sessions under that heading (others under "Other signed-in devices"); Reset hidden when a rule is at its default; "Example" appears once at the top of the rail (caption only); the text count appears once when the editor is open; "Leave them" aligned; "When the calendar failed" arrow placement like the other fallback cards; the steps-back card title "Hand-off text" (section heading stays "When the assistant steps back"); Reset aligned to the right content edge; Messages intro shortened to two short sentences and the network-notice line to one; "Remember this device" default and the deck agree.
