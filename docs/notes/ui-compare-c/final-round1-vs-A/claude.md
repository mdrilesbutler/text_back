I'm **Claude Opus 5.5** (`claude-opus-5-5`). Portal X wins, 90 to 62. It covers all six owner jobs, Portal Y covers about two, and X explains consequences much more carefully.

## 1. Evidence and confidence

**What I opened:**
- **Portal X:** 42 of 114 images, chosen to cover every page at both widths, plus the key state and save shots. These included `01-sign-in-phone-01`, `02-enter-code-desktop-01`, `03-home-desktop-01/02`, `03-home-phone-01/02/03`, `04-messages-desktop-01/05/07/09`, `04-messages-phone-01/06/12`, `05-schedule-desktop-01/02/03/04`, `05-schedule-phone-02/05`, `06-calendar-phone-01`, `07-phone-desktop-01..04`, `07-phone-phone-03`, `08-account-phone-01`, nine `state-*` images and four `save-*` images.
- **Portal Y:** 29 of 37 images. These were `01-sign-in-phone-01`, `02-enter-code-desktop-01`, `03-messages-desktop-01..09` (all nine), `03-messages-phone-01/02/06/07/09/10/12`, `04-business-desktop-01`, `04-business-phone-01/02`, `05-calendar-desktop-01`, `05-calendar-phone-01` and all six `save-*` images.
- **Text files:** I read both INDEX files and every page `.txt` for X (home, messages, schedule, calendar, phone, account) and for Y (messages, business, calendar).

**Confidence: high.** I could view every image I opened. I did not open every X state shot or every middle scroll frame, so a small defect in an unopened frame could be missing. Header names like "(desktop 043715)" on the save screens come from the test harness's private copy, so I didn't count them against either portal.

## 2. Scores

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 4 | 4 | 5 | 5 | 5 | 4 | 4 | 5 | 5 | 4 | 90 |
| Y | 4 | 3 | 2 | 3 | 4 | 3 | 3 | 3 | 4 | 2 | 62 |

## 3. Observations

### Portal X
1. **Home shows whether the service works.** `03-home-desktop-01.png`: the headline "Not working yet: 1 step left." sits above three setup cards: Calendar "Waiting on FluxWorks", Call forwarding "Needs you" with a **Finish forwarding** button, and Texting approval "Waiting on phone companies". Each card has a next step. However, "1 step left" sits above three unfinished cards, so the owner has to work out that only one of them needs them.
2. **Demo data is labelled everywhere.** `03-home-desktop-02.png` and `03-home-phone-02.png`: "This week" carries an **EXAMPLE NUMBERS** tag, and every caller row (Dana Whitfield, Priya Natarajan, Marcus Lee) carries **EXAMPLE**. The "Wants to talk to you" row has large **Call** and **Text** buttons, which is useful between jobs.
3. **Unsaved changes are hard to lose on a phone.** `state-messages-unsaved-phone.png`: a sticky top bar reads "● 2 texts changed" with **Discard** and **Save**. Below it sits a sticky "Jump to: Questions" picker. The edited card shows an **Unsaved** badge and a "Was: What's the address for the job?" line. After saving, `save-01-messages-wording-phone.png` confirms: "Saved. You changed 'Question 2: the address'."
4. **Consequences are stated before and after saving.** `05-schedule-desktop-01.png` says "Applies right away, including customers mid-conversation." under Appointment length, with "Default: 60 minutes" and Reset. `save-02-schedule-length-90-phone.png` repeats the consequence in the confirmation.
5. **Renaming the business finds stale texts.** `save-03-business-name-rename-offer-phone.png`: "1 text still says 'Oak & Pine Tree Care'. Update it to the new name?" with **Update it** and **Leave it** buttons. `save-04-rename-texts-updated-desktop.png` then shows the first-text preview with the new name.
6. **Call forwarding is a full, safe walkthrough.** `07-phone-desktop-02.png` to `07-phone-desktop-04.png`:
   - an amber warning: "Only forward busy and unanswered calls…";
   - carrier chips;
   - `*71 704 555 0100` with a **Copy** button, and the turn-off code `*73`;
   - a five-step "Is forwarding working?" checklist. Steps the system can't see are ticked by the owner ("I checked this"), and the footnote says "checks 1, 2 and 4 come from example calls."
7. **Friction: the Messages page is very long on a phone.** It runs to 12 phone-height screens (`04-messages-phone-01` to `04-messages-phone-12`). The sticky jump picker reduces the pain but doesn't remove it.

