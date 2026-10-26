# TextBack client portal bake-off: judge scorecard

## 1. Judge identity, evidence and limits
- **Judge:** Claude Opus 5.5 (`claude-opus-5-5`).
- **Images opened:** I viewed every image below myself.
  - **Portal X:** 45 of about 95. This covers sign-in, enter-code, Home, Messages, Schedule, Calendar, Phone and Account, plus most state screens on both widths.
  - **Portal Y:** 28 of 44. This covers both sign-in screens, Messages desktop 01/02/04/05/07/09, Messages phone 01/02/06/09/10/12, Business desktop and phone, Calendar desktop and phone, and all six `save-*` screens.
- **Text files read:** both `INDEX.md` files; X `03-home`, `05-schedule`, `06-calendar`, `07-phone` and `08-account` (desktop); Y `03-messages`, `04-business` and `05-calendar` (desktop). I also searched X's Messages text to check whether Y's ideas already exist in X.
- **Limits:**
  - I did not open every intermediate scroll screen. Mid-page Messages scrolls on both portals and some X carrier and toast states are unseen.
  - No image of Y's account menu exists, so I can't confirm Y has a sign-out.
  - Confidence is high on the verdict and moderate on small finish details.

## 2. Scores

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 5 | 4 | 5 | 5 | 4 | 5 | 5 | 5 | 4 | 4 | 92 |
| Y | 3 | 3 | 2 | 3 | 4 | 3 | 4 | 3 | 4 | 2 | 62 |

## 3. Observations

### Portal X
1. **Home status (`03-home-desktop-01.png`):** The headline "Not working yet: 2 steps left." sits above "Calendar · Needs you · Connect calendar" and "Call forwarding · Needs you · 3 of 5 checks done · Finish forwarding". An owner knows within five seconds that the service isn't live and which button to press. This is the only portal that answers job 6.
2. **Call forwarding setup (`07-phone-desktop-02.png`, `07-phone-desktop-03.png`, `07-phone-phone-03.png`):**
   - A warning reads "Only forward busy and unanswered calls. Forwarding every call stops answered calls from reaching you."
   - Carrier chips (Verizon, T-Mobile, AT&T, Cricket, Other) change the dial code, e.g. `*71 704 555 0100`, which has a Copy button. The `*73` turn-off code also has one.
   - A 5-step "Is forwarding working?" checklist marks the example-sourced checks EXAMPLE. This covers job 5 fully; Y has no equivalent.
3. **Schedule rules (`05-schedule-desktop-01.png`, `state-schedule-any-time-warning-desktop.png`, `state-schedule-saved-toast-desktop.png`):**
   - Every rule shows "Default: …" with its own Reset.
   - Choosing "Any day, any time" raises a warning, "Customers can be offered times like 1 AM. Set your hours.", with a one-tap "Use Mon–Fri, 8 AM–5 PM" button.
   - The save banner says when the change takes effect: "It applies now, including customers mid-conversation."
4. **Phone save bar (`state-messages-unsaved-bar-phone.png`, `state-schedule-unsaved-bar-phone.png`):** A sticky bar ("2 texts changed / 1 rule changed · Discard · Save") sits above a 5-tab bottom nav. On `04-messages-phone-06.png` the section chips (Missed call, Questions, Booking, No reply) stay pinned under the header. Long pages stay manageable on a phone.
5. **Business rename (`state-phone-rename-offer-desktop.png`):** After renaming, the banner says "2 texts still say 'Oak & Pine Tree Care'. Update them to the new name?" with "Update them" and "Leave them". This catches stale wording that Y silently leaves behind.
6. **Sign-out and mobile change:**
   - `state-account-sign-out-phone.png`: "Sign out everywhere" asks "You'll need a new code on each one" before acting.
   - `state-phone-confirm-mobile-phone.png`: a new mobile must be confirmed by code, with a "Keep my current mobile" way out.
   - `state-phone-invalid-mobile-phone.png`: the error reads "Enter your mobile as 10 digits, area code first."
7. **Friction (`04-messages-desktop-01.png`):** The intro stacks two info notes, a chip row and a timeline before the first text. It is accurate but dense. "Steps back" and "Stepped back" (Home stats) are odd terms for an owner.

### Portal Y
1. **Messages page (`03-messages-desktop-01.png`):** It is clear and attractive. It has a timeline of texts, a "Customized" badge, "STOP line added for you · 1 text · 107 characters", and a sticky "Conversation preview" with a "Books a job" picker labelled "Sample conversation · nothing is sent · names invented". Job 2 is handled well.
2. **Leaked dev links (`03-messages-desktop-05.png`, `03-messages-phone-12.png`):** The booking confirmation customers receive shows raw links: `http://hermes-cloud.tailefb1a4.ts.net:8765/a/k7q2-ref/g` (also `/o` and `/i`). That is internal vendor plumbing in a customer-facing text, wrapping mid-token over about 10 lines on a phone. An owner would reasonably worry that this is what customers get.
3. **Missing jobs:**
   - The only pages are Messages, Business and Calendar (`03-messages-phone-01.png` bottom nav).
   - There is no page for appointment length, working hours, quiet hours or reminder timing (job 3).
   - There is no business-line field and no call-forwarding setup (job 5 is partial; `04-business-desktop-01.png` has only name, HELP number and mobile).
   - There is no "is it working" status (job 6).
