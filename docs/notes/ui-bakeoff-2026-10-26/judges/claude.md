## 1. Judge identity, evidence, confidence

- **Judge:** Claude Opus 5.5 (`claude-opus-5-5`).
- **Portal X files opened:** 28 images and 7 text files.
  - Images: `01-sign-in-phone-01`, `02-enter-code-phone-01`, `03-home-phone-01/02`, `03-home-desktop-01`, `04-messages-phone-01/02/06/12`, `04-messages-desktop-01`, `05-scheduling-phone-01/02/03`, `05-scheduling-desktop-01`, `06-calendar-phone-02`, `07-phone-phone-01/02/03`, `07-phone-desktop-01`, `08-account-phone-01`, `save-01-messages-phone/desktop`, `save-02-scheduling-phone/desktop`, `save-03-availability-phone/desktop`, `save-04-phone-phone`, `save-05-checklist-desktop`.
  - Text: `INDEX.md` plus the phone `.txt` for home, messages, scheduling, calendar, phone and account.
- **Portal Y files opened:** 24 images and 4 text files.
  - Images: `01-sign-in-phone-01`, `01-sign-in-desktop-01`, `02-enter-code-phone-01`, `03-messages-phone-01/02/04/05/07/09/10/12`, `03-messages-desktop-01/04/06/09`, `04-business-phone-01/02`, `04-business-desktop-01`, `05-calendar-phone-01`, `save-01-messages-phone/desktop`, `save-02-business-phone`, `save-03-owner-mobile-change-desktop`, `save-04-keep-mobile-desktop`.
  - Text: `INDEX.md` plus the phone `.txt` for messages, business and calendar.
- **Confidence: medium-high.** I viewed every image I cite. For the long Messages pages I sampled the scroll positions rather than opening all 9–12, and filled the gaps from the `.txt` files.
- **Limits:**
  - Y's account menu is never shown open, so I can't confirm where Y's sign-out is.
  - Neither portal shows the "Edit wording" or "Set hours" panels opened.
  - The test harness's edits (e.g. "(desktop 043715)", "Where is the job? (desktop)") are test inputs, not design defects.

## 2. Scores

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 4 | 2 | 5 | 4 | 3 | 4 | 2 | 4 | 4 | 3 | 70 |
| Y | 4 | 4 | 2 | 4 | 4 | 3 | 3 | 4 | 5 | 3 | 72 |

## 3. Observations

### Portal X
1. **Strength, orientation (`03-home-phone-01`):** Home opens with three status cards: "NOT SET UP – No calendar yet" with a **Set up** button, "NEEDS ATTENTION – Forwarding 1 of 5" with **Finish setup**, and "Messaging registration". Within seconds an owner knows what's broken and where to tap. Y has nothing like it.
2. **Strength, scheduling (`05-scheduling-phone-01/03`):** Every rule shows "Default: …" plus a **Reset** link: appointment length (with 30–120 min quick picks), time zone, working hours, quiet hours, first nudge, last nudge, close the lead. Caveats are plain: "A nudge that is already scheduled keeps its time." `save-02-scheduling-phone` confirms with "Saved. New conversations use these hours and delays."
3. **Strength, numbers and forwarding (`07-phone-phone-02/03`):**
   - Business number, texting number and mobile each have a **Verify** button.
   - The mobile hint says "Changing it texts a code to the new number first."
   - There is a carrier picker (Verizon/T-Mobile/AT&T/Cricket/Other) and a warning: "Only forward busy and unanswered calls."
   - A five-step **Checks** list, with steps 1, 2 and 4 "ticked from real calls."
   - This is the only portal that covers job 5 in full.
4. **Failure, jargon (`04-messages-phone-01/02/06`):**
   - Every message card carries "Includes the '[SignalWire Free Trial]' tag until registration completes."
   - Every card shows a "Business name {business_name}" chip, even under texts that don't use it ("The job", "Safety hand-off").
   - The Confirmation card lists raw tokens such as `{invite_line}`, `{calendar_links}` and `{event_id}` (`04-messages-phone.txt`).
   - Home says "CAMPAIGN IN REVIEW" (`03-home-phone-01`); the Calendar cards say "Ask text_back to connect it" (`06-calendar-phone-02`).
   - A non-technical owner reads vendor plumbing on every screen.
5. **Failure, honesty (`03-home-phone-02`):**
   - "Last conversations" shows named customers (Marcus Lee, Dana Whitfield) with no sample label.
   - It sits directly under "This week · Since Monday, Oct 26" with every counter at 0, yet the rows say "Wednesday 2:40 PM" and "Tuesday 1:55 PM".
   - `03-home-desktop-01` shows "Booked: tree removal on Thursday, Oct 23". Oct 23, 2026 is a Friday.
6. **Failure, calendar (`save-03-availability-phone`):** "Next free times" is subtitled "A real read of the calendar the assistant books on." It is a test calendar, and it offers "Mon, Oct 26 · 1:00–1:45 AM", then 1:30 AM, then 2:00 AM: overlapping middle-of-the-night slots. They come from the default "Any day, any time" working hours (`05-scheduling-phone-02`). An owner would see the assistant offering customers 1 AM appointments.
7. **Friction, phone Messages page (`04-messages-phone-01`):** The sticky "Save messages" bar, the "Preview" drawer and the bottom nav stack into roughly a fifth of the screen. The 12-screen page has no jump links.

### Portal Y
1. **Strength, messages as a timeline (`03-messages-phone-01/02`):**
   - Messages are a numbered story: Missed call → The questions → Booking → No reply → Owner steps in.
   - Each text is a green bubble with "1 text · 75 characters".
   - Each card shows a status badge ("Customized" or "✓ Standard wording") and a per-message **Reset**.
   - Jump chips (Missed call, Questions, Booking, No reply…) scroll sideways.
   - This is the clearest Messages page of the two.
