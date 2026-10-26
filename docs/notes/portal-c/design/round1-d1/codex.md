Judge: **Codex (GPT-6)**. I opened **all 133 images: 96 for X and 37 for Y**, as listed in `X/INDEX.md` and `Y/INDEX.md`, including every scroll position and supplied state/save screenshot. I also read both indexes, X’s desktop page-text files for Home through Account, X’s four phone error/sign-out text files, and Y’s three desktop page-text files.

Confidence: **high for visual design and visible coverage; moderate for functionality**. Screenshots establish presented states, not whether controls, persistence or integrations work. I used only this folder and made no changes or external requests.

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 5 | 4 | 5 | 4 | 4 | 4 | 3 | 3 | 4 | 4 | 80 |
| Y | 4 | 3 | 2 | 3 | 4 | 3 | 3 | 3 | 4 | 3 | 64 |

**Portal X — observations**

- `X/03-home-phone-01.png`: “Not working yet: 2 steps left,” followed by “Connect calendar” and “Finish forwarding,” gives the owner an immediate status and useful next actions. `X/03-home-phone-02.png` clearly labels the activity counts and callers as examples.
- `X/05-schedule-phone-02.png` and `X/05-schedule-phone-04.png`: working-day switches, paired time fields and readable reminder selectors provide actual controls for the scheduling job. Defaults and individual Reset actions make recovery understandable.
- `X/state-schedule-any-time-warning-phone.png`: the warning explicitly explains that unrestricted hours can produce 1 AM appointments and offers a weekday-hours preset. `X/07-phone-phone-03.png` similarly explains the consequence of forwarding every call.
- `X/state-messages-unsaved-bar-phone.png` and `X/state-messages-saved-toast-phone.png`: a visible change count, Discard/Save controls and a confirmation naming the changed message make editing manageable. The save bar occupies the bottom navigation’s position while changes are pending.
- `X/04-messages-phone-02.png` and `X/04-messages-phone-09.png`: persistent section links help navigate a very long editor. Nevertheless, repeated notices, generous card spacing and the appended conversation produce eleven phone captures; this remains substantial scrolling between jobs.
- `X/state-phone-confirm-mobile-phone.png` and `X/state-account-sign-out-phone.png`: number verification preserves the current sign-in number until confirmation; signing out everywhere explains the consequence first.
- `X/state-calendar-connected-phone.png`: the selected calendar, “In use” badge and “Use this calendar” action give the booking destination a concrete, understandable home. This is evidence of a designed state, not a verified Google connection.

**Portal Y — observations**

- `Y/03-messages-phone-01.png`: “Your messages,” chronological sections and the explanation of when saved changes take effect orient the owner well. The first message visibly includes its automatically added STOP line.
- `Y/03-messages-phone-03.png`: showing “Sometime next week” immediately before the assistant’s clarification makes an exception easier to understand than an isolated response template.
- `Y/03-messages-phone-04.png`: compact optional-question cards keep each switch beside its heading and explanatory text. Their arrangement is efficient and readable on a phone.
- `Y/save-01-messages-phone.png`: the save confirmation identifies the changed question. However, it covers the page heading and introductory text; X’s confirmation reserves space instead.
- `Y/save-03-owner-mobile-change-desktop.png`: the verification screen clearly distinguishes saved business details from the still-unconfirmed mobile number and offers both cancellation and resend.
- `Y/04-business-phone-02.png`: the full-width “Save business details” button is clear, but the page covers only name, HELP number and owner mobile. Across `Y/INDEX.md`, there is no scheduling page, forwarding setup or overall service-status page; the visible Account icon alone does not establish a sign-out flow.
- `Y/03-messages-phone-02.png` through `Y/03-messages-phone-10.png`: bottom page navigation remains available, but section links scroll away and the resting save control is deep in the editor. Moving around this twelve-capture page takes more effort than in X.

**“Looks broken” — visible defects and inconsistencies**