4. **Calendar dead end (`05-calendar-desktop-01.png`):** The "Test mode · No calendar connected" card is honestly labelled. But it ends at "Connecting a calendar from this page is still being set up by FluxWorks." There is no button, no contact action and no next step.
5. **Save confirmation, good and bad:**
   - Good (`save-01-messages-desktop.png`): the toast names what changed, "Saved. Changed: Question 2: the location."
   - Good (`save-03-owner-mobile-change-desktop.png`): a new mobile goes through a two-step "Details saved → Confirm number" flow with "Keep my current mobile".
   - Bad (`save-02-business-desktop.png`): after the name is saved as "Oak & Pine Tree Care (desktop 043715)", the "IN THE FIRST TEXT" preview still reads "Hey, this is Oak & Pine Tree Care." Nothing warns the owner.
6. **Phone save placement (`03-messages-phone-10.png`):** "No unsaved changes · Save changes" sits in the page flow after the START, HELP and STOP section. It is not sticky. An owner who edits Question 1 has to scroll about nine screens to save. The section chips also aren't sticky: they're gone by `03-messages-phone-02.png`.

## 4. Looks broken

**Portal X**
- **Enabled Save with nothing to save** (`04-messages-desktop-08.png`, `07-phone-desktop-04.png`): a solid green "Save" sits next to "No unsaved changes".
- **Off-grid section headings** (`03-home-desktop-01.png` "Setup", `07-phone-desktop-03.png` "Is forwarding working?"): they use a dash marker instead of a timeline circle and sit about 8 px left of every other section heading.
- **Contradictory calendar copy** (`06-calendar-desktop-01.png`): "Google asks you to let TextBack see and edit your calendars" is followed by "TextBack sees your calendars only."
- **Clipped chip row** (`04-messages-phone-06.png`, `state-messages-edit-open-phone.png`): "No reply" is cut at the right edge and "Steps back" is off-screen, with no scroll cue.
- **Missing chip row** (`state-messages-unsaved-bar-phone.png`): the chips are absent below the intro in this state, though they show in `04-messages-phone-01.png`.
- **No unsaved bar after an edit** (`state-schedule-custom-length-phone.png`): 50 minutes is entered with Custom selected, but no unsaved bar shows. Compare `state-schedule-unsaved-bar-phone.png`.
- **Booked state looks unchanged** (`state-messages-example-booked-desktop.png`): it is visually the same as the default view. The preview still opens at the first text, so the "booked" state isn't evident.

**Portal Y**
- **Raw dev URLs in a customer text** (`03-messages-desktop-05.png`, `03-messages-phone-06.png`, `03-messages-phone-12.png`): `hermes-cloud.tailefb1a4.ts.net:8765` links appear in the booking confirmation.
- **Stale name preview** (`save-02-business-desktop.png`, `save-02-business-phone.png`): the first-text preview keeps the old business name after the name is saved.
- **Truncated header name** (`save-01-messages-phone.png`, `save-02-business-phone.png`): it shows as "Oak & Pine Tree Care (…".
- **Calendar dead end** (`05-calendar-desktop-01.png`, `05-calendar-phone-01.png`): there is no action at all.
- **Clipped, non-sticky chips** (`03-messages-phone-01.png`): "No reply" is clipped at the right edge, and the chips don't stay pinned.
- **Inconsistent label** (`01-sign-in-desktop-01.png` vs `04-business-desktop-01.png`): sign-in says "Business mobile", the Business page says "Your mobile".
- **Past sample date** (`03-messages-desktop-05.png`): the booking says "Thursday, Oct 22", which is already past against the Mon, Oct 26 preview date.

## 5. Three ideas from Y (the lower-ranked portal) that X should adopt
1. **Disabled Save when nothing changed** (`03-messages-desktop-09.png`): "No unsaved changes" sits next to a greyed-out "Save changes", so the button's state matches the words. That fixes X's always-green Save.
2. **Owner-centred section name** (`03-messages-desktop-07.png`): "Owner steps in — When a text needs you, automated scheduling pauses and you get a lead." This is clearer to an owner than X's "Steps back" / "Stepped back".
3. **Inline outcome chip on the booking text** (`03-messages-desktop-05.png`): a "Booked · on your calendar" chip under the booking confirmation tells the owner what has actually happened when that text is sent.

## 6. Recommendation
Portal X wins clearly. It is the only one that covers all six owner jobs: its Schedule page, call-forwarding setup with carrier codes and a checklist, and "Not working yet: 2 steps left" Home have no equivalent in Y. It also labels every invented number EXAMPLE and adds safeguards before risky changes: the 1 AM warning, mobile confirmation, the sign-out-everywhere confirm, and the rename offer. Y's Messages page is polished, but it has three serious problems:
- it sends customers raw `hermes-cloud…ts.net:8765` links;
- its Calendar page is a dead end;
- it has no scheduling rules or forwarding setup at all.

Before an owner sees X, it must:
- disable Save when nothing has changed;
- align the dash-marker headings ("Setup", "Is forwarding working?") to the timeline;
- fix the "see and edit / sees only" calendar contradiction;
- add a scroll cue to the clipped phone chip row;
- rename "Steps back" to owner language.

VERDICT: WINNER X
