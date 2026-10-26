Judge: **Codex (GPT-6)**. I opened **41 images for X and 61 for Y**, covering all eight pages at both widths, all twelve phone Messages captures per portal, and save/state screenshots. I also opened both `INDEX.md` files and the desktop page-text files: X pages 03–08 and Y pages 01–08. Specific opened files are cited below.

Confidence: **high on the visual comparison; moderate on functionality**. Screenshots demonstrate interface states, not successful live delivery, calendar integration, or persistence. I performed no interactions or external research. Neither portal loses points simply for having no connected Google account.

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 4 | 2 | 4 | 3 | 4 | 3 | 2 | 3 | 4 | 3 | 64 |
| Y | 4 | 4 | 4 | 4 | 4 | 4 | 5 | 5 | 4 | 4 | 84 |

Both provide findable places for the six owner jobs. Calendar connection remains incomplete as a self-service task: X says connecting is unavailable; Y provides a support route and additional example states for choosing and checking a connected calendar.

**Portal X observations**

- **Efficient overview:** `X/03-home-desktop-01.png` puts setup problems, weekly totals, and recent conversations in one viewport. The owner can scan the business’s apparent status quickly, although the unlabelled examples undermine its reliability.
- **Accessible basic controls:** `X/01-sign-in-phone-01.png` has a clear mobile field and large “Text me a code” button. `X/08-account-phone-01.png` provides an obvious Sign out button and a direct link to change the sign-in number.
- **Too much technical detail in editing:** `X/04-messages-phone-07.png` devotes most of the screen to tokens such as `{calendar_links}`, `{invited_email}`, and `{event_id}`. An owner must navigate implementation vocabulary to adjust customer wording.
- **Useful persistent actions, crowded working space:** `X/04-messages-phone-01.png` keeps Save messages, Preview, and navigation available. Those three bottom layers consume substantial screen space, while the long form has no visible section jump control.
- **Good defaults and change explanation:** `X/05-scheduling-phone-03.png` places defaults and Reset beside reminder settings and explains that an already scheduled nudge keeps its time. However, Save is at the bottom rather than persistently available.
- **Some strong safety cues:** `X/04-messages-phone-02.png` explicitly protects STOP; `X/07-phone-phone-02.png` says changing the owner mobile sends a verification code first. The supplied screenshots do not demonstrate completion of that verification.
- **Uneven feedback:** `X/save-01-messages-phone.png` explains that saved wording applies to new conversations. `X/save-04-phone-phone.png` only says “Saved,” leaving the owner to infer which details changed.

**Portal Y observations**

- **Actionable setup status:** `Y/03-home-phone-01.png` leads with “Not working yet: 1 step for you, 2 waiting on others.” Its cards distinguish “Needs you” from “Waiting on FluxWorks,” making responsibility clearer.
- **Examples are unmistakable:** `Y/03-home-desktop-02.png` labels totals and callers as examples and identifies a booking as being on the test calendar. `Y/07-phone-phone-04.png` also labels simulated forwarding checks.
- **Customer wording comes first:** `Y/04-messages-phone-01.png` shows the rendered text, an Edit wording control, Reset, and a section jump menu. `Y/state-messages-edit-wording-phone.png` offers a plain “Business name” insertion control instead of exposing a token catalog.
- **Changes are reviewable:** `Y/state-messages-unsaved-top-phone.png` shows “2 texts changed,” Discard, Save, and the previous wording. `Y/save-01-messages-wording-phone.png` identifies the specific message saved.
- **Consequences are explicit:** `Y/05-schedule-phone-01.png` explains that appointment-length changes affect customers already mid-conversation. `Y/05-schedule-phone-03.png` separately reassures the owner that existing bookings retain their settings.
- **Number changes have a clear recovery path:** `Y/state-phone-confirm-new-mobile-phone.png` identifies the destination number, code expiry, when sign-in changes, and “Keep my current mobile.” `Y/state-phone-invalid-mobile-phone.png` explains that other edits remain and nothing was saved.
- **Business renaming handles existing wording:** `Y/save-03-business-name-rename-offer-phone.png` identifies a text still containing the old name and offers Update it or Leave it. `Y/save-04-rename-texts-updated-phone.png` confirms the update.
- **Excessive length remains:** `Y/05-schedule-phone-01.png` through `Y/05-schedule-phone-05.png`, and `Y/07-phone-phone-01.png` through `Y/07-phone-phone-05.png`, show substantial scrolling. Generous spacing, nested cards, and repeated explanations make routine settings slower to scan.
- **Saving disrupts location:** `Y/save-06-forwarding-tick-phone.png` confirms a checklist change but shows the top of Phone & business, far from the checklist. The feedback is specific, but the owner loses their place.

**Looks broken**

For X:

- `X/03-home-desktop-01.png`: Dana’s booking says **“Thursday, Oct 23.”** October 23, 2026 is Friday.
- `X/03-home-desktop-01.png`: seeded callers, counts, and registration status appear without example labels. They look like operational business data.
- `X/07-phone-phone-03.png`: the checklist explicitly claims checks come from **“real calls”**, despite the supplied preview context.
- `X/07-phone-phone-03.png`: check 1 records a test call, while check 2 says **“No call recorded yet.”** The unexplained contradiction makes troubleshooting harder.
- `X/06-calendar-desktop-01.png` and `X/save-03-availability-phone.png`: “A real read” of availability sits alongside “No real calendar is connected” and “Bookings aren’t recorded anywhere yet.” The test results need an unambiguous explanation.
- `X/03-home-phone-01.png` and `X/06-calendar-phone-01.png`: Home offers **Set up**, but Calendar says connecting is not turned on and provides no actionable connection/support control. This is a visible setup dead end.
- `X/05-scheduling-phone-02.png`: **“No texts between”** contradicts the nearby explanation that first texts and active replies still go out immediately.
- `X/03-home-desktop-01.png`: the business identity is truncated to **“Oak & Pine Tre…”**. `X/03-home-phone-02.png` truncates every conversation excerpt, with no visible expansion affordance.
- `X/08-account-desktop-01.png`: desktop copy repeatedly calls the device “this phone.” Its date-only expiry also omits the time needed to understand a 12-hour session.

For Y: **none seen that establishes a broken control, incorrect date, horizontal clipping, or unintended overlap.** The long pages and post-save return to the top are usability shortcomings described above. Actual button behavior remains unverified.

**Three ideas Y should adopt from X**

1. **A more compact status overview** — `X/03-home-desktop-01.png` makes setup and recent activity visible together. Y should retain its example labels and responsibility cues while reducing vertical spread.
2. **A persistent phone preview entry point** — `X/04-messages-phone-01.png` keeps Preview available beside editing. Y could use a compact equivalent to reduce travel between its editor and end-of-page example conversation.
3. **Availability with end times** — `X/save-03-availability-phone.png` shows complete intervals such as “1:00–1:45 AM.” Y’s availability results would be easier to assess if they showed the full appointment block.

Choose **Portal Y**. Its clearer wording, labelled examples, explicit change consequences, and demonstrated verification states make it substantially easier for an owner to understand and trust. Before an owner sees it, shorten the Schedule and Phone pages and keep save confirmation near the setting just changed. Also make the exact network notice inspectable in the message preview so owners can review the complete customer-facing text.

VERDICT: WINNER Y