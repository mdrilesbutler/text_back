1. **Judge:** Claude Opus 5.5 (`claude-opus-5-5`).
   - **Files opened:** 26 images and 4 text files for Portal X. 34 images and 4 text files for Portal Y. Every page type on both widths, plus the after-save screens.
   - **Portal X images:** home, messages, scheduling, calendar, phone, account, sign-in, enter-code, and five save screens.
   - **Portal Y images:** the same pages, plus nine state/save screens: unsaved bar, set hours, calendar free times, calendar picker, invalid mobile, rename offer, mobile confirm step, account menu, schedule length saved.
   - **Not opened:** about 30 Y scroll and state frames (several messages, schedule and phone scroll positions, sign-in error, enter-code error, sign-out everywhere) and a few X scroll frames (some messages frames, `06-calendar-phone-02`, `08-account-desktop-01`).
   - **Confidence:** high on the ranking, medium-high on single scores. Things I read only in the text files are marked "(txt)".

2. **Scores**

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 3 | 2 | 4 | 3 | 3 | 3 | 1 | 3 | 3 | 2 | 54 |
| Y | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | 5 | 4 | 92 |

3. **Observations**

**Portal X**
- `03-home-desktop-01.png`, setup cards:
  - "CAMPAIGN IN REVIEW / Texts carry a '[SignalWire Free Trial]' tag" is vendor plumbing an owner won't understand.
  - The sidebar footer reads "text_back · missed-call recovery", an internal name.
  - Plus: the "NOT SET UP / No calendar yet" and "Forwarding 1 of 5 / Finish setup" cards do give a clear next action.
- `03-home-desktop-01.png`, "Last conversations" table:
  - Shows callers (Marcus Lee, Dana Whitfield) with no example label anywhere.
  - "This week" shows four 0 counters, while the list below has only weekday names ("Wednesday", "Tuesday"). An owner can't tell which week the activity is from.
  - Dana's row says "Thursday, Oct 23", but Oct 23, 2026 is a Friday.
- `04-messages-desktop-01.png` and `04-messages-phone-01.png`:
  - Every text is a raw textarea with code tokens (`{business_name}'s scheduling assistant`).
  - Each one carries a long footnote ("Uses a special character (—), so each text holds 70 characters").
  - There is no per-text reset, only "Standard wording."
  - The Booking confirmation box (`04-messages-phone-06.png`) is all tokens: `{service} on {when} at {location} … {invite_line} {calendar_links}`.
  - Plus: the lock line "STOP stays in. Carriers require the word STOP." protects opt-out.
- `04-messages-phone-01.png`:
  - Three fixed bars stack at the bottom (Save messages bar, Preview drawer, tab bar), covering about a quarter of a 390 px screen on a 12-screen page with no jump links.
  - Plus: the sticky "Save messages" bar is always reachable.
- `06-calendar-desktop-01.png` and `save-03-availability-phone.png`:
  - Home's "Set up" button leads to "Connecting a calendar from this page isn't turned on yet" and "Ask text_back to connect it", with no button or contact. That is a dead end.
  - "Next free times" claims to be "A real read of the calendar", yet sits beside "Test calendar" and offers "Mon, Oct 26 · 1:00–1:45 AM".
- `07-phone-desktop-01.png`, Checks card:
  - "1. A test call rang through — Done (Oct 19 …)" sits right above "2. Exactly one text went out — No call recorded yet".
  - Meanwhile "Your business number" is empty (placeholder only).
  - The page has two separate saves ("Save" and "Save checks").
- `save-01-messages-phone.png`, `save-02-scheduling-phone.png`, `save-04-phone-phone.png`: save banners exist ("Saved. New conversations use these messages from now on."). But they don't say what changed, and "Saved." on the Phone page says nothing at all.

**Portal Y**
- `03-home-desktop-01.png` and `03-home-phone-01.png`:
  - The headline "Not working yet: 1 step for you, 2 waiting on others." answers job 6 in five seconds.
  - Each setup card says who owns it ("Waiting on FluxWorks", "Needs you", "Waiting on phone companies").
  - Demo data carries EXAMPLE tags, and the banner says "This preview mixes example calls with real settings."
- `03-home-phone-03.png`, "This week's callers":
  - The "Wants to talk to you" row gives Marcus Lee big Call / Text buttons.
  - Dana's row says "Booked on test calendar", honest about where the booking went.
  - "The counts and the list below cover the same days" heads off any count-versus-list confusion.
- `04-messages-desktop-01.png`:
  - Texts show as real green bubbles in conversation order, with jump chips (Missed call / Questions / Booking / No reply / Steps back).
  - Each text has a "Customized" or "Standard wording" status, "Edit wording" and "Reset".
  - The network notice is explained in plain words, not by vendor name.
