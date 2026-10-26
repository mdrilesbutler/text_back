Judge: **Codex (GPT-6)**. I opened **56 images from X and 27 from Y**, including every numbered phone screenshot, desktop examples of each signed-in page, and save/error/verification states. I also opened both `INDEX.md` files and phone page-text files. Confidence is high for visible layout and coverage, moderate for functionality: screenshots demonstrate states, but cannot establish that buttons, persistence, authentication or calendar connections work. I did not inspect every desktop/state variant or access anything outside this folder.

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 5 | 4 | 5 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | 88 |
| Y | 4 | 3 | 2 | 3 | 4 | 3 | 3 | 3 | 4 | 3 | 64 |

**Portal X observations**

- **An actionable starting point.** `X/03-home-phone-01.png` leads with “Not working yet: 2 steps left,” followed by “Connect calendar” and “Finish forwarding.” An owner can identify the outstanding work immediately. `X/03-home-phone-02.png` clearly labels the counts and callers as examples.
- **All six owner jobs have visible destinations.** `X/08-account-phone-01.png` exposes sign-out controls; `X/05-schedule-phone-01.png` through `X/05-schedule-phone-05.png` cover appointment length, working hours, quiet hours and reminder delays; `X/07-phone-phone-02.png` distinguishes the business, texting and owner numbers. This is substantially more complete than Y.
- **Changes have useful feedback.** `X/state-messages-unsaved-bar-phone.png` shows a persistent change count, Discard and Save. `X/state-schedule-saved-toast-phone.png` names the changed setting and explains that it affects customers already mid-conversation. Owners get more assurance than a generic success message.
- **Number changes and business renaming receive attention.** `X/state-phone-confirm-mobile-phone.png` explains that sign-in stays on the current number until verification. `X/state-phone-rename-offer-phone.png` notices two messages containing the old business name and offers to update them.
- **Forwarding instructions explain consequences.** `X/07-phone-phone-03.png` warns against forwarding every call, provides carrier-specific instructions, and includes reversal instructions. `X/07-phone-phone-04.png` explicitly distinguishes a check TextBack cannot perform from checks represented by example data.
- **Calendar states offer a next step.** `X/06-calendar-phone-01.png` explains the connection and permissions; `X/06-calendar-phone-02.png` labels availability as belonging to a test calendar. `X/state-calendar-not-connected-no-connect-phone.png` supplies a support action when self-service connection is unavailable.
- **Phone navigation is strong, but pages remain lengthy.** `X/04-messages-phone-02.png` keeps the section jump control and bottom navigation visible. Nevertheless, Messages occupies twelve supplied phone captures, while Schedule and Phone each occupy five. Repeated explanatory blocks increase scrolling, and the navigation label “Phone” does not immediately advertise business-name settings.
- **Defaults deserve improvement.** `X/state-schedule-any-time-warning-phone.png` clearly warns about bookings at 1 AM and offers weekday hours. However, “Any day, any time” remains the reset default—a poor starting point for this audience.

**Portal Y observations**

- **The message editor explains its purpose well.** `Y/03-messages-phone-01.png` tells owners what they can edit and when changes begin. The shaded message region, distinct action footer, and visible “STOP line added for you” make the first card understandable.
- **Business settings are focused and readable.** `Y/04-business-phone-01.png` and `Y/04-business-phone-02.png` place the name, HELP number and sign-in mobile in one short form with generous fields and a full-width save button.
- **Mobile verification has a clear escape route.** `Y/save-03-owner-mobile-change-desktop.png` names the proposed number, explains expiry and preserves the current sign-in number until confirmation. “Keep my current mobile” is explicit; `Y/save-04-keep-mobile-desktop.png` confirms that choice.
- **Coverage is materially incomplete.** `Y/INDEX.md` lists no scheduling, forwarding or service-overview page. The navigation in `Y/04-business-desktop-01.png` contains only Messages, Business and Calendar. An Account control is visible, but the supplied evidence does not expose a sign-out action; I cannot award credit for an unseen menu.
- **Calendar is a dead end.** `Y/05-calendar-phone-01.png` acknowledges test mode and no connection, but offers neither connection nor a support action. The deduction concerns the missing route forward, not the disconnected test state.
- **Long-page navigation is weaker.** `Y/03-messages-phone-01.png` puts section links in a horizontally overflowing strip. By `Y/03-messages-phone-08.png`, those links are no longer visible; only the main bottom navigation remains. Moving between distant message sections requires more effort.
- **Save feedback varies in usefulness.** `Y/save-01-messages-phone.png` identifies the changed question, while `Y/save-02-business-phone.png` says only “Saved.” The latter also leaves the first-text preview using the previous business name without explaining why.
- **Examples are labelled, but some local presentation is misleading.** `Y/03-messages-phone-12.png` labels the conversation as a sample at its end, yet displays “Booked · on your calendar.” With no calendar connected, the success badge should carry its own example/test qualification.

