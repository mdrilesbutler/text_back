# Competitor settings and setup screens — research for candidate C (2026-10-26)

Scope: owner-facing settings/setup screens of Podium, Hatch, Goodcall (docs/COMPETITOR-MATRIX.md)
plus Jobber, Housecall Pro, Numa and GoHighLevel. Public pages only: help centers, docs,
marketing pages. No sign-ups, logins, trials or API keys. `tvly` and the Playwright browser were
not installed on this box, so evidence comes from WebSearch and WebFetch of the pages cited.

Evidence labels used below:
- **[F]** page fetched and read directly.
- **[S]** seen only in a search-result snippet of the page (page itself JS-rendered or not fetched).
- **unknown** = not found on any public page; do not assume.

Nobody in this set publishes screenshots of their settings pages as text, so phone-layout
findings (section 7) are thin and mostly "unknown". Treat the carrier-code tables as examples of
*presentation*; verify the codes themselves against carriers before shipping.

## Summary — what to copy, what to avoid

1. COPY Jobber's six-step wizard that ends with a literal "Test your Receptionist" step and a
   final "Receptionist is set up!" state, plus a dashboard Status block showing On/Off per channel.
2. COPY Numa's "Settings > Phone numbers > Test my setup" button and its one-line manual
   fallback: "call your business's phone number from your personal phone … you should hear …".
3. COPY GoHighLevel's split between ALL CALLS and MISSED CALLS codes per carrier and its
   three-point verification (reaches the agent, follows the flow, no repeated calls/loops).
4. COPY Goodcall's launch gating language: "Nothing changes until you approve it", practice
   scenarios marked "Passed", and the owner chooses "every call" vs "only missed calls".
5. COPY Housecall Pro's missed-call rule: the text must include the company name, and the
   three-way hours scope "During business hours / Outside business hours / Any time of day".
6. COPY Hatch's per-day rows with an on/off toggle per day and an inherit/custom dropdown.
7. AVOID GHL's visible `{{contact.first_name}}` / Hatch's `[[Contact First Name]]` tokens and
   "Custom Values"; show inserts as plain-label chips (Part 2 already requires this).
8. AVOID jargon these tools lean on: DND, A2P 10DLC, toll-free verification, sub-account,
   location, workflow recipe, IVR, call flow widget, Simul-Ring, hunt group, Voice AI.
9. AVOID forward-all-only instructions (Hatch's card forwards *all* calls; Goodcall's Verizon post
   leads with *72) without the "answered calls stop reaching you" warning.
10. AVOID dead ends: none of the seven shows a status that contradicts another step, but none
    except Jobber and Goodcall shows "is it working" in one line either — that is C's opening.

## Podium

Official help center moved to a Salesforce site (help.podium.com → podium.my.site.com) that
renders only via JavaScript; WebFetch returned a "Loading / CSS Error" shell twice. Claims below
are therefore [S] from search snippets or [F] from podium.com marketing pages.

1. **Is it working**: unknown. No public status/health page found.
2. **Setup checklist**: unknown. The April 2023 what's-new page only says "Phones Settings" holds
   number management and that Missed Call Auto Reply exists:
   "Automatically send a text message reply to every missed caller." [F]
   https://www.podium.com/whats-new/whats-new-in-podium-april-2023
3. **Message editor**: templates are created from "the More tile, then Settings" and used in
   Automations, Payments, Reviews, Bulk Messages, Surveys [S]
   https://help.podium.com/hc/en-us/articles/360039896853-Creating-Editing-Messaging-Templates
   Placeholder display, preview, character count, reset: unknown.
   After-hours switch-to-text template example: "Thanks for reaching out to us! We're closed
   now, but we'll give you a text back as soon as we open tomorrow." [F]
   https://www.podium.com/whats-new/whats-new-in-podium-improved-after-hours-call-routing
4. **Call forwarding**: unknown (Podium Phones is a VoIP system; forwarding docs not public).
5. **Business hours**: Settings > Your Business > Business Hours; default 9–5 Mon–Fri; special
   hours for holidays; "After-Hours Responder" toggle with a custom message; if you text a customer
   manually after hours the responder pauses for that customer for 60 minutes; after-hours
   missed-call and voicemail settings live under Settings > Phones [S]
   https://help.podium.com/hc/en-us/articles/360057143993-Setting-Up-Business-Hours
   Per-number after-hours behaviour is supported [F] (after-hours routing page above).
