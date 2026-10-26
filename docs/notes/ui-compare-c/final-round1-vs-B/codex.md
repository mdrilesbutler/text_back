Judge: **Codex (GPT-6)**.

I opened **105 images: 61 for X and 44 for Y**, including every numbered phone screenshot, the first desktop screenshot of every page, additional desktop views, all nine X phone save captures, and eight Y save captures. I also opened `X/INDEX.md`, `Y/INDEX.md`, and all 14 desktop page-text files. Specific image evidence is cited below. Confidence is **high for the visible design comparison, moderate for functional behavior**: screenshots demonstrate states, but cannot establish whether controls, verification or integrations actually work. Neither portal loses points simply for having no real calendar connected.

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 4 | 4 | 4 | 5 | 5 | 4 | 4 | 4 | 4 | 4 | 84 |
| Y | 3 | 2 | 3 | 3 | 4 | 3 | 2 | 3 | 4 | 3 | 60 |

**Portal X — observations**

- `X/03-home-desktop-01.png`: Setup cards distinguish “Needs you” from “Waiting on FluxWorks” and “Waiting on phone companies.” The owner gets a concrete “Finish forwarding” action instead of having to interpret technical registration status.
- `X/03-home-phone-02.png` and `X/07-phone-phone-04.png`: Counts, callers and automated forwarding checks carry explicit example labels. This prevents the owner from mistaking seeded activity for proof that their service works.
- `X/04-messages-phone-01.png` and `X/state-messages-edit-wording-phone.png`: Rendered customer texts come before editing controls, and “Business name” is a readable insertion button. Owners can inspect actual wording without first understanding template syntax.
- `X/state-messages-unsaved-top-phone.png` and `X/save-01-messages-wording-phone.png`: The persistent change bar offers Save and Discard, shows how many texts changed, and the confirmation names the changed question. This is excellent feedback for interrupted work.
- `X/save-03-business-name-rename-offer-phone.png` and `X/save-04-rename-texts-updated-phone.png`: Renaming the business detects an old name in customized wording and offers to update it. The follow-up capture confirms the replacement.
- `X/save-07-owner-mobile-confirm-step-phone.png`: The new-number screen explains that sign-in moves only after confirmation, provides resend, and offers “Keep my current mobile.” The consequences and escape route are clear.
- `X/06-calendar-phone-01.png` and `X/state-calendar-connected-picker-phone.png`: Calendar setup has an explicit support action; the supplied connected-state example names the destination calendar and offers a picker. Initial connection still requires outside help, limiting self-service coverage.
- `X/04-messages-phone-10.png` and `X/07-phone-phone-05.png`: Generous spacing and readable controls produce lengthy pages. Messages has jump navigation, but Phone lacks an equivalent shortcut through its five captured scroll positions.

**Portal Y — observations**

- `Y/03-home-desktop-01.png`: Setup, weekly totals and recent conversations fit into one desktop viewport. This compact overview helps an owner scan status quickly, although its sample records and registration status lack example labels.
- `Y/01-sign-in-phone-01.png` and `Y/08-account-phone-01.png`: Sign-in and sign-out are straightforward, with clear primary buttons and comfortable field widths. The Account page is particularly concise.
- `Y/04-messages-phone-01.png` and `Y/04-messages-phone-07.png`: `{business_name}`, `{invite_line}`, `{event_id}` and repeated vendor notices dominate the editing experience. An owner must work through implementation vocabulary to change ordinary customer wording.
- `Y/04-messages-phone-04.png`: Save and Preview remain reachable while scrolling, alongside the bottom navigation. That is useful, but the three stacked bottom controls reduce the usable editing area, and no section-jump control is visible.
- `Y/05-scheduling-phone-01.png` and `Y/05-scheduling-phone-03.png`: Appointment presets, stated defaults and individual Reset actions make timing rules approachable. “Close the lead” and “expired” are less direct than describing what happens to the customer.
- `Y/save-01-messages-phone.png`: The success banner clearly says new conversations use the saved messages. `Y/save-04-phone-phone.png` provides only “Saved,” offering less assurance about which setting changed.
- `Y/07-phone-phone-02.png`: Mobile verification is explained beside the number, and number settings have their own Save action. Forwarding checks are saved separately, giving the two tasks clear boundaries.
- `Y/06-calendar-phone-01.png`: Calendar connection is explicitly unavailable, but there is no actionable connection or support control. The owner reaches a page describing the missing capability without a clear way to finish setup.

