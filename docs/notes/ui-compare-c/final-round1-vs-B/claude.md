I'm Claude Opus 5.5 (`claude-opus-5-5`), and I judge Portal Y the clear winner, 88 to 56.

**What I opened:**
- **Portal X:** 25 screenshots, including all 8 pages on desktop and phone and 5 of the 9 save screens. Also `INDEX.md` and 6 page-text files (home, messages, scheduling, calendar, phone, account).
- **Portal Y:** 34 screenshots, including all 8 pages, 16 of the 48 state and save screens, and both sign-in error screens. Also 6 page-text files.

**Confidence:** high on the ranking, medium on individual criteria.

**Limitations:**
- Y's pack has about 48 state and save screens; X's has 9 save screens and no state screens. So I could not see X's error states, the forwarding codes after choosing a carrier, or the phone-number confirm step. I scored X only on what is visible, which may undercount X under b2 and d2.
- `Y/state-schedule-set-hours-desktop.png` shows the top of the page, not the set-hours state. That is a fault in the evidence, not in the portal.
- I did not open every scroll position of every long page. I relied on the page-text files for the rest.

## Score table

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 3 | 2 | 4 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 56 |
| Y | 4 | 4 | 5 | 5 | 4 | 4 | 4 | 5 | 5 | 4 | 88 |

## Observations

### Portal X
1. **Clear setup cards on Home.** In `X/03-home-desktop-01.png` the three cards across the top ("NOT SET UP · No calendar yet · Set up", "NEEDS ATTENTION · Forwarding 1 of 5 · Finish setup") each have a green button. An owner knows within seconds what is missing and where to tap. This is X's best orientation moment.
2. **Vendor jargon and code-like tokens throughout.**
   - The third Home card says "CAMPAIGN IN REVIEW … Texts carry a '[SignalWire Free Trial]' tag".
   - In `X/04-messages-desktop-01.png` the first text area shows `{business_name}`, with a chip "Business name {business_name}".
   - Under it: "Uses a special character (—), so each text holds 70 characters."
   - The sidebar footer says "text_back · missed-call recovery".
   - In `X/04-messages-desktop-06.png` the Booking confirmation has 12 chips, including `{event_id}`, `{links_page}` and `{invite_line}`.

   A tree-care owner would not understand these words.
3. **Unlabelled demo data that contradicts itself.** In `X/03-home-desktop-01.png` "This week · Since Monday, Oct 26" shows 0 / 0 / 0 / 0. Directly below, "Last conversations" lists Marcus Lee, Dana Whitfield and two numbers with "Booked", "Handed off" and "In progress", and none of them carries an example tag. The owner can't tell what is real.
4. **Calendar page is a dead end.** In `X/06-calendar-desktop-01.png` the "Test calendar" card says "Connecting a calendar from this page isn't turned on yet." The Outlook and iCloud cards say "Ask text_back to connect it." There is no button, link or contact.
5. **Free times in the middle of the night, with no warning.** After saving, `X/save-03-availability-desktop.png` lists "Next free times" as "Mon, Oct 26 · 1:00–2:30 AM", "1:30–3:00 AM" and "2:00–3:30 AM". These are overlapping night slots for a tree-care business, and the page doesn't suggest setting working hours.
6. **Real strengths on Scheduling and Phone:**
   - In `X/05-scheduling-desktop-02.png` every rule shows "Default: … Reset" inline, and there is an explicit "No quiet hours" switch.
   - In `X/07-phone-desktop-02.png` there are "Verify" buttons beside each number, the warning "Only forward busy and unanswered calls", and the honest note "Steps 1, 2 and 4 are ticked from real calls recorded by the assistant".
   - In `X/04-messages-desktop-01.png` the opt-out line is locked ("STOP stays in. Carriers require the word STOP.").
7. **Phone editing is cramped.** In `X/04-messages-phone-01.png` three sticky bars stack at the bottom: "Save messages", "Preview ^" and the five-tab nav. Together they take about a quarter of the screen, and the Messages page runs 12 screens with no jump links.

### Portal Y
1. **Clear status at the top of Home.** `Y/03-home-desktop-01.png` opens with "Not working yet: 1 step left." The setup list shows who owns each item ("Calendar · Waiting on FluxWorks", "Call forwarding · Needs you", "Texting approval · Waiting on phone companies … Nothing for you to do").
2. **Demo data is labelled everywhere.**
   - Home has an "EXAMPLE" tag on each caller and on the forwarding progress, and "EXAMPLE NUMBERS" on the weekly counts. Its note says "This preview mixes example calls with real settings."
   - The counts (3 / 3 / 1 / 1) match the caller list below them (`Y/03-home-desktop-02.png`).
   - The calendar card is titled "Test calendar, not yours" (`Y/06-calendar-desktop-01.png`).
3. **Strong edit feedback.**
   - In `Y/state-messages-unsaved-desktop.png` an edited text shows an "Unsaved" tag and a "Was: What's the address for the job?" line. The example phone updates live, and a sticky bar lists "2 texts changed: First text after a missed call, Question 2: the address" with Discard and Save.
   - After saving, `Y/save-01-messages-wording-phone.png` confirms: 'Saved. You changed "Question 2: the address".'