6. **Language**: plain, customer-voice examples ("after hours", "voicemail greeting"). The
   60-minute pause rule is a good *consequence line* pattern: it tells the owner what the
   automation will NOT do after they act.
7. **Phone layout**: unknown.

## Hatch

Docs at docs.usehatchapp.com (Mintlify, fetchable).

1. **Is it working**: no status or health indicator mentioned anywhere in workspace settings [F]
   https://docs.usehatchapp.com/how-to-use-hatch/workspace-settings/overview
2. **Setup checklist**: none. Settings are three tabs: General, Features, Team [F] (same page).
   After saving a forwarding number "the card shows as enabled" — a card-level state word [F]
   https://docs.usehatchapp.com/how-to-use-hatch/workspace-settings/how-to-setup-call-forwarding-for-your-workspace.md
3. **Message editor**: campaign templates show merge fields as double-bracket tokens:
   "Hi [[Contact First Name]], this is [[User First Name]] with [[Details Company Name]].
   Thanks for texting us!" Some templates ship with raw instructions inside the token:
   "[[YOU MUST MANUALLY INSERT LINK HERE]]". Opt-out line: "Reply END to stop texts." After
   "Use Template" you can change wording, add/remove messages, change channels. Preview,
   character count, reset: unknown [F]
   https://docs.usehatchapp.com/getting-started/messaging/hatch-campaign-templates
   The after-hours SMS also accepts "[[Contact First Name]]" snippets [F] (business-hours page).
4. **Call forwarding**: Workspace Configs > Features > Call Forwarding card > enter number >
   Save. "all calls coming into this workspace will be redirected to that number." Turn off =
   trash icon; "Calls will return to ringing in Hatch as normal." No conditional option, no
   warning, no test step [F] (forwarding page above). Hatch is the inbound destination here, not
   the owner's carrier, so this is a different problem from C's.
5. **Business hours**: Workspace Configs > General > Business Hours. Top dropdown: inherit from
   organization / another workspace / "Custom Hours". With Custom Hours, one row per weekday,
   toggle on = open with open/close times, toggle off = closed. Save / Cancel. "After Hours"
   section has its own "Inherit From" dropdown; "Custom Response" reveals "Send SMS" toggle and a
   text field. Only managers can edit hours. Time zone lives in General Settings, not on the
   hours grid; copy-to-all-days: unknown [F]
   https://docs.usehatchapp.com/how-to-use-hatch/business-hours-features/workspace-level-business-hours.md
6. **Language**: "Workspace Configs", "Inherit From", "org-level" are internal-admin words. The
   per-day toggle itself is plain.
7. **Phone layout**: unknown (desktop-first rep tool).

## Goodcall

1. **Is it working**: marketing shows a practice-calls list where four scenarios (leak quote,
   price request, after-hours call, "ask for the owner") each show "Passed", and a weekly
   "Calls that became leads" count; no named status indicator [F]
   https://www.goodcall.com/how-it-works
   Help center: judge the agent by reading the Calls list (caller, time, what the agent heard, grey
   "action chips", a status for "beginning, middle and end" of each call) [F]
   https://help.goodcall.com/en/articles/8007516-calls-why-who-and-when
2. **Setup checklist**: Build → Test → Launch → Learn. "Hear it before any customer does."
   "It goes live on your line when you say so." "Nothing changes until you approve it."
   "Changed your mind? Roll back." [F] (how-it-works)
3. **Message editor**: n/a (voice agent). Owner briefs it "like a new hire"; changes shown as a
   removed/added diff ("You asked Gabi") [F] (how-it-works).
4. **Call forwarding**: "Keep your number, or get a new one"; guides for 24 carriers; owner
   chooses whether the agent answers every call or only missed ones [F] (how-it-works).
   Verizon post: *72 (all calls) + number + #, wait for tone; *71 = busy/no-answer only; *73 off;
   "Verify Call Forwarding": call your number from another phone; warns voicemail or conditional
   rules can override forwarding; check for typos in the number [F]
   https://www.goodcall.com/post/how-to-forward-calls-from-verizon-to-your-goodcall-agent
   Note: the post leads with forward-all (*72) and only lists *71 as an "option" — the ordering C
   must invert.
   Agent Settings: answer "immediately" vs "after no answer" (busy, outside hours, or ~15 s) [S]
   https://help.goodcall.com/en/articles/8007540-teach-your-agent-to-be-an-operator