- **X: misleading demo status.** `X/07-phone-phone-04.png` presents completed call/text checks with timestamps, and `X/07-phone-phone-05.png` explicitly attributes them to “real calls TextBack recorded.” These seeded results lack example labels. The texting-registration claim in `X/03-home-phone-01.png` likewise lacks a demo qualifier.
- **X: contradictory calendar explanation.** `X/03-home-phone-01.png` says bookings go to a test calendar before connection; `X/06-calendar-phone-01.png` says the assistant cannot book jobs without a calendar. The owner cannot confidently tell what currently happens to a caller.
- **X: misleading quiet-hours label.** `X/05-schedule-phone-04.png` says “No texts between,” although `X/05-schedule-phone-03.png` explains that several kinds of texts still send immediately.
- **X: inconsistent booking preview.** Email collection is off in `X/04-messages-desktop-04.png`, but the confirmation card in `X/04-messages-desktop-05.png` promises an email invitation. The conversation in `X/04-messages-phone-11.png` omits that promise. The card does not explain that it illustrates a different configuration.
- **X: business-name inconsistency.** `X/state-phone-rename-offer-phone.png` shows the saved “Tree Service” name while the header still says “Tree Care.” The offer to update two texts is useful, but “Used in every text” overstates automatic propagation.
- **X: ambiguous save-state evidence.** `X/state-schedule-unsaved-bar-phone.png` shows 90 minutes, whereas `X/state-schedule-saved-toast-phone.png` announces a change while showing 60. The analogous phone-name captures show “Tree Service” before saving and “Tree Care” afterward. These are apparent state mismatches; separate captures do **not** prove persistence failed.
- **Both: unsupported human-follow-up promises.** `X/04-messages-phone-08.png` promises direct follow-up and names a FluxWorks operator; `Y/03-messages-phone-09.png` promises owner follow-up, including for danger. These promises conflict with the supplied automated-service brief. Both retain useful 911 wording.
- **Y: exposed internal URLs and awkward wrapping.** `Y/03-messages-phone-06.png` and `Y/03-messages-phone-12.png` display long internal hostnames, a port and reference paths inside booking messages. They dominate the message and look unfinished.
- **Y: stale booking date.** `Y/03-messages-phone-12.png` resolves “Thursday at 4” to October 22, already past on the October 26 judging date, despite the conversation starting “just now.”
- **Y: misleading success presentation.** `Y/03-messages-phone-06.png` says “Booked · on your calendar,” while `Y/05-calendar-phone-01.png` says nothing is recorded on any calendar. Examples are disclosed elsewhere, but this success badge needs qualification where it appears.
- **Y: calendar dead end.** `Y/05-calendar-phone-01.png` explains that connection is still being set up but provides neither a connection action nor a support action. The disconnected test state itself is not the defect.
- **Y: stale text after business rename.** `Y/save-02-business-phone.png` confirms the changed business name while its first-text preview retains the old name, despite claiming the name is used in every text. No reconciliation offer is visible.
- **Y: confirmation overlap and header truncation.** `Y/save-01-messages-phone.png` and `Y/save-02-business-phone.png` show toasts covering headings and introductory copy; the longer test business names are ellipsized in the header, although the business field remains readable.

No additional hard field clipping or unintended page-wide horizontal overflow was evident. Cropping at ordinary scroll boundaries is not counted as a defect.

**Three ideas X should adopt from Y**

1. **Show the customer input beside exception responses**, as in `Y/03-messages-phone-03.png`. This explains why clarification happens.
2. **Use compact optional-question cards**, as in `Y/03-messages-phone-04.png`, to reduce scrolling without shrinking controls.
3. **Show an explicit unchanged state and disable unnecessary saving**, as in `Y/03-messages-phone-10.png`: “No unsaved changes” is clearer than X’s resting active Save button.

Choose **Portal X**: it provides visible places for all six owner jobs, clearer setup priorities and stronger navigation through lengthy settings. Its advantage is practical coverage, supported by useful warnings, verification and specific feedback. Before an owner sees it, label all seeded status evidence, reconcile calendar and preview inconsistencies, and remove unsupported human-follow-up promises. Also explain scheduling changes’ immediate effect before saving and resolve the apparent saved-value mismatches.

VERDICT: WINNER X