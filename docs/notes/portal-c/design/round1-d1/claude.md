1. **Judge and evidence**
   - **Model:** Claude Opus 5.5 (`claude-opus-5-5`).
   - **Opened, Portal X: 34 images.** Sign-in and enter-code on both widths. Messages desktop 01–09. Messages phone 01, 02, 03, 06, 07, 09, 10, 11, 12. Business desktop and phone 01–02. Calendar desktop and phone. All six `save-*` screens. I also read `03-messages-phone.txt`, `04-business-phone.txt`, `05-calendar-phone.txt` and `INDEX.md`.
   - **Opened, Portal Y: 55 images.** Sign-in on both widths and enter-code phone. Home desktop 01–02 and phone 01–03. Messages desktop 01–08 and phone 01, 02, 06, 09, 11. Schedule desktop 01–04 and phone 02–03. Calendar desktop 01–02. Phone page desktop 01–04 and phone 01, 03, 04. Account on both widths. Seventeen `state-*` screens: messages unsaved bar (desktop and phone), saved toast, edit open, example booked, phone confirm-mobile, invalid mobile, rename offer, saved toast, schedule any-time warning, schedule unsaved bar, calendar connected, calendar no-connect, sign-in error, code error, account menu and sign-out. I also read `INDEX.md`.
   - **Not opened:** X messages phone 04, 05, 08. About 27 of Y's other state and scroll images, including carrier-verizon, custom-length, hours-grid, keep-mobile toast, and Y's enter-code desktop and schedule phone 01, 04, 05.
   - **Confidence:** high. I could view every image I opened. The gap between the portals is large, so the unopened files are unlikely to change the ranking.

2. **Scores**

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 4 | 3 | 2 | 3 | 4 | 3 | 3 | 3 | 4 | 2 | 62 |
| Y | 5 | 4 | 5 | 5 | 4 | 5 | 4 | 5 | 4 | 3 | 88 |

3. **Observations**

**Portal X**
- **Customer text shows a dev server address.** In `03-messages-desktop-05.png` (and `03-messages-phone-12.png`), the "Booking confirmation" bubble shows raw links like `http://hermes-cloud.tailefb1a4.ts.net:8765/a/k7q2-ref/g`. That is internal plumbing in a text customers receive. The links also push the message to "3 texts · 376 characters".
- **No scheduling rules page.** The only pages are Messages, Business and Calendar. "First reminder: Sent after the first follow-up delay" (`03-messages-desktop-06.png`) points to a delay the owner can't see or change anywhere. There are also no controls for appointment length, working hours or quiet hours (job 3).
- **Calendar page is a dead end.** `05-calendar-desktop-01.png` shows "Test mode · No calendar connected" and "Connecting a calendar from this page is still being set up by FluxWorks". There is no button and no contact path. Meanwhile the Messages card in `03-messages-desktop-05.png` shows a "Booked · on your calendar" chip, which contradicts it.
- **Business name change doesn't reach the first text.** In `save-02-business-desktop.png` the toast says "Saved." and the name field reads "Oak & Pine Tree Care (desktop 043715)". The "IN THE FIRST TEXT" bubble directly below still says "Hey, this is Oak & Pine Tree Care." The owner gets no warning that the customized first text kept the old name.
- **Some safety and feedback work is strong.**
  - Changing the mobile goes through a two-step check (`save-03-owner-mobile-change-desktop.png`): "Details saved → Confirm number", with "Keep my current mobile" as an exit.
  - Save toasts name what changed: "Saved. Changed: Question 2: the location." (`save-01-messages-desktop.png`).
  - Cards say "STOP line added for you".
