I'll judge Portal X and Portal Y only from the screenshots and page text in this folder, starting with each index so I open every image.The indexes and page text are in. Next I’ll open the screenshots themselves, starting with sign-in and the main pages on both portals.## 1. Judge, evidence, confidence

Judge: Grok 4.7. I opened every image in this folder: **54 in Portal X** and **36 in Portal Y**, plus each `INDEX.md` and every page-text file. I did not leave the folder, and I did not click, type, or submit anything.

Confidence is high for what is on screen. I did not see expanded states that were not captured: Portal Y’s account menu, Portal Y’s “Edit wording” fields, any preview scenario other than “Books a job”, Portal X’s “Set hours” grid, or a carrier’s forwarding codes.

## 2. Scores

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X | 4 | 2 | 5 | 4 | 4 | 4 | 2 | 3 | 4 | 2 | 68 |
| Y | 4 | 4 | 2 | 3 | 4 | 3 | 3 | 4 | 5 | 3 | 70 |

## 3. Portal X

The signed-in shell tells an owner where the six jobs live. `X/03-home-desktop-01.png` puts “No calendar yet”, “Forwarding 1 of 5”, and “Messaging registration” in three cards with “Set up” and “Finish setup”. The phone bottom bar in `X/03-home-phone-01.png` keeps Home, Messages, Scheduling, Calendar, and Phone on screen.

Sign-in matches the owner’s mobile. `X/01-sign-in-desktop-01.png` prefills `(980) 555-0123` and says it is the mobile on file. `X/02-enter-code-phone-01.png` explains the six-digit code, the ten-minute expiry, and “Remember this phone for 30 days”. `X/08-account-phone-01.png` has a real “Sign out” button and points number changes to the Phone page.

Scheduling is a complete rules page. `X/05-scheduling-desktop-01.png` shows appointment length (60 minutes, with 30–120 minute chips), time zone, and working hours, each with a default and a Reset. `X/05-scheduling-desktop-02.png` sets quiet hours at 9:00 PM–8:00 AM and says the first text, a live reply, and STOP/HELP still go out. `X/save-02-scheduling-desktop.png` confirms “Saved. New conversations use these hours and delays.”

The messages editor is where a non-technical owner gets lost. `X/04-messages-phone-01.png` opens with “Words in {braces}” and a `{business_name}` chip, then a SignalWire character count. `X/04-messages-phone-07.png` lists `{invite_line}`, `{google_link}`, `{ical_link}`, and `{event_id}` under the booking text. `X/04-messages-desktop-10.png` adds the rule “Must promise a follow up (those two words).” The sticky “Save messages” bar is useful, and `X/save-01-messages-desktop.png` does show the edited line “Where is the job? (desktop)” in the preview.

The Phone page covers the numbers and forwarding job, with a broken checklist. `X/07-phone-desktop-01.png` has business name, business number `(704) 555-0123`, texting number `(704) 555-0100`, owner mobile, HELP number, carrier chips, and “Only forward busy and unanswered calls.” `X/07-phone-phone-03.png` marks check 1 done from a call on Oct 19, then check 2 says “No call recorded yet”, and the note says steps 1, 2, and 4 are ticked from real calls.

## 4. Portal Y

An owner can read the customer conversation without learning template syntax. `Y/03-messages-desktop-01.png` says changes start on the next missed call, labels the green bubbles as made-up, and shows the first text as a bubble with “STOP line added for you” and a Customized badge. `Y/03-messages-phone-03.png` shows a customer reply “Sometime next week” and the correction the assistant sends. `Y/03-messages-phone-12.png` ends the sample with “Sample conversation · nothing is sent · names invented” and “Back to editing”.

Saving a text names the change. `Y/save-01-messages-desktop.png` toasts “Saved. Changed: Question 2: the location.” The save button on `Y/03-messages-desktop-09.png` stays disabled beside “No unsaved changes”. START, HELP, and STOP sit in a collapsed block: “Required by phone companies. Most businesses never change these.”

Changing the owner’s mobile is the clearest safety step in either portal. `Y/save-03-owner-mobile-change-desktop.png` says a code went to `(980) 555-0199`, that sign-in stays on the current mobile until the code is entered, and offers “Keep my current mobile”. `Y/save-04-keep-mobile-desktop.png` confirms “Kept your current mobile.”

The rest of the owner’s job is missing or wrong. There is no scheduling page and no forwarding page. `Y/05-calendar-phone-01.png` stops at “No calendar connected” and “still being set up by FluxWorks”, with no check and no next step. `Y/04-business-phone-02.png` edits the business name, the HELP number, and “Your mobile”, and does not mention the business line, the texting number, or call forwarding. No screenshot shows Sign out. `Y/01-sign-in-phone-01.png` prefills `704 555 0123` under “Business mobile”, while `Y/04-business-desktop-02.png` says sign-in codes go to `(980) 555-0123`.

