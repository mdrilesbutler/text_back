# TextBack portal bake-off: blind judge scorecard

## 1. Judge, evidence opened, confidence

- **Judge:** Claude Opus 5.5 (`claude-opus-5-5`).
- **Portal X files opened:** 23 images and 1 text file.
  - Sign-in: `01-sign-in-desktop-01`, `01-sign-in-phone-01`
  - Enter code: `02-enter-code-desktop-01`, `02-enter-code-phone-01`
  - Messages, desktop: `03-messages-desktop-01`, `-05`, `-09`
  - Messages, phone: `03-messages-phone-01`, `-03`, `-06`, `-09`, `-12`
  - Business: `04-business-desktop-01`, `-02`, `04-business-phone-01`, `-02`
  - Calendar: `05-calendar-desktop-01`, `05-calendar-phone-01`
  - After saving: `save-01-messages-desktop`, `save-01-messages-phone`, `save-02-business-phone`, `save-03-owner-mobile-change-desktop`, `save-04-keep-mobile-desktop`
  - Text: `03-messages-desktop.txt`
- **Portal Y files opened:** 50 images and 2 text files.
  - Sign-in and code: `01-sign-in-desktop-01`, `01-sign-in-phone-01`, `02-enter-code-phone-01`
  - Home: `03-home-desktop-01`, `-02`, `03-home-phone-01`, `-02`, `-03`
  - Messages: `04-messages-desktop-01`, `-05`, `-07`, `-09`, `04-messages-phone-01`, `-07`, `-12`
  - Schedule: `05-schedule-desktop-01` to `-04`, `05-schedule-phone-02`
  - Calendar: `06-calendar-desktop-01`, `-02`
  - Phone: `07-phone-desktop-01`, `-02`, `-03`, `-05`, `07-phone-phone-02`, `-03`, `-05`
  - Account: `08-account-phone-01`
  - 25 `state-*` images: sign-in error, enter-code error, account menu, sign-out, messages (edit open, unsaved bar, saved toast on desktop and phone, example booked), schedule (hours grid, any-time warning, unsaved bar, saved toast), calendar (connected, not connected), phone (confirm mobile, rename offer, invalid mobile, unsaved bar, saved toast)
  - Text: `04-messages-desktop.txt`, `07-phone-desktop.txt`
- **Confidence:** high on the ranking, medium on single scores.
  - I could view every image I opened.
  - I skipped some middle scroll positions on both portals.
  - Y's folder has many more state captures than X's. Some of X's friction and error behaviour simply wasn't captured, so X's b2 score is based on less evidence.

## 2. Scores

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 4 | 3 | 2 | 3 | 4 | 3 | 3 | 3 | 4 | 3 | 64 |
| Y | 5 | 4 | 5 | 5 | 5 | 4 | 4 | 5 | 5 | 4 | 92 |

## 3. Observations

### Portal X
1. **Missing pages (`04-business-desktop-01`, `05-calendar-desktop-01`).** The sidebar has only Messages, Business and Calendar.
   - There is no place to set appointment length, working hours, quiet hours or reminder timing (job 3).
   - There is no home or status page saying whether the service works (job 6).
   - The Business page has no business line, no texting number and no call-forwarding setup (job 5 is only partly covered).
   - An owner who wants to stop 1 AM bookings has nowhere to go.
2. **Internal server links in the booking text (`03-messages-desktop-05`, `03-messages-phone-06`, `03-messages-phone-12`).** The "Booking confirmation" bubble shows raw links like `http://hermes-cloud.tailefb1a4.ts.net:8765/a/k7q2-ref/g`. On a phone this fills about 10 lines of the bubble. It shows the owner internal server details, and they would assume customers get the same thing.
3. **Good handling of a mobile number change (`save-03-owner-mobile-change-desktop`, `save-04-keep-mobile-desktop`).**
   - A two-step "Details saved → Confirm number" screen texts a code to the new number.
   - It says "until then codes still go to your current mobile".
   - It offers a "Keep my current mobile" way out, which then shows a "Kept your current mobile." toast.
   - This protects the owner's sign-in well.
4. **Calendar page is a dead end (`05-calendar-phone-01`).** The "No calendar connected" card has a "Test mode" badge and says "Connecting a calendar from this page is still being set up by FluxWorks." There is no button, no contact and no next step. It is honest, but the owner can do nothing from here.
5. **Strong messages timeline (`03-messages-desktop-01`).**
   - A step rail (Missed call → The questions → Booking → No reply) with a "Conversation preview" phone next to it.
   - "Edit wording / Reset" on every card.
   - The billing warning "Billed as 3 texts. Customers still see one message." with a three-dot segment meter.
   - The note "changes start with the next missed call after you save" is a good safety cue.
6. **Save toast is specific, but the preview goes stale (`save-01-messages-phone`, `save-04-keep-mobile-desktop`).**
   - The toast says "Saved. Changed: Question 2: the location."
   - After the business name was changed to "Oak & Pine Tree Care (desktop 043715)", the "IN THE FIRST TEXT" preview still says "Hey, this is Oak & Pine Tree Care", even though the field help says "Used in every text customers get."
   - Nothing tells the owner why the two differ.

### Portal Y
1. **Home answers "is it working?" (`03-home-desktop-01`).**
   - The headline reads "Not working yet: 2 steps left."
   - Below it, "Needs you" cards for Calendar ("Connect calendar") and Call forwarding ("Finish forwarding").
   - A "Texting approval: Waiting on phone companies … Nothing for you to do" card.
   - An owner knows what to do next within five seconds.
