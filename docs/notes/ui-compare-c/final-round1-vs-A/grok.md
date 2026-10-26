I'll judge both portals from this folder only: first I'll inventory the evidence, then open every screenshot and page-text file before scoring.I’ll read both indexes and page-text files first, then open every screenshot so the scores rest on what is actually on screen.Next I’ll read the page-text files, then open the screenshots in batches so every score is tied to a real screen.I’ll pull the rest of Y’s schedule copy, then start opening the screenshots themselves.Sign-in and code screens are in. Next I’ll walk Portal X’s messages, business, calendar, and save states.X’s desktop IA is thin. I’ll check phone layout, save confirmations, and the remaining X screens next.X is fully reviewed. I’ll now open Portal Y from sign-in through home, then the rest of its pages.I’ll open Y’s state and save screens next so feedback, errors, and confirmations are scored from the actual UI.I'll finish the remaining Y state and save screenshots, then write the scorecard from the evidence in this folder.Opening remaining Y state and save screenshots in batches so the scorecard is based on the actual images.Continuing with remaining phone, schedule, messages, and save screenshots.Re-opening the X screenshots and the Y pages that carry the remaining defects so citations stay first-hand.Opening the remaining overlapping X phone scrolls so the image count is complete.# TextBack client portal bake-off scorecard — 2026-10-26

**Judge:** Grok 4.6 (xAI). Blind labels X / Y only. No git, no repos, no web, no other judges.

**Files opened:** Every PNG listed in `X/INDEX.md` (**37 images**) plus X page-text dumps. For Y, every `save-*` (18), every `state-*` (42), and page screenshots for all eight routes at both widths, including first and last scroll positions of long pages (Home, Messages, Schedule, Phone, Account). A few 120 px-overlap middle frames of Y’s longest pages were sampled after start, key section, and end rather than every consecutive crop. Images rendered; none failed to open.

**Confidence:** High on coverage, honesty, and mobile nav. Slightly lower on live tap-target feel (static screenshots) and on what X’s header person-icon actually opens (never shown). X has no error-state captures.

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 3 | 2 | 2 | 3 | 3 | 2 | 2 | 3 | 4 | 2 | 52 |
| Y | 5 | 4 | 5 | 5 | 4 | 4 | 5 | 5 | 4 | 3 | 88 |

---

## Portal X — observations

1. **`X/03-messages-desktop-01.png` — “Your messages” + Conversation preview.** An owner landing after sign-in sees a three-item nav (Messages / Business / Calendar) and a strong two-column editor: green bubbles, “Edit wording / Reset”, STOP called out under the first text, and a live phone mock labelled “Sample conversation · nothing is sent · names invented”. Within five seconds they know this page edits customer texts. They do not know whether the service is set up, how hours work, or how to sign out.

2. **`X/03-messages-desktop-05.png` and `X/03-messages-phone-06.png` — Booking confirmation.** The confirmation bubble dumps raw `http://hermes-cloud.tailefb1a4.ts.net:8765/a/k7q2-ref/...` Google/Outlook/iCal URLs, then a green pill **“Booked · on your calendar”**. The same owner on `X/05-calendar-desktop-01.png` reads **“No calendar connected / Bookings are not recorded on any calendar yet.”** That contradiction is what they would believe about live jobs.

3. **`X/01-sign-in-desktop-01.png` — “Business mobile”.** The field is prefilled `704 555 0123` (the business line), labelled “Business mobile”, while the test owner’s sign-in number is 980 555 0123. Copy says “Enter the business mobile on file”. A tree-care owner between jobs can easily text a code to the wrong phone. Enter-code (`X/02-enter-code-phone-01.png`) is otherwise plain: six boxes, ten-minute expiry, resend.