2. **Strength, plain cost and opt-out cues (`03-messages-phone-07`):** "STOP line added for you", plus an amber warning "Billed as 3 texts. The '—' symbol limits each text to 70 characters" with a three-segment meter. The unexpected cost is stated in plain words. START/HELP/STOP sit in a collapsed section: "Required by phone companies. Most businesses never change these." (`03-messages-phone-10`).
3. **Strength, safe mobile change (`save-03-owner-mobile-change-desktop`):**
   - The change is a two-step flow: "Details saved" → "Confirm number".
   - Copy: "We texted a six-digit code to (980) 555-0199 … until then codes still go to your current mobile."
   - There is a **Keep my current mobile** escape, which leads to the toast "Kept your current mobile." (`save-04-keep-mobile-desktop`).
   - The save toast names what changed: "Saved. Changed: Question 2: the location." (`save-01-messages-phone`).
   - The sample conversation is labelled "Sample conversation · nothing is sent · names invented" (`03-messages-phone-12`).
4. **Failure, scope:** Y has only three pages: Messages, Business, Calendar.
   - No appointment length, working hours, quiet hours or reminder timing. "Sent after the first follow-up delay" (`03-messages-desktop-06`) refers to a setting the owner cannot reach.
   - No business line, no texting-number setting and no call-forwarding setup (`04-business-phone-02`).
   - No status overview of whether the service works.
   - Jobs 3 and 6, plus half of job 5, have no home.
5. **Failure, leftover dev URLs (`03-messages-phone-05`, `03-messages-phone-12`):** The booking-confirmation bubble contains `http://hermes-cloud.tailefb1a4.ts.net:8765/a/k7q2-ref/g` three times. That is the text customers would receive.
6. **Failure, business name not used (`save-04-keep-mobile-desktop`, `save-02-business-phone`):** The name is saved as "Oak & Pine Tree Care (desktop 043715)", yet the "IN THE FIRST TEXT" preview right below still says "Hey, this is Oak & Pine Tree Care." The field claims to be "Used in every text customers get", but the customized first text hard-codes the name.
7. **Friction, save placement (`03-messages-phone-10`):** "Save changes" sits at the end of a 12-screen page and is not sticky. On desktop the sidebar nav scrolls away with the page (`03-messages-desktop-04` shows an empty left rail).

## 4. Looks broken

**Portal X**
- `save-03-availability-phone` / `-desktop`: offers overlapping 1 AM–3:30 AM slots, labelled "A real read" of a test calendar.
- `03-home-phone-02` / `03-home-desktop-01`: counters say 0 this week while undated "Wednesday" and "Tuesday" conversations sit below them.
- `03-home-desktop-01`: "Thursday, Oct 23" is the wrong weekday.
- `07-phone-phone-03`, `save-05-checklist-desktop`: check 1 says "A test call rang through · Done", while check 2 says "No call recorded yet". The checks also mix circles and squares without explaining the difference.
- `05-scheduling-phone-01`, `save-02-scheduling-phone`: the length field reads 60 (later 45), but the matching quick-pick chip is not highlighted.
- `03-home-desktop-01` and every X desktop shot: the sidebar truncates the name to "Oak & Pine Tre…", and the footer shows "text_back".
- `04-messages-phone-02/12`: the "Business name {business_name}" chip appears under texts that don't contain the token.

**Portal Y**
- `03-messages-phone-05/12`: tailnet dev URLs in the customer confirmation text.
- `save-02-business-phone`, `save-04-keep-mobile-desktop`: the business-name change is not reflected in the "IN THE FIRST TEXT" preview.
- `save-01-messages-phone`: the header truncates to "Oak & Pine Tree Care (…".
- `01-sign-in-phone-01`: the field is labelled "Business mobile" with placeholder 704 555 0123 (the business line's area code). The Business page calls the sign-in number "Your mobile", (980) 555-0123.
- `03-messages-phone-12`: a "Booked · on your calendar" chip appears while the Calendar page says "No calendar connected".
- `03-messages-desktop-04/06`: the desktop nav scrolls away, leaving an empty sidebar.

## 5. Three ideas Y should adopt from X

1. **Home status cards:** each problem gets a **Set up** / **Finish setup** button and a forwarding progress count. See `X/03-home-phone-01`.
2. **Scheduling page with "Default: …" and Reset on every rule:** length quick-picks, quiet hours with a "No quiet hours" switch, and the three nudge delays. See `X/05-scheduling-phone-01`, `X/05-scheduling-phone-03`.
3. **Forwarding setup with carrier picker and five live checks:** includes the forward-all warning. See `X/07-phone-phone-02`, `X/07-phone-phone-03`.

## 6. Recommendation

Y wins on the rubric, but only by 72 to 70. X misses the ideal on coverage alone; Y loses there and wins on plain language, honesty, phone layout and visual polish. An owner reading Y understands every text the customer gets, sees cost and opt-out warnings in plain words, and cannot lock themselves out when changing their mobile. X buries the same jobs under SignalWire tags, `{event_id}` tokens, unlabelled fake customers and 1 AM "real" availability.

The margin is narrow because Y is missing half the product. Before any owner sees it, Y must:
- add a Scheduling page, a Numbers & Forwarding page and a Home status page, modelled on X's;
- strip the `hermes-cloud…ts.net` links from the confirmation text;
- make the business name actually flow into the first text;
- make the Save bar sticky on the long Messages page.

VERDICT: WINNER Y