- `state-messages-unsaved-phone.png`: a sticky top bar shows "2 texts changed · Discard · Save". The edited card is marked "Unsaved" and shows "Was: What's the address for the job?". This is the best change-safety pattern in either portal.
- `05-schedule-desktop-01.png` and `save-02-schedule-length-90-phone.png`:
  - Every rule has a bold "Once saved: Applies right away, including customers mid-conversation."
  - The save banner repeats it: "You changed 'Appointment length'. Applies right away…"
  - The selected chip (90 min) is highlighted.
- `save-03-business-name-rename-offer-phone.png` and `save-07-owner-mobile-confirm-step-phone.png`:
  - After a rename it asks "1 text still says 'Oak & Pine Tree Care'. Update it to the new name?" with Update it / Leave it.
  - A mobile change becomes a two-step confirm, "nothing changes until you enter it", with "Keep my current mobile".
- `06-calendar-phone-01.png`: "No calendar yet — Waiting on FluxWorks … Until then, bookings go on a test calendar you can't see", next to a section titled "Test calendar, not yours". The not-connected state is explained honestly.
- `07-phone-desktop-03.png` and `07-phone-desktop-04.png`:
  - Carrier codes show in large monospace with Copy buttons and a "Turn it off" code.
  - "Is forwarding working?" checks are EXAMPLE-tagged, and the one thing the system can't see ("TextBack can't see answered calls, so this one is yours to tick") is a checkbox for the owner.

4. **Looks broken**

**Portal X**
- **Sidebar name cut off:** every desktop screen (e.g. `03-home-desktop-01.png`) shows "Oak & Pine Tre…".
- **Wrong weekday:** in `03-home-desktop-01.png`, "Thursday, Oct 23" falls on a Friday in 2026.
- **Dev link in a customer text (txt):** `04-messages-desktop.txt` shows raw dev links in the booking confirmation preview: "http://100.124.192.46:8003/a/1-000000000000/g".
- **Chip not highlighted:** in `05-scheduling-desktop-01.png` (60) and `save-02-scheduling-phone.png` (45), the field value's matching chip isn't highlighted.
- **Night-time, overlapping slots:**
  - `save-03-availability-desktop.png` offers "1:00–2:30 AM", "1:30–3:00 AM", "2:00–3:30 AM", labelled "A real read".
  - `save-03-availability-phone.png` shows the same thing with 45-minute slots.
- **Calendar dead end:** `06-calendar-desktop-01.png` says "Connecting a calendar from this page isn't turned on yet" and "Ask text_back to connect it" with no action. Home's "Set up" button ends here.
- **Contradictory checks:** `07-phone-desktop-01.png` shows check 1 "Done" next to check 2 "No call recorded yet", with the business number field empty.
- **Misleading placeholder:** the HELP-number placeholder "(704) 555-0123" contradicts the hint "Leave blank to show the texting number" (0100), in `07-phone-desktop-02.png` and `07-phone-phone-02.png`.
- **Stacked bottom bars:** three fixed bars stack on the phone in `04-messages-phone-01.png`.
- **No time on sign-in expiry:** `08-account-phone-01.png` says "Signed in until Oct 26, 2026", which is today's date with no time.

**Portal Y**
- **Awkward slot wording:** `state-calendar-not-connected-free-times-phone.png` reads "Mon, Oct 26 · starts at 3:30, 4:00 PM".
- **Mismatched intro sentence:** in `07-phone-desktop-01.png`, the "Numbers" section intro reads "This is the number customers call", but the section holds three numbers.
- Otherwise none seen.

5. **Three ideas from X (the lower-ranked portal) that Y should adopt**
- **Coloured status pills** for each caller (New / Handed off / Booked / In progress) in a scannable list, in `03-home-desktop-01.png`. Y's statuses are plain bold text.
- **A visible lock on the opt-out wording**, "STOP stays in. Carriers require the word STOP.", right on the STOP line, in `04-messages-desktop-01.png`. Y keeps STOP in a collapsed section.
- **Showing other calendar choices** ("Outlook / Microsoft 365" and "iCloud", available on request), in `06-calendar-desktop-01.png`, so an owner who doesn't use Google knows they're covered. Y should add this with a working "Text FluxWorks support" action rather than X's dead-end copy.

6. **Recommendation**

Portal Y wins clearly. It is the only one that tells the owner in one sentence whether the service works and whose move it is, and it labels every invented number. It shows texts the way customers see them, and it states the consequence of each change before and after saving. It also protects the two risky actions, a mobile change and a rename, with a confirm step and an update-the-texts offer. Portal X does have pages for every job, but its calendar setup is a dead end and it leaks `{tokens}`, "SignalWire", "text_back" and dev URLs to the owner. Before an owner sees Y, it must:
- fix the "starts at 3:30, 4:00 PM" slot wording;
- rewrite the "Numbers" intro so it covers all three numbers;
- add a jump or sticky control to the bottom of the 12-screen Messages page on phone;
- put Account in the phone navigation instead of only in the header dropdown.

VERDICT: WINNER Y
