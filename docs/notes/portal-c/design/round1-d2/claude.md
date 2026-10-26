## 1. Judge identity, evidence opened, confidence

- **Judge:** Claude Opus 5.5 (`claude-opus-5-5`).
- **Images I opened and looked at:**
  - **X, 20 images:** `01-sign-in-desktop-01`, `01-sign-in-phone-01`, `02-enter-code-phone-01`, `03-messages-desktop-01/05/07/09`, `03-messages-phone-01/06/10/12`, `04-business-desktop-01`, `04-business-phone-02`, `05-calendar-desktop-01`, `05-calendar-phone-01`, `save-01-messages-desktop`, `save-01-messages-phone`, `save-02-business-phone`, `save-03-owner-mobile-change-desktop`, `save-04-keep-mobile-desktop`.
  - **Y, 39 images:** `01-sign-in-phone-01`, `03-home-desktop-01`, `03-home-phone-01/02`, `04-messages-desktop-01/04`, `04-messages-phone-01/08/10`, `05-schedule-desktop-01/02/03/04`, `05-schedule-phone-02`, `06-calendar-desktop-01`, `06-calendar-phone-01`, `07-phone-desktop-01/02/03`, `07-phone-phone-03/04`, `08-account-phone-01`, plus 17 `state-*` files: sign-in error, enter-code error, account menu, sign-out confirm, messages edit-open, unsaved bar, saved toast, example booked, schedule hours grid, unsaved bar, any-time warning, saved toast, calendar connected, calendar picked toast, phone confirm-mobile, invalid mobile, rename offer.
  - **Text files:** both `INDEX.md` files; X `03-messages-desktop.txt`, `04-business-desktop.txt`, `05-calendar-desktop.txt`; Y `03-home`, `04-messages`, `05-schedule`, `06-calendar`, `07-phone`, `08-account` desktop `.txt`.
- **Confidence:** high on the winner, medium-high on individual scores.
- **Limitations:**
  - Y's pack has many error and state screens; X's has only save screens. So I could not see X's error states, and X's b2 score rests on less evidence.
  - I did not open every scroll position: 9 X images and 10 Y numbered screenshots were skipped where the page text covered them.
  - The "(desktop 043715)" suffixes on X's save screens come from the private test copy, so I did not count them as defects.

## 2. Scores

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 4 | 3 | 2 | 3 | 4 | 3 | 3 | 4 | 4 | 2 | 64 |
| Y | 5 | 4 | 5 | 5 | 4 | 4 | 4 | 5 | 4 | 3 | 86 |

## 3. Observations

### Portal X
1. **Missing pages (b1).** The nav has only Messages, Business and Calendar (`03-messages-desktop-01`, sidebar; `03-messages-phone-01`, bottom nav). There is nowhere to set:
   - appointment length, working hours, quiet hours or reminder timing;
   - call forwarding or the business line;
   - and there is no "is it working" status page.
   
   Reminders only say "Sent after the first follow-up delay" (`03-messages-desktop.txt`), and the owner can't see or change that delay.
2. **Calendar page is a dead end.** `05-calendar-desktop-01` shows a "Test mode" badge and "No calendar connected", then "Connecting a calendar from this page is still being set up by FluxWorks." It is honest, but there is no button and no next step.
3. **Server addresses in a customer text.** The Booking confirmation bubble in `03-messages-desktop-05` and `03-messages-phone-06` contains raw links like `http://hermes-cloud.tailefb1a4.ts.net:8765/a/k7q2-ref/g`. On a phone (`03-messages-phone-12`) these wrap into a wall of text. An owner would think this is what customers receive.
4. **Good change and save safety.**
   - Each card has "STOP line added for you" and a red "Billed as 3 texts… the '—' symbol limits each text to 70 characters" warning (`03-messages-desktop-07`).
   - The save toast names what changed: "Saved. Changed: Question 2: the location." (`save-01-messages-desktop`).
   - Changing the owner mobile goes to a two-step "Confirm your new mobile" screen with a "Keep my current mobile" escape (`save-03-owner-mobile-change-desktop`), confirmed by "Kept your current mobile." (`save-04-keep-mobile-desktop`).
5. **Save button is hard to reach on phone.** On a page about 12 screens long, "No unsaved changes / Save changes" sits inline near the bottom (`03-messages-phone-10`). It is not sticky, and the jump chips at the top (`03-messages-phone-01`) scroll away.
6. **Preview contradicts the Calendar page.** The sample booking is labelled "Booked · on your calendar" (`03-messages-desktop-05`), but `05-calendar-desktop-01` says no calendar is connected.

### Portal Y
1. **Home gives a status in five seconds.** `03-home-desktop-01` opens with "Not working yet: 2 steps left." Calendar and Call forwarding each show "Needs you" with a direct button ("Connect calendar", "Finish forwarding"), and Texting approval says "Nothing for you to do." Every count and caller row is tagged "EXAMPLE NUMBERS" or "EXAMPLE" (`03-home-phone-02`).
2. **Best change-and-save handling of the two.**
   - The phone unsaved bar lists what changed, with Discard and Save, and the card shows a "Was:" line with the old wording and an "Unsaved" tag (`state-messages-unsaved-bar-phone`).
   - The schedule save banner states the consequence: "Applies now, including customers mid-conversation; reminders already scheduled keep their time." (`state-schedule-saved-toast-phone`).
   - Every rule shows its default and a Reset (`state-schedule-unsaved-bar-desktop`).