- **The phone layout reads well but is long.** The Messages page is 12 screens on a phone. The jump chips in `03-messages-phone-01.png` cut "No reply" off at the right edge and are gone by `03-messages-phone-02.png` (they don't stick). Save sits only at the bottom (`03-messages-phone-10.png`). The bottom tab bar (Messages, Business, Calendar) is clear and easy to tap.
- **No status overview.** Nothing tells the owner whether the service is set up and working (job 6). There is no call-forwarding help and no texting-number field (job 5).

**Portal Y**
- **Home answers "is it working?" at a glance.** `03-home-desktop-01.png` opens with "Not working yet: 2 steps left." Each step has a status pill and a button: Calendar "Needs you" → "Connect calendar"; Call forwarding "3 of 5 checks done" → "Finish forwarding"; Texting approval "Waiting on phone companies… Nothing for you to do."
- **Sample data is labeled throughout.**
  - The "This week" counts carry an "EXAMPLE NUMBERS" badge, and each caller has an "EXAMPLE" tag (`03-home-desktop-02.png`).
  - Bookings say "Booked on test calendar".
  - The calendar section is headed "Test calendar, not yours" (`06-calendar-desktop-02.png`).
- **Covers all six owner jobs.** The Schedule page has per-rule Reset and shows each default, e.g. "Default: 60 minutes" (`05-schedule-desktop-01.png`). The Phone page has carrier-specific forwarding codes with Copy buttons (`07-phone-desktop-03.png`). Account has "Sign out everywhere" with a confirmation step (`state-account-sign-out-phone.png`).
- **Warns before risky choices and offers the fix.**
  - Choosing "Any day, any time" shows "Customers can be offered times like 1 AM" with a "Use Mon–Fri, 8 AM–5 PM" button (`state-schedule-any-time-warning-desktop.png`).
  - Call forwarding warns "Only forward busy and unanswered calls…" (`07-phone-desktop-02.png`).
  - After a rename, it asks "Update 2 texts that still say 'Oak & Pine Tree Care'" with "Update them / Leave them" (`state-phone-rename-offer-desktop.png`). That handles exactly the case X gets wrong.
- **Strong on phones.**
  - On phone, an unsaved bar sticks to the bottom: "2 texts changed · Discard · Save" (`state-messages-unsaved-bar-phone.png`).
  - The jump chips stick under the header and highlight the current section (`04-messages-phone-06.png`).
  - The billing warning offers a one-tap fix: "Replace — with -" (`04-messages-desktop-06.png`).
- **Weak spots an owner would notice.**
  - Every bubble is headed "Network notice", but the notice wording itself is never shown (`04-messages-desktop-01.png`).
  - Hand-offs say "These go to the FluxWorks operator" (`04-messages-desktop-07.png`), which leaves the owner unsure whether they get the lead.
  - The forwarding checks claim to "tick themselves from real calls TextBack recorded" (`07-phone-desktop-04.png`) but carry no example label.

4. **Looks broken**

**Portal X**
- Raw dev-host URLs inside the booking-confirmation customer text: `03-messages-desktop-05.png`, `03-messages-phone-06.png`, `03-messages-phone-12.png`.
- First-text preview stays stale after a business rename: `save-02-business-desktop.png`, `save-04-keep-mobile-desktop.png`, `save-02-business-phone.png`.
- Inconsistent state: "Booked · on your calendar" (`03-messages-desktop-05.png`) vs "No calendar connected… Bookings are not recorded on any calendar yet" (`05-calendar-desktop-01.png`).
- Dead end: the Calendar page has no action at all (`05-calendar-desktop-01.png`, `05-calendar-phone-01.png`).
- Phone chip row clipped at the right edge, and the chips are not sticky (`03-messages-phone-01.png`).
- Reminder cards reference "the first follow-up delay" and "the second delay", which can't be set anywhere (`03-messages-desktop-06.png`, `03-messages-desktop-07.png`).
- The standard wording ships with an em-dash that triples the billing. The page warns about it but offers no fix (`03-messages-desktop-07.png`, `03-messages-desktop-08.png`).

**Portal Y**
- Contradiction about what happens without a calendar:
  - `03-home-desktop-01.png` says "bookings go on a test calendar you can't see".
  - `06-calendar-desktop-01.png` and `state-calendar-not-connected-no-connect-phone.png` say "the assistant can't check free times or book jobs".
- Booking confirmation promises "A calendar invite is on its way to dana@example.com" (`04-messages-desktop-05.png`) while "Email address" shows "Not asked" and is switched off (`04-messages-desktop-04.png`). The example conversation omits that line (`04-messages-phone-11.png`).
- Forwarding checks 1, 2 and 4 show "Done" with timestamps ("Mon, Oct 26, 9:12 AM from a number ending 0141") and no example label (`07-phone-desktop-03.png`). The timestamp matches the EXAMPLE caller Dana on Home.
- "Network notice" label with no notice text (`04-messages-desktop-01.png`, `04-messages-phone-01.png`).
- Avatar shows a single "O" in the preview header (`04-messages-desktop-01.png`).
- Mobile shown unformatted as "980 555 0123" next to formatted "(704) 555-0123" numbers (`07-phone-desktop-02.png`).
- "Within a minute the caller gets this text" sits directly above "Sent the moment a call goes unanswered" (`04-messages-phone-01.png`).
- Same error shown twice, in the banner and inline (`state-sign-in-error-phone.png`, `state-enter-code-error-phone.png`).
- The unsaved bar replaces the bottom tab bar on phone (`state-messages-unsaved-bar-phone.png`).
- Account has no highlighted tab on phone (`08-account-phone-01.png`).
- Empty outline circles beside "Not working yet" and each setup card read like unchecked radio buttons (`03-home-phone-01.png`).

5. **Three ideas from Portal X that Y should adopt**
- **Show the customer reply that triggers each fallback.** X pairs a "CUSTOMER: Sometime next week" bubble with the TEXTBACK reply under "If the time could not be understood" (`03-messages-desktop-03.png`; same for the email case in `03-messages-desktop-04.png`). Y shows only the bot bubble.
- **Owner-centred hand-off copy.** "When a text needs you, automated scheduling pauses and you get a lead" and "you get an urgent lead" (`03-messages-desktop-07.png`, `03-messages-desktop-08.png`). That beats Y's "These go to the FluxWorks operator".
- **Business name on the sign-in screen.** "SCHEDULING ASSISTANT SETTINGS / Oak & Pine Tree Care" (`01-sign-in-desktop-01.png`) tells the owner they're in the right place before they type. Y's sign-in says only "Owner settings".

6. **Recommendation**

Portal Y should win. It is the only portal that covers all six owner jobs. Its Home page answers "is it working?" in one line with a button for each step. Its safety design is clearly better: guarded defaults, rename propagation, carrier-specific forwarding codes, and a sticky Save/Discard bar on phones. Portal X has good copy in places but no scheduling rules, a calendar dead end, and a dev URL inside a customer-facing text. Before an owner sees Y, it must fix four things:
- make Home and Calendar agree on whether bookings happen without a calendar;
- label the forwarding-check data honestly;
- show the actual network-notice wording and say plainly whether the owner gets the hand-off lead;
- tie the confirmation's calendar-invite line to the email toggle.

VERDICT: WINNER Y
