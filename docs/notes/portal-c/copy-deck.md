# TextBack owner portal, candidate C: copy deck (2026-10-26)

Every word an owner can see in `/client`, page by page. Built from the Part 2 word rules in
`../ui-bakeoff-2026-10-26/design-prompt-100.md`, the judges' deductions, A's and B's strings, and the
default customer texts in `messages.py`. Use it verbatim in mockups and templates.

Conventions
- **key**: the id a template or test uses. Message-text rows reuse the key from `messages.py`.
- **text**: the words on screen. `[like this]` is a value filled in from settings or live state; the
  brackets never show. ` / ` separates variants or states of one string; `(1) (2)` number list items.
- Product name on screen: TextBack. Company: FluxWorks. Never the repository name or the carrier vendor.
- Part 2 word rules apply to every row: approval paperwork is "texting approval", a billed unit is a
  "text", a captured enquiry is "customer details", fill-ins are insert chips with plain labels, no
  plumbing words, a follow-up text is a "reminder", and the moment the assistant stops is "when the
  assistant steps back".
- Customer-facing samples come from the real default texts. None promises a person or the number that
  went unanswered (`tests/test_no_live_human_copy.py`). The word STOP stays mandatory.

## 1. Sign in (`/client/login`)

| key | text | where |
|---|---|---|
| signin_brand | TextBack | top bar, signed out |
| signin_eyebrow | (not shown) | retired in round 2: the heading names the business instead |
| signin_title | [business name] / Sign in to TextBack / Sign in | heading / line under it / stepper label |
| signin_intro | Enter your mobile number. We text a six-digit code to the mobile on file for this business. No password. | intro line |
| signin_mobile_label | Your mobile number | field label |
| signin_mobile_placeholder | 10 digits | placeholder; never a real number |
| signin_submit | Text me a code / Sending… | primary button / while posting |
| signin_mobile_error | Enter your mobile as 10 digits, area code first. | under the field, shown once; the field keeps what was typed |
| signin_rate_limited | We've sent three codes in the last 15 minutes. Wait a few minutes, then try again. If you don't get a text within a minute, check the number and send a new code. | notice; the typed number stays in the field (m8/m9) |
| signin_verify_link | Enter the code you got | link back to Enter code under the form, only when this device already asked for a code (m8) |
| signin_signed_out | You signed out. | notice on the sign-in page after a plain Sign out (m5) |
| signin_foot | TextBack by FluxWorks | page foot |

Unknown numbers get the same next page as known ones (existing behaviour); nothing says whether the
number was recognised.

## 2. Enter code (`/client/verify`)

| key | text | where |
|---|---|---|
| verify_eyebrow | [business name] | above the heading |
| verify_title | Check your phone | heading |
| verify_intro | Enter the six-digit code we just texted. It expires in ten minutes. If you don't get a text within a minute, check the number and send a new code. | intro line (m9: allows for a typo) |
| verify_code_label | Sign-in code | field label |
| verify_remember | Remember this device for 30 days / Otherwise this device signs out after 12 hours. | switch, off by default (a borrowed phone never stays signed in) / under it |
| verify_submit | Sign in / Signing in… | primary button / while posting |
| verify_code_error | That code isn't right, or it has expired. Check the text or send a new code. | under the field |
| verify_resend | Didn't get it? Send a new code | link back to sign in |

Byte-identical for an unknown number and a wrong code; no part of any phone number renders here.

## 3. Home (`/client`)

