I'll judge Portal X and Portal Y only from the screenshots and page text in this folder. First I'll inventory both sets, then open the images.Both indexes are in. Next I’ll read the page text and open the screenshots, starting with sign-in, home, and the long settings pages.Sign-in and home are in. Next I’ll go through messages, schedule, calendar, phone, and account, including the save and error states.## Judge

Grok 4.7. Read both `INDEX.md` files, all 16 Portal X page-text files, and all 12 Portal Y page-text files. Opened **48 of 114** Portal X images and **42 of 54** Portal Y images, including every page at desktop and phone, the save shots, and the error, confirm, and calendar-result states. I did not open every overlapping scroll frame (mostly extra X messages and schedule positions, and a few Y message-phone frames).

Confidence is high on the ranking. Limit: a few unopened scroll frames could hide another clip, and the raw server address in `Y/04-messages-desktop.txt` never appeared inside a screenshot viewport I opened. The preview pane stays on the opening texts.

## Scores

| Portal | a1 | a2 | b1 | b2 | c1 | c2 | d1 | d2 | e1 | e2 | Total /100 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| X | 5 | 4 | 5 | 4 | 4 | 4 | 5 | 5 | 5 | 4 | 90 |
| Y | 3 | 2 | 4 | 3 | 3 | 3 | 2 | 3 | 4 | 2 | 58 |

## Portal X

The home screen tells an owner the service is not working yet and what is theirs to do. In `X/03-home-desktop-01.png` the heading is “Not working yet: 1 step for you, 2 waiting on others,” with an EXAMPLE badge, then Calendar (“Waiting on FluxWorks”), Call forwarding (“Needs you”), and Texting approval. The phone version in `X/03-home-phone-02.png` labels “EXAMPLE NUMBERS” and each caller (Dana Whitfield EXAMPLE). The counts, 3 missed, 3 texted, 1 booked, 1 wants to talk, match that list.

Saving says what changed and who it hits. `X/save-02-schedule-length-90-phone.png` shows the toast “Saved. You changed ‘Appointment length’. Applies right away, including customers mid-conversation,” and the 90 min chip is selected. `X/state-messages-unsaved-phone.png` keeps a sticky bar, “2 texts changed,” with Discard and Save, an Unsaved badge, and the previous line under “Was:”.

Changing the sign-in number does not take effect on a whim. `X/state-phone-confirm-new-mobile-phone.png` is a second step, “Confirm your new mobile,” with a code sent to (980) 555-0155, “until then codes still go to your current mobile,” and a “Keep my current mobile” button. `X/state-account-signout-everywhere-phone.png` asks “Sign out of every device?” and warns that each device will need a new code.

The phone tab bar is the real gap. `X/03-home-phone-01.png` shows Home, Messages, Schedule, Calendar, and Phone. Account and Sign out sit under the business-name control, shown open in `X/state-home-account-menu-phone.png`. An owner between jobs can miss that. After a rename, `X/state-phone-rename-offer-phone.png` correctly offers “Update it” because one text still says “Oak & Pine Tree Service,” but the green first-text bubble is sliced by the bottom bar so only “Hey, this is Oak & Pine Tree” shows.

## Portal Y

Sign-in itself is plain. `Y/01-sign-in-phone-01.png` says “Text me a code” and “The mobile on file for this business.” Quiet hours are also plain: `Y/05-scheduling-phone-02.png` uses two menus, “9:00 PM” and “8:00 AM,” and says the first text, replies, and STOP/HELP still go out.

The messages page talks like a vendor console. `Y/04-messages-phone-01.png` leads with “Words in {braces},” shows `{business_name}` in the first-text box, and explains a “[SignalWire Free Trial]” tag, “3 texts,” and “each text holds 70 characters.” The sticky “Save messages” bar covers the next line. `Y/04-messages-desktop-10.png` prints the internal rule “Must promise a follow up (those two words).” `Y/04-messages-phone-08.png` covers the follow-up box so it reads “Hi again from {business_name}'s” and then the save bar.