5. **Business hours**: set in the account with holidays; example "Mon to Sat, 7 am to 6 pm" [F]
   (how-it-works). Hours can also be fed as a "Documents" upload (knowledge, not action) [S]
   https://help.goodcall.com/en/articles/12523771-how-to-use-the-documents-feature-in-goodcall
6. **Language**: strongest plain-language set in the sample. Owner-first verbs, no vendor words
   on the marketing surface. "Documents" vs "Skills" in the help center is internal jargon.
7. **Phone layout**: unknown.

## Jobber (Receptionist, powered by Jobber AI)

Help article fetched directly [F]:
https://help.getjobber.com/hc/en-us/articles/25315927533847-Receptionist-powered-by-Jobber-AI

1. **Is it working**: "Explore the Receptionist dashboard" — a Status section shows whether
   Receptionist accepts calls and texts; Text and Voice each show "On" / "Off"; enabled actions
   carry an "enabled" label; conversations are tagged General inquiry / Needs action / Request
   created / Assessment scheduled / Job scheduled / Took a message / Spam / Call escalated.
2. **Setup checklist**: six steps — 1 Set up your greeting, 2 What should Receptionist do
   automatically, 3 Who is in the loop, 4 Essential information, 5 Test your Receptionist
   (Receptionist calls your number), 6 "Receptionist is set up!". Pause behaviour is spelled out:
   while paused it "cannot book appointments or take other actions"; set up forwarding elsewhere.
3. **Message editor**: "SMS send back" is editable via an "Edit" control. Rules stated to the
   owner: sent to new callers, callers matching a client profile, callers who haven't had a
   text-back in 24 hours, and callers who haven't replied "STOP". Placeholders/preview/count:
   not mentioned. Greeting changes "may be reviewed and not saved if they misrepresent your
   business or could put callers at risk" — a safety cue worth echoing for the hand-off text.
4. **Call forwarding**: carrier-side; "after a certain number of rings or outside business hours,
   usually by dialing a code"; "check with your provider". Google Voice: turn off "Screen calls",
   turn off GV caller-ID masking, then enable "Answering delay" in Jobber (adds two rings).
   Disable the delay if the carrier already delays. No forwarding test call described; escalation
   number must differ from the business number. Dedicated number required.
5. **Business hours**: "Business hours" toggle under Phone greeting gives separate greetings and
   per-slot phone menus for open vs closed; off = one default greeting.
6. **Language**: "You control what it can and can't do." "Who is in the loop." Escalation
   keywords ("emergency", "speak to a manager") are owner words. Jargon: IVR, overage.
7. **Phone layout**: Jobber app bottom nav = Home, Schedule, (Timesheet), Search, Messages, More;
   settings = More > gear icon top-right; Home top bar holds settings, activity feed, messages;
   older and newer articles disagree on the exact tab set [S]
   https://help.getjobber.com/hc/en-us/articles/7061327071639-Jobber-App-Basics
   https://help.getjobber.com/en/articles/home-in-the-jobber-app/
   Whether Receptionist settings are editable in the app: unknown.

## Housecall Pro (Voice)

Voice Settings Overview fetched directly [F]:
https://help.housecallpro.com/en/articles/6750234-voice-settings-overview

1. **Is it working**: no overall status. Plan Usage widget warns when nearing a limit and errors
   when exceeded; Call Reasons has Active/Archived tabs. A red permission banner appears in the
   mobile app when a permission is missing [F]
   https://help.housecallpro.com/en/articles/8346509-voice-on-mobile
2. **Setup checklist**: none. Call flow is a widget list (Incoming Call, Call Hours, Simul-Ring,
   Send to Voicemail, Forward Call, Play a Greeting, Call Menu, Call Queue) saved with
   "Update Call Flow". Warning: "Updating a call flow during a call may cause that call to fail."
3. **Message editor**: Missed Call Automation — toggle or pencil to edit; "Customize message"
   button; "Add variable" dropdown for inserts; booking link insert if Online Booking is on;
   rule: "You must include your company name in the text so the customer knows who is texting."
   Scope selector: "During business hours" / "Outside business hours" / "Any time of day".
   Preview, character count, default/reset: unknown. Search snippet says the automation targets
   existing customers [S] — new-caller behaviour unknown.
4. **Call forwarding**: n/a for the owner's carrier (HCP is the phone system). Within the flow,
   "Forward Call" sends to an employee or external number with rollover.
5. **Business hours**: Call Hours widget: "Available 24/7" / "Use business hours from company
   profile" / "Use customized hours for calls". Call Menu has one menu per side (open hours,
   closed hours), up to five options; message repeats twice on no/invalid input.
