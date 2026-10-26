## TextBack client portal scorecard: Claude judge, 2026-10-26

### 1. Judge, files opened, confidence

- **Judge:** Claude Opus 5.5 (`claude-opus-5-5`).
- **Images I opened and viewed:**
  - **Portal X, 22 images:** `03-home-desktop-01`, `03-home-phone-01/02/03`, `04-messages-desktop-01`, `04-messages-desktop-06`, `04-messages-phone-01`, `05-schedule-phone-01/03`, `state-schedule-set-hours-phone`, `state-messages-unsaved-phone`, `state-home-account-menu-phone`, `06-calendar-phone-01`, `07-phone-phone-02/03/05`, `08-account-phone-01`, `01-sign-in-phone-01`, `save-01-messages-wording-desktop`, `save-02-schedule-length-90-phone`, `save-03-business-name-rename-offer-phone`, `save-07-owner-mobile-confirm-step-phone`.
  - **Portal Y, 20 images:** `01-sign-in-desktop-01`, `02-enter-code-phone-01`, `03-messages-desktop-01/05/06/09`, `03-messages-phone-01/06/09/10/11/12`, `04-business-phone-01/02`, `05-calendar-phone-01`, `save-01-messages-desktop`, `save-01-messages-phone`, `save-02-business-phone`, `save-03-owner-mobile-change-desktop`, `save-04-keep-mobile-desktop`.
- **Text files I read:** both `INDEX.md` files. For X: `03-home-desktop.txt`, `04-messages-desktop.txt`, `05-schedule-desktop.txt`, `06-calendar-desktop.txt`, `07-phone-desktop.txt`, `08-account-desktop.txt`. For Y: `03-messages-desktop.txt`, `04-business-desktop.txt`, `05-calendar-desktop.txt`.
- **Confidence:** high on the overall ranking, medium on single scores.
- **Limitations:**
  - I did not open every scroll position. X's desktop Schedule and Phone pages I judged from their text files plus the phone captures.
  - Portal Y has no captured account menu, and its page text has no "Sign out" string. So I could not confirm that sign-out exists on Y. I scored that as unverified, not as missing.
  - X's `state-schedule-set-hours-phone.png` shows the top of the Schedule page, not the hours editor. That looks like a capture problem, not a portal defect.

### 2. Scores

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | 4 | 4 | 90 |
| Y | 3 | 2 | 2 | 3 | 4 | 3 | 2 | 3 | 4 | 2 | 56 |

### 3. Observations

**Portal X**
1. **Status at a glance.** `03-home-desktop-01.png` and `03-home-phone-01.png`: the Home headline reads "Not working yet: 1 step for you, 2 waiting on others." Below it, a setup timeline has a card each for Calendar ("Waiting on FluxWorks"), Call forwarding ("Needs you", with a **Finish forwarding** button) and Texting approval. An owner knows within seconds whether the service works and what to do next. This is owner job 6, and Y has no page for it.
2. **Demo data is labelled everywhere.** `03-home-phone-02.png` and `03-home-phone-03.png`: the "This week" counts carry an **EXAMPLE NUMBERS** tag, and every caller (Dana Whitfield, Priya Natarajan, Marcus Lee) has an **EXAMPLE** chip. Dana's booking reads "Booked on test calendar," not "on your calendar." The "Wants to talk to you" row has large **Call** and **Text** buttons.
3. **Unsaved changes are hard to lose.** `state-messages-unsaved-phone.png`: a sticky top bar shows "● 2 texts changed" with **Discard** and **Save**, plus a sticky "Jump to: Questions" selector. The edited card shows an "Unsaved" chip and a "Was: What's the address for the job?" line, so the owner sees the before and after.
4. **Scheduling rules state their consequences.** `05-schedule-phone-01.png`, `05-schedule-phone-03.png` and `save-02-schedule-length-90-phone.png`: Appointment length has preset chips, a range hint ("15 to 480 minutes, in steps of 5") and "Default: 60 minutes". Each rule has an "Once saved:" line, for example "Applies right away, including customers mid-conversation." The save banner repeats that consequence.
5. **Forwarding setup is tailored to the carrier.** `07-phone-phone-03.png` and `07-phone-phone-05.png`: a warning box says "Only forward busy and unanswered calls." The page shows carrier chips (Verizon selected), the dial code **\*71 704 555 0100** with **Copy**, the turn-off code **\*73**, and a numbered "Is forwarding working?" checklist. The checklist is honest that TextBack can't see answered calls, so the owner ticks that check ("I checked this").
6. **Renaming the business doesn't leave stale texts.** `save-03-business-name-rename-offer-phone.png`: after the rename, a banner says "1 text still says 'Oak & Pine Tree Care'. Update it to the new name?" with **Update it** / **Leave it** buttons.
7. **Friction.**
   - The Phone page runs about five phone screens and the Schedule page about five (`07-phone-phone-01…05`, `05-schedule-phone-01…05`).
   - On `07-phone-phone-02.png`, the Numbers intro "This is the number customers call. TextBack never changes it." sits above three numbers, so "This" is ambiguous.
   - Account is not in the phone bottom nav; it is only in the header dropdown (`state-home-account-menu-phone.png`), which does make Sign out reachable.