4. **`X/04-business-desktop-01.png` / `X/save-02-business-desktop.png`.** Business name, HELP number, and owner mobile are here, with honest “we text a code to the new number and nothing changes until you enter it.” There is no business line, no texting number, and no forwarding. After renaming to “Oak & Pine Tree Care (desktop 043715)”, the toast is only **“Saved.”** and the first-text bubble still says “Oak & Pine Tree Care” with no suffix — the preview did not update. Phone header truncates to “Oak & Pine Tree Care (…” (`X/save-02-business-phone.png`).

5. **`X/save-03-owner-mobile-change-desktop.png`.** Two-step “Confirm your new mobile” with code to `(980) 555-0199`, expiry copy, “Keep my current mobile”, and resend. This is the strongest safety pattern X has. There is no matching phone capture of this flow.

6. **`X/03-messages-phone-01.png` + `X/03-messages-phone-10.png`.** Jump chips “Missed call / Questions / Booking / No reply” clip the last chip at the right edge; there is no “Steps back”. Save sits at the bottom of a ~12-screen page as a grey **“No unsaved changes / Save changes”** bar, then the conversation preview starts *below* that. An owner on a phone edits, scrolls past Save without noticing, and only then sees the sample thread.

---

## Portal Y — observations

1. **`Y/03-home-desktop-01.png` / `Y/03-home-phone-01.png` — “Not working yet: 1 step left.”** EXAMPLE-labelled setup: Calendar “Waiting on FluxWorks”, Call forwarding “Needs you · 3 of 5”, Texting approval “Waiting on phone companies”. “This week” is badged **EXAMPLE NUMBERS**; callers Dana / Priya / Marcus are **EXAMPLE**, and Dana is “Booked on test calendar”. An owner knows in one glance what is broken, what is demo, and what to tap next (“Finish forwarding”).

2. **`Y/state-messages-unsaved-top-phone.png` + `Y/save-01-messages-wording-desktop.png`.** Editing produces a sticky **“2 texts changed / Discard / Save”** bar (replacing the site header on phone), an **Unsaved** badge, and a **Was:** previous-copy line. After save, the toast names the field: **“Saved. You changed ‘Question 2: the address’.”** That is how a non-technical owner finishes a change between jobs.

3. **`Y/save-03-business-name-rename-offer-desktop.png` / `Y/save-04-rename-texts-updated-desktop.png`.** Renaming to “Oak & Pine Tree Service” saves, then asks **“1 text still says ‘Oak & Pine Tree Care’. Update it to the new name?”** with Update it / Leave it. After Update, the first-text bubble actually reads the new name. X never offered this and never updated the preview.

4. **`Y/07-phone-desktop-02.png` through `Y/07-phone-desktop-04.png`.** Business number, locked texting number, owner mobile, Verizon/T-Mobile/AT&T/Cricket/Other chips, copyable `*71 704 555 0100` / `*73`, warning **“Only forward busy and unanswered calls”**, and a 5-check forwarding list with EXAMPLE on checks 1, 2 and 4 and owner-only “I checked this” on 3 and 5. Footer: “In this preview, checks 1, 2 and 4 come from example calls.” This is owner job 5, which X does not have.

5. **`Y/05-schedule-desktop-01.png` / `Y/save-02-schedule-length-90-desktop.png` / `Y/state-schedule-any-time-desktop.png`.** Appointment length chips + custom, timezone, working hours, quiet hours 9pm–8am, reminder delays, per-rule Default + Reset, and **“Applies right away, including customers mid-conversation”** both on the control and in the save toast. Switching to “Any day, any time” raises **“Customers can be offered times like 1 AM.”** X has no Schedule page at all.

6. **`Y/state-home-account-menu-phone.png` + `Y/state-account-signout-everywhere-desktop.png`.** Header “Oak & Pine Tree Care” opens Signed in as (980) 555-0123, Account, Sign out. Sign-out-everywhere is a red confirm: **“You’ll need a new code on each one.”** Remembered devices are EXAMPLE-labelled. X never shows sign-out.

---

## Looks broken

**Portal X**
- `X/03-messages-desktop-05.png`, `X/03-messages-phone-05.png`, `X/03-messages-phone-06.png`, `X/03-messages-phone-12.png`: leftover `hermes-cloud.tailefb1a4.ts.net:8765` URLs in the booking text customers would receive.
- `X/03-messages-desktop-05.png` vs `X/05-calendar-desktop-01.png`: “Booked · on your calendar” while Calendar says nothing is recorded.
- `X/03-messages-phone-01.png`: jump chips clip “No reply”; later sections have no chip.
- `X/save-02-business-phone.png`: header truncates to “Oak & Pine Tree Care (…”.
- `X/save-02-business-desktop.png`: first-text preview ignores the saved new name “(desktop 043715)”.
- `X/03-messages-phone-03.png`: “Question 4: the name” heading clipped by the bottom nav.
- `X/save-01-messages-desktop.png`: harness leftover “Oak & Pine Tree Care (desktop)” in the header and in the conversation mock.

**Portal Y**
- `Y/04-messages-phone-02.png`: sticky “Jump to: Questions” bar covers the “Questions” heading.
- `Y/04-messages-phone-11.png`: “Example conversation” heading sliced through by the header.
- `Y/04-messages-desktop-01.png` / `Y/04-messages-desktop-09.png`: customer bubble “Thursday at 10” cut off at the bottom of the desktop conversation pane.
- `Y/save-03-business-name-rename-offer-phone.png`: first-text preview clipped by the bottom tab bar.
- `Y/02-enter-code-desktop-01.png`, `Y/state-phone-confirm-new-mobile-desktop.png`: first code box has a double focus ring (inner + outer).
- `Y/save-01-messages-wording-desktop.png`: example conversation still contains harness leftover **“(desktop 185849)”** in the address question.
- `Y/state-phone-invalid-mobile-field-desktop.png`: sticky “Not saved · 1 change” bar covers the forwarding codes `*71 704 555 0100`.
- `Y/state-calendar-connected-desktop.png`: connected demo uses `owner@example.com` with no EXAMPLE badge (extra connected state, not the live test client).

---

## Three ideas from the lower portal (X) that the winner should adopt

1. **Sticky desktop conversation column** (`X/03-messages-desktop-01.png` through `X/03-messages-desktop-09.png`). The sample thread stays on screen while the owner scrolls every text. Y’s pane is similar but clips the last customer bubble and is not as clearly a persistent editor companion.

2. **Optional-question toggles with SKIP** (`X/03-messages-desktop-04.png`, `X/03-messages-phone-04.png`). “Best phone number” off / “Email address” on, plus “If the email could not be read”. Y’s question list is fixed; an owner who does not want email has no switch.

3. **Per-bubble SMS billing warning** (`X/03-messages-desktop-05.png`, `X/03-messages-phone-07.png`). Orange “Billed as 3 texts. The ‘—’ symbol limits each text to 70 characters.” sits on the bubble the owner is editing. Y counts “with the notice” but does not show segment cost this clearly.

---

## Recommendation

Portal Y is the portal an owner can actually run the business from: Home says whether it is working, Schedule and Phone exist, forwarding is copy-and-dial, demo data is labelled EXAMPLE, saves name the field and the consequence, and sign-out is findable on a phone. Portal X’s messages editor is the prettier conversation theater, but it is a three-page settings fragment that contradicts its own calendar, leaks internal URLs into customer copy, and never shows hours, forwarding, or sign-out.

Before an owner sees Y, fix the jump bar covering section titles, stop clipping the first-text preview and the desktop “Thursday at 10” bubble, strip harness tokens such as “(desktop 185849)”, and replace repeated “FluxWorks” in owner copy (“What happens next” step 2 on `Y/04-messages-desktop-09.png`) with “us” / “support”. Adopt X’s optional-question toggles and per-text billing warning on that same Messages page.

VERDICT: WINNER Y