4. **Consequences stated before saving.** `Y/05-schedule-desktop-01.png` says "Applies right away, including customers mid-conversation." under Appointment length. The working-hours section (`Y/05-schedule-desktop-02.png`) says "Bookings already made stay as they are."
5. **Number changes are verified and nothing is lost by mistake.**
   - `Y/state-phone-confirm-new-mobile-phone.png` shows a two-step "Confirm your new mobile" screen: "until then codes still go to your current mobile", plus a "Keep my current mobile" button.
   - `Y/state-phone-invalid-mobile-field-phone.png` shows the inline error "Enter your mobile as 10 digits, area code first."
   - `Y/save-03-business-name-rename-offer-desktop.png` offers "1 text still says 'Oak & Pine Tree Care'. Update it to the new name?" with "Update it" and "Leave it".
6. **Works well on a phone.**
   - `Y/04-messages-phone-05.png` has a sticky "Jump to: Booking" selector, and the save bar appears only when something has changed (`Y/state-messages-unsaved-top-phone.png`).
   - Forwarding codes come with Copy buttons (`Y/07-phone-desktop-03.png`).
   - Sign out everywhere asks first: "Sign out of every device? … Stay signed in / Yes, sign out everywhere" (`Y/state-account-signout-everywhere-desktop.png`).
7. **Friction:** Account is not in the phone tab bar; it is reached through the business-name menu (`Y/state-home-account-menu-phone.png`). The Messages page is still about 12 phone screens long.

## Looks broken

**Portal X**
- `X/03-home-desktop-01.png`:
  - The weekly counts are all 0 while four conversations are listed below them.
  - The Booked row reads "Thursday, Oct 23", but Oct 23, 2026 is a Friday, and it is in the past.
  - The rows use bare weekdays ("Wednesday 2:40 PM") that, in a week starting Monday Oct 26, can only mean last week.
- `X/03-home-desktop-01.png` (and every desktop page): the sidebar business name is cut off as "Oak & Pine Tre…".
- `X/04-messages-desktop.txt`: the preview's booking confirmation contains raw dev links such as `http://100.124.192.46:8003/a/1-000000000000/g`. This comes from the page-text file; I did not open the preview screenshot that shows it.
- `X/04-messages-desktop-10.png`: a "Business name {business_name}" chip sits under texts that never use it ("Safety hand-off", "When the owner needs to step in"). The rule text "Must promise a follow up (those two words)" reads like a developer note.
- `X/save-03-availability-desktop.png`: overlapping night slots (1:00, 1:30 and 2:00 AM starts).
- `X/06-calendar-desktop-01.png`: dead end ("isn't turned on yet" and "Ask text_back" with no action).
- `X/07-phone-desktop-02.png`: the "Number shown in HELP replies" placeholder shows (704) 555-0123, the business number. But the hint says leaving it blank shows the texting number, (704) 555-0100. Also, the empty "Your business number" field shows a grey placeholder that looks like a saved value.
- `X/04-messages-phone-01.png`: three stacked sticky bars hide part of the content.

**Portal Y**
- `Y/03-home-desktop-01.png`: "Not working yet: 1 step left" is shown while the calendar is also not connected. The headline undercounts what is pending; it seems to mean one step that is up to the owner.
- `Y/state-messages-unsaved-desktop.png`: the sticky "2 texts changed" bar covers the next card's "Edit wording" row.
- `Y/08-account-phone-01.png` vs `Y/state-account-signout-everywhere-desktop.png`: the phone view lists "Other signed-in devices · Another device" with no EXAMPLE tag; the desktop view has no such section.
- `Y/07-phone-desktop-03.png`: "3 of 5 done" counts checks that are marked EXAMPLE toward real progress.

## Three ideas from Portal X that Portal Y should adopt
1. **List the other calendars that are supported.** `X/06-calendar-desktop-01.png` has "AVAILABLE ON REQUEST" cards for Outlook / Microsoft 365 and iCloud. Y's calendar page (`Y/state-calendar-connected-picker-desktop.png`) only shows Google, so an Outlook user can't tell if they're covered.
2. **Show the phone number on every caller row.** `X/03-home-desktop-01.png` lists a number under each customer. In Y (`Y/03-home-desktop-02.png`) only the "Wants to talk to you" row shows a number, so the owner can't easily call back anyone else.
3. **Add Verify buttons beside each number.** `X/07-phone-desktop-01.png` has "Verify" next to the business number, texting number and mobile. Y's business number field (`Y/07-phone-desktop-02.png`) is plain text with no check.

## Recommendation
Portal Y wins on every area of the rubric:
- It speaks the owner's language.
- It labels every made-up example.
- It states when a change takes effect and who it affects.
- It protects number changes with a confirm step.
- It gives a clear, specific confirmation after each save.

Portal X covers the same jobs, but leaks internal names (SignalWire, `{tokens}`, text_back, raw IP links) and shows unlabelled, contradictory activity. Its calendar page also leads nowhere. Before an owner sees Portal Y, it should:
- Reword "1 step left" so it doesn't undercount pending setup.
- Stop counting example ticks in forwarding progress.
- Keep the sticky save bar from covering card controls.
- Tag or remove the unlabelled "Other signed-in devices" row on phone.
- Add phone numbers to every caller row.

VERDICT: WINNER Y
