**Judge identity:** Claude Opus 5.5 (`claude-opus-5-5`).

**Files opened:**
- Both `INDEX.md` files.
- Every `.txt` page-text file for home, messages, schedule/scheduling, calendar, phone and account on both portals.
- **Portal X, 42 images:** sign-in and enter-code on desktop and phone; home desktop 01–02 and phone 01–03; messages desktop 01, 02, 05, 09 and phone 01, 02, 06, 09, 12; `state-messages-edit-wording-phone`, `state-messages-unsaved-phone`, `save-01-messages-wording-phone`; schedule desktop 01–04, schedule phone 02, `state-schedule-set-hours-phone`, `save-02-schedule-length-90-phone`; calendar desktop 01, `state-calendar-not-connected-free-times-phone`, `state-calendar-connected-picker-phone`; phone desktop 01–03, phone phone 01 and 05, `state-phone-invalid-mobile-field-phone`, `save-03-business-name-rename-offer-phone`, `save-07-owner-mobile-confirm-step-phone`; account desktop and phone; `state-home-account-menu-phone`.
- **Portal Y, 30 images:** sign-in and enter-code on desktop and phone; home desktop 01 and phone 01–02; messages desktop 01, 02, 06, 10 and phone 01, 06; `save-01-messages-phone`, `save-01-messages-desktop`; scheduling desktop 01–03 and phone 01; `save-02-scheduling-phone`, `save-03-availability-phone`; calendar desktop 01 and phone 02; phone desktop 01–02 and phone 02; `save-04-phone-phone`, `save-05-checklist-desktop`; account desktop and phone.

**Confidence and limits:** High on the ranking, moderate on single points. I did not open every in-between scroll image. Portal X has many more state captures than Y, so I've seen more of X's error and confirmation states. I didn't hold the missing captures against Y. Y's raw-IP calendar links appear only in its page text; I didn't see them in a screenshot.

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | 5 | 4 | 92 |
| Y | 3 | 2 | 4 | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 56 |

## Portal X — observations
1. **Clear status on Home.** `03-home-desktop-01.png`: the headline "Not working yet: 1 step for you, 2 waiting on others." sits above a Setup timeline. Each card says who it's waiting on (Calendar "Waiting on FluxWorks", Call forwarding "Needs you", Texting approval "Waiting on phone companies") and has one action button. An owner knows within seconds whether the service works and what's theirs to do.
2. **Demo data is labelled everywhere.** There are EXAMPLE tags on each caller (`03-home-phone-03.png`), on the "This week" counts (`03-home-desktop-02.png`: EXAMPLE NUMBERS), on forwarding checks 1, 2 and 4 (`07-phone-desktop-03.png`, plus a footnote in `07-phone-phone-05.png`) and on the remembered device (`08-account-desktop-01.png`). The calendar page says plainly "Test calendar, not yours … These times are not from your calendar" (`06-calendar-desktop-01.png`).
3. **Strong feedback when saving.**
   - `state-messages-unsaved-phone.png`: a sticky top bar shows "2 texts changed" with Discard and Save. The card shows an "Unsaved" chip and a "Was:" line with the old wording.
   - `save-02-schedule-length-90-phone.png`: the confirmation repeats the consequence ("Applies right away, including customers mid-conversation").
   - `save-03-business-name-rename-offer-phone.png`: after a rename, it offers to update the one text that still uses the old name.
4. **Safety cues before saving.**
   - Every schedule rule has an "Once saved: …" line in bold (`05-schedule-desktop-01.png`, `-02.png`, `-03.png`).
   - A changed owner mobile goes through a confirm-by-code step ("until then codes still go to your current mobile"; `save-07-owner-mobile-confirm-step-phone.png`).
   - The STOP line is added automatically ("STOP line added for you", `04-messages-desktop-01.png`).
   - The danger text must mention 911, and a "What happens next" list explains the hand-off (`04-messages-desktop-09.png`).
5. **Friction: long pages.** The Messages page runs 12 phone screens (`04-messages-phone-01` to `-12`). The sticky "Jump to:" selector (`04-messages-phone-02.png`) helps. On phone, Account isn't in the bottom tab bar; it's only in the header business-name menu (`state-home-account-menu-phone.png`).
6. **Phone layout works well.** Phone fields are full width, tap targets are large, and buttons like "Confirm new mobile" and "Keep my current mobile" span the screen (`save-07-…-phone.png`). Inline errors are specific: "Enter your mobile as 10 digits, area code first." (`state-phone-invalid-mobile-field-phone.png`).

## Portal Y — observations
1. **Vendor plumbing shown to the owner.**
   - "[SignalWire Free Trial]" appears on Home ("CAMPAIGN IN REVIEW" card, `03-home-desktop-01.png`) and on every message's character note (`04-messages-desktop-01.png`).
   - `{business_name}`, `{invite_line}`, `{calendar_links}` and `{event_id}` chips sit under every text box (`04-messages-desktop-06.png`).
   - Every page footer reads "text_back · missed-call recovery", and the calendar page says "Ask text_back to connect it" (`06-calendar-desktop-01.png`).
2. **Demo data isn't labelled, and some is presented as real.**
   - The "Last conversations" table (`03-home-desktop-01.png`) shows Marcus Lee and Dana Whitfield with no example tag, while all four counts read 0.
   - The Checks card says "Steps 1, 2 and 4 are ticked from real calls recorded by the assistant" (`07-phone-desktop-02.png`).
   - "Next free times" is described as "A real read of the calendar" even though the card next to it says Test calendar (`06-calendar-desktop-01.png`).
