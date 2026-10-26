## TextBack client portal bake-off: independent judge scorecard

### 1. Judge, files opened, confidence

- **Judge:** Claude Opus 5.5 (`claude-opus-5-5`).
- **Files opened:** Both `INDEX.md` files. Text files: X `03-messages-desktop.txt`, `04-business-desktop.txt`, `05-calendar-desktop.txt`; Y `03-home-desktop.txt`, `05-schedule-desktop.txt`, `06-calendar-desktop.txt`, `07-phone-desktop.txt`, `08-account-desktop.txt`, and a search of `04-messages-desktop.txt`.
- **Portal X, 27 images viewed:** both sign-in screens, the phone enter-code screen, messages desktop 01/02/04/05/07/09, messages phone 01/02/04/06/09/10/11/12, both business desktop/phone 01 plus phone 02, both calendar screens, and all six `save-*` files.
- **Portal Y, 35 images viewed:** sign-in, enter-code, home (desktop 01–02, phone 01 and 03), messages (desktop 01/04/09, phone 01/06/12), schedule (desktop 01–02, phone 02), phone page (desktop 01–04, phone 03), calendar phone, account phone, and 15 `state-*` and `save-*` files.
- **Confidence:** High on the overall ranking, medium-high on individual scores.
- **Limitations:** I didn't open every scroll position. Portal Y supplies far more state and save screens than X, so I saw more of its behaviour. I didn't penalise X for missing screenshots, only for missing pages. X's sign-out lives in a header avatar menu that was never captured open, so I couldn't verify it.

### 2. Scores

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 4 | 3 | 2 | 3 | 4 | 3 | 3 | 3 | 4 | 3 | 64 |
| Y | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | 4 | 4 | 90 |

### 3. Observations

**Portal X**
1. **Strength, messages page.** In `03-messages-desktop-01.png`, the "Your messages" page shows each text as a green bubble with a "1 text · 107 characters" count. The phone preview on the right is captioned "Sample conversation · nothing is sent · names invented". An owner can see exactly what customers receive.
2. **Leaked internal links.** The booking confirmation bubble in `03-messages-desktop-05.png` and `03-messages-phone-12.png` shows three raw `http://hermes-cloud.tailefb1a4.ts.net:8765/a/k7q2-ref/...` URLs. They take up six lines on a phone, and the page presents them as what customers get. That is vendor plumbing an owner should never see.
3. **Scope gaps.** The only pages are Messages, Business and Calendar (`04-business-desktop-01.png`). There is no place to set:
   - appointment length, working hours, quiet hours or reminder timing;
   - the business line or texting number;
   - call forwarding.

   There is also no status or home view. `05-calendar-phone-01.png` is a dead end: "No calendar connected … Connecting a calendar from this page is still being set up by FluxWorks", with no action button.
4. **Phone save is hard to reach.** On a phone, the messages page runs to 12 screens. The "No unsaved changes / Save changes" bar is not sticky; it appears only once, in `03-messages-phone-10.png`, after the last message card. An owner who edits Question 1 has to scroll about nine screens to save.
5. **Strength, mobile number change.** `save-03-owner-mobile-change-desktop.png` shows a two-step "Confirm your new mobile" flow with "Keep my current mobile" and "Send the code again". `save-04-keep-mobile-desktop.png` confirms with "Kept your current mobile." This is solid number-change safety.
6. **Stale preview.** In `save-04-keep-mobile-desktop.png` the Business name field reads "Oak & Pine Tree Care (desktop 043715)". The "IN THE FIRST TEXT" bubble directly below still says "Oak & Pine Tree Care", with no explanation. The save toast in `save-02-business-phone.png` is just "Saved." and doesn't say what changed.

**Portal Y**
1. **Strength, status at a glance.** `03-home-desktop-01.png` opens with "Not working yet: 1 step for you, 2 waiting on others." Below it are Setup cards for Calendar ("Waiting on FluxWorks"), Call forwarding ("Needs you", with a "Finish forwarding" button) and Texting approval. This is the only portal where an owner can see within five seconds whether the service works.
2. **Strength, demo data is labelled everywhere.** EXAMPLE badges appear on every invented item:
   - the counts header ("EXAMPLE NUMBERS") and each caller name in `03-home-desktop-02.png`;
   - the forwarding checks in `07-phone-desktop-03.png`, plus the footnote "In this preview, checks 1, 2 and 4 come from example calls" in `07-phone-desktop-04.png`;
   - the calendar section titled "Test calendar, not yours" in `state-calendar-not-connected-free-times-phone.png`.