6. **Language**: the three-way hours phrasing and the company-name rule are plain. Jargon:
   Simul-Ring, call flow, lead source, ring group, text-to-speech, Alpha.
7. **Phone layout**: bottom nav includes Customers, Schedule, Inbox, More (and Dashboard per one
   article); Inbox > Call Log has tabs All / Missed / Voicemails; "Voice settings can only be
   found in the HCP web portal" — settings are NOT editable on mobile [F] (voice-on-mobile) [S]
   https://help.housecallpro.com/en/articles/14742078-navigating-housecall-pro-new-navigation-experience

## Numa

Intercom help center, fetchable. Carrier article fetched directly [F]:
https://intercom.help/numa/en/articles/3149772-t-mobile-wireless

1. **Is it working**: section "How to Confirm It's Working": "Go to Settings > Phone numbers >
   Test my setup, or call your business's phone number from your personal phone. If nobody
   answers, you should hear your Numa Voicemail greeting." What the in-app test shows: unknown.
   Owner sees voicemails transcribed with audio, missed calls "kept on record", notifications on
   any device with the app [F]
   https://help.numa.com/en/articles/3139976-how-are-missed-calls-handled
2. **Setup checklist**: one carrier article per carrier (T-Mobile, AT&T, Verizon-family, Spectrum,
   US Cellular, Rogers, Telus, MetroPCS, Patriot, Freedom, Google Voice, Ooma…), each with the
   same headings: Setup Instructions / Alternate Instructions / How to Confirm It's Working /
   Troubleshooting / Turn off Call Forwarding. Mobile setup guide offers three options: keep your
   number and forward missed calls; switch to a Numa number; new line or port [F]
   https://help.numa.com/en/articles/3139977-setup-guide-for-businesses-with-mobile-wireless-phones
3. **Message editor**: whether the switch-to-text auto-reply is editable: unknown. Per-location
   auto-replies exist [S] https://help.numa.com/en/articles/4220183-how-numa-supports-multiple-locations
4. **Call forwarding**: T-Mobile: No Answer `**61*1` + number + `#`; Busy `**67*1`…; Not Reachable
   `**62*1`…; "Wait for a series of 'beeps' or other confirmation" after each; off = `##61#`,
   `##67#`, `##62#`. Alternate: the carrier's web portal. Troubleshooting: turn off any answering
   machine that picks up first; hunt groups need forwarding on every line; "Contact your phone
   provider to confirm forwarding is set up and active." Only conditional codes are given; no
   forward-all code and no warning about it [F]. Ring advice elsewhere: "We recommend 3-4
   rings" (Spectrum Business) and 12–15 s (MNSi) [S]
   https://intercom.help/numa/en/articles/4324674-mnsi-phone-setup
   https://help.numa.com/en/articles/3149749-spectrum-business
   Ooma: an "artificial delay" must be shorter than the ring group's voicemail [S]
   https://help.numa.com/en/articles/3311716-ooma-office
5. **Business hours**: unknown where edited.
6. **Language**: "Test my setup", "Turn off Call Forwarding", "don't hesitate to contact Numa
   support!" are the plainest forwarding words found. Jargon: hunt group, artificial delay.
7. **Phone layout**: unknown.

## GoHighLevel (LeadConnector) — Missed Call Text Back

Articles fetched directly [F]:
https://help.gohighlevel.com/support/solutions/articles/48001239140-where-and-how-to-configure-the-missed-call-text-back-feature
https://help.gohighlevel.com/support/solutions/articles/155000004201-call-forwarding-to-your-highlevel-phone-number
https://help.gohighlevel.com/support/solutions/articles/48000982605-business-profile-settings
https://help.gohighlevel.com/support/solutions/articles/155000006881-phone-number-edit-configuration-incoming-calls-settings-

1. **Is it working**: no status page. A failed send "is logged in the contact's conversation with
   the reason" — failure surfaces in the inbox, not on the settings page. Call status labels
   "Completed" vs "Voicemail" leak carrier behaviour (timeout > ~20 s makes a missed call show as
   "Completed").
2. **Setup checklist**: none. Path: Settings (bottom-left) > Phone System > Voice > "Voicemail &
   Missed Call Text Back" > "Missed Call Text Back". Checkbox "Enable Missed Call Text Back";
   "Customize" opens a pop-up with "Enter message"; "Save". Older Business Profile path: type your
   number in the field below the feature, click "Send Test", HighLevel texts you the configured
   message — the only test-send control found in the whole sample.