3. **Strong safety cues.**
   - "Any day, any time" triggers "Customers can be offered times like 1 AM" with a one-tap "Use Mon–Fri, 8 AM–5 PM" fix (`state-schedule-any-time-warning-phone`).
   - Call forwarding warns "Only forward busy and unanswered calls" before showing carrier codes, with Copy and a turn-off code (`07-phone-desktop-02`).
   - "Sign out of every device?" asks for confirmation (`state-account-sign-out-phone`).
4. **Forwarding checklist uses example data as real progress.** In `07-phone-desktop-03`, checks 1, 2 and 4 show a green "Done", each tagged EXAMPLE. The note under them says "Checks 1, 2 and 4 tick themselves from real calls TextBack recorded." Home then reports "3 of 5 checks done" as real progress (`03-home-desktop-01`).
5. **Unclear who gets the lead.** Both hand-off texts say "These go to the FluxWorks operator." (`04-messages-phone-08`). An owner can't tell whether they hear about the customer or a third party does.
6. **Calendar connect is explained up front.** `06-calendar-phone-01` lists "What Google will ask" in four numbered steps, and the test times are headed "TEST CALENDAR, NOT YOURS" (`06-calendar-desktop-01`). The connected state confirms the choice: "Saved. The assistant now books on Oak & Pine jobs." (`state-calendar-picked-toast-desktop`).

## 4. Looks broken

**Portal X**
- Raw server addresses in the booking confirmation: `03-messages-desktop-05`, `03-messages-phone-06`, `03-messages-phone-12`.
- "Booked · on your calendar" contradicts "No calendar connected": `03-messages-desktop-05` vs `05-calendar-desktop-01`.
- The "In the first text" preview still says "Oak & Pine Tree Care" after the name field was changed and saved, with no note explaining why: `save-02-business-phone`, `save-04-keep-mobile-desktop`.
- Header business name truncates to "Oak & Pine Tree Care (…" on phone: `save-01-messages-phone`, `save-02-business-phone`.
- Calendar page has no action at all: `05-calendar-desktop-01`.
- The jump-chip row is cut off at the right edge ("No reply" clipped) with no hint that it scrolls: `03-messages-phone-01`.
- The sample booking is dated "Thursday, Oct 22", which is before the Mon, Oct 26 these captures appear to be from: `03-messages-desktop-05` (minor).

**Portal Y**
- The unsaved bar text is clipped mid-word ("…missed call, Questic"): `state-messages-unsaved-bar-phone`.
- After renaming to "Oak & Pine Tree Service", the header still says "Oak & Pine Tree Care". Two separate "Saved" messages stack on screen, and curly and straight quotes are mixed in the copy: `state-phone-rename-offer-desktop`.
- The "Customers can be offered times like 1 AM" warning still shows while "Set hours" is selected: `05-schedule-desktop-02`.
- Example forwarding checks show as "Done" and feed the real setup status: `07-phone-desktop-03`, `03-home-desktop-01`.
- The bottom-nav active-tab bar overlaps the content above it: "Edit wording" is hidden in `04-messages-phone-01`, and a green bar crosses "Missed calls" in `03-home-phone-01`.
- Awkward wrap "(704) 555-/0100" in the HELP-number help text: `07-phone-desktop-02`.
- The owner mobile is written "980 555 0123" while the other numbers use "(704) 555-0123": `07-phone-desktop-01`.

## 5. Three ideas from X (ranked lower) that Y should adopt

1. **Show the customer message that triggers each fallback text.** X puts a customer bubble above each fallback reply, e.g. "A big limb just came down on the power line by our house" above the Safety hand-off (`03-messages-desktop-09`). Y's fallback cards show only the reply (`04-messages-desktop-04`, "When the time is already taken").
2. **"Texts stop here" end marker.** X places a pill after the Last reminder so the owner sees the sequence really ends (`03-messages-desktop-07`).
3. **"Back to editing" link at the end of the phone preview.** It returns the owner to the editor after a long scroll (`03-messages-phone-12`).

## 6. Recommendation

Portal Y wins clearly. It is the only one with a place for all six owner jobs (Home status, Schedule, Calendar connect, Phone numbers with call forwarding, Account sign-out). It also has the strongest feedback when saving and the clearest consequence warnings. X is tidy, but it lacks scheduling rules, call forwarding and a status page, and its customer-text preview shows raw server addresses. Before an owner sees Y, it must fix:
- forwarding checks marked "Done" from example data, which then appear as real progress on Home;
- the clipped unsaved-changes bar;
- the header not updating after a rename;
- the 1 AM warning showing while Set hours is selected;
- "These go to the FluxWorks operator", which should say plainly who gets the lead.

VERDICT: WINNER Y