2. **Schedule page covers job 3 completely, with consequences spelled out (`05-schedule-desktop-01` to `-04`).**
   - Appointment length chips and a time zone setting.
   - Per-day working hours.
   - Quiet hours, explaining which texts still go out immediately.
   - Reminder delays.
   - Every rule shows "Default: …", a "Reset" link, and an "Applies right away…" line.
   - `state-schedule-any-time-warning-phone` warns "Customers can be offered times like 1 AM" and offers a one-tap "Use Mon–Fri, 8 AM–5 PM".
3. **Phone & business covers job 5 end to end (`07-phone-desktop-02`, `07-phone-desktop-03`, `07-phone-desktop-05`).**
   - Business number, a read-only "Texting number (704) 555-0100 – Set up by FluxWorks", and Your mobile.
   - Carrier chips with copyable `*71 704 555 0100` / `*73` codes.
   - A warning: "Only forward busy and unanswered calls."
   - An "Is forwarding working? 3 of 5 done" checklist. Its demo checks are tagged EXAMPLE, with the note "In this preview, checks 1, 2 and 4 come from example calls."
4. **Phone editing flow is the best of the two (`state-messages-unsaved-bar-phone`, `state-messages-saved-toast-phone`, `state-phone-rename-offer-desktop`).**
   - A sticky top bar replaces the header: "● 2 texts changed ▾ · Discard · Save".
   - The save banner names the change: "Saved. You changed 'Question 2: the address'."
   - After renaming the business, it asks: "2 texts still say 'Oak & Pine Tree Care'. Update them / Leave them". This is exactly the stale-name problem X has.
5. **Booking bubble doesn't match what customers get (`04-messages-desktop-05`, `state-messages-example-booked-phone`).**
   - The bubble shows tidy "Add to Google Calendar ›" links, but the count reads "3 texts · 370 characters", so the real SMS carries raw URLs.
   - The intro says "Green bubbles are what customers see", so this slightly over-promises.
6. **Too many separate Save buttons (`07-phone-desktop-01`, `07-phone-desktop-05`, `08-account-phone-01`).**
   - The Phone page has a "Save business details" button in the middle and a separate "Save" at the bottom.
   - On Account, the "Remember this phone for 30 days" toggle needs its own Save.
   - An owner may think one Save covers the whole page.

## 4. Looks broken

**Portal X**
- **Raw internal links:** booking-confirmation bubbles show `hermes-cloud.tailefb1a4.ts.net:8765` URLs (`03-messages-desktop-05`, `03-messages-phone-06`, `03-messages-phone-12`).
- **Booking date is in the past:** the example says "Booked: tree removal on Thursday, Oct 22", and Question 3 suggests "Oct 22 at 4pm". Today is Oct 26, so the example books a past date (`03-messages-phone-03`, `03-messages-desktop-05`).
- **Name preview out of date:** "IN THE FIRST TEXT" still shows the old business name after a rename (`save-04-keep-mobile-desktop`, `save-02-business-phone`).
- **Header truncation:** on the phone the header shows "Oak & Pine Tree Care (…". The long name comes from the test harness, but the truncation is the portal's (`save-01-messages-phone`).
- **Clipped jump chips:** "No reply" is cut off at the right edge, and nothing hints that the row scrolls sideways (`03-messages-phone-01`).
- **Calendar dead end:** no action at all on the Calendar page (`05-calendar-desktop-01`).
- **Inconsistent label:** sign-in calls the number "Business mobile" (`01-sign-in-phone-01`), while the Business page calls it "Your mobile" (`04-business-phone-02`).

**Portal Y**
- **Booking bubble mismatch:** the bubble shows link labels while the character count implies raw URLs (`04-messages-desktop-05`).
- **Demo data in the real status headline:** "Not working yet: 2 steps left" counts the Call forwarding card, which is tagged EXAMPLE (`03-home-desktop-01`, `03-home-phone-01`). The headline mixes demo state with real state.
- **Misaligned footnote:** "In this preview, checks 1, 2 and 4…" sits left of the card column on desktop and phone (`07-phone-desktop-05`, `07-phone-phone-05`).
- **Two save scopes on one page:** `07-phone-desktop-01` and `07-phone-desktop-05`.

## 5. Three ideas from Portal X (lower-ranked) that Y should adopt
1. **Make the bubble match the real SMS.** X's booking bubble shows the actual link text the customer receives, which matches the character count (`03-messages-desktop-05`). Y should do the same, using a short branded link domain rather than X's internal one.
2. **Segment meter next to the text count.** X shows three small dots beside "3 texts · 376 characters" (`03-messages-desktop-05`), so the billing cost is visible at a glance.
3. **Visible jump chips on phone.** X's always-visible chip row (Missed call / Questions / Booking / No reply) at the top of `03-messages-phone-01` shows the page structure up front. Y hides it in a collapsed "Jump to a step" dropdown. Fix X's clipping and add a scroll hint if adopting it.

## 6. Recommendation
Portal Y wins clearly:
- It has a real place for all six owner jobs. X has none for scheduling rules, the service status or call forwarding.
- Its phone experience is better: five-tab bottom nav, a sticky "Jump to" bar, and a sticky "changes · Discard · Save" bar.
- It labels every demo element (EXAMPLE, "test calendar you can't see") and explains what each change does before you save it.

Before an owner sees it, Y must fix four things:
- Make the booking-confirmation bubble show what the SMS really contains.
- Take the EXAMPLE-tagged forwarding step out of the real "Not working yet" headline count.
- Merge the Phone page's two save scopes into one sticky save.
- Align the forwarding-check footnote with the cards.

VERDICT: WINNER Y