3. **Message editor**: inserts via a "custom value tag icon"; tokens render as
   `{{contact.first_name}}` / `{{location.name}}` (third-party guides [S]); "They only populate if
   the system already recognizes the contact" — an honesty problem C avoids by only offering
   inserts the text can actually use. No default text, no preview, no character count on the
   page. Warning: the text may come from a different number than the one dialled (fallback
   order: dialled number → number previously used with this contact → default outbound → any
   eligible number); fix = verify a number (A2P 10DLC / toll-free verification).
4. **Call forwarding**: table per carrier with two columns, "ALL CALLS" and "MISSED CALLS"
   (unanswered or busy), plus deactivate: Verizon *72 / *71 / *73; AT&T mobile *21 / — / #21#;
   T-Mobile `**21*1…#` / `**61*1…#` / `##21#` or `##61#`; Xfinity and Spectrum Mobile *72 / *71 /
   *73; "Other carriers" *72 / *92 / *73 or *93. Redirect-loop warning: make sure the HighLevel
   number, forwarding number, user number and Business Profile number don't route back. Verify:
   (1) call the original number from a different phone, (2) confirm it reaches HighLevel and
   follows the inbound flow, (3) confirm it doesn't reconnect repeatedly or create multiple
   inbound calls. Incoming Call Timeout slider: 10–20 s recommended; warning shown outside the
   range but still saveable ("guidance only").
5. **Business hours**: Business Profile has a Time Zone field ("Automated events within campaigns
   work with this field"); Missed Call Text Back "works after hours" (FAQ). No hours grid for the
   text-back itself.
6. **Language**: heaviest jargon in the sample: sub-account, location, DND, A2P 10DLC, toll-free
   verification, custom values, number pool, call tracking number, workflow recipe, LC phone.
   Plain bits: "missed call", "text back", "a missed opportunity", "Answered calls never trigger
   a text."
7. **Phone layout**: unknown (web app; mobile app article covers inbound calling only).

## Pattern → rubric map

| Pattern (source tool) | Helps | Why |
|---|---|---|
| One-line Status block, On/Off per channel; wizard ends "…is set up!" (Jobber) | a1, d1, e2 | Answers "is it working" before anything else; real state, not copy |
| "Test my setup" button + manual fallback sentence (Numa) | b2, d1, d2 | Evidence-based tick; tells the owner what they should hear |
| Practice scenarios marked "Passed"; "Nothing changes until you approve it" (Goodcall) | a1, d2 | Launch gating in owner words; no surprise go-live |
| Every call / only missed calls as an owner choice (Goodcall) | a2, d2 | Frames conditional forwarding without the word "conditional" |
| ALL CALLS vs MISSED CALLS columns per carrier + deactivate code (GHL) | b1, b2, d2 | One table, codes to turn it off too; C adds the forward-all warning |
| Three-point verification: reaches, follows flow, no loops (GHL) | d1, d2 | Checklist ticks map to observable evidence |
| Headings Setup / Alternate / Confirm / Troubleshoot / Turn off (Numa) | a1, c2, e1 | Same skeleton on every carrier page; jump-chip targets |
| "Wait for a series of beeps or other confirmation" (Numa) | a2, b2 | Tells the owner what success sounds like |
| Hunt group / answering machine / "contact your provider" troubleshooting (Numa) | b2, d1 | Names the reasons a test can fail |
| Three-way hours scope: during / outside / any time (Housecall Pro) | a2, b2 | Plain scope words for quiet hours and reminders |
| "You must include your company name so the customer knows who is texting" (HCP) | d2 | A rule stated as a reason, model for the hand-off and STOP rules |
| Per-day rows with an on/off toggle (Hatch) | b2, c1 | Fits 390 px better than a 7×2 time grid; closed day = toggle off |
| Inherit / Custom dropdown above a settings block (Hatch) | b2 | Pattern for "Default: … / Reset" per rule |
| Card shows "enabled" after save (Hatch) | b2, e1 | State word on the card, not only a toast |
| After-hours responder pauses 60 min after you text manually (Podium) [S] | d2 | Consequence line: what the automation will NOT do after your action |
| Owner-voice example texts in docs (Podium, Hatch) | a2 | Copy reads like a text, not a spec |
| Greeting changes "may be reviewed and not saved if they misrepresent your business" (Jobber) | d2 | Precedent for refusing a hand-off text that lies |
| Failed send logged with the reason (GHL) | d1 | Failures are visible, not silent |
| Timeout out-of-range warning that still saves (GHL) | b2, d2 | Warn, don't block; C's "any time" hours warning |
| "Changed your mind? Roll back." (Goodcall) | b2, d2 | Reset/undo named in owner words |
| Settings not editable in the mobile app; red permission banner (HCP) | c1, c2 (by contrast) | C must do what HCP does not: full settings at 390 px |
| Bottom nav Home / Schedule / Messages / More; settings behind More > gear (Jobber) | c2 | Confirms owners expect a bottom bar; C puts Account behind the header name |
| Raw tokens `{{contact.first_name}}`, `[[Contact First Name]]`, `[[YOU MUST MANUALLY INSERT LINK HERE]]` (GHL, Hatch) | a2, e2 (avoid) | Exactly the braces Part 2 bans |
| Forward-all (*72) listed first, conditional as an "option" (Goodcall Verizon post) | d2 (avoid) | C leads with busy/unanswered and warns about forward-all |
| Inserts that "only populate if the system already recognizes the contact" (GHL) | d1 (avoid) | Never show an insert a first-time caller's text cannot fill |

## Gaps that could change a decision

- No tool's actual settings screenshots were readable; phone-layout patterns (sticky save, jump
  links, toast placement) are unknown across the sample. The ux-researcher track must carry c1/c2.