**Portal Y**
1. **Internal server links in customer texts.** `03-messages-desktop-05.png`, `03-messages-phone-06.png` and `03-messages-phone-12.png`: the Booking confirmation bubble shows raw `http://hermes-cloud.tailefb1a4.ts.net:8765/a/k7q2-ref/g`-style links (an internal server address) to every owner, in both the editor and the preview. It is the worst plain-language and polish failure in the set.
2. **The preview claims a calendar booking that can't happen.** `03-messages-phone-12.png` and `03-messages-desktop-05.png`: the preview and the confirmation card both show the badge "✓ Booked · on your calendar". But `05-calendar-phone-01.png` says "Test mode · No calendar connected · Bookings are not recorded on any calendar yet."
3. **Calendar page is a dead end.** `05-calendar-phone-01.png`: "Connecting a calendar from this page is still being set up by FluxWorks." There is no button, no contact link and no next step.
4. **Settings missing.**
   - There is no Schedule page (appointment length, working hours, quiet hours, reminder timing). Yet `03-messages-desktop-06.png` says the First reminder is "Sent after the first follow-up delay with no reply," a delay the owner cannot see or change.
   - There is no call-forwarding setup, no business-number or texting-number display, and no home or status page. The nav is only Messages / Business / Calendar.
5. **Good: verified mobile change.** `save-03-owner-mobile-change-desktop.png`: a "Confirm your new mobile" stepper with a 6-box code entry, a **Keep my current mobile** button and "Send the code again". The copy says codes keep going to the current mobile until the new one is confirmed.
6. **Save friction on phone.** `03-messages-phone-10.png`: the "No unsaved changes / Save changes" bar is a normal block about 10 screens down the 12-screen Messages page. Nothing in `03-messages-phone-06`/`09` shows it stays visible while scrolling.
   - `03-messages-phone-01.png`: the jump chips (Missed call / Questions / Booking / No reply) run off the right edge, and there is no cue that the row scrolls.
7. **Rename leaves a stale first text.** `save-02-business-phone.png`: the saved business name changed, but "IN THE FIRST TEXT" still shows "Hey, this is Oak & Pine Tree Care." Nothing warns that the customized first text kept the old name, and the toast says only "Saved."

### 4. Looks broken

- **Y:** raw internal links (`hermes-cloud.tailefb1a4.ts.net:8765`) in the Booking confirmation, wrapping mid-word ("k7 / q2-ref") (`03-messages-desktop-05.png`, `03-messages-phone-06.png`, `03-messages-phone-12.png`).
- **Y:** inconsistent state. "Booked · on your calendar" (`03-messages-phone-12.png`) contradicts "No calendar connected" (`05-calendar-phone-01.png`).
- **Y:** example date already in the past. The sample confirmation reads "Thursday, Oct 22," but the build's own date is Mon Oct 26 (`03-messages-phone-12.png`, `03-messages-phone-11.png`).
- **Y:** dead-end Calendar page with no action (`05-calendar-phone-01.png`).
- **Y:** jump-chip row clipped at "No reply" (`03-messages-phone-01.png`, `save-01-messages-phone.png`).
- **Y:** the first-text preview shows the old name after a rename, with no prompt (`save-02-business-phone.png`, `save-04-keep-mobile-desktop.png`).
- **Y:** the reminder copy refers to a "follow-up delay" setting that exists nowhere in the portal (`03-messages-desktop-06.png`).
- **Y:** the default reminder and step-in wording uses "—", and the portal itself warns this bills 2–3 texts (`03-messages-desktop-06.png`, `03-messages-phone-09.png`). The default is costing extra by design.
- **Y:** the sign-in field says "Business mobile" (`01-sign-in-desktop-01.png`); the Business page says "Your mobile" (`04-business-phone-02.png`).
- **X:** the Numbers intro sentence is ambiguous (`07-phone-phone-02.png`).
- **X:** the Appointment length number field and the "Custom" chip are both shown, which is redundant (`05-schedule-phone-01.png`).
- **X:** no clipping, overlap or wrong dates seen.

### 5. Three ideas from Y (the lower-ranked portal) that X should adopt

1. **"↑ Back to editing" link** at the end of the phone conversation preview, so the owner isn't stranded at the bottom of a long page (`Y/03-messages-phone-12.png`).
2. **Text-count dots and a plain reason for long texts**, for example "3 texts · 376 characters ▬▬▬" plus "The '—' symbol limits each text to 70 characters" (`Y/03-messages-desktop-05.png`, `Y/03-messages-phone-09.png`). X states counts in words only; the dots make the cost visible at a glance.
3. **One short business-details form, kept separate from forwarding.** Business name, HELP number and mobile sit on one short page with one **Save business details** button (`Y/04-business-phone-02.png`). X could split its five-screen Phone page into "Business & numbers" and "Call forwarding."

### 6. Recommendation

Portal X wins clearly. It covers all six owner jobs, starts with an honest status headline, labels every example, states what each change affects before it is saved, and protects unsaved work with a sticky Save/Discard bar. Portal Y has a solid Messages editor and a verified mobile change. But it has no scheduling rules, call forwarding or status page. It also shows owners internal server links and claims bookings land "on your calendar" when no calendar is connected. Before an owner sees X, it must:
- shorten or split the Phone and Schedule pages on phone;
- fix the ambiguous Numbers intro;
- drop the redundant Custom length control;
- put Account in the phone bottom nav;
- add a "Back to editing" link after the phone preview.

VERDICT: WINNER X