**“Looks broken”**

- **X — incomplete customer preview:** `X/04-messages-phone-01.png` says the network adds a notice before the owner’s wording, but the bubble omits it. `X/04-messages-phone-12.png` repeats that the notice exists without showing it. This is a preview-fidelity defect, although the omission is acknowledged in surrounding copy.
- **X — incorrect device terminology on desktop:** `X/08-account-desktop-01.png` calls the current device “This phone” and offers “Remember this phone.”
- **Y — exposed implementation URLs:** `Y/03-messages-phone-06.png` and `Y/03-messages-phone-12.png` display long `hermes-cloud…:8765` addresses and route tokens inside the booking message. They wrap across many lines and make the confirmation look unfinished.
- **Y — stale example date:** `Y/03-messages-phone-03.png` suggests October 22; `Y/03-messages-phone-12.png` confirms that date in the example booking. It predates the October 26 judging date. This is stale sample content, not evidence of an actual past booking.
- **Y — unexplained name mismatch after saving:** `Y/save-02-business-phone.png` shows the changed business name in the field while “IN THE FIRST TEXT” retains the old name. Even if customized wording intentionally remains unchanged, the owner receives no explanation or repair action.
- **Y — confirmation overlays obscure orientation:** `Y/save-01-messages-phone.png` and `Y/save-02-business-phone.png` place dismissible success notifications over the page heading and introductory copy.
- **Y — cut-off section navigation:** `Y/03-messages-phone-01.png` cuts off the “No reply” pill at the right edge and leaves subsequent destinations offscreen. This is navigation-strip overflow; the screenshots do not establish whole-page sideways scrolling.
- **Y — calendar dead end and ambiguous success state:** `Y/05-calendar-phone-01.png` offers no next action; `Y/03-messages-phone-12.png` nevertheless uses an unqualified “on your calendar” badge inside its sample.

No other definite clipping, overlapping controls or malformed fields were apparent in the inspected images. Ordinary content passing behind fixed bars at intermediate scroll positions was not counted as a defect.

**Three ideas X should adopt from Y**

1. **Stronger separation within message cards.** The shaded preview area and clearly divided editing footer in `Y/03-messages-phone-02.png` distinguish customer-facing text from owner controls more immediately.
2. **Mark the protected phrase itself.** The underlined STOP wording in `Y/03-messages-phone-01.png`, alongside the automatic-addition label, makes the protected text easier to identify. X should retain its protections and adopt this additional visual cue.
3. **Make business settings explicit in navigation.** The “Business” destination in `Y/04-business-desktop-01.png` makes renaming easy to find. X should give its combined phone/business destination an equally explicit label while retaining its broader controls.

Choose **Portal X** because it provides visible paths for all six owner jobs and gives substantially better guidance around setup, changes and recovery. Its advantage comes from task coverage and feedback, with readable phone controls supporting both. Before owners see it, render the actual network notice in customer previews, replace unrestricted scheduling as the reset default, and correct desktop device wording. Also make business settings easier to find and shorten repeated explanations on the longest phone pages.

VERDICT: WINNER X