### Portal Y
1. **Clear page headers, but no home or status page.** `03-messages-desktop-01.png`: "Your messages" with "Tap Edit wording to change one; changes start with the next missed call after you save" orients well. But the only pages are Messages, Business and Calendar (`03-messages-phone-01.png` bottom bar), so an owner can never see whether the service is set up or working.
2. **Internal server links shown to customers.** `03-messages-desktop-05.png` and `03-messages-phone-06.png`: the Booking confirmation bubble contains three raw links of the form `http://hermes-cloud.tailefb1a4.ts.net:8765/a/k7q2-ref/g`. They wrap mid-word across six lines, and the owner is shown them as what the customer receives.
3. **Scheduling rules and forwarding are missing.** The text says "Sent after the first follow-up delay with no reply" (`03-messages-phone-07.png`), but no page sets that delay, appointment length, working hours or quiet hours. `04-business-desktop-01.png` has only Business name, HELP number and Your mobile: no business line, no texting number, no forwarding.
4. **The calendar page is a dead end.** `05-calendar-phone-01.png`: a "Test mode" chip, "No calendar connected", "Connecting a calendar from this page is still being set up by FluxWorks." There is no button, no contact and no timeline.
5. **Good mobile-number check.** `save-03-owner-mobile-change-desktop.png`: a "Confirm your new mobile" step, "until then codes still go to your current mobile", and **Keep my current mobile**. `save-04-keep-mobile-desktop.png` confirms "Kept your current mobile."
6. **A rename leaves the preview wrong.** `save-02-business-desktop.png`: the name is saved as "Oak & Pine Tree Care (desktop 043715)" and the toast says only "Saved.", but "IN THE FIRST TEXT" still reads "Hey, this is Oak & Pine Tree Care." No warning or offer to update appears.
7. **The save button is far from the edits.** `03-messages-phone-10.png`: "No unsaved changes / Save changes" only appears after about 10 phone screens of cards. It isn't sticky.

## 4. Looks broken

### Portal Y
- **Internal links in customer text:** raw `hermes-cloud.tailefb1a4.ts.net:8765` URLs in the booking confirmation (`03-messages-desktop-05.png`, `03-messages-phone-06.png`, `03-messages-phone-12.png`).
- **Contradictory calendar state:** "Booked · on your calendar" (`03-messages-desktop-05.png`, `03-messages-phone-12.png`) versus "Bookings are not recorded on any calendar yet" (`05-calendar-desktop-01.png`).
- **Stale preview after rename:** the business-name change doesn't reach the first-text preview, and nothing warns about it (`save-02-business-desktop.png`, `save-02-business-phone.png`).
- **Desktop navigation scrolls away:** once the page scrolls, the sidebar nav and header disappear, leaving only "TextBack by FluxWorks" near the top of an empty sidebar (`03-messages-desktop-02.png` through `03-messages-desktop-09.png`).
- **Calendar dead end:** no action of any kind (`05-calendar-phone-01.png`).
- **Past date in the sample:** the booking is for "Thursday, Oct 22", which is before the build's current date of Mon Oct 26 (`03-messages-desktop-05.png`).
- **Header truncation on phone:** the business name is cut to "Oak & Pine Tree Care (…" (`save-01-messages-phone.png`). The long name comes from the harness, but it shows the header has no room for longer names.

### Portal X
- **Confusing step count:** "Not working yet: 1 step left." above three unfinished setup cards (`03-home-desktop-01.png`, `03-home-phone-01.png`).
- **One unlabelled demo row:** "Other signed-in devices · Another device · last used Mon, Oct 26" has no EXAMPLE tag, while the row just above it does (`08-account-phone-01.png`).
- **Misplaced subtitle:** "This is the number customers call. TextBack never changes it." sits under the **Numbers** heading, which covers three numbers, but it describes only the first (`07-phone-desktop-01.png`).
- **Inconsistent save-bar wording:** "2 texts changed" (`state-messages-unsaved-phone.png`) versus "Not saved · 1 change" (`state-phone-invalid-mobile-field-phone.png`).

## 5. Three ideas from Portal Y that X should adopt
1. **Name the fixable cause of extra billing.** "Billed as 3 texts. The '—' symbol limits each text to 70 characters." (`03-messages-desktop-07.png`). X's reminder card says only "Billed as 2 texts". X should name the culprit in plain words, for example "the long dash makes this cost more; use a plain hyphen".
2. **Show a small text-count meter.** The ▬▬▬ dots next to "3 texts · 376 characters" (`03-messages-desktop-05.png`) show the cost at a glance, before anyone reads the number.
3. **Say what the portal is for at sign-in.** The "SCHEDULING ASSISTANT SETTINGS" line above the business name (`01-sign-in-phone-01.png`) tells a non-technical owner what they're signing into. X says only "Sign in to TextBack".

## 6. Recommendation
Portal X should go forward. It is the only one where an owner can do all six jobs: sign in and out, edit texts, set every timing rule, check the calendar, manage all three numbers plus forwarding, and see whether the service is working. It also states each change's consequence before and after saving, protects unsaved work with a sticky Save/Discard bar, verifies a new mobile, and offers to fix texts that still carry the old business name. Portal Y is visually tidy and has a good mobile-confirm step, but it is missing scheduling rules, forwarding and a status page, and it shows internal server links in a customer text. Before an owner sees X, it should:
- reword the Home headline so the step count matches the cards;
- tag every demo row, including the second account device;
- fix the misplaced Numbers subtitle;
- make the save-bar wording consistent;
- shorten the phone Messages page, for example by collapsing the less-used branch messages by default.

VERDICT: WINNER X