| key | text | where |
|---|---|---|
| home_title | Home | page heading |
| home_status_working | Working: missed calls get a text within a minute. | first line, every setup card Done |
| home_status_not_yet | Not working yet: 1 step left. / Not working yet: [N] steps left. | first line otherwise |
| home_status_waiting | Set up on your side. Waiting on the phone companies to approve texting. / Set up on your side. Waiting on FluxWorks to connect your calendar. / Set up on your side. Waiting on FluxWorks and the phone companies. | first line when nothing needs the owner: only texting approval pending / only the calendar waits on FluxWorks / both (P3) |
| home_example_note | This preview mixes example calls with real settings. | under the first line, only when a counted setup card is harness example data |
| home_setup_heading | Setup | section heading |
| home_cards | Calendar / Call forwarding / Texting approval | the three card titles |
| home_state_words | Done / Needs you / Waiting on phone companies / Waiting on FluxWorks | card state word (Waiting on phone companies for texting approval only; Waiting on FluxWorks for a calendar FluxWorks must connect, P3); only Needs you counts as a step left |
| home_calendar_detail | Bookings go on [calendar name]. / No calendar of yours yet. Until you connect one, bookings go on a test calendar you can't see. / Google disconnected the calendar. Bookings are paused until you reconnect. / FluxWorks connects your calendar for you. | Calendar card: connected / not connected / reconnect needed / connecting isn't set up for the account (P3) |
| home_calendar_button | Connect calendar / Reconnect / Open Calendar / Text FluxWorks support | the one button; the last (sms link) only while waiting on FluxWorks and a support contact is configured |
| home_forwarding_detail | A forwarded call reached TextBack on [Fri, Oct 23, 2:40 PM]. / [N] of 5 checks done. | Forwarding card: done / not done |
| home_forwarding_button | Finish forwarding / Open Phone | the one button; Finish forwarding lands at the checks (/client/phone#checks, m22) |
| home_approval_detail | Texts go out with no network notice. / FluxWorks has filed your business for texting approval. Until it clears, each text starts with a short network notice. Nothing for you to do. / FluxWorks hasn't filed for texting approval yet. Until then each text starts with a short network notice. | Texting approval card: complete / pending / not started |
| home_approval_failed | Needs you / Phone companies turned down the texting approval. FluxWorks is fixing it; text FluxWorks support if texts aren't going out. | Texting approval card: a stage was rejected, failed, denied, suspended, expired, deactivated or cancelled (state word, then detail); counts as a step left in the first line |
| home_approval_unknown | Couldn't check / TextBack couldn't check texting approval just now. It will try again soon. | Texting approval card: the live check failed or returned words TextBack doesn't know (state word, then detail); retried after a minute; the first line reads like waiting |
| home_week_heading | This week | section heading |
| home_week_caption | Since [Mon, Oct 20]. The counts and the list below cover the same days. | under the heading |
| home_week_counts | Missed calls / Customers texted / Booked / Wants to talk to you | the four count labels (m30) |
| home_callers_heading | This week's callers | section heading |
| home_callers_empty | No callers this week. They appear here after the next missed call. | empty state |
| home_callers_columns | Customer / Status / Last activity / Last text | columns; Last activity is always a full date like "Fri, Oct 23, 2:40 PM" |
| home_caller_status | Booked / Booked on test calendar / Texting / Waiting for a reply / Wants to talk to you / No reply / Asked us to stop | status pill, in that order of states (m30) |
| home_caller_reach | [(980) 555-0177] / Call / Text | under a caller who asked for a person: the number, then tel: and sms: buttons, 44 px each (P4) |
| home_example_tag | Example | tag on every seeded caller in the preview harness |
| home_week_example | Example numbers | tag beside the This week heading while the counts come from seeded calls |
| home_example_setup | Example | tag on the Call forwarding and Texting approval cards while their status comes from preview data; the first line never counts those cards and never carries the tag (P2) |

## 4. Messages (`/client/messages`)

### Page frame and step headings

| key | text | where |
|---|---|---|
| messages_title | Messages | page heading (matches the nav label) |
| messages_intro | The texts customers get after a missed call, in order. Changes start with the next missed call. | intro line, two short sentences (fix pass) |
| messages_meta | Green bubbles are what customers see. The job, address, time and names are made-up examples. | under the intro |
| messages_jump | On this page: Missed call / Questions / Booking / No reply / Steps back / Jump to: [step] / Jump to a step | chip row from 640 px; below 640 px one sticky 44 px control whose summary reads "Jump to: [current step]" (without JS "Jump to a step") and opens the five steps as links; accessible name "On this page" |
| messages_not_enabled | Message editing isn't turned on for your account yet. FluxWorks sets this up for you. / Text FluxWorks support | notice when no messages file is configured / button (sms link) only when a support contact is configured |
| step_missed | Missed call / A call goes unanswered. Within a minute the caller gets this text. | heading / blurb |
| step_questions | Questions / Asked one at a time, in this order. The assistant moves on only once it has an answer. | heading / blurb |
| step_booking | Booking / Once it has the answers, the assistant checks your calendar and books a free time. | heading / blurb |
| step_no_reply | No reply / If the customer goes quiet, the assistant sends two reminders. Then the texting stops. | heading / blurb |
| step_steps_back | When the assistant steps back / When a text needs a person, the assistant stops scheduling and passes the customer's details on. | heading / blurb |
| step_keywords | START, HELP and STOP / Required by phone companies. Most businesses never change these. | collapsed section heading / blurb |
| step_optional_eyebrow | Optional questions | eyebrow above the phone and email cards |

### Card titles and when-lines (one row per text key)

| key | text | where |
|---|---|---|
| intro | First text after a missed call / (no when-line) | title / the step blurb already says when it is sent |
| prompt_service | Question 1: the job / Asked as soon as the customer replies. | title / when |
| prompt_location | Question 2: the address / Asked once the job is known. | title / when |
| prompt_preferred_time | Question 3: day and time / Asked once the address is known. Examples in everyday words help: Wednesday at 2, tomorrow at 10am. | title / when |
| preferred_time_reprompt | If the time couldn't be understood / Sent instead of moving on when the reply isn't a day and time. | title / when (branch card) |
| prompt_name | Question 4: the name / Asked once the time is known. | title / when |
| prompt_phone | Best phone number / Asked only when switched on. YES keeps the number they're texting from. | title / when (optional) |
| phone_reprompt | If the phone number couldn't be read / Sent when the reply isn't a phone number or YES. | title / when (branch) |
| prompt_email | Email address / Asked only when switched on. SKIP is allowed. | title / when (optional) |
| email_reprompt | If the email couldn't be read / Sent when the reply isn't an email address or SKIP. | title / when (branch) |
| slot_unavailable | When the time is already taken / Sent when your calendar shows that time busy. | title / when (branch) |
| booking_confirmation | Booking confirmation / Sent only after the appointment is on your calendar. | title / when |
| booking_error | When the calendar failed / Sent if the appointment couldn't be added to your calendar. It tells the customer no booking was made. | title / when (branch) |
| followup_1 | First reminder / Sent [2 hours] after the first text if there's no reply. | title / when (delay from Schedule) |
| followup_2 | Last reminder / Sent [1 day] after the first reminder. After this the assistant stops texting. | title / when |
| handoff_ack | Steps-back text / Sent when the customer asks for the owner or the assistant can't help. | title / when; the step heading stays "When the assistant steps back" (fix pass; "Hand-off text" is ruled out by the banned-words rule) |
| handoff_ack_safety | When someone may be in danger / Sent when a text mentions danger. | title / when |
| opt_in | Reply to START / Sent when a customer texts START. | title / when |
| help | Reply to HELP / Sent when a customer texts HELP. The number it shows is set on the Phone page. | title / when |
| opt_out_ack | Reply to STOP / Sent once when a customer texts STOP. Nothing follows it. | title / when |
| opt_out_suffix | Opt-out line / Added to the first text, both reminders and the START and HELP replies when they leave out the word STOP. | title / when |

### Rules shown inside the editor

| key | text | where |
|---|---|---|
| rule_stop | Phone companies require "Reply STOP to opt out." If your wording leaves out STOP, we add that line for you. | intro, both reminders, START and HELP replies |
| rule_stop_word | The word STOP stays. Phone companies check for it. | opt-out line |
| rule_booking_error | Must say "No booking was made" and can't use the word "call". The customer stays in the text thread. | calendar-failed card |
| rule_steps_back | This text must tell the customer someone will follow up. Don't ask them to call, and don't say they'll be put through to someone. | steps-back card |
| rule_steps_back_destination | What happens next: (1) TextBack stops texting this customer. (2) Their name, number and message go to FluxWorks. (3) FluxWorks passes them to you. You follow up; the text promised the customer someone would. | three numbered steps on both steps-back cards, in view (not inside the editor); the rule line and, on the danger card, the 911 rule stay above it |
| rule_safety | Must tell people to call 911 if anyone is in danger, and must say someone will follow up. | danger card |
| rule_paragraph | Sent as one paragraph. Up to 480 characters. | every editor, help line |

Destination label, from settings. Never promise the owner gets these unless that is configured:

| key | text | when |
|---|---|---|
| destination_chat | FluxWorks | alert channel is the chat app and a destination is set ("These go to FluxWorks."); never "the FluxWorks operator" (m30) |
| destination_log | a log FluxWorks can read. Nobody is alerted. Ask FluxWorks to set up where these should go. | alert channel is "log" |
| destination_off | These go nowhere yet. FluxWorks turns this on when your account is set up. | alert channel is off or the destination is "unconfigured" (replaces the whole rule_steps_back_destination line) |

### Badges, cost line, inserts, switches

| key | text | where |
|---|---|---|
| badge_state | Customized / Standard wording / Unsaved / Not saved | card head pill: saved custom / nothing custom (caption in the foot) / edited / rejected save |
| badge_asked | Asked / Not asked | optional question, read-only view |
| optout_added | STOP line added for you · [cost line] | receipt line, when the line was added; the · is real text so screen readers hear it (F9) |
| cost_line | 1 text · [N] characters with the notice / [N] texts · [N] characters with the notice / 1 text · [N] characters | receipt line: while texting approval is pending the count includes the 24-character network notice; after approval the plain form |
| cost_bill_symbol | Billed as [N] texts. The “[symbol]” symbol makes each text hold only 70 characters. Use “[plain symbol]” instead. / Replace — with - | amber line / its one-tap fix button |
| cost_bill_long | Billed as [N] texts. Customers still see one message. | amber line, long text with plain characters |
| cost_bill_links | Billed as [N] texts. The calendar links make this text long. Customers still see one message. | booking confirmation only: the honest note, never a fix button (m32) |
| cost_limit | [N] of 480 characters | shown from 420 characters |
| trial_notice | Until texting is approved, the network adds a short notice to each text, and the counts here include it. | one line in the page head, never inside a bubble; only while approval is pending (fix pass: one sentence) |
| chips_label | Insert a detail / Insert [label] | chip group accessible name / each chip's accessible name (F9); a chip adds a space where it would touch a word (m1) |
| chip_business_name | Business name | every text except the opt-out line |
| chips_confirmation | Job / Day and time / Address / Calendar links / Invite sentence / Customer's email / Google Calendar link / Outlook link / iCal link / Calendar links page | booking confirmation only, in this order after Business name; no chip for the booking's internal id |
| chip_contact_sentence | Your HELP number | HELP reply (m30) |
| chips_none | This text fills in no details. | editor, texts with no inserts |
| switch_phone | Also ask for the best phone number | phone question card head |
| switch_email | Also ask for an email address | email question card head |
| switch_off_note | Off. Customers skip this question. | under an optional card that is off |
| editor_open | Edit wording | disclosure; accessible name "Edit wording: [card title]" (F9) |
| editor_reset | Reset / Reset and save | per card, custom wording only / without JavaScript |
| step_save | Save every text | end of every step section, without JavaScript only (M8) |
| link_labels | Add to Google Calendar › / Add to Outlook › / Add to iCal › | in a preview bubble; the full link shows on tap |

### Example conversation (the rail)

| key | text | where |
|---|---|---|
| rail_title | Example conversation | rail heading |
| rail_show | Show | select label |
| rail_scenarios | Books a job / Unclear answers / No reply / Booking failed / Asks for the owner / Mentions danger / START, HELP and STOP | select options |
| rail_phone_sub | Text message | phone frame header line |
| rail_badges | Customer / TextBack | bubble role badges |
| rail_pills | Missed call · just now / No reply / Still no reply / Texts stop here / No booking was made | thread pills; "Texts stop here" also ends the No reply step on the page |
| rail_notice_hint | Each text in this example also starts with the network notice. | under the example phone, while approval is pending |
| trigger_label | When the customer sends something like | caption above the customer bubble shown on every fallback card |
| speaker_labels | Customer / [business name] | small visible labels over bubbles in the example conversation and on cards that show a customer reply |
| trigger_examples | Sometime next week / my cell / dana at gmail / Wednesday at 10 / Thursday at 10 / Can I just talk to the owner? / A big limb just came down on the power line by our house / START / HELP / STOP | customer bubble per card: time re-ask / phone re-ask / email re-ask / time taken / calendar failed / steps back / danger / START / HELP / STOP |
| rail_pill_booked | Booked · on your calendar / Booked · on the test calendar | thread pill: calendar connected / not connected |
| rail_divider_steps_back | The assistant steps back here | divider |
| rail_pill_details_sent | Customer's details sent to [destination label, short form] | thread pill after the divider ("…sent to FluxWorks") |
| rail_foot | Nothing is sent · names made up | caption right under the title "Example conversation", so "Example" appears once (fix pass) |
| rail_back | Back to editing | link |

Every TextBack bubble in the rail comes from running the real product code on the scripted customer
replies, so the thread can never show a step-back or a time reading the product would not make.

### Save bar, toasts and rejected saves

| key | text | where |
|---|---|---|
| savebar_changed | 1 text changed / [N] texts changed: [card title], [card title] / 1 setting changed / [N] settings changed / [N] changes / No unsaved changes / Show what changed | unsaved count (a question switch is a setting; texts and settings together read "[N] changes", m29) / resting state beside a visibly disabled Save / hidden hint on the count toggle |
| link_note | Each label is a link. The text count includes the full links. | under a bubble whose calendar links show as labels |
| draft_was | Was: [saved wording] | under an unsaved draft bubble |
| savebar_actions | Save / Saving… / Discard | primary / while posting / ghost |
| savebar_not_saved | Not saved · [N] texts changed | after a rejected save |
| savebar_nojs | Saves every text at once | without JavaScript |
| toast_saved | Saved. You changed “[card titles]”. / Saved. Back to standard wording: “[card titles]”. / Saved. You turned on “[question]”. / Saved. You turned off “[question]”. / Saved. No wording changed. | one notice under the header after the save's redirect, never over the title; one "Saved." then each part (m29) |
| expired_kept | This page was open a long time. Check your changes and press Save again. | Messages, a save whose page token expired: the typed wording comes back with a fresh token; nothing saved (m28) |
| toast_discarded | Changes discarded. / Undo | toast / its action |
| error_summary | Not saved. "[card title]" needs a change: [reason] Go to that text | top of the list; the last three words are a link |
| error_summary_kept | Your other edits are still here. Nothing was saved yet. | second line |
| draft_was | Was: [old text] | under a changed text's draft bubble until it is saved |
| phone_renamed | Saved. You changed “Business name”. / 2 texts still say “[old name]”. Update them to the new name? | one notice: the save, then the offer with Update them / Leave them |
| error_summary_fields | Not saved. [N] things need a change. | top of a settings form when several fields are wrong; each item links to its field |
| reason_unanswered_number | Take out "[phrase]". Customers stay in the text thread, so say you'll follow up by text, like "We'll follow up with you by text." | rejected save |
| reason_follow_up | Add the words "follow up", like "We'll follow up with you by text." | rejected save |
| reason_911 | Tell people to call 911 if anyone is in danger. | rejected save |
| reason_no_booking | Say "No booking was made" and leave out the word "call". | rejected save |
| reason_stop | Include the word STOP. Phone companies require it. | rejected save |
| reason_bad_insert | Something typed by hand isn't a detail we can fill in. Use the Insert buttons under the box, or remove it. | rejected save |
| reason_wrong_insert | This text can't fill in [names]. It can use: [chip labels]. / It fills in no details. | rejected save |
| reason_too_long | Shorten it to 480 characters or fewer. | rejected save |

## 5. Schedule (`/client/schedule`)

| key | text | where |
|---|---|---|
| schedule_title | Schedule | page heading |
| schedule_intro | The timing rules the assistant follows when it books. Reset puts a rule back to its default. | intro line |
| card_appointments | Appointments / How long each booking blocks on your calendar, and which time zone it uses. | card title / subtitle |
| duration | Appointment length / minutes | field label / unit after the field |
| duration_chips | 30 min / 45 min / 60 min / 90 min / 120 min / Custom | quick picks; the chip matching the field is selected, any other value selects none and shows Custom |
| duration_hint | Used for new bookings. 15 to 480 minutes, in steps of 5. / Default: [60] minutes | hint / default line |
| duration_applies | Applies right away, including customers mid-conversation. | under the field, before saving |
| duration_error | Appointment length must be 15 to 480 minutes, in steps of 5. / You tapped one length and typed another. Pick one: tap a length, or tap Custom and type the minutes. | error / without JavaScript, a tapped chip and a typed number that disagree (m36) |
| timezone | Time zone / Used for working hours, quiet hours and the times in texts. / Default: [Eastern (New York)] | label / hint / default line |
| timezone_applies | Applies right away to the times in texts. | under the field, before saving |
| timezone_error | Pick a time zone from the list. | error |
| card_hours | Working hours / When the assistant may book a job. | card title / subtitle |
| hours_mode | Any day, any time / Set hours | the two options |
| hours_hint | The assistant accepts any time a customer asks for if your calendar is free, including the middle of the night. / The assistant turns down times outside these hours and asks the customer for another time. | hint: any time / set hours |
| hours_any_warning | Customers can be offered times like 1 AM. Set your hours. / Use Mon–Fri, 8 AM–5 PM | warning while any-time is saved / its one-tap button (fills the grid; still needs Save) |
| hours_day_controls | Open on [Monday] / [Monday] opening time / [Monday] closing time | accessible names; visible text is the day name |
| hours_default | Default: Any day, any time | default line |
| hours_errors | Choose Any day, any time or Set hours. / Set at least one open day, or choose Any day, any time. / Pick times from the list. / [Monday]: opening time must be before closing time. / [Monday]: the hours are shorter than one appointment ([60] minutes). | errors |
| hours_corrupt | Your saved working hours couldn't be read, so every time counts as open until you save again. | warning |
| card_quiet | Quiet hours / Reminders and retried texts wait until quiet hours end. Still sent right away: the first text after a missed call, replies to a customer who is texting, and the START, HELP and STOP replies. | card title / subtitle |
| quiet_controls | Quiet hours / Hold reminders between / and / Off. Texts may go out at any hour. | switch (on = quiet hours apply) / legend / between the selects / under the switch when off |
| quiet_default | Default: [9:00 PM]–[8:00 AM] | default line |
| quiet_applies | Applies right away to reminders not yet sent. | under the quiet-hours controls, before saving |
| quiet_error | Pick quiet hours from the list. / Start and end can't be the same time. To turn quiet hours off, use the switch. | error / equal times with the switch on (M2); Off then On brings back the last custom times |
| card_reminders | Reminders / Two reminders when a customer never replies to the first text. After that the assistant stops texting. | card title / subtitle |
| reminder_1 | If there's no reply, send a reminder after / Default: [2 hours] | label / default line |
| reminder_2 | Send the last reminder after another / Default: [1 day] | label / default line |
| reminder_stop | Stop waiting for a reply after / Counted from the last reminder. The customer is marked "No reply" on Home. / Default: [2 days] | label / hint / default line |
| reminder_errors | Reminder delays must be between 5 minutes and 14 days. / The waiting time must be between 1 hour and 30 days. | errors |
| reminder_consequence | A reminder that is already scheduled keeps its time. Later reminders use the new delays. | note |
| schedule_reset | Reset / Reset and save | per-rule ghost button; accessible name "Reset [rule]"; with JavaScript it resets in place and waits for Save; without it "Reset and save"; hidden while the rule is at its default (m11) |
| schedule_save | Save | primary |
| schedule_toast | Saved. You changed “[rule]”. / Saved. | toast naming only what changed, then each changed rule's own note word for word (duration_applies, timezone_applies, hours_applies, quiet_applies, reminder_consequence; with several rules "[rule]: [note]"); no note for the waiting time; "Saved." when nothing changed (fix pass m10) |
| schedule_unsaved | 1 rule changed: [rule] / [N] rules changed | sticky bar above the nav while unsaved |
| hours_day_words | Open / Closed | word beside each day switch |
| hours_any_note | Sets Mon–Fri, 8 AM–5 PM below. Tap Save to keep it. | under the Use Mon–Fri button |
| hours_applies | Applies right away to times the assistant offers. Bookings already made stay as they are. | under the hours, before saving |

## 6. Calendar (`/client/calendar`)

| key | text | where |
|---|---|---|
| calendar_title | Calendar | page heading |
| calendar_intro | The assistant offers only times that are free on this calendar, and adds every booking to it before the customer gets a confirmation. | intro line |
| cal_connected | Connected / Google Calendar / Bookings go here: [calendar name]. | state word / title / body (no "Connected as": the account is not stored) |
| cal_connected_buttons | Reconnect Google Calendar | text link under the body; the picker below replaces "Use a different calendar" |
| cal_not_connected | Not connected / No calendar yet / No calendar of yours yet. Until you connect one, bookings go on a test calendar you can't see. / Connect the Google account that owns your business calendar, so the assistant offers your real free times and books onto your calendar. | state word / title / body (same words as Home) / why, above the Connect button |
| cal_not_connected_no_web | To book onto your own calendar, it has to be connected. Connecting from this page isn't set up for your account yet. FluxWorks sets this up for you. | second paragraph when there is no Connect button, above Text FluxWorks support |
| cal_waiting | Waiting on FluxWorks / FluxWorks connects your calendar for you. / Until then, bookings go on a test calendar you can't see. / Text FluxWorks support | not connected and no web client: state word (clock node) / body / second line / sms button only with a support contact (P3; replaces cal_not_connected_no_web on the page) |
| cal_connect | Connect Google Calendar / Opening Google… | primary when the Google web client is configured / while posting |
| cal_no_connect | Connecting from this page isn't set up for your account yet. FluxWorks sets this up for you. / Text FluxWorks support | body when no web client / button (sms link) shown only when a support contact is configured |
| cal_reconnect | Reconnect needed / Google disconnected the calendar, so bookings are paused until you reconnect. Customers are told no booking was made. | state word / body |
| cal_unreadable | Couldn't be read / TextBack couldn't read the calendar connection. Bookings are paused until you reconnect. | state word / body |
| cal_asks | What Google will ask: (1) You pick the Google account that owns your business calendar. (2) Google asks you to let TextBack see and edit your calendars. TextBack uses this only to find free times and add bookings. (3) Afterwards you choose which calendar it uses. | disclosure, open while not connected |
| cal_picker | Which calendar should the assistant use? / Free times are checked on this calendar and new appointments are added to it. / (main calendar) / In use / Use this calendar | legend / hint / after the main calendar / pill / button |
| cal_picker_error | Pick one of the calendars listed. | error |
| cal_picker_only | This is the only calendar this account can add appointments to. | empty state, one calendar |
| cal_toast_picked | Saved. The assistant now books on [calendar name]. | toast |
| cal_errors | Google didn't give TextBack calendar access. Try connecting again. / Connecting a calendar isn't set up for this account yet. | notices |
| avail_title | Next free times on [calendar name] / Test calendar, not yours | availability card title: connected / nothing connected |
| avail_intro | The first three free start times for a [60]-minute appointment in the next 14 days, inside your working hours. / Shows how the check works. These times are not from your calendar. | card intro: connected / test (fix pass: the length is said once here) |
| avail_row | [Mon, Oct 19] · starts at [1:30, 2:00, 2:30 PM] | one row per day of free start times; never ranges, so 30-minute steps never read as overlapping (fix pass) |
| avail_button | Check free times / Checking… | button / while posting |
| avail_caption | Checked just now · next 14 days · working hours [Mon–Fri, 8 AM–5 PM] | under results |
| avail_empty | No free [60]-minute time in the next 14 days inside your working hours. | empty result |
| avail_unreachable | Couldn't reach Google Calendar. Try again in a minute. | error |
| avail_reconnect_first | Reconnect the calendar first. | replaces the button when reconnect is needed |

## 7. Phone (`/client/phone`)

### Business and numbers

| key | text | where |
|---|---|---|
| phone_title | Phone | page heading |
| phone_intro | Your business name, the numbers TextBack uses, and call forwarding. | intro line |
| card_business | Business | card title |
| business_name | Phone & business / Business details / Business name / Used in every text. The first text is shown below. / In the first text / Save business details | Phone page h1 / first section (its own form: name, first-text preview, HELP number) / label / hint / preview eyebrow / that form's Save |
| business_name_error | Enter a business name of 1 to 60 characters. / A business name can't use curly or angle brackets. Take them out. | error / the name has { } < or > (M7) |
| business_name_symbol | This name has a [symbol], which makes each text hold only 70 characters. | amber line under the field, live while typing, when the name has a symbol outside the plain text alphabet (M7) |
| rename_offer | 2 texts still say “[old name]”. Update them to the new name? / Update them / Leave them / 1 text still says “[old name]”. Update it to the new name? / Update it / Leave it / Updated [N] texts. / Kept the texts as they are. / Kept the text as it is. | offer inside the save notice / buttons / one-text offer and buttons (m18) / notices after each choice (m17) |
| card_numbers | Numbers / This is the number customers call. TextBack never changes it. | card title / subtitle (m31) |
| business_line | Your business number / The number customers call. Calls you don't answer forward from here to the texting number. | label / hint |
| business_line_errors | Enter your business number as 10 digits, area code first, or leave it blank. / Your business number and the texting number can't be the same. | errors |
| texting_number | Texting number / Set up by FluxWorks. It can't be changed here. / Not assigned yet. FluxWorks sets this up for you. | read-only row / note under it, exactly this / when no number is on the account |
| owner_mobile | Your mobile / Sign-in codes come to this number. If you change it, we text a code to the new number and nothing changes until you enter it. | label / hint |
| owner_mobile_error | Enter your mobile as 10 digits, area code first. | error under the field; the page also shows an error summary (multi-field form) |
| phone_error_summary | Not saved. 1 thing needs a change: | error summary heading on Phone, one link per field |
| phone_unsaved | 1 change: [field label] / [N] changes | sticky bar above the nav while unsaved |
| phone_toast | Saved. You changed “[field label]”. / Checks start again because the business number changed. | toast naming what changed / added when the business number changed and was set before (m15) |
| owner_mobile_status | This is the number that signs you in. / Save to text a code to [new number]. | status line: unchanged / changed |
| help_number | Number in the HELP reply / Shown when a customer texts HELP. Leave blank to show [texting number]. Customers are never transferred to it; the assistant handles the texting. | label (tagged Optional) / hint |
| help_number_error | Enter the phone number as 10 digits, area code first, or leave it blank. | error; US numbers only, 10 digits with an optional +1 (m20) |
| phone_save | Save / Saved. / Code sent to [new number]. Your mobile changes after you enter it. | primary / toast / toast on the confirm step after a new mobile (m34) |

### Owner mobile, step two

| key | text | where |
|---|---|---|
| confirm_title | Confirm your new mobile | heading |
| confirm_steps | Details saved / Confirm number | stepper: done / current |
| confirm_intro | We texted a six-digit code to [new number]. Enter it to move sign-in to that number. It expires in ten minutes; until then codes still go to your current mobile. | intro line |
| confirm_code_label | Code from the text | field label |
| confirm_submit | Confirm new mobile / Confirming… | primary / while posting |
| confirm_keep | Keep my current mobile | secondary, exactly this |
| confirm_resend | Didn't get it? / Send the code again | text / ghost button |
| confirm_toasts | Saved. Sign-in codes now go to [new number]. Other devices stay signed in. / Kept your current mobile. | toast: confirmed (m7: sessions are not ended) / kept; Account's "Signed in as" reads the new number |

### Forwarding

| key | text | where |
|---|---|---|
| forwarding_heading | Call forwarding | section heading |
| forwarding_intro | Forward the calls you don't answer to your texting number. Your business number stays the same, and answered calls still reach you. | intro |
| forwarding_warning | Only forward busy and unanswered calls. Forwarding every call stops answered calls from reaching you. | warning, always visible |
| carrier | Your carrier / Verizon / T-Mobile / AT&T / Cricket / Other | legend / chips |
| carrier_error | Pick a carrier from the list. / Pick your carrier to see the codes. | error / note before a pick |
| codes_headings | Turn forwarding on / Turn it off | subheadings |
| code_rows | Busy and no answer / No answer / Busy / Unreachable / No answer, ring 20 seconds first / Reset all forwarding | row labels |
| code_copy | Copy / Copied / Select the code and copy it | button (accessible name "Copy [row label] code"), shown on plain http too / for 2 seconds after / when the browser can't copy and the code is left selected (M3) |
| code_note_verizon | Covers busy and no answer. Dial from your phone while on Verizon's network, then press Call. | note |
| code_note_tmobile | Dial each code, then press Call. | note |
| code_att | Android: open the Phone app, then Settings, then Call forwarding. Set "When busy" and "When unanswered" to [texting number]. / On iPhone, skip the Settings toggle: it forwards every call. Dial the codes instead. | steps / note |
| code_note_cricket | Cricket doesn't publish codes. Check with *#61# and *#67#. If forwarding won't turn off, call 611. | note |
| code_steps_other | Ask your carrier to forward only busy and unanswered calls to [texting number]. They call it conditional call forwarding. Never forward all calls. | steps |
| code_unverified | We haven't confirmed these codes on [carrier]. Make a test call afterwards to check. | warning under AT&T and Cricket |
| codes_need_number | The codes fill in once FluxWorks assigns your texting number. | note when no texting number |

### Checklist

| key | text | where |
|---|---|---|
| checks_heading | Is forwarding working? / [N] of 5 done / All 5 done. Forwarding works. | heading / progress / when complete |
| check_states | Done / Not yet / You checked this / Example / I checked this | state words: from evidence / none / manual tick; tag on checks 1, 2, 4 in the preview; label of the manual tick box |
| check_1 | A call to your business number reached TextBack / [Fri, Oct 23, 2:40 PM] from a number ending [0123] / No forwarded call recorded yet. From another phone, call your business number and let it ring out. Calls made straight to the texting number don't count. | step / evidence done / evidence not yet |
| check_2 | Exactly one text went out / Sent [Fri, Oct 23, 2:41 PM] / Waits for check 1. | step / evidence done / not yet |
| check_3 | An answered call sent no text / Answer a call to your business number, then confirm no text arrived. TextBack can't see answered calls, so this one is yours to tick. | step (manual) / hint |
| check_4 | The caller's own number came through / The text went to the caller's number, not your business number or the texting number. / Waits for check 1. / Enter your business number first. | step / evidence done / not yet / no business number |
| check_5 | You saved the turn-off code / Keep it where you'll find it: [turn-off code]. / Ask your carrier how to turn off forwarding, and write it down. | step (manual) / hint / hint with carrier Other (m16) |
| checks_evidence_note | Checks 1, 2 and 4 tick from calls TextBack recorded. / In this preview, checks 1, 2 and 4 come from example calls. | note: live / preview harness |
| checks_save | (retired) / Checks saved. | the checks post with the page's one Save / toast |

## 8. Account (`/client/account`)

| key | text | where |
|---|---|---|
| account_title | Account | page heading |
| account_signed_in | Signed in as [owner mobile as (980) 555-0123] | first line |
| account_change_mobile | To change the mobile that signs you in, open Phone. | note; "Phone" is a link |
| account_devices | This device / This device · signed in [Fri, Oct 23] · stays signed in until [Nov 22] / Remembered devices / Other signed-in devices / Another device · last used [Thu, Oct 22] / Only this device is signed in. / Example | card title / this device row / group of remembered sessions / group of the rest / their rows (device icon) / empty state / tag on seeded device rows in the preview |
| account_remember | Remember this device for 30 days / On. This device stays signed in for 30 days. / Off. This device signs out after 12 hours. / Saved. This device now stays signed in for 30 days. / Saved. This device now signs out after 12 hours. | switch / under it on / under it off / save notices (m4) |
| account_signout_everywhere | Sign out everywhere / Sign out of every device? You'll need a new code on each one. / Yes, sign out everywhere / Stay signed in | secondary button / inline confirm, scrolled fully into view above the bottom bar (m6) / confirm actions |
| account_signout | Sign out | button |
| account_toast_everywhere | Signed out everywhere. | toast on the sign-in page |

## 9. Shared

| key | text | where |
|---|---|---|
| nav | Home / Messages / Schedule / Calendar / Phone / Account | bottom nav on phones (Account behind the business name), sidebar on desktop with Account last; accessible name "Pages" |
| header | TextBack / [business name] / Account | product name / wraps to two lines, never cut short / menu trigger behind the business name |
| menu | Signed in as [owner mobile] / Account / Sign out / current page | account menu; on the Account page the business-name trigger is marked current (hidden text "current page") |
| foot | TextBack by FluxWorks | sidebar foot |
| skip_link | Skip to content | first focusable |
| toast_dismiss | Dismiss | toast close, accessible name |
| unsaved_bar | 1 text changed / [N] texts changed / Unsaved changes | sticky bar: Messages counts texts; other pages say Unsaved changes |
| unsaved_leave | Leave this page? Your changes aren't saved. | browser prompt on navigation with unsaved changes |
| error_generic | Something went wrong on our side. Nothing was saved. Try again. | notice |
| error_offline | You're offline. Nothing was saved. Try again when you're back online. | notice |
| expired | This page expired / Reload the page and try again. Nothing was saved. / Reload | heading / intro / button |
| session_ended | You were signed out. Sign in again to continue. | notice on the sign-in page after a session ends |
| not_found | That page doesn't exist. / Home | any /client page that doesn't exist: a portal page with a link Home, never JSON (status 404, m27) |
| page_title | [Page] · [business name] · TextBack | every page's <title> (F9) |
| empty_generic | Nothing here yet. | fallback empty state |

## Open

Strings whose exact wording depends on a fact I could not find in the repo or notes:

1. `cal_no_connect`, `messages_not_enabled`: no support contact exists in config; the design prompt says
   to add one. Both [support number] and [reply time] stay empty placeholders until Michael names the
   number and a reply time; neither row ships with made-up values.
2. `destination_chat`: the chat-app channel delivers to FluxWorks' private operator chat, not to the
   owner. The row now says only that FluxWorks sees them and the owner should ask how they'll be
   reached. A firmer line ("FluxWorks passes the customer's details to you") is a promise only
   Michael can confirm for paying clients; add it back only on his word.
3. The default steps-back text in `messages.py` ("The owner will follow up with you directly") is
   product code, not this deck, and is true only when a destination is configured. Decide whether
   the card shows a warning when the destination is "unconfigured" or the channel is off.
4. `cal_connected`: the connected Google account's email is not stored (only the calendar id and
   name). Either store it at connect time or drop "Connected as […]".