- Podium's official articles could not be rendered (JS shell + CAPTCHA warning); its hours and
  template claims are snippet-level only.
- Whether Numa's switch-to-text auto-reply, Jobber's SMS send-back and HCP's missed-call text
  show a preview, character/segment count or "reset to default" is unknown for all three. No
  competitor in the sample is confirmed to show segment counts; C's "Billed as 3 texts" line has
  no precedent here and should be user-tested, not assumed.
- Carrier codes differ between GHL's table (AT&T mobile *21) and Numa's (AT&T *92/*90, MNSi
  *92/*90); treat all codes as unverified until checked against the carrier.

## Sources (fetched directly unless marked [S])

- https://www.podium.com/whats-new/whats-new-in-podium-april-2023
- https://www.podium.com/whats-new/whats-new-in-podium-improved-after-hours-call-routing
- https://help.podium.com/hc/en-us/articles/360057143993-Setting-Up-Business-Hours [S]
- https://help.podium.com/hc/en-us/articles/360039896853-Creating-Editing-Messaging-Templates [S]
- https://docs.usehatchapp.com/how-to-use-hatch/workspace-settings/overview
- https://docs.usehatchapp.com/how-to-use-hatch/workspace-settings/how-to-setup-call-forwarding-for-your-workspace.md
- https://docs.usehatchapp.com/how-to-use-hatch/business-hours-features/workspace-level-business-hours.md
- https://docs.usehatchapp.com/getting-started/messaging/hatch-campaign-templates
- https://www.goodcall.com/how-it-works
- https://www.goodcall.com/post/how-to-forward-calls-from-verizon-to-your-goodcall-agent
- https://help.goodcall.com/en/articles/8007516-calls-why-who-and-when
- https://help.goodcall.com/en/articles/8007540-teach-your-agent-to-be-an-operator [S]
- https://help.getjobber.com/hc/en-us/articles/25315927533847-Receptionist-powered-by-Jobber-AI
- https://help.getjobber.com/hc/en-us/articles/7061327071639-Jobber-App-Basics [S]
- https://help.housecallpro.com/en/articles/6750234-voice-settings-overview
- https://help.housecallpro.com/en/articles/8346509-voice-on-mobile
- https://intercom.help/numa/en/articles/3149772-t-mobile-wireless
- https://help.numa.com/en/articles/3139977-setup-guide-for-businesses-with-mobile-wireless-phones
- https://help.numa.com/en/articles/3139976-how-are-missed-calls-handled
- https://help.numa.com/en/articles/3149749-spectrum-business [S]
- https://help.gohighlevel.com/support/solutions/articles/48001239140-where-and-how-to-configure-the-missed-call-text-back-feature
- https://help.gohighlevel.com/support/solutions/articles/155000004201-call-forwarding-to-your-highlevel-phone-number
- https://help.gohighlevel.com/support/solutions/articles/48000982605-business-profile-settings
- https://help.gohighlevel.com/support/solutions/articles/155000006881-phone-number-edit-configuration-incoming-calls-settings-