3. **Strength, consequences stated before saving.** On the schedule page (`05-schedule-desktop-01.png`, `05-schedule-desktop-02.png`):
   - "Once saved: Applies right away, including customers mid-conversation."
   - "Bookings already made stay as they are."
   - Each rule shows its default, with a Reset link.

   The save toast in `save-02-schedule-length-90-phone.png` repeats the consequence.
4. **Strength, editing feedback.** In `state-messages-unsaved-phone.png` a sticky top bar reads "2 texts changed" with Discard and Save. The edited card shows an "Unsaved" badge and a "Was:" line with the old wording. `state-messages-unsaved-top-desktop.png` notes that a STOP line will be added if the owner leaves it out.
5. **Strength, rename offer.** `save-03-business-name-rename-offer-desktop.png` handles a rename honestly: "1 text still says 'Oak & Pine Tree Care'. Update it to the new name?" with "Update it" and "Leave it" buttons. This is the same situation X leaves stale.
6. **Friction, Account on phone.** The phone bottom bar has five tabs and no Account tab. On `08-account-phone-01.png` no tab is highlighted, and the page is reachable only through the business-name menu in the header (`state-home-account-menu-phone.png`). The phone messages page is also long (12 scroll positions), though the sticky "Jump to: Booking" selector in `04-messages-phone-06.png` helps.

### 4. Looks broken

**Portal X**
- Raw internal-host `http://` URLs inside the customer booking text: `03-messages-desktop-05.png`, `03-messages-phone-06.png`, `03-messages-phone-12.png`.
- The "IN THE FIRST TEXT" preview contradicts the saved business name: `save-04-keep-mobile-desktop.png`, `save-02-business-phone.png`.
- The Calendar page is a dead end with no action: `05-calendar-desktop-01.png`, `05-calendar-phone-01.png`.
- The Save bar isn't sticky on the 12-screen phone messages page; it appears only in `03-messages-phone-10.png`.
- The jump-chip row is cut off at "No reply" on the right edge with no scroll cue: `03-messages-phone-01.png`.
- The header business name is truncated to "Oak & Pine Tree Care (…": `save-01-messages-phone.png`.
- Sign-in says "Business mobile" (`01-sign-in-desktop-01.png`) while the Business page says "Your mobile" (`04-business-desktop-01.png`).

**Portal Y**
- The sign-in error field shows a green focus ring wrapped around a red error border, a double outline: `state-sign-in-error-phone.png`.
- The "Scroll for the rest" pill sits on top of a clipped "Thursday at 10" bubble in the preview: `04-messages-desktop-01.png`, `04-messages-desktop-04.png`.
- On the Account page no bottom tab is active, and Account has no phone tab: `08-account-phone-01.png`.
- "Your business number" is an editable field even though its help text says "TextBack never changes it", so it's unclear whether the owner should edit it: `07-phone-desktop-02.png`.

### 5. Three ideas from Portal X (lower ranked) that Y should adopt
1. **Name the character that raises the cost.** X says "Billed as 2 texts. The '—' symbol limits each text to 70 characters." (`03-messages-phone-09.png`). That tells the owner which character to remove to cut the cost.
2. **Mark where texting stops.** X puts a "Texts stop here" marker under the last reminder (`03-messages-desktop-07.png`), so the end of the reminder sequence is visible in the flow itself.
3. **Use a visible chip row to jump between sections on phone.** X shows Missed call / Questions / Booking / No reply chips at the top of the phone page (`03-messages-phone-01.png`). That's one tap to a section, versus opening Y's "Jump to" dropdown. Add a scroll cue so the cut-off chip doesn't look broken.

### 6. Recommendation
Portal Y wins clearly. It covers all six owner jobs: a Home status page, Messages, Schedule, Calendar, Phone & business with call forwarding, and Account. Portal X has no scheduling rules, no forwarding or numbers, no status view, and its calendar page is a dead end. Y also does better on trust:
- every demo item carries an EXAMPLE label;
- every rule says when a change takes effect and for whom;
- edits show the old wording and sit behind a sticky Discard/Save bar.

Before an owner sees Y, it should:
- give Account a tab (or an obvious entry) in the phone bottom bar;
- stop the "Scroll for the rest" pill covering the preview bubble;
- fix the double focus/error ring on sign-in;
- make clear whether the business number can be edited;
- shorten the 12-screen phone Messages page, for example by collapsing the fallback texts by default.

VERDICT: WINNER Y