**Looks broken**

These are visible defects or inconsistencies; I did not infer backend failures from screenshots.

- **X — ambiguous readiness count:** `X/03-home-desktop-01.png` says “1 step left” while showing incomplete forwarding, an unconnected calendar and pending texting approval. It appears to count owner actions, but does not say so.
- **X — contradictory conversation explanation:** `X/04-messages-phone-02.png` says the job question is asked as soon as the customer replies. In `X/04-messages-phone-11.png`, “Tree trimming” instead advances directly to the address question. The explanation should describe when the job question is skipped.
- **Both — incomplete code-entry recovery guidance:** `X/02-enter-code-phone-01.png` and `Y/02-enter-code-phone-01.png` show neither the destination mobile number nor a visible change-number action. X specifically tells the owner to “check the number” without displaying it.
- **Both — truncated conversation details:** `X/03-home-phone-03.png` cuts Dana’s confirmation at “Add to…”. `Y/03-home-phone-02.png` truncates every last-message summary. No visible expansion control accompanies these excerpts; Y also truncates the business identity in `Y/03-home-desktop-01.png`.
- **Y — calendar contradiction and setup dead end:** `Y/06-calendar-desktop-01.png` says bookings are not recorded anywhere, alongside “A real read of the calendar the assistant books on.” `Y/save-03-availability-phone.png` then shows test-calendar availability under that same “real read” description. The unavailable connection and “Ask text_back” copy provide no visible actionable contact.
- **Y — demo presented as operational evidence:** `Y/03-home-desktop-01.png` leaves seeded conversations and registration status unlabelled. `Y/07-phone-phone-03.png` explicitly attributes seeded checks to “real calls.”
- **Y — contradictory forwarding evidence:** `Y/07-phone-phone-03.png` records a completed test call, then says “No call recorded yet” under the next check.
- **Y — incorrect weekday/date pairing:** Dana’s booking in `Y/03-home-desktop-01.png` says “Thursday, Oct 23.” October 23, 2026 is Friday.
- **Y — misleading quiet-hours label:** `Y/05-scheduling-phone-02.png` labels the interval “No texts between,” although the paragraph immediately above lists texts that still go out.
- **Y — mismatched save feedback and weak selection feedback:** `Y/save-02-scheduling-phone.png` shows a changed appointment length, but confirms “these hours and delays.” The 45-minute preset is also visually indistinguishable from the other presets.
- **Y — desktop device wording:** `Y/08-account-desktop-01.png` calls the current device “this phone.”

No clear permanent horizontal clipping or unrecoverable layout overlap was seen. Content passing behind sticky bars during scrolling was not treated as proof of inaccessible content.

**Three ideas X should adopt from Y**

1. **A compact desktop overview:** `Y/03-home-desktop-01.png` keeps setup and recent activity together. X should reduce its Home page’s vertical expansion while preserving its example labels.
2. **A persistent phone Preview control:** `Y/04-messages-phone-01.png` makes Preview immediately discoverable throughout editing. X should adopt that access without reproducing Y’s bulky stack of bottom bars.
3. **Separate saves for independent Phone tasks:** `Y/07-phone-desktop-02.png` separates number settings from “Save checks.” X should adopt that task boundary while retaining its detailed confirmations.

Choose **Portal X** for the owner-facing portal. It wins through clearer customer-text previews, stronger change feedback, explicit example labels and better explanations of consequential actions. Before release, fix the readiness count, reconcile the job-question explanation with the preview, and add a visible number-correction route during sign-in. Shorten the long settings pages and preserve X’s clear support path for calendar setup.

VERDICT: WINNER X