5. `account_devices`: the session table holds expiry and phone, not a device or browser name. Rows can
   only say "This phone" and "Another device" with dates unless the build records more.
6. `timezone`: the code default is UTC, which no owner wants as a "Default:" line. Decide whether the
   per-client default is set at onboarding or the line reads "Default: your time zone".
7. `home_approval_detail`: "has filed" assumes approval state is read live from the registry (the
   diff-review fix), not from staged files. Confirm before using it.
8. `link_labels`: the real public base URL is a long ts.net:8443 address. The label hides it in the
   bubble, but the tapped link still shows it. A short domain of our own needs Michael's decision.
9. `check_4`: the current evidence compares the call's "from" number with the business number. Confirm
   the plain-words claim matches what the code checks before it ships.


## Round 2 changes (d1, 2026-10-26)

The rows above already carry the new wording. The rules behind the changes:

- Phone numbers: every owner-facing number reads (980) 555-0123 and never breaks across lines. The standard phone re-ask text now says "like (704) 555-0123"; that is customer-facing default wording in `messages.py` and needs Michael's yes before the code changes.
- Errors never use a real-looking number as the example ("area code first"), because the old example matched the business number.
- Quotes are curly everywhere (“ ”).
- Booking confirmation preview: no invite sentence while the email question is off ("A calendar invite is on its way to …" is shown only when email is switched on).
- Cost lines include the network notice (24 characters) while approval is pending. With it, the STOP acknowledgment (opt_out_ack) bills as 2 texts instead of 1. Flag for Michael.
- Folded from d1/proposed-copy.json (deleted): nav "Pages", jump "On this page", heading "Messages", "Signed in as", insert markers [ ], "Replace — with -", "I checked this", "1 rule changed", "1 change", Open/Closed, the any-time note, "Used in every text. The first text is shown below.", Account "Save", error-summary heading.