Home and the phone checks disagree with themselves. `Y/03-home-desktop-01.png` truncates the business to “Oak & Pine Tre…”, labels a card “CAMPAIGN IN REVIEW” and “SignalWire Free Trial,” and lists Marcus Lee and Dana Whitfield with no example label beside a This week row of zeros. `Y/07-phone-phone-03.png` says “1 of 5 done,” step 2 “No call recorded yet,” and step 4 “Enter your business number first,” then “Steps 1, 2 and 4 are ticked from real calls recorded by the assistant.” The business number is already filled on `Y/07-phone-desktop-02.png`. After a save, `Y/save-05-checklist-desktop.png` still says step 4 needs the business number.

Calendar results are not usable. `Y/06-calendar-phone-01.png` says no calendar is connected and “Connecting a calendar from this page isn't turned on yet,” then “A real read of the calendar.” `Y/save-03-availability-phone.png` returns Mon, Oct 26, 1:00–1:45 AM, 1:30–2:15 AM, and 2:00–2:45 AM. Those 45-minute windows overlap. `Y/08-account-phone-01.png` says the phone signs out after 12 hours and “Signed in until Oct 26, 2026,” with no time, on the same calendar day.

## Looks broken

Portal X

- `X/03-home-phone-01.png`: bottom bar has five tabs and no Account.
- `X/state-phone-rename-offer-phone.png`: the green first-text bubble is cut off by the bottom bar.
- `X/07-phone-phone-04.png`: the “I checked this” row sits under the bottom bar. The next frame, `X/07-phone-phone-05.png`, shows that row once scrolled.
- `X/08-account-phone-01.png`: “Remember this device for 30 days” wraps so “days” sits alone.
- `X/04-messages-desktop-01.png`: the sample thread fades on “Thursday at 1” until “Scroll for the rest.”

Portal Y

- `Y/03-home-desktop-01.png`: sidebar title “Oak & Pine Tre…” and the footer “text_back · missed-call recovery” wraps onto two lines.
- `Y/04-messages-desktop-02.png`, `Y/04-messages-phone-06.png`, `Y/04-messages-phone-08.png`: the sticky Save bar covers the next field.
- `Y/04-messages-desktop-01.png`: the preview pane clips the last bubble (“What day and time works best?”).
- `Y/07-phone-phone-01.png`: the texting-number Verify button is cut by the bottom bar.
- `Y/save-04-phone-phone.png`: the texting-number field is cut by the bottom bar.
- `Y/07-phone-phone-03.png` and `Y/07-phone-desktop-02.png`: check count, empty steps, “enter your business number first,” and “steps 1, 2 and 4 are ticked” cannot all be true. The business number is already on screen.
- `Y/save-03-availability-phone.png`: three overlapping early-morning slots offered as free times.
- `Y/08-account-phone-01.png`: expiry is “Oct 26, 2026” with no clock, against the 12-hour line.
- `Y/04-messages-desktop.txt`: the booking preview text includes `http://100.124.192.46:8003/a/1-000000000000/…`. I did not see that address painted in a screenshot. The preview viewport never reaches the booking line.

## Ideas the winner should take from Y

1. Edit the text in place and show the customer thread update immediately. `Y/save-01-messages-desktop.png` changes the preview bubble to “Where is the job? (desktop)” next to the field.
2. Keep a person button in the phone header on every page so Account and sign-out are one tap. `Y/03-home-phone-01.png`.
3. Let appointment length be a number with chips as shortcuts, and keep quiet hours as two time menus with a Reset on each rule. `Y/05-scheduling-desktop-01.png` and `Y/05-scheduling-phone-02.png`.

## Recommendation

Portal X is the one an owner can use between jobs. Every job has a page, sample calls are marked EXAMPLE, saves name the change and who it affects, a new mobile waits for a code, and the test calendar’s free times are weekday mornings labeled as not theirs. Portal Y covers the same jobs, but it speaks in `{business_name}`, SignalWire, and `text_back`, its phone checks contradict the sentence under them, and the availability check offers overlapping 1 a.m. slots. Before an owner sees X, put Account on the phone bar, keep the bottom bar from covering the first-text bubble and the “I checked this” row, and make the sample thread readable without hunting for “Scroll for the rest.”

VERDICT: WINNER X