## 5. Looks broken

Portal X:

- The desktop sidebar cuts the business name to “Oak & Pine Tre...” on every signed-in desktop screen, including `X/03-home-desktop-01.png` and `X/08-account-desktop-01.png`. The same sidebar prints `text_back · missed-call recovery`.
- The messages preview card slices the bottom bubble on every desktop messages shot. In `X/04-messages-desktop-01.png` the cut line is “[SignalWire Free Trial] What day and time works best?”
- The sticky save bar covers the next field. `X/04-messages-phone-02.png` covers the location box. `X/04-messages-phone-10.png` covers the STOP reply. `X/05-scheduling-phone-03.png` lets the sticky “Scheduling” title sit on the “Nudges” heading.
- `X/03-home-desktop-01.png` says this week’s missed calls, texts, bookings, and handoffs are all 0, then lists Marcus Lee, Dana Whitfield, and two other callers under “The ten most recent callers” with no sample label. Four rows are shown.
- `X/07-phone-desktop-02.png`: check 1 is a completed test call, check 2 says “No call recorded yet”, check 4 says “Enter your business number first” while `(704) 555-0123` is already in the field, and the footnote says steps 1, 2, and 4 are ticked. `X/07-phone-phone-03.png` draws checks 1, 2, and 4 as circles and checks 3 and 5 as squares. The same test call is Oct 19, 12:50 PM in `X/07-phone-desktop-01.png` and Oct 23, 9:29 PM in `X/save-05-checklist-desktop.png`.
- `X/save-03-availability-desktop.png` lists Mon, Oct 26, 1:00–3:30 AM as the next free times on a card that still says no real calendar is connected. `X/save-02-scheduling-desktop.png` shows 90 in the length field while every preset chip looks unselected.
- `X/04-messages-desktop.txt` puts raw `http://100.124.192.46:8003/...` links in the booking preview. The preview card is clipped before that bubble, so those links are in the page text and not fully visible in the screenshots.

Portal Y:

- `Y/01-sign-in-desktop-01.png` and `Y/01-sign-in-phone-01.png` prefill `704 555 0123`. The business page’s sign-in mobile is `(980) 555-0123`.
- `Y/03-messages-desktop-05.png` and `Y/03-messages-phone-12.png` put `hermes-cloud.tailefb1a4.ts.net:8765` in the booking text a customer would receive. On `Y/03-messages-phone-06.png` the address breaks mid-token (`a/k7` / `q2-ref`).
- After a rename, the “IN THE FIRST TEXT” bubble still says “Hey, this is Oak & Pine Tree Care” on `Y/save-02-business-desktop.png` and `Y/save-02-business-phone.png`. The field and header show the new name with the `(desktop 043715)` or `(phone 043715)` suffix.
- The phone toast covers the page copy. `Y/save-01-messages-phone.png` hides the first line of the messages introduction. `Y/save-02-business-phone.png` hides “How the assistant introduces the business”. The header truncates to “Oak & Pine Tree Care (…)”.
- The desktop preview stays on the opening of “Books a job” and cuts off at a “TEXTBACK” label, including while the booking section is on screen in `Y/03-messages-desktop-05.png`.
- `Y/05-calendar-desktop-01.png` is a dead end: test mode, no calendar, and no control.

## 6. Three ideas from Portal X that Portal Y should adopt

1. A home status board, from the three setup cards and the week counts on `X/03-home-desktop-01.png`. Sample callers need a label Portal X does not have.
2. A scheduling page with length, working hours, quiet hours, reminder delays, defaults, and Reset, as on `X/05-scheduling-desktop-01.png` and `X/05-scheduling-desktop-02.png`.
3. One phone-and-forwarding page: business line, texting number, owner mobile, carrier choice, and the five setup checks, as on `X/07-phone-desktop-01.png` and `X/07-phone-phone-03.png`. Pair it with the sticky “Save messages” bar on `X/04-messages-phone-01.png` so a long page can be saved without scrolling to the end.

## 7. Recommendation

Portal Y wins by two points because an owner can tell what each screen does, the customer texts are written in plain language, samples are labeled, and a mobile-number change waits for a code. Portal X can reach more of the six jobs, and its language, unlabeled callers, and checklist contradictions cost more under this rubric than Y’s missing pages. Before an owner sees Portal Y, it needs a visible sign-out, a scheduling page, and forwarding for the business line and texting number, plus a single place that says whether the service is working. It also has to prefill `(980) 555-0123` on sign-in, make the first-text preview follow the business name, stop the phone toast from covering the page, and remove the `hermes-cloud` address from the booking text.

VERDICT: WINNER Y
