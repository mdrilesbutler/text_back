I'll judge Portal X and Portal Y only from the screenshots and page text in this folder, starting with each index so I open every image.Indexes are in. Next I’ll open the sign-in, code, and home screens for both portals, then work through the rest page by page.I'll open the last eight Portal X phone-state screenshots, then write the scorecard from what those images actually show.The last phone states are in. I'll re-open the screenshots that decide the score so those citations come from the images, not the notes.## 1. Judge

Grok 4.7 (xAI). I opened every PNG in this pack: **99 in `X/`** (55 page shots + 44 state shots) and **37 in `Y/`**. Screenshots are the authority. I re-opened the eight last X phone states and re-checked the screens cited below. Confidence is high on copy, hierarchy, and the defects named here. Limits: these are static shots, so I did not tap anything; Y never shows the person-icon menu open, so sign-out on Y is unscored as not shown; numbered scroll seams that only repeat a sticky bar are not counted as bugs.

## 2. Scores

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| X | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | 4 | 3 | 88 |
| Y | 3 | 3 | 2 | 3 | 3 | 3 | 2 | 3 | 4 | 2 | 56 |

## 3. Portal X

- On `X/03-home-desktop-01.png` the heading is **“Not working yet: 2 steps left.”** The Calendar card says **“Needs you”** and **“No calendar of yours yet. Until you connect one, bookings go on a test calendar you can’t see,”** with **Connect calendar**. An owner on a phone between jobs can see what is blocking the service and where to go.
- On `X/state-schedule-any-time-warning-desktop.png` the **Working hours** card, with **Any day, any time** selected, says the assistant will take a free slot **“including the middle of the night,”** then an amber box: **“Customers can be offered times like 1 AM.”** The button **Use Mon–Fri, 8 AM–5 PM** says it only fills the grid and still needs Save. Quiet hours stay on, and the copy says START, HELP, and STOP still go out.
- On `X/state-messages-example-booked-desktop.png` the example pill says **“Booked · on the test calendar,”** the confirmation is **Thursday, Oct 29 at 10:00 AM EDT**, and the count is **“131 characters with the notice.”** The same shot’s phone mock cuts the bubble off at **“Add to Google Calendar ›.”**
- On `X/state-phone-rename-offer-desktop.png` the banner reads **“Saved. You changed ‘Business name’. 2 texts still say ‘Oak & Pine Tree Care’. Update them to the new name?”** with **Update them** and **Leave them**. On `X/state-phone-keep-mobile-toast-desktop.png` the toast is **“Kept your current mobile.”** Changing the name or the sign-in number does not silently rewrite live texts or move sign-in.
- On `X/state-phone-unsaved-bar-phone.png` the field says **Oak & Pine Tree Service** while the **IN THE FIRST TEXT** bubble still says **Oak & Pine Tree Care**, under the line **“The first text is shown below.”** The bottom bar is **Home, Messages, Schedule, Calendar, Phone**. Account is only via the business-name menu, which is a real extra step on a phone.
- On `X/state-schedule-unsaved-bar-desktop.png` the floating bar **“1 rule changed: Appointment length”** is clear, and the **90 min** chip matches the field, but the page title **Schedule** is sliced so only the bottoms of the letters show under the top bar.

## 4. Portal Y