3. **Calendar is a dead end.** The Home "No calendar yet" card has a green **Set up** button (`03-home-desktop-01.png`). It leads to "Connecting a calendar from this page isn't turned on yet." (`06-calendar-desktop-01.png`), with no button to contact support.
4. **Plain but generic save feedback.**
   - "Saved." (`save-04-phone-phone.png`), "Saved. New conversations use these hours and delays." (`save-02-scheduling-phone.png`), "Checks saved." (`save-05-checklist-desktop.png`).
   - There's no unsaved-changes indicator and no per-setting consequence text before saving.
   - Strengths: a sticky "Save messages" bar ("Edits apply to new conversations", `04-messages-desktop-01.png`), and an always-visible Default plus Reset on each rule (`05-scheduling-desktop-01.png`).
5. **Crowded phone screen while editing texts.** On Messages, three fixed bars stack at the bottom: the save bar, the "Preview ^" drawer and the tab bar (`04-messages-phone-01.png`). Together they cover about 370 of 844 px, so the owner edits through a small window.
6. **Ambiguous fields on the Phone page** (`07-phone-desktop-01.png`).
   - "Your business number" shows "(704) 555-0123" in grey placeholder text, and check 4 says "Enter your business number first." An owner can't tell the field is empty.
   - The HELP-number placeholder "(704) 555-0123" contradicts its own hint ("Leave blank to show the texting number", which is 555-0100).

## Looks broken
**Portal X**
- `04-messages-desktop-01.png`: the "Scroll for the rest" pill overlaps a cut-off "Thursday at 1(" customer bubble in the example phone.
- `save-03-business-name-rename-offer-phone.png`: the preview label reads "Oak & Pine Arborists" above a bubble that still says "Oak & Pine Tree Care". This is explained by the pending rename offer, but it looks inconsistent for a moment.
- Otherwise none seen.

**Portal Y**
- **Wrong weekday:** Dana's row says "Booked: tree removal on Thursday, Oct 23" (`03-home-desktop-01.png`), but Oct 23, 2026 is a Friday. The rows show "Wednesday" and "Tuesday" with no year, under "This week, since Monday, Oct 26" with all counts at 0.
- **Truncation:**
  - The business name is cut to "Oak & Pine Tre…" in the desktop sidebar on every page (`03-home-desktop-01.png`).
  - Message previews are cut mid-word ("yo…", "Th…") in `03-home-phone-02.png`.
  - On phone, the business name doesn't appear in the header at all.
- **Odd free times** (`save-03-availability-phone.png`): overlapping middle-of-night slots "Mon, Oct 26 · 1:00–1:45 AM / 1:30–2:15 AM / 2:00–2:45 AM", labelled "A real read" on a test calendar.
- **Dead end:** the Home "Set up" button leads to a calendar page where setup "isn't turned on yet" (`06-calendar-desktop-01.png`).
- **Leftover dev text:**
  - The footer "text_back · missed-call recovery" on every page.
  - Raw `http://100.124.192.46:8003/a/…` links in the preview booking text (seen in `04-messages-desktop.txt` only, not in a screenshot).
- **Wrong example copy:** the business-name hint quotes "Thanks for calling Oak & Pine Tree Care", which no text actually says (`07-phone-desktop-01.png`).
- **Account page** (`08-account-desktop-01.png`): "Signed in until Oct 26, 2026" gives no time. A "Sign out" heading sits over a "Sign out" button. There's no "sign out everywhere".
- **Selected value not shown:** the appointment-length preset chips don't highlight 60, even though 60 is set (`05-scheduling-desktop-01.png`).
- **Sign-in placeholder:** it shows the owner's actual mobile, "(980) 555-0123" (`01-sign-in-desktop-01.png`).

## Three ideas from Portal Y (ranked lower) that X should adopt
1. **List the calendars you support.** Cards for "Outlook / Microsoft 365" and "iCloud", each marked "Available on request" (`06-calendar-desktop-01.png`), tell the owner what's possible. X's calendar page only says "Waiting on FluxWorks."
2. **A compact setup row.** Y fits the setup status cards, each with a solid primary action button, into the first phone screen (`03-home-phone-01.png`). X's timeline needs about two phone screens before the counts appear.
3. **Two columns on the desktop Phone page.** Y puts the forwarding codes and the 5-step checks beside the number fields (`07-phone-desktop-01.png`), so the whole forwarding job fits on one screen. X stacks the same content over four desktop screens.

## Recommendation
Portal X wins clearly. It's the only portal that tells the owner honestly whether the service works, labels every invented number as an example, and states what each change will do before and after saving. It also covers all six jobs: sign-in and sign-out (including sign out everywhere), message editing, schedule rules, calendar status with a support action, numbers and forwarding with code-verified mobile changes, and the Home status. Portal Y has the same pages, but vendor names, raw `{tokens}`, unlabelled demo rows, a wrong date and a calendar dead end would confuse a non-technical owner. Before an owner sees X, fix the "Scroll for the rest" pill covering the example bubble, and add Account to the phone tab bar (or make the header menu's affordance clearer). Also shorten the 12-screen Messages page on phone, for example by collapsing the less-used fallback texts under "Most businesses never change these".

VERDICT: WINNER X