## Round 3 changes (d1, 2026-10-26, last design round)

- Rows edited: messages_jump, rule_steps_back_destination, savebar_changed, cal_asks, signin_mobile_error, business_name, account_devices.
- Rows added: speaker_labels, duration_applies, timezone_applies, hours_applies, quiet_applies.
- The steps-back card keeps its title "When the assistant steps back"; owner-titled variants are not allowed because the owner may not be the one notified.
- Each consequence line ("Applies right away…") is a claim about scheduling behaviour; pin it to a test when it is built.

## Fix pass (2026-10-26, verification list)

- Default customer texts (P1, `messages.py`, product call): no possessive and no em dash. First text: "Hey, sorry we
  missed your call. This is the scheduling assistant for [business name]. What were you calling about?" Reminders:
  "Hi again from the scheduling assistant for [business name]. Still happy to get you on the calendar. What job do
  you need done?" / "Last check-in from the scheduling assistant for [business name]. Reply with the job you need and
  we'll set a time." Confirmation: "Booked: [job] on [when] at [address]. This is the scheduling assistant for
  [business name]. [invite sentence] [calendar links]". START: "You're subscribed to scheduling texts from [business
  name]. Msg & data rates may apply. Reply HELP for help or STOP to opt out." HELP: "This is the scheduling assistant
  for [business name]. Reply with the job type, location, and a time that works. Anything we can't handle by text,
  the owner follows up on.[Your HELP number] Msg & data rates may apply." Question 1: "What's the job you need done?
  For example: tree removal, trimming or stump grinding."
- Sample values (P5): Tree trimming, 412 Maple St, Charlotte, Dana Whitfield, Thursday at 10.
- Every successful save answers with a redirect and a one-time notice (M1); a rejected save answers in place.