- On `Y/01-sign-in-desktop-01.png` the card is simple: business name, one field, **Text me a code**. The field is labelled **Business mobile** and already contains **704 555 0123**. On `Y/04-business-phone-01.png` the page says sign-in codes go to **Your mobile**, and that screen never shows 704 555 0123. An owner would request a code for a number that is not the owner mobile on file (980 555 0123).
- On `Y/03-messages-desktop-05.png` the **Booking confirmation** bubble is the text customers would get: **“Booked: tree removal on Thursday, Oct 22 at 4:00 PM”** plus raw links `http://hermes-cloud.tailefb1a4.ts.net:8765/a/k7q2-ref/g` (and the Outlook and iCal twins). The pill under it says **“Booked · on your calendar.”** Oct 22 is the previous Thursday. On `Y/03-messages-phone-06.png` those links break mid-token (`…/a/k7` then `q2-ref/g`).
- On `Y/05-calendar-desktop-01.png` the only card is **Test mode / No calendar connected / “Bookings are not recorded on any calendar yet.”** The next line is **“Connecting a calendar from this page is still being set up by FluxWorks.”** There is no connect button, no support action, and no free-time check. That contradicts the booking pill.
- `Y/INDEX.md` lists sign-in, code, Messages, Business, and Calendar only. There is no screen for appointment length, working hours, quiet hours, reminder timing, call forwarding, or a setup status. Reminder cards on `Y/03-messages-desktop-07.png` say **“Sent after the second delay”** and never show an hour or a day control.
- The same `Y/03-messages-desktop-07.png` heading **Owner steps in** is the clearest handoff in either pack: **“When a text needs you, automated scheduling pauses and you get a lead.”** The preview footer on `Y/03-messages-desktop-01.png` says **“Sample conversation · nothing is sent · names invented.”**
- On `Y/save-01-messages-phone.png` the toast **“Saved. Changed: Question 2: the location.”** is specific, and it covers the first line of the intro. The header is cut to **“Oak & Pine Tree Care (…”**. On `Y/04-business-phone-01.png` the intro hyphenates as **“sign-” / “in codes go.”**

## 5. Looks broken

- `X/state-schedule-unsaved-bar-desktop.png`: heading **Schedule** is cut through the middle of the letters under the top bar while the unsaved bar is on screen.
- `X/state-messages-example-booked-desktop.png`: example phone clips the booking bubble at **Add to Google Calendar ›**.
- `X/state-phone-unsaved-bar-desktop.png` and `X/state-phone-unsaved-bar-phone.png`: **Business name** is **Oak & Pine Tree Service**; the first-text bubble still says **Oak & Pine Tree Care**.
- `Y/03-messages-desktop-05.png` and `Y/03-messages-phone-06.png`: customer booking text contains a private host and port, wraps mid-token on the phone, uses **Thursday, Oct 22**, and says **Booked · on your calendar**.
- `Y/05-calendar-desktop-01.png`: says bookings are recorded nowhere, and offers no next step. Dead end, and it disagrees with the messages pill.
- `Y/01-sign-in-desktop-01.png` vs `Y/04-business-phone-01.png`: sign-in number and “where codes go” do not match.
- `Y/save-01-messages-phone.png`: header truncated with a stray “(”; toast covers the intro. `Y/save-02-business-desktop.png` and `Y/save-02-business-phone.png`: business-name field and header carry harness suffixes **(desktop 043715)** and **(phone 043715)** on a field marked as used in every text; the bubble does not.
- `Y/04-business-phone-01.png`: **sign-in** breaks across a line as **sign- / in**.

## 6. Three ideas from Y that X should adopt

1. **`Y/03-messages-desktop-07.png`, heading “Owner steps in.”** Say that automated scheduling pauses and the owner gets a lead. X’s “steps back” plus a FluxWorks handoff is harder for a tree-care owner to picture.
2. **`Y/03-messages-desktop-01.png`, caption under Conversation preview:** **“Sample conversation · nothing is sent · names invented.”** Put that one line under the preview on every messages scroll, including phone, so it does not depend on an EXAMPLE badge inside a clipped mock.
3. **`Y/01-sign-in-desktop-01.png`, the button “Text me a code” on a card that already shows the business name.** Keep X’s owner-mobile rules and 10-digit check. Take Y’s single button and the business name on the card. Do not take Y’s **Business mobile** label or the 704 prefill.

## 7. Recommendation

X is the portal an owner can actually run. Sign-in, sign-out, the texts, the hours, the calendar, the phone numbers, forwarding, and a plain “not working yet” status all have a findable place, and the test calendar, example calls, and STOP line are labelled before anything is saved. Y is a tidy editor for messages and the business name, and then it stops: no schedule, no forwarding, no status, a calendar page with nothing to press, and a sample booking that would send a past date and a private server address. Before an owner sees X, the Schedule title has to stay readable when the unsaved bar is up, and the example phone has to show the whole booking text. The first-text bubble should match the name in the field, or the screen should say it changes only after **Update them**.

VERDICT: WINNER X
