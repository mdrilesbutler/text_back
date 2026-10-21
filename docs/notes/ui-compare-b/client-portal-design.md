# text_back client portal — IA and build design (comparison build B)

Path when saved: `docs/notes/ui-compare-b/client-portal-design.md`
Worktree: `/home/ubuntu/projects/text_back-ui-b` (branch `ui/compare-b`). Every path below is relative to that root unless absolute.
Binding inputs: BRIEF.md, DECISIONS.md, EXPLORER-REPORT.md (scratchpad). Where this document and DECISIONS.md differ, DECISIONS.md wins.

Conventions used throughout:
- "setting `x`" = row in `client_settings` with key `x`; "env default" = the value in `app.state.defaults[x]` captured at boot from `AppConfig`.
- "live" = takes effect for the next conversation without a restart.
- Copy rules: never "AI", never the substring "business line", never promise a person. The product is "the assistant" or "text_back". The three numbers are always "Your business number", "Texting number", "Your mobile". Nothing is phrased as a question to the owner. (The settings key `business_line` contains an underscore, so it does not trip the substring scan; it never appears in visible copy.)
- Status is always shown three ways: colour token + icon + word.

---

## A. Navigation and shell

### A.1 Nav items (final order; each layer adds its own)

| # | Label | Path | Icon (components macro `icon`) | Layer that ships the page |
|---|---|---|---|---|
| 1 | Home | `/client` | `house` | 1 |
| 2 | Messages | `/client/messages` | `chat` | 2 (layer 1 keeps the old string page under the new shell, see I.1) |
| 3 | Scheduling | `/client/scheduling` | `clock` | 2 |
| 4 | Calendar | `/client/calendar` | `calendar` | 3 (layer 1 keeps the old page) |
| 5 | Phone | `/client/phone` | `phone` | 3 (`/client/business` 301 → `/client/phone` from layer 3 on) |

Customers is not in the nav (design only; a link to nothing is a bug). `NAV` is a tuple in `client_portal.py` (builder-owned) passed to every `render()` as `nav`; `layout.html` iterates it and marks `active` by path prefix. Layer 1 ships `NAV = (Home, Messages, Business[/client/business], Calendar)`; layer 2 inserts Scheduling after Messages; layer 3 replaces Business with Phone (last). Nothing in the nav ever points at a route that does not exist in that commit.

### A.2 Header and account menu

- Left: business name as text (links to `/client`). Truncated with ellipsis at 24ch on phone.
- Right: an "Account" button rendered as `<details class="menu"><summary aria-label="Account menu">` with the owner's initials circle (first letters of the first two words of the business name). No JS required. On phone the open `<details>` is styled as a bottom sheet; on desktop as a 280px popover anchored right.
- Menu contents, top to bottom:
  1. Business name (bold) and "Signed in as (980) 555-0123" (owner mobile formatted by `policy.format_contact_number`).
  2. Form `POST /client/account/remember` (hidden csrf, hidden `remember` = 0 or 1) rendered as a switch row "Remember this phone for 30 days" with the current state; submitting flips it (see A.6).
  3. Link "Account" → `/client/account` (same two controls on a full page, for no-JS and screen readers).
  4. Form `POST /client/logout` (hidden csrf) button "Sign out" (secondary style).

### A.3 Layout

- Phone (≤ 899px): header 56px; content with 16px gutters; fixed bottom tab bar 64px + `env(safe-area-inset-bottom)`, five tabs, each ≥ 44×44, icon above an 11px label; active tab uses the accent token and `aria-current="page"`. Body gets `padding-bottom` so the last control is never under the bar.
- Desktop (≥ 900px): left sidebar 240px with the business name on top, five nav rows (icon + label, 44px tall, `aria-current="page"` on the active one), account block at the bottom; content column max 880px with 32px gutters. The Messages page uses a two-column grid at ≥ 1100px (editor 1fr, preview 360px sticky).
- Headings: one `<h1>` per page (the page title), sections `<h2>`, cards `<h3>`.

### A.4 Flashes and toasts

- Server flashes render inline in `layout.html` directly under the `<h1>`: `{% block flash %}` filled by the page from `error` / `notice` context. Error: `<div class="flash flash-error" role="alert">` with an icon, the word "Not saved" or "Error" in bold, then the reason. Success: `<div class="flash flash-ok" role="status">` with a check icon and the text. These survive without JS.
- Field-level errors render under the field (`<p class="field-error" id="err-{name}">`) and the input gets `aria-invalid="true" aria-describedby="err-{name} hint-{name}"`. The flash at the top repeats the first field error prefixed "Not saved: " so the existing tests (which look for "Not saved" + the reason) stay green.
- Toasts (JS only) are used for one thing: "Copied" after a copy-to-clipboard button. Region `<div id="toast" role="status" aria-live="polite">` sits above the tab bar on phone and bottom-right on desktop; auto-hides after 2.5s.

### A.5 Sign-in and verify screens (`templates/auth.html` shell, `pages/login.html`, `pages/verify.html`)

Sign-in (`GET /client/login`):
```
┌──────────────────────────────┐
│          text_back           │   (wordmark, small)
│  ┌────────────────────────┐  │
│  │ Sign in                │  │  h1
│  │ Enter your mobile.     │  │
│  │ We'll text a six-digit │  │
│  │ code.                  │  │
│  │ Your mobile            │  │  label
│  │ [ (980) 555-0123     ] │  │  tel, autocomplete=tel, inputmode=tel
│  │ [   Text me a code   ] │  │  primary, full width, 48px
│  └────────────────────────┘  │
└──────────────────────────────┘
```
- Error (bad digits), inline under the field and in the flash: "Enter the mobile number as digits, like 704 555 0123." (unchanged text).
- Always 303 → `/client/verify` on a well-formed number, whether or not it is the owner's (existing behaviour, keep).

Verify (`GET /client/verify`):
```
┌────────────────────────────┐
│ Check your phone           │  h1
│ Enter the six-digit code   │
│ we texted. It expires in   │
│ ten minutes.               │
│ [flash if error]           │
│ Sign-in code               │
│ [ 1 2 3 4 5 6 ]            │  inputmode=numeric autocomplete=one-time-code pattern=[0-9]{6}
│ [x] Remember this phone    │  <input type=checkbox name=remember value=1> (unticked by default
│     for 30 days            │   unless setting remember_default == "1")
│ [        Sign in        ]  │
│ Send a new code            │  link → /client/login
└────────────────────────────┘
```
- Error text unchanged: "That code is not right or has expired. Check the text or send a new code." The page must contain nothing that varies per request (no csrf, no nonce, no timestamps): test 10 needs two error bodies byte-identical.
- Success: 303 → `/client` (Home). Session TTL 12 h, or 30 days when `remember=1`; cookie `max_age` matches.

### A.6 Sessions and "remember this phone"

- `client_sessions` gains `remember INTEGER NOT NULL DEFAULT 0` (migration in H).
- `POST /client/verify` with `remember=1`: insert the session with `remember=1`, `expires_at = now + 30d`; otherwise `remember=0`, `now + 12h`.
- `POST /client/account/remember` (csrf): `remember=1` → `UPDATE client_sessions SET remember=1, expires_at=now+30d WHERE token_hash=?` and re-set the cookie with `max_age=30d`; `remember=0` → `remember=0, expires_at = MIN(expires_at, now+12h)` and cookie `max_age=12h`. Also stores setting `remember_default` ("1"/"0") so the verify checkbox remembers the preference. Flash: "This phone stays signed in for 30 days." / "This phone signs out after 12 hours."
- `_session()` is unchanged (it only checks `pending=0 AND expires_at > now`).

### A.7 General state pattern (every page)

| State | Pattern |
|---|---|
| Empty | A bordered grey panel with one sentence and at most one action, e.g. "No conversations yet. They appear here after the first missed call." No illustration. |
| Loading | Pages are server-rendered, so loading exists only for JS-enhanced buttons (Verify, Check availability, Copy): the button gets `aria-busy="true"`, is disabled, and its label changes to the present participle ("Checking…"). Without JS the form posts and the page re-renders. |
| Error | Flash `role=alert` at the top + field error under the field. Never a bare HTTP error page for a form (csrf mismatch stays a 400 JSON per the existing tests). |
| Success | Flash `role=status` "Saved." or the page-specific text; the saved values are re-rendered from the store, not echoed from the form. |

---

## B. Pages

### B.1 Home — `/client`

Purpose: tell the owner in one glance whether the three things that make the product work are working, what happened this week, and who texted last.

Phone (375):
```
┌──────────────────────────────┐
│ Oak & Pine Tree Care   (OP) │  header
├──────────────────────────────┤
│ Home                        │ h1
│ ┌──────────────────────────┐│
│ │ ✓ Calendar connected     ││ card 1 (status word + icon)
│ │ Tree jobs · Google       ││
│ │                 [Open ▸] ││
│ └──────────────────────────┘│
│ ┌──────────────────────────┐│
│ │ ● Forwarding 3 of 5      ││ card 2
│ │ Two checks left          ││
│ │         [Finish setup ▸] ││
│ └──────────────────────────┘│
│ ┌──────────────────────────┐│
│ │ ● Messaging registration ││ card 3 (omitted if dir unreadable)
│ │ In review · texts carry  ││
│ │ a trial tag until done   ││
│ └──────────────────────────┘│
│ This week                   │ h2 + "since Monday"
│ ┌─────┐┌─────┐┌─────┐┌─────┐│
│ │  4  ││ 11  ││  2  ││  1  ││ stat tiles
│ │Miss.││Texts││Book.││Hand.││
│ └─────┘└─────┘└─────┘└─────┘│
│ Last conversations          │ h2
│ Dana        ● Booked  Today │ rows (not links)
│ (704) 555-0188 ● New   Mon  │
│ …                           │
├──────────────────────────────┤
│ Home Msgs Sched Cal Phone   │ tab bar
└──────────────────────────────┘
```
Desktop (1024):
```
┌────────┬─────────────────────────────────────────────────────┐
│ Oak &  │ Home                                                │
│ Pine   │ ┌───────────────┐┌───────────────┐┌───────────────┐ │
│        │ │✓ Calendar     ││● Forwarding   ││● Registration │ │
│ ● Home │ │ connected     ││ 3 of 5 checks ││ In review     │ │
│  Msgs  │ │ Tree jobs     ││ [Finish setup]││ (no action)   │ │
│  Sched │ │ [Open]        ││               ││               │ │
│  Cal   │ └───────────────┘└───────────────┘└───────────────┘ │
│  Phone │ This week · since Monday                            │
│        │ [ 4 Missed calls ][ 11 Texts sent ][ 2 Booked ][ 1 Handed off ] │
│        │ Last conversations                                  │
│ (OP)   │ Name/number      Status      Last activity   Last message │
│ Account│ Dana             ● Booked    Today 3:02 PM   "Booked: tree removal…" │
└────────┴─────────────────────────────────────────────────────┘
```

Field table (Home has no inputs; this lists what each card reads):

| Element | Owner-facing copy | Source of truth | Default | Validation | Enforced by | Live |
|---|---|---|---|---|---|---|
| Calendar card | Headline per state: `ready` → "Calendar connected" + "{calendar name} · Google"; `reauth_required` → "Calendar needs reconnecting" + "Bookings are paused until you reconnect."; `unavailable` → "Calendar connection can't be read"; `none` → "No calendar yet" + "Bookings aren't recorded anywhere."; `managed` → "Calendar connected" + "{provider}, managed for you". Action label: ready "Open", reauth "Reconnect", unavailable "Open", none "Set up", managed "Open". All → `/client/calendar`. | `client_settings.calendar_status(state)` + `calendar_choices` | – | – | booking.py (calendar.is_free/create_event), booking_jobs.py | yes |
| Forwarding card | 5/5 → "Forwarding verified" (green, check); else "Forwarding {n} of 5" (amber, dot) + "{5-n} checks left" + action "Finish setup" → `/client/phone#forwarding` | `portal_data.forwarding_checklist(state)` (F.6) | 0 of 5 | – | n/a (evidence only) | yes |
| Registration card | see A.7/F; headline from file presence: none → "Registration not started"; brand only → "Brand submitted"; +campaign → "Campaign in review"; +order → "Number assigned"; complete → "Registered". Second line while incomplete: "Texts carry a '[SignalWire Free Trial]' tag until registration completes." No action. Card omitted entirely when the directory is missing/unreadable. | `TEXT_BACK_REGISTRATION_DIR` (default `~/.config/text_back/registration`), files `brand-response.json`, `campaign-response.json`, `order-response.json`, read-only, JSON `state` lowercased shown verbatim as a third line "Status: {state}" | – | – | carrier | n/a |
| This week tiles | "Missed calls", "Texts sent", "Booked", "Handed off"; caption "This week · since Monday" | `portal_data.week_counts(store, tz, now)`: window = Monday 00:00 in `state.timezone_name` → now; missed = `outcome_events.event_type='call.missed'`; texts = `sms_outbox.status='sent' AND kind!='login_code'`; booked = `calendar.event_created`; handed off = `lead.handoff_requested`. Parse timestamps in Python like brief.py (do not string-compare across offsets). | 0 | – | – | yes |
| Last conversations | row: name (from `conversation_fields.name`) or formatted phone; status pill (G.2 derivation); last activity ("Today 3:02 PM", weekday within 7 days, else "Oct 12"); last message snippet ≤ 60 chars (latest of inbound body / outbox body, outbox `'[sign-in code]'` excluded by kind). Rows are plain (no link) this session. | `portal_data.recent_conversations(store, limit=10)` (query in G.6) | empty | – | – | yes |

Actions: none besides the card links. Logout/remember in the header (A.2).

States: Empty tiles show 0; empty list shows "No conversations yet. They appear here after the first missed call."; registration card omitted when unreadable (not an error state); calendar `unavailable` is shown as the card's red state, not a page error. Loading: none. Success: none.

Intentionally not shown: no number purchase or "get a number"; no Customers link (page not built); no editable controls on Home; no per-row drill-down (would lead nowhere); no revenue (brief.py's attributed revenue is operator-entered and would read 0).

### B.2 Messages — `/client/messages`

Purpose: let the owner rewrite every text the assistant sends, see the whole conversation as a customer would, and never be able to save something the carrier or the product rules reject.

Phone (375): editor first, preview below under a "Preview" `<h2>` (the phone frame is 320px wide, centred, max-height 70vh, scrolls internally). A sticky bottom bar holds "Save messages" above the tab bar while the form is dirty (JS; without JS the button is at the end of the form).
```
┌──────────────────────────────┐
│ Messages                    │ h1
│ Edit any text. Words in     │
│ {braces} fill in by them-   │
│ selves.                     │
│ [flash]                     │
│ ▸ First text          (2)   │ group headers (<details open> on phone, plain h2 on desktop)
│  First text after a missed  │ field label
│  call                       │
│  Sent the moment a call     │ hint
│  goes unanswered.           │
│  ┌────────────────────────┐ │
│  │Hey, sorry we missed... │ │ textarea
│  └────────────────────────┘ │
│  {business_name}            │ chips
│  Default: Hey, sorry we…    │ grey, with [Reset]
│  135 characters · 1 text    │ counter (+ notes)
│  Opt-out line               │
│  ┌────────────────────────┐ │
│  │Reply STOP to opt out.  │ │
│  └────────────────────────┘ │
│  STOP stays in: carriers    │ lock note
│  require it.                │
│ ▸ Questions           (9)   │
│ ▸ Confirmation        (3)   │
│ ▸ Follow-ups          (2)   │
│ ▸ STOP and HELP       (5)   │
│ Preview                     │ h2
│ ┌──────[phone frame]──────┐ │
│ │ Missed call from Dana   │ │
│ │ ◻ Hey, sorry we missed… │ │
│ │          Tree removal ◼ │ │
│ └─────────────────────────┘ │
│ [     Save messages     ]   │
└──────────────────────────────┘
```
Desktop (1024, ≥1100 two columns):
```
┌────────┬──────────────────────────────────┬──────────────────┐
│ nav    │ Messages                         │ Preview (sticky) │
│        │ [flash]                          │ ┌──────────────┐ │
│        │ First text                        │ │ 9:41    ▂▄▆ │ │
│        │  First text after a missed call  │ │ Oak & Pine   │ │
│        │  [textarea]                      │ │ Tree Care    │ │
│        │  chips · Default · Reset · count │ │──────────────│ │
│        │  Opt-out line [textarea] lock    │ │ ◻ Hey, sorry │ │
│        │ Questions                        │ │   we missed… │ │
│        │  … 9 fields, two with switches   │ │  Tree removal◼│ │
│        │ Confirmation … Follow-ups …      │ │ ◻ What's the │ │
│        │ STOP and HELP …                  │ │   address…   │ │
│        │ [Save messages]                  │ │ …            │ │
└────────┴──────────────────────────────────┴──────────────────┘
```

Field table. All templates: source of truth = the messages JSON file at `state.messages.path` (`TEXT_BACK_MESSAGES_FILE`), which is itself the override store; default = `messages.DEFAULT_TEMPLATES[key]`; validation = `messages.validate_templates` (exact texts in C.4); enforced by `messages.MessageSet.render` via `policy.*_sms`, `followup.followup_sms`, `booking._queue_confirmation`; live = yes (mtime/size re-read on every `current()`). Max 480 chars after whitespace collapse (`maxlength=480` on the textarea too).

| Group | Key | Label | Hint (when sent) | Chips |
|---|---|---|---|---|
| First text | `intro` | First text after a missed call | Sent the moment a call goes unanswered. | `{business_name}` |
| First text | `opt_out_suffix` | Opt-out line | Added to the first text, follow-ups, START and HELP replies when they leave out the word STOP. Lock note: "STOP stays in: carriers require it." | none |
| Questions | `prompt_service` | The job | Sent only when the caller's first reply is blank; otherwise the first reply is taken as the job. | `{business_name}` |
| Questions | `prompt_location` | The location | Asked after the job. | `{business_name}` |
| Questions | `prompt_preferred_time` | Day and time | Asked after the location. | `{business_name}` |
| Questions | `prompt_name` | The name | Asked after the time. | `{business_name}` |
| Questions | `prompt_phone` + switch `ask_phone` | Best phone number (optional) | Switch label: "Also ask for the best phone number". Hint: Asked only when this is on. YES keeps the number they are texting from. | `{business_name}` |
| Questions | `prompt_email` + switch `ask_email` | Email address (optional) | Switch label: "Also ask for an email address" (exact; test). Hint: Asked only when this is on. SKIP is allowed. | `{business_name}` |
| Questions | `preferred_time_reprompt` | When the time can't be read | | `{business_name}` |
| Questions | `phone_reprompt` | When the phone number can't be read | Used only when the phone question is on. | `{business_name}` |
| Questions | `email_reprompt` | When the email can't be read | Used only when the email question is on. | `{business_name}` |
| Confirmation | `booking_confirmation` | Booking confirmation | Sent only after the calendar event exists. | `{service}` `{when}` `{location}` `{business_name}` `{invite_line}` `{calendar_links}` `{links_page}` `{google_link}` `{outlook_link}` `{ical_link}` `{invited_email}` `{event_id}` |
| Confirmation | `slot_unavailable` | When the time is taken | | `{business_name}` |
| Confirmation | `booking_error` | When the calendar can't be reached | Must say no booking was made and must not contain "call". | `{business_name}` |
| Follow-ups | `followup_1` | First nudge (no reply) | Sent {delay_1} after the first text if there's no reply. ({delay_1} from the scheduling settings, e.g. "2 hours") | `{business_name}` |
| Follow-ups | `followup_2` | Last nudge (no reply) | Sent {delay_2} after the first nudge. | `{business_name}` |
| STOP and HELP | `help` | Reply to HELP | The contact line comes from the Phone page. | `{business_name}` `{contact_line}` |
| STOP and HELP | `opt_in` | Reply to START | | `{business_name}` |
| STOP and HELP | `opt_out_ack` | Reply to STOP | | `{business_name}` |
| STOP and HELP | `handoff_ack` | When the owner needs to step in | Must promise a follow up (two words). | `{business_name}` |
| STOP and HELP | `handoff_ack_safety` | Safety hand-off | Must mention 911 and promise a follow up. | `{business_name}` |
| (hidden) | `fields` | – | Written as `service, location, preferred_time, name` + `phone` + `email` in that order when the switches are on (existing behaviour). | – |

Switch markup must be exactly `<input type=checkbox name=ask_email value=1 checked>` when on and the same without ` checked` when off (test_contact_fields asserts the on-markup and that the word "checked" is absent when off). Therefore on this page: no `aria-checked`, no CSS/JS inline, and no copy containing "checked" or "unchecked".

Textarea value rule (unchanged): the textarea shows the override when the current value differs from the default, otherwise it is empty with the default as `placeholder`; the "Default: …" line always prints the default text (so "Hey, sorry we missed your call" is in the HTML either way, test 4).

Actions:

| Action | Route | Method | CSRF | Success | Failure |
|---|---|---|---|---|---|
| Save messages | `/client/messages` | POST | yes | `write_message_file(path, overrides)` where overrides = non-blank fields + `fields`; `state.messages.current()`; flash "Saved. New conversations use these messages from now on." | Validate **per field** first (C.4) and render inline errors + top flash "Not saved: {first reason}"; nothing written. If `state.messages.path is None`: flash "Message editing is not set up for this account yet." and no Save button (test 7 needs "not set up" and no "Save messages"). |
| Reset (per field) | `/client/messages` | POST, submit button `name=reset value={key}` | yes | Server drops that key from the overrides, writes the file, re-renders with flash "Reset to the standard wording." JS enhancement: clears the textarea and updates preview/counter without a round trip (then Save persists). | as Save |
| Insert chip | none (JS only) | – | – | Inserts `{name}` at the caret of the field the chip belongs to; without JS the chips are plain `<code>` spans (reading the allowed names is still useful). | – |

States: Empty = not applicable (defaults always exist). Loading = none. Error = inline + flash; the preview still renders the attempted text so the owner sees what failed. Success = flash; the preview re-renders from the saved set. Read-only mode (no messages file): every textarea `disabled`, switches `disabled`, the explanatory flash above.

Intentionally not shown: no HTML/MMS, no per-customer sends, no "send me a test text" (would spend the trial quota and touch quiet hours logic), the `fields` order is not editable (a reorder would silently change which reply becomes the service), no editing of the voice greeting (cxml.py is not a template), nothing that mentions AI.

### B.3 Scheduling — `/client/scheduling`

Purpose: set the few timing rules the engine actually enforces — appointment length, working hours, quiet hours, nudge timing and time zone — with the env values as visible defaults.

Phone (375):
```
┌──────────────────────────────┐
│ Scheduling                  │
│ [flash]                     │
│ Appointments                │ h2 card
│  Appointment length         │
│  [ 60 ] minutes             │ number, step 5
│  (30)(45)(60)(90)(120)      │ chips
│  Default: 60 minutes [Reset]│
│  Time zone                  │
│  [ Eastern (New York)   ▾]  │ select
│  Default: UTC [Reset]       │
│ Working hours               │ h2 card
│  (•) Any day, any time      │ radio hours_mode=any
│  ( ) Set hours              │ radio hours_mode=set
│   Mon [x] [08:00▾]–[17:00▾] │ rows (hidden until "Set hours")
│   Tue [x] [08:00▾]–[17:00▾] │
│   …                         │
│   Sun [ ] Closed            │
│  Times a caller asks for    │
│  outside these hours are    │
│  declined and they're asked │
│  for another time.          │
│ Quiet hours                 │ h2 card
│  No texts between           │
│  [21:00▾] and [08:00▾]      │
│  [ ] No quiet hours         │
│  Default: 9:00 PM–8:00 AM   │
│ Nudges                      │ h2 card
│  First nudge                │
│  [ 2 hours ▾] after the     │
│  first text                 │
│  Last nudge                 │
│  [ 1 day ▾] after the first │
│  nudge                      │
│  Give up                    │
│  [ 2 days ▾] after the last │
│  nudge                      │
│  Default: 2 hours · 1 day · │
│  2 days [Reset]             │
│ [        Save          ]    │
└──────────────────────────────┘
```
Desktop (1024): same cards in a single 720px column; working-hours rows become a 7-row grid (day · switch · open · close) with the explanatory sentence to the right.

Field table:

| Field (form name) | Label · hint | Source of truth | Default | Validation (exact error) | Enforced at runtime | Live |
|---|---|---|---|---|---|---|
| `appointment_duration_minutes` | Appointment length · "How long each booking blocks on the calendar." | setting `appointment_duration_minutes` → `state.appointment_duration_minutes` | env `TEXT_BACK_APPOINTMENT_DURATION_MINUTES` (60) | integer, 15 ≤ n ≤ 480, n % 5 == 0. "Appointment length must be 15 to 480 minutes, in steps of 5." | `inbox._process` passes `state.appointment_duration_minutes` → `booking.book_appointment` (`slot_end`), `calendar_links` (:111) | yes (new bookings; old /a links change too — note shown: "Changes the length on new bookings.") |
| `timezone` | Time zone · "Used for working hours, quiet hours and the times in texts." | setting `timezone` → `state.timezone_name` and `FollowupPolicy.timezone_name` | env `TEXT_BACK_TIMEZONE` (UTC) | must be in the curated list (D.5) or equal the current value, and `ZoneInfo()` must resolve. "Pick a time zone from the list." | `handlers` (parse_preferred_time), `booking` (`when`), `followup.next_allowed_send_time`, `working_hours.slot_within_hours` | yes after rebuild (D.4) |
| `hours_mode` + `open_{dow}` + `{dow}_open` + `{dow}_close` | Working hours · radio "Any day, any time" / "Set hours"; per day a switch "Open" and two selects | setting `working_hours` (JSON, D.1) | absent = any day, any time (today's behaviour) | D.6: ≥ 1 open day when `set`; `open < close`; values from the 15-minute list ("24:00" allowed as close); each open day's window ≥ appointment length. Errors: "Set at least one open day, or choose Any day, any time." / "{Day}: opening time must be before closing time." / "Pick times from the list." / "{Day}: the hours are shorter than one appointment ({n} minutes)." | `booking.book_appointment` via `working_hours.slot_within_hours` (D.2), also on `booking_jobs.run_due_bookings` retries | yes |
| `quiet_hours_start`, `quiet_hours_end`, `no_quiet_hours` | Quiet hours · "No automated texts go out between these times. Replies to STOP and HELP are always sent." | settings `quiet_hours_start`/`quiet_hours_end` → `FollowupPolicy.quiet_start/quiet_end` | env (21:00 / 08:00) | HH:MM from the 30-minute list; `no_quiet_hours=1` stores both as the same value ("00:00"), which the engine treats as off. "Pick quiet hours from the list." | `followup.next_allowed_send_time` from `run_due_followups` and `sms.run_due_sms` (uses `store.sms_policy`) | yes after rebuild |
| `followup_delay_1`, `followup_delay_2` | First nudge / Last nudge · "after the first text" / "after the first nudge" | setting `followup_delays_minutes` ("120,1440") → `FollowupPolicy.delays_minutes` | env (120,1440) | each an integer 5 ≤ n ≤ 20160 (14 days). Ascending is NOT required: the engine treats each as a gap after the previous send (`sms._complete`). "Nudge delays must be between 5 minutes and 14 days." | copied into `completion_json` when the intro/follow-up is queued (`handlers.handle_voice_event`, `followup.run_due_followups`), applied by `sms._complete` | yes for new sequences; in-flight sequences keep their copied delays (hint says so) |
| `followup_expiry_minutes` | Give up · "after the last nudge; the lead is marked expired" | setting `followup_expiry_minutes` → `FollowupPolicy.expiry_minutes` | env (2880) | integer 60 ≤ n ≤ 43200 (30 days). "Give-up time must be between 1 hour and 30 days." | `sms._complete` → `advance_followup(next_action='expire')`, `followup.run_due_followups` | yes for new sequences |

Select presets (current value is always appended if not present): nudge 1 = 30 min, 1 h, 2 h, 4 h, 8 h, 1 day; nudge 2 = 2 h, 4 h, 1 day, 2 days, 3 days; give up = 1 day, 2 days, 3 days, 7 days. Labels are human ("2 hours"), values are minutes.

Actions:

| Action | Route | Method | CSRF | Success | Failure |
|---|---|---|---|---|---|
| Save | `/client/scheduling` | POST | yes | Save all keys, rebuild policy (D.4), flash "Saved. New conversations use these hours and delays." | Inline errors + "Not saved: {first reason}"; a `ValueError` from `FollowupPolicy.__post_init__` is shown as "Not saved: {message}"; nothing stored. |
| Reset (per card) | `/client/scheduling` | POST `reset={group}` (`appointments`, `hours`, `quiet`, `nudges`) | yes | `set_setting(key, None)` for the group's keys, rebuild, flash "Reset to the defaults." | – |

States: no empty state. Loading none. Error/success as above. A corrupt `working_hours` JSON in the DB renders as "Any day, any time" with a flash-level warning "Saved working hours couldn't be read; the assistant is treating every time as open until you save again." (fail open to today's behaviour; log it).

Intentionally not shown: handoff destination, delivery channel, pilot recipients, wiring mode (locked/operator); per-service durations (engine has one duration); buffer time between jobs (not enforced anywhere); holidays (not enforced); lead time ("earliest booking tomorrow") — not enforced today and out of scope.

### B.4 Calendar — `/client/calendar`

Purpose: show whether bookings are landing on a real calendar, let the owner connect or reconnect Google and pick the calendar, and prove it works with a live free/busy read.

Phone (375):
```
┌──────────────────────────────┐
│ Calendar                    │
│ [flash]                     │
│ ┌──────────────────────────┐│
│ │ G  Google Calendar       ││
│ │ ✓ Connected              ││ status row
│ │ Bookings go on Tree jobs ││
│ │ [Reconnect]              ││ secondary
│ │ Which calendar           ││ h3 (only if >1 choice)
│ │ (•) Personal (main)      ││ radios
│ │ ( ) Tree jobs            ││
│ │ [Use this calendar]      ││
│ └──────────────────────────┘│
│ ┌──────────────────────────┐│
│ │ Next free times          ││
│ │ [Check availability now] ││
│ │ Thu, Oct 22 · 4:00 PM    ││ results after POST
│ │ Fri, Oct 23 · 8:00 AM    ││
│ │ Fri, Oct 23 · 9:00 AM    ││
│ │ Checked just now · 60-min││
│ │ slots inside your hours  ││
│ └──────────────────────────┘│
│ ┌──────────────────────────┐│
│ │ Outlook / Microsoft 365  ││ "available on request" card
│ │ Available on request.    ││
│ │ Ask your operator to set ││
│ │ it up; there's nothing to││
│ │ click here yet.          ││
│ └──────────────────────────┘│
│ ┌──────────────────────────┐│
│ │ iCloud  … same pattern   ││
│ └──────────────────────────┘│
└──────────────────────────────┘
```
Desktop: Google card (left, 2/3) and availability card (right, 1/3) in one row; the two request cards side by side below.

Field table:

| Field | Label · copy | Source of truth | Default | Validation (error) | Enforced by | Live |
|---|---|---|---|---|---|---|
| status row | per state (E.1) | `client_settings.calendar_status(state)` | – | – | `booking`, `booking_jobs`, `reconnect.maintain_credentials` | yes |
| `calendar_id` radios | "Which calendar" · "Free times are checked here and bookings are added here." Option text = summary, "(main)" suffix for primary; the chosen one is wrapped in `<strong>` in the status line (test expects `<strong>Personal</strong>`) | setting `google_calendar_id` → `state.calendar.calendar_id`; options from setting `calendar_choices` | env `TEXT_BACK_GOOGLE_CALENDAR_ID` | must be one of the cached choices: "Pick one of the calendars listed." (exact; test) | `GoogleCalendarProvider.is_free/create_event/find_event` | yes |
| Check availability | button; results list | live `/freeBusy` + `next_free_slots` (E.4) | – | – | informational (same provider call booking uses) | n/a |

Actions:

| Action | Route | Method | CSRF | Success | Failure |
|---|---|---|---|---|---|
| Connect / Reconnect Google Calendar | `/client/calendar` `action=connect` | POST | yes | 303 → `create_link(state,'client',15 min)` (`/calendar/connect?token=…`) → Google consent → `/calendar/callback` → 303 `/client/calendar` (flash from query `error` only). Button text exactly "Connect Google Calendar" (status none/reauth/unavailable) or "Reconnect Google Calendar" (ready). | `can_connect` false → flash "Connecting a calendar is not set up for this account yet." and instead of the button the line "Connecting a calendar from this page is still being set up by your operator." (tests need "still being set up" / "not set up"). Denied consent: flash shows the callback's text "Google did not grant calendar access. Try connecting again." |
| Use this calendar | `/client/calendar` `calendar_id=` | POST | yes | `use_calendar`; flash "The assistant now uses {summary}." | "Pick one of the calendars listed." |
| Check availability now | `/client/calendar/availability` | POST | yes | Renders the Calendar page with the results panel filled (E.4). Button label while busy "Checking…". | `CalendarProviderError` → panel error "Couldn't reach {Google Calendar|the calendar}. Try again in a minute."; `reauth_required` → button replaced by "Reconnect first." |

States: see E.1. Empty results: "No free {n}-minute slot in the next 14 days inside your working hours." Loading: button `aria-busy`. Error: red panel inside the availability card (not a page flash). Success: list of three.

Intentionally not shown: no Microsoft/iCloud connect buttons (no owner flow exists → would be dead); no event list or calendar grid (not needed for the job); no "disconnect" (would pause bookings silently; operator task); no token/email/id strings from Google beyond the calendar summary.

### B.5 Phone — `/client/phone`

Purpose: the three numbers the product depends on, typed and checked; the HELP contact; and the forwarding setup with proof it works.

Phone (375):
```
┌──────────────────────────────┐
│ Phone                       │
│ [flash]                     │
│ Business                    │ h2 card
│  Business name              │
│  [Oak & Pine Tree Care   ]  │
│  Used in every text.        │
│ Numbers                     │ h2 card
│  Your business number       │
│  [(980) 555-0100] [Verify]  │ tel + secondary button (formaction)
│  The number customers call. │
│  It forwards here when you  │
│  don't answer. We never     │
│  change it.                 │
│  Texting number             │
│  [(980) 555-0177] [Verify]  │
│  The number texts come      │
│  from. It must already be   │
│  on this account.           │
│  ✓ Owned by this account    │ verify result (after Verify/Save)
│    and pointed at text_back │
│  Your mobile                │
│  [(980) 555-0123] [Verify]  │
│  Sign-in codes and alerts   │
│  go here. Changing it texts │
│  a code to the new number   │
│  first.                     │
│  Number shown in HELP       │
│  replies                    │
│  [(980) 555-0100]           │
│  Leave blank to show the    │
│  texting number.            │
│ [        Save          ]    │
│ Forwarding            #forwarding
│  Your carrier               │ h2 card
│  (Verizon)(T-Mobile)(AT&T)  │ radio pills name=carrier
│  (Cricket)(Other)           │
│  Turn forwarding on         │
│  *719805550177     [Copy]   │ code rows with Copy
│  Turn it off                │
│  *73               [Copy]   │
│  Checks                     │ h3
│  ✓ 1 A test call rang       │ evidence rows
│      through · Oct 19       │
│  ✓ 2 Exactly one text went  │
│      out                    │
│  [ ] 3 An answered call     │ manual checkbox (form)
│      sent no text           │
│  ✓ 4 Caller ID came through │
│  [ ] 5 Turn-off code saved  │
│  [Save checks]              │
└──────────────────────────────┘
```
Desktop: Business + Numbers card left (560px), Forwarding card right (sticky); checks list under the codes.

Field table (`{digits}` = national 10 digits of the texting number):

| Field (name) | Label · hint | Source of truth | Default | Validation (exact error) | Enforced at runtime | Live |
|---|---|---|---|---|---|---|
| `business_name` | Business name · "Used in every text, for example 'Thanks for calling {business_name}'." Input must render `value="…"` double-quoted (test expects `value="Oak &amp; Pine Tree Care"`). | setting `business_name` → `state.business_name` | env `TEXT_BACK_BUSINESS_NAME` | 1–60 chars after whitespace collapse: "Enter a business name of 1 to 60 characters." | `inbox` (every handler), `send_code`, voice greeting, `calendar_links` | yes |
| `business_line` | Your business number · "The number customers call. It forwards here when you don't answer. We never change it." | setting `business_line` (new) | "" (unset) | blank allowed; else `normalize_mobile`: "Enter your business number as digits, like 704 555 0123, or leave it blank."; must differ from the texting number: "Your business number and texting number can't be the same." May equal Your mobile (the owner's cell usually is the business number). | forwarding evidence only (F.6 step 4) | yes |
| `text_back_number` | Texting number · "The number texts come from. It must already be on this account." | setting `text_back_number` → `state.business_number` and `telecom.allowed_from_number` | env `TEXT_BACK_SIGNALWIRE_FROM_NUMBER` | blank = env default; else `normalize_mobile`: "Enter the texting number as digits, like 704 555 0123, or leave it blank."; then F.2 ownership/handler check with reasons "not a number this account owns" / "its voice/SMS handlers do not point at text_back" | `send_code` (from), `followup.run_due_followups` fallback sender, `reconnect` alerts, `SignalWireTelecom.send_sms_with_callback` sender guard | yes (both attributes set) |
| `owner_mobile` | Your mobile · "Sign-in codes and alerts go here. Changing it texts a code to the new number first." | setting `owner_mobile` → `state.owner_mobile`; pending in `owner_mobile_pending` | env `TEXT_BACK_OWNER_MOBILE` | required, `normalize_mobile`: "Enter your mobile as digits, like 704 555 0123." | `client_portal.login` | yes after code |
| `business_contact` | Number shown in HELP replies · "Leave blank to show the texting number." | setting `business_contact` → `state.business_contact` | env `TEXT_BACK_BUSINESS_CONTACT` | blank or `normalize_mobile`, stored formatted: "Enter the customer phone number as digits, like 704 555 0123, or leave it blank." (exact; test looks for "customer phone number") | `policy.help_sms` via `handlers` | yes |
| `carrier` | Your carrier · pills Verizon / T-Mobile / AT&T / Cricket / Other | setting `carrier` (new) | "" (no pill selected → codes section shows "Pick your carrier to see the codes.") | one of `verizon,tmobile,att,cricket,other`: "Pick a carrier from the list." | none (display) | yes |
| `check_answered_no_text`, `check_deactivation_saved` | manual checks 3 and 5 | setting `forwarding_checklist` JSON `{"answered_no_text": iso|null, "deactivation_saved": iso|null}` | both null | – | Home card roll-up | yes |

Actions:

| Action | Route | Method | CSRF | Success | Failure |
|---|---|---|---|---|---|
| Save (business + numbers) | `/client/phone` | POST | yes | Validate all; if `text_back_number` changed run F.2 (on success set setting + `state.business_number` + `telecom.allowed_from_number` when the attribute exists); save name/line/contact/carrier; if `owner_mobile` ≠ current → set `owner_mobile_pending`, `send_code(purpose="new mobile")`, render the confirm card (below) with heading "Confirm your new mobile" and the formatted new number; else flash "Saved." | Inline + "Not saved: {reason}". Name and contact are saved only when every field passes (change from today's partial save). |
| Verify (one field) | `/client/phone/verify` | POST, submit button `name=verify value=business_line|text_back_number|owner_mobile` (formaction, same form so typed values travel) | yes | Nothing is saved. Result line under the field: business number → "Looks good: (980) 555-0100."; texting number → "Owned by this account and pointed at text_back." (green) or the F.2 reason (red); mobile → same as current: "This is the number that signs you in."; different: "Save to text a code to (980) 555-0199." | Format errors as above, under the field. |
| Confirm new mobile | `/client/phone/confirm` `code=` | POST | yes | `check_code` → set `owner_mobile`, clear pending, flash "Saved. Sign-in codes now go to (980) 555-0199." | `CODE_FAILURE` text in the confirm card. |
| Keep current mobile | `/client/phone/confirm` `cancel=1` | POST (replaces the state-changing GET `/client/business/keep`) | yes | clear pending, flash "Kept your current mobile." | – |
| Save checks | `/client/phone/checklist` | POST | yes | Store ticks with timestamps; flash "Checks saved." | – |
| Copy code | JS only | – | – | Clipboard write + toast "Copied". Without JS the code is selectable text in a `<code>` element; Copy buttons are not rendered without JS (progressive enhancement adds them). | – |
| Old path | `/client/business`, `/client/business/confirm`, `/client/business/keep` | GET→301 `/client/phone`; POSTs → 307 to the new paths | – | – | – |

Confirm card (replaces the whole Numbers card while `owner_mobile_pending` exists): "Confirm your new mobile" · "We texted a six-digit code to **(980) 555-0199**. Enter it to switch sign-in to that number. It expires in ten minutes." · code input · [Confirm new mobile] · [Keep my current mobile] (secondary submit with `name=cancel value=1`).

States: Empty: texting number unset and env empty → field empty with hint "Ask your operator for the texting number assigned to you." Codes section without a texting number: "Enter your texting number above to fill in the codes." (codes shown with `<your texting number>`; no Copy). Loading: Verify buttons `aria-busy`. Error/success: as above.

Intentionally not shown: buy / port / provision / "get a number" / number search — never, anywhere; carrier login links; call-forwarding "test call" button (we cannot place calls); pilot allowlist; the SignalWire project id or space URL; the webhook URLs themselves (shown only as "pointed at text_back").

### B.6 Customers — DESIGN ONLY (see G)

Not built, not in the nav this session.

### B.7 Account — `/client/account`

Purpose: the two session controls, on a page as well as in the header menu.

```
┌──────────────────────────────┐
│ Account                     │
│ Oak & Pine Tree Care        │
│ Signed in as (980) 555-0123 │
│ ┌──────────────────────────┐│
│ │ Remember this phone for  ││ switch row = form POST /client/account/remember
│ │ 30 days            [on]  ││
│ │ Signed in until Nov 19   ││
│ └──────────────────────────┘│
│ [ Sign out ]                │ form POST /client/logout
│ To change the mobile that   │
│ signs you in, use the Phone │
│ page.                       │ link
└──────────────────────────────┘
```

| Field | Label | Source | Default | Validation | Enforced | Live |
|---|---|---|---|---|---|---|
| `remember` | Remember this phone for 30 days | `client_sessions.remember` for the current session; setting `remember_default` | 0 | 0/1 | `_session` expiry | immediate |

Actions: remember toggle (A.6) flash texts; Sign out → 303 `/client/login` (session row deleted when csrf matches; cookie always deleted).

Not shown: name/email profile (no such data), password (none), multiple users (none).

---

## C. Messages page detail

### C.1 Grouping (DECISIONS)

First text (intro, opt_out_suffix) · Questions (prompt_service, prompt_location, prompt_preferred_time, prompt_name, prompt_phone + ask_phone, prompt_email + ask_email, preferred_time_reprompt, phone_reprompt, email_reprompt) · Confirmation (booking_confirmation, slot_unavailable, booking_error) · Follow-ups (followup_1, followup_2) · STOP and HELP (help, opt_in, opt_out_ack, handoff_ack, handoff_ack_safety). Group headers show the count of fields that currently differ from default as a small "n edited" pill.

### C.2 Live preview script

Sample data (server passes it as `data-*` on `#preview`; JS reads it, never hard-codes): business "Oak & Pine Tree Care"; caller "Dana"; service "tree removal"; location "412 Maple St"; when "Thursday, Oct 22 at 4:00 PM EDT"; email "dana@example.com"; contact_line " Contact: (980) 555-0100." (from `business_contact`, else the formatted texting number, else ""); `calendar_links` = `"Add to calendar: Google {base}/a/1-000000000000/g Outlook {base}/a/1-000000000000/o iCal {base}/a/1-000000000000/i"` with `base = state.public_base_url` so the length matches a real send; `links_page = {base}/a/1-000000000000`; `google_link/outlook_link/ical_link` the three URLs; `event_id = "evt-0001"`; `invite_line` = "A calendar invite is on its way to dana@example.com." when `ask_email` is on else ""; `invited_email` likewise; delay labels from the current `FollowupPolicy` ("2 hours", "1 day").

Rendering rule per bubble = `render(key)` reimplemented in JS: fill allowed placeholders (unknown → ""), collapse whitespace, append `" " + opt_out_suffix` when key ∈ {intro, followup_1, followup_2, opt_in, help} and the raw template lacks `\bstop\b` (case-insensitive), prepend "[SignalWire Free Trial] " when `data-trial="1"`.

Ordered bubbles (◻ = outbound, ◼ = inbound sample reply, ▭ = dimmed "conditional" outbound, ⋯ = centred caption):

1. ⋯ "Missed call from Dana"
2. ◻ `intro`
3. ▭ `prompt_service` — caption "sent only if the first reply is blank"
4. ◼ "Tree removal"
5. ◻ `prompt_location`
6. ◼ "412 Maple St"
7. ◻ `prompt_preferred_time`
8. ◼ "Thursday at 4"
9. ◻ `prompt_name`
10. ◼ "Dana"
11. ◻ `prompt_phone` (only when ask_phone on)
12. ◼ "YES" (only when ask_phone on)
13. ◻ `prompt_email` (only when ask_email on)
14. ◼ "dana@example.com" (only when ask_email on)
15. ◻ `booking_confirmation`
16. ⋯ "If Dana doesn't reply"
17. ◻ `followup_1` — timestamp label "{delay_1} later"
18. ◻ `followup_2` — "{delay_2} after that"
19. ⋯ "If the time is taken" → ◻ `slot_unavailable`
20. ⋯ "If the calendar can't be reached" → ◻ `booking_error`
21. ⋯ "If a reply can't be read" → ◻ `preferred_time_reprompt`; ◻ `phone_reprompt` (ask_phone on); ◻ `email_reprompt` (ask_email on)
22. ⋯ "If Dana texts STOP" → ◼ "STOP" → ◻ `opt_out_ack`
23. ⋯ "If Dana texts HELP" → ◼ "HELP" → ◻ `help`
24. ⋯ "If Dana texts START" → ◼ "START" → ◻ `opt_in`
25. ⋯ "If Dana asks for a person" → ◼ "Can I talk to someone?" → ◻ `handoff_ack`
26. ⋯ "If Dana mentions an emergency" → ◻ `handoff_ack_safety`

Focusing a textarea scrolls the frame to its bubble (`scrollIntoView({block:'center'})`) and outlines it; typing updates that bubble on `input`. Each bubble has `data-key`. The frame has `aria-hidden="true"` (the textareas plus counters are the accessible representation); a visually hidden note before the frame says "Preview of the conversation with sample data."

### C.3 Segment counter

Computed on the **rendered sample** of the field (C.2 rule), by `portal.js`:

1. Classify: every char in the GSM-7 basic set counts 1 septet; `^ { } \ [ ~ ] | €` count 2; any other char (em dash "—", curly quotes, emoji) switches the whole message to UCS-2.
   GSM-7 basic set: `@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !"#¤%&'()*+,-./0-9:;<=>?¡A-ZÄÖÑÜ§¿a-zäöñüà`.
2. GSM-7: 1 text if septets ≤ 160, else `ceil(septets/153)`. UCS-2: count UTF-16 code units; 1 text if ≤ 70, else `ceil(units/67)`.
3. Display: "135 characters · 1 text" / "2 texts". Notes appended as small lines when they apply: "Includes the opt-out line." (suffix appended), "Includes the '[SignalWire Free Trial]' tag until registration completes." (`data-trial="1"`; the prefix is 24 chars / 26 septets because `[` and `]` are extension chars), "Uses a special character (—), so each text holds 70 characters." (UCS-2). At > 480 raw characters the counter turns red with "Over the 480-character limit."
4. Without JS: the counter is not rendered; the server-side `maxlength=480` and `validate_templates` still hold.

### C.4 Per-field validation mapping (server, `portal_messages.validate_field(key, text, merged)`)

For each submitted non-blank field: `validate_templates({**current_overrides, key: text})`; catch `MessageTemplateError` and attach `str(exc)` to that field. The suffix and the cross-field checks are reported on the field named in the message. Mapping of `messages.validate_templates` messages → where shown:

| Exact message | Shown under |
|---|---|
| `{key} cannot be empty` | not reachable from the form (blank = default) |
| `{key} is longer than 480 characters` | that field |
| `unbalanced { or } in template` | that field |
| `placeholders must look like {business_name}` | that field |
| `{key} uses unsupported placeholder(s) {x}; allowed: {…}` | that field |
| `{key} must not promise a person or the business line ('phrase')` | that field (the test expects "business line" to appear on the page, which this message provides) |
| `opt_out_suffix must tell the customer to reply STOP` | `opt_out_suffix` (lock note turns red) |
| `handoff_ack_safety must direct emergencies to 911` | `handoff_ack_safety` |
| `handoff acknowledgements must promise a follow-up` | whichever of `handoff_ack`/`handoff_ack_safety` lacks the two words "follow up" (check both; show on each failing one) |
| `booking_error must say no booking was made and keep the customer texting` | `booking_error` |
| `unknown question(s)…`, `a question is listed twice`, `questions must include …` | not reachable (fields is built server-side) |

The top flash is "Not saved: {first message}". After all fields pass individually, call `write_message_file` once with the full override set (it validates the merged set again; a failure there is shown as the top flash only).

### C.5 Reset behaviour

- Per field: submit button `name=reset value={key}` → server removes the key from overrides, writes, re-renders, flash "Reset to the standard wording." (works without JS). JS intercepts the click: clears the textarea, refreshes bubble + counter, marks the form dirty; nothing is written until Save.
- `opt_out_suffix` Reset restores "Reply STOP to opt out."
- The switches have no Reset (off is the default; turning off and saving removes `fields`).

### C.6 Placeholder chips per key

As in the B.2 table; each chip is `<button type=button class=chip data-insert="{business_name}" aria-label="Insert {business_name}">{business_name}</button>`. `booking_confirmation` shows the twelve chips in two rows with `{service} {when} {location} {business_name} {invite_line} {calendar_links}` first. For `opt_out_suffix` and `fields` no chips, the line "No fill-ins in this text."

---

## D. Scheduling page detail

### D.1 Working-hours model

Setting `working_hours` is JSON:
```json
{"mon":{"open":"08:00","close":"17:00"},"tue":{"open":"08:00","close":"17:00"},
 "wed":{"open":"08:00","close":"17:00"},"thu":{"open":"08:00","close":"17:00"},
 "fri":{"open":"08:00","close":"17:00"},"sat":null,"sun":null}
```
- Keys exactly `mon…sun` (Python `weekday()` order). `null` = closed. `open`/`close` are `HH:MM` wall-clock in the business timezone, minutes ∈ {00,15,30,45}; `close` may be `"24:00"` (end of day).
- Setting absent (or `hours_mode=any` saved as deletion of the key) = open every day all day = today's behaviour. The page shows this as the selected radio "Any day, any time" with the hint "Every time a caller asks for is accepted if the calendar is free."
- When the owner switches to "Set hours" the form pre-fills Mon–Fri 08:00–17:00, Sat/Sun closed (Hatch-like default); nothing is stored until Save.
- New module `src/text_back/working_hours.py`: `WEEKDAYS = ("mon",…,"sun")`, `parse_working_hours(raw: str|None) -> dict|None` (None for absent/invalid; invalid also logs), `slot_within_hours(start: datetime, end: datetime, hours: dict|None, tz: ZoneInfo) -> bool`, `describe(hours) -> str` ("Mon–Fri 8:00 AM–5:00 PM" for cards).

### D.2 Enforcement in `booking.book_appointment` (pseudo-code; insert after the timezone check at booking.py:60-62 and before `end = slot_end(...)` at :64)

```python
zone = ZoneInfo(timezone_name)
hours = parse_working_hours(store.setting("working_hours"))   # None → any time
end = slot_end(start, duration_minutes)
if not slot_within_hours(start, end, hours, zone):
    _record_slot_check(store=store, caller=caller, conversation_id=conversation_id,
                       start=start, available=False, checks=0)   # metadata {"available": False, "checks": 0, "reason": "outside_hours"}
    raise SlotUnavailableError("requested slot is outside working hours")

def slot_within_hours(start, end, hours, tz):
    if hours is None:
        return True
    local_start = start.astimezone(tz)          # start is tz-aware (parse_preferred_time guarantees it)
    local_end = end.astimezone(tz)              # DST: convert the real instant, then compare wall clocks
    day = hours.get(WEEKDAYS[local_start.weekday()])
    if day is None:
        return False                            # closed that day
    open_m = hhmm_to_minutes(day["open"]); close_m = hhmm_to_minutes(day["close"])   # "24:00" → 1440
    start_m = local_start.hour * 60 + local_start.minute
    # minutes from local midnight of the START day to the local end wall-clock
    end_m = (local_end.date() - local_start.date()).days * 1440 + local_end.hour * 60 + local_end.minute
    if local_end.second or local_end.microsecond: end_m += 1       # never round a late end down
    return open_m <= start_m and end_m <= close_m
```
Consequences and edge cases:
- A 60-minute slot asked for at 4:30 PM with close 17:00 has `end_m = 1050 > 1020` → rejected; the engine sends `slot_unavailable` and clears `preferred_time` (handlers.py:471-485), identical to a busy calendar. Same on the `booking_jobs.run_due_bookings` retry path (:55-61).
- A slot crossing local midnight is rejected unless `close == "24:00"` and the end is exactly 00:00 next day (`end_m == 1440`).
- DST: spring-forward day (e.g. America/New_York 2026-03-08) — a start at 01:30 local with 60 minutes ends at 03:30 local wall clock; the check uses the converted wall clock, so hours 00:00–24:00 pass and 08:00–17:00 reject, as a person would expect. Fall-back day — ambiguous local times never reach booking (`parse_preferred_time` fails closed on them); an unambiguous 01:30 EST slot converts normally.
- `store.setting` is RLock-synchronised and `book_appointment` already runs inside `atomic_sms_handler`'s transaction; the read is safe there.
- No change to `SlotUnavailableError` handling anywhere; the customer copy is the existing `slot_unavailable` template.

### D.3 Quiet hours, delays, expiry, duration, timezone — storage

| Key | Format stored | Applied to |
|---|---|---|
| `quiet_hours_start`, `quiet_hours_end` | `HH:MM` | `FollowupPolicy.quiet_start/quiet_end` via `followup._parse_hhmm` |
| `followup_delays_minutes` | `"120,1440"` (same as env) | `FollowupPolicy.delays_minutes` tuple |
| `followup_expiry_minutes` | `"2880"` | `FollowupPolicy.expiry_minutes` |
| `appointment_duration_minutes` | `"60"` | `state.appointment_duration_minutes` |
| `timezone` | IANA name | `state.timezone_name`, `FollowupPolicy.timezone_name` |
| `working_hours` | JSON (D.1) or absent | `booking` via `store.setting` at call time |

### D.4 Rebuild on save and at boot

`client_settings.apply_scheduling(state)` (new; called from `apply_settings` at boot and from the save handler):
```python
defaults = state.defaults                      # dict captured in create_app: {"timezone": config.timezone_name, ...}
tz = store.setting("timezone") or defaults["timezone"]
duration = int(store.setting("appointment_duration_minutes") or defaults["appointment_duration_minutes"])
delays = tuple(int(p) for p in (store.setting("followup_delays_minutes") or defaults["followup_delays_minutes"]).split(",") if p.strip())
expiry = int(store.setting("followup_expiry_minutes") or defaults["followup_expiry_minutes"])
qs = _parse_hhmm(store.setting("quiet_hours_start") or defaults["quiet_hours_start"], "quiet_hours_start")
qe = _parse_hhmm(store.setting("quiet_hours_end") or defaults["quiet_hours_end"], "quiet_hours_end")
policy = dataclasses.replace(state.followup_policy, delays_minutes=delays, expiry_minutes=expiry,
                             quiet_start=qs, quiet_end=qe, timezone_name=tz)   # __post_init__ validates
state.followup_policy = policy
state.store.sms_policy = policy                # both are required (sms.atomic_sms_handler reads store.sms_policy)
state.timezone_name = tz
state.appointment_duration_minutes = duration
```
`create_app` stores `app.state.defaults = {"business_name", "business_contact", "owner_mobile", "timezone", "appointment_duration_minutes", "followup_delays_minutes", "followup_expiry_minutes", "quiet_hours_start", "quiet_hours_end", "text_back_number": config.signalwire_from_number, "google_calendar_id"}` before `apply_settings`. The save handler validates first, then writes every key in one `store.transaction()`, then calls `apply_scheduling`. A `ValueError` from `replace()` means nothing is written (validate by constructing the policy before the transaction). `/health` keeps reporting `timezone` and `appointment_duration_minutes` from state, so the deploy check still works.

### D.5 Timezone select

Curated list (label → value): Eastern (New York) `America/New_York`; Central (Chicago) `America/Chicago`; Mountain (Denver) `America/Denver`; Arizona (Phoenix) `America/Phoenix`; Pacific (Los Angeles) `America/Los_Angeles`; Alaska `America/Anchorage`; Hawaii `Pacific/Honolulu`; Puerto Rico `America/Puerto_Rico`; Atlantic (Halifax) `America/Halifax`; Newfoundland `America/St_Johns`; Eastern (Toronto) `America/Toronto`; Central (Winnipeg) `America/Winnipeg`; Saskatchewan (Regina) `America/Regina`; Mountain (Edmonton) `America/Edmonton`; Pacific (Vancouver) `America/Vancouver`; UTC `UTC`. If the current value is not in the list it is appended as "{value} (current)". Server accepts only list values ∪ {current}; `ZoneInfo` must resolve.

### D.6 Exact validation rules and errors (server; all checked before anything is written)

| Field | Rule | Error |
|---|---|---|
| appointment length | int, 15..480, %5==0 | "Appointment length must be 15 to 480 minutes, in steps of 5." |
| time zone | in D.5 ∪ current, resolvable | "Pick a time zone from the list." |
| hours_mode | `any` or `set` | "Choose Any day, any time or Set hours." |
| open days | at least one when `set` | "Set at least one open day, or choose Any day, any time." |
| day times | from the 15-minute list; close may be 24:00 | "Pick times from the list." |
| day order | open < close | "{Day}: opening time must be before closing time." |
| day fits appointment | close − open ≥ appointment length | "{Day}: the hours are shorter than one appointment ({n} minutes)." |
| quiet hours | from the 30-minute list; `no_quiet_hours` → both "00:00" | "Pick quiet hours from the list." |
| nudge delays | ints, 5..20160 each (gaps; ascending not required) | "Nudge delays must be between 5 minutes and 14 days." |
| give up | int, 60..43200 | "Give-up time must be between 1 hour and 30 days." |
| policy | `FollowupPolicy.__post_init__` | "Not saved: {message}" |

Save button label "Save"; success flash "Saved. New conversations use these hours and delays."

---

## E. Calendar page detail

### E.1 States (from `calendar_status(state)`)

| status | Card headline (icon + word) | Body | Button | Availability card |
|---|---|---|---|---|
| `none` (stub) | grey · "Test calendar" | "No real calendar is connected. Bookings aren't recorded anywhere yet." | "Connect Google Calendar" if `can_connect` else the "still being set up" line | shown; uses the stub's busy list, caption "Test calendar" |
| `ready` | green check · "Connected" | "Google Calendar is connected. Appointments are checked against and booked on **{name}**." | "Reconnect Google Calendar" (secondary) | shown |
| `reauth_required` | red · "Disconnected" | "Google has disconnected the calendar. Bookings are paused until you reconnect." (contains "disconnected"; test) | "Connect Google Calendar" (primary) | button replaced by "Reconnect first." |
| `unavailable` | red · "Can't be read" | "The calendar connection could not be read. Reconnect to resume bookings." | "Connect Google Calendar" | replaced by "Reconnect first." |
| `managed` | green · "Connected" | "Your {Microsoft|iCloud|Google} calendar is connected and managed by your operator." | none | shown if the provider has `busy_intervals` (Google only this session) else "Availability check isn't available for this calendar yet." |

### E.2 Connect / Reconnect flow (existing routes, unchanged)

POST `/client/calendar` `action=connect` → 303 `{base}/calendar/connect?token=` → 303 Google (PKCE, `prompt=consent`) → GET `/calendar/callback` → `remember_calendars` → 303 `/client/calendar` (or `?error=…`). The page reads `error` (≤ 200 chars, escaped) into the flash.

Risk to decide (orchestrator): Chrome applies CSP `form-action` to the redirect chain of a form submission, so `form-action 'self'` blocks the hop to `accounts.google.com` in Chrome. Two fixes, pick one: (a) add `https://accounts.google.com` to `form-action` in `portal_ui.py` (one-line, tests unchanged); (b) have the POST return a 200 interstitial "Sending you to Google… [Continue]" with `<meta http-equiv=refresh>` (changes test 4's 303 assertion). Recommended: (a).

### E.3 Calendar picker

Radios only when `len(calendar_choices(state)) > 1`; each `<label><input type=radio name=calendar_id value="…"> {summary}{" (main)" if primary}</label>`; the current one carries ` checked` (this page may use the word). Button "Use this calendar". Choices come only from the cached writable list (so "Holidays" never appears).

### E.4 "Check availability now"

New provider method, Google (`calendars/google.py`):
```python
def busy_intervals(self, time_min: datetime, time_max: datetime) -> list[tuple[datetime, datetime]]:
    # identical POST {base}/freeBusy as is_free; same error handling; parse entry["busy"]
    # items {"start","end"} RFC3339 → aware UTC datetimes; malformed → CalendarProviderError
def is_free(self, start, end) -> bool:
    return self.busy_intervals(start, end) == []        # refactor; behaviour unchanged
```
Stub (`calendar_stub.py`): `busy_intervals` returns `[(s,e) for s,e in self.busy] + [(ev["start"], ev["end"]) for ev in self.events.values()]` clipped to the window. Microsoft/iCloud: not implemented this session (route guards with `hasattr`).

Pure function, new module `src/text_back/availability.py`:
```python
def next_free_slots(busy, now, duration_minutes, working_hours, tz, *, count=3, horizon_days=14, step_minutes=15) -> list[datetime]:
    """busy: iterable of (start,end) aware datetimes; now: aware; working_hours: dict|None (D.1);
    returns up to `count` aware starts in `tz`, earliest first."""
    local = now.astimezone(tz)
    cursor = ceil_to_step(local + timedelta(minutes=step_minutes), step_minutes)   # never 'now' itself
    limit = local + timedelta(days=horizon_days)
    out = []
    while cursor < limit and len(out) < count:
        end = cursor + timedelta(minutes=duration_minutes)
        if slot_within_hours(cursor, end, working_hours, tz) and not any(cursor < b_end and end > b_start for b_start, b_end in busy):
            out.append(cursor)
        cursor += timedelta(minutes=step_minutes)
    return out
```
Route `POST /client/calendar/availability` (csrf): `window = (now, now + 14 days)`; `busy = state.calendar.busy_intervals(*window)`; `slots = next_free_slots(busy, now, state.appointment_duration_minutes, parse_working_hours(store.setting("working_hours")), ZoneInfo(state.timezone_name))`; render the page with `slots` formatted `strftime("%A, %b %d at %I:%M %p %Z").replace(" 0", " ")` (same format as the confirmation text) and the caption "Checked just now · {n}-minute slots inside your working hours". Empty → "No free {n}-minute slot in the next 14 days inside your working hours." Errors → E.1 copy. Nothing is stored; `calendar.slot_checked` is NOT recorded (it is a lead event, and this is not a lead).

### E.5 Microsoft and iCloud cards

Two identical "available on request" cards, no buttons:
- Outlook / Microsoft 365 — "Available on request. text_back can book on Outlook.com and Microsoft 365 calendars; your operator sets it up for you. Nothing to click here yet."
- iCloud — "Available on request. text_back can book on an iCloud calendar with an app-specific password; your operator sets it up for you. Nothing to click here yet."
If the active provider is one of them, that card becomes the status card ("Connected · managed by your operator") and the other remains a request card.

---

## F. Phone page detail

### F.1 Typed numbers with live formatting and Verify

- Inputs: `type=tel inputmode=tel autocomplete=tel maxlength=24`; JS formats on `input` to `(980) 555-0177` for 10/11-digit North American numbers and leaves anything starting with `+` alone (international allowed by `normalize_mobile`). The server always normalises with `client_portal.normalize_mobile` and stores E.164; display uses `policy.format_contact_number`.
- Each field has a "Verify" secondary button (`formaction=/client/phone/verify name=verify value={field}`), ≥ 44px, placed to the right at ≥ 400px and below the input on narrower screens. Result renders under the field (`<p class="field-note ok|error" role=status|alert>` with icon + word).

### F.2 Texting-number ownership and handler check

New in `telecom.py`:
```python
@dataclass(frozen=True)
class NumberLookup:
    owned: bool
    voice_url: str = ""
    sms_url: str = ""
    verification_status: str = ""

class SignalWireTelecom:
    def lookup_number(self, e164: str) -> NumberLookup:
        # GET {space_url}/api/laml/2010-04-01/Accounts/{project_id}/IncomingPhoneNumbers?PhoneNumber={e164}
        # BasicAuth(project_id, api_token), timeout_seconds, follow_redirects=False  (scripts/pilot_check.py:127-142)
        # non-2xx → TelecomError(f"SignalWire number lookup returned HTTP {status}")
        # httpx.RequestError → TelecomError("SignalWire number lookup failed (<ExcName>)")
        # match = first incoming_phone_numbers[] with phone_number == e164 → NumberLookup(True, voice_url or "", sms_url or "", verification_status or "")
        # no match → NumberLookup(False)

@dataclass
class FakeTelecom:
    outbound: list[OutboundSms] = field(default_factory=list)
    owned_numbers: dict[str, dict] = field(default_factory=dict)      # e164 -> {"voice_url":..., "sms_url":...}
    lookups: list[str] = field(default_factory=list)
    def lookup_number(self, e164):
        self.lookups.append(e164)
        entry = self.owned_numbers.get(e164)
        return NumberLookup(False) if entry is None else NumberLookup(True, entry.get("voice_url",""), entry.get("sms_url",""), entry.get("verification_status",""))
```
Portal check `portal_phone.check_texting_number(state, e164) -> tuple[bool, str]`:
1. `not hasattr(state.telecom, "lookup_number")` → `(False, "Checking numbers is not set up for this account yet.")`
2. `TelecomError` → `(False, "SignalWire could not be reached. Try again in a minute.")`
3. `not result.owned` → `(False, "(980) 555-0177 is not a number this account owns.")`
4. `result.voice_url != base + "/webhooks/voice" or result.sms_url != base + "/webhooks/sms"` (base = `state.public_base_url`) → `(False, "(980) 555-0177 can't be used: its voice/SMS handlers do not point at text_back.")`
5. else `(True, "Owned by this account and pointed at text_back.")`
On Save success: `set_setting("text_back_number", e164)`, `state.business_number = e164`, and `if hasattr(state.telecom, "allowed_from_number"): state.telecom.allowed_from_number = e164`. `apply_settings` does the same at boot. Blank → `set_setting(None)` and both attributes back to `state.defaults["text_back_number"]`. Never any copy about buying, porting, provisioning or choosing a number.

### F.3 HELP contact field

`business_contact` as in B.5; the Messages preview uses it for `{contact_line}`. Hint also says "Customers who text HELP see this number."

### F.4 Owner-mobile change flow

Existing code path moved: `POST /client/phone` detects `mobile != state.owner_mobile` → `set_setting("owner_mobile_pending", mobile)`, `send_code(state, mobile, now, purpose="new mobile")` (rate limit 3 per 15 min applies per new number), render confirm card. `GET /client/phone` shows the confirm card while pending. `POST /client/phone/confirm` with `code` → `check_code` → commit; with `cancel=1` → clear. Flash texts exactly as today (B.5). The old GET `/client/business/keep` is removed (state-changing GET) and replaced by the POST cancel.

### F.5 Forwarding setup

Carrier pills (`<input type=radio name=carrier>` styled as pills, in the main form). Codes with `<TB>` replaced by the national 10 digits of the texting number (`digits`), each in `<code>` with a Copy button (JS) and a one-line step:

| Carrier | Turn on | Turn off | Notes shown |
|---|---|---|---|
| Verizon | `*71{digits}` | `*73` | "Covers busy and no answer. Dial from your phone while on Verizon's network, then press Call." |
| T-Mobile | No answer `**61*1{digits}#` · Busy `**67*1{digits}#` · Unreachable `**62*1{digits}#` · optional ring delay `**61*1{digits}**20#` (5–30 s) | `##61#` · `##67#` · `##62#` · reset all `##004#` | "Dial each code, then press Call." |
| AT&T | Android: Phone app → Settings → Call forwarding → set 'When busy' and 'When unanswered' to {formatted}. iPhone: codes `**61*1{digits}#` and `**67*1{digits}#` | `##61#` · `##67#` · `##004#` | "On iPhone, don't use the Settings toggle: it forwards every call. These codes are unverified on AT&T." |
| Cricket | same codes as AT&T | `##61#` · `##67#` · `##004#` | "Cricket doesn't publish codes. Check with `*#61#` / `*#67#`; if forwarding sticks, call 611." |
| Other | — | — | "Ask your carrier to turn on conditional call forwarding (busy and no answer) to {formatted}. Never forward all calls." |

Copy for the section intro: "Forward calls you don't answer to your texting number. Your business number stays the same." Warning line under every carrier: "Only forward busy and unanswered calls. Forward-all would send every call to the assistant."

### F.6 Verification checklist (5 steps) and evidence

`portal_data.forwarding_checklist(state) -> dict` with keys `steps` (list of 5 `{n, label, done, evidence, manual}`), `done_count`, `verified`.

| # | Label | Evidence rule | Evidence line |
|---|---|---|---|
| 1 | A test call rang through | exists `outcome_events` with `event_type='call.missed'` and `lead_id NOT IN (business_line, text_back_number)` (owner mobile is allowed: the doc says "a phone that is NOT the client's", meaning the business phone). Take the latest such event as `probe`. | "Oct 19, 3:02 PM from (•••) •••-0123" (last 4 digits only) |
| 2 | Exactly one text went out | for `probe.evidence_id` (call_sid): exists `outcome_events` `event_type='sms.initial_sent' AND idempotency_key='call:'||sid||':initial_sms'` (UNIQUE guarantees exactly one) and `sms_outbox` key `sid||':intro'` has `status='sent'` | "Sent Oct 19, 3:02 PM" |
| 3 | An answered call sent no text | manual (`forwarding_checklist.answered_no_text` timestamp) | "Ticked Oct 19" |
| 4 | Caller ID came through | `business_line` is set AND the `inbound_jobs` voice row `key='voice:'||sid` has `params_json.from_number` ≠ `business_line` and ≠ `text_back_number`. If `business_line` is empty: not done, hint "Enter your business number above first." | "From (•••) •••-0123, not your business number" |
| 5 | Turn-off code saved | manual (`forwarding_checklist.deactivation_saved`); the row shows the carrier's turn-off code inline | "Ticked Oct 19" |

Manual ticks are checkboxes in a small form (`POST /client/phone/checklist`, csrf) with "Save checks". `verified = all five done`; Home card reads `done_count` and `verified`. Caveat shown under the list in small text: "Steps 1, 2 and 4 are ticked from real calls recorded by the assistant." (Honest limitation, not shown: ForwardedFrom is not persisted, so a direct call to the texting number looks the same as a forwarded one.)

---

## G. Customers page — DESIGN ONLY

### G.1 Table

Columns: Name (or "—"), Phone (formatted), Service, Location, Preferred time (raw text), Email, Status (pill), Last activity (sortable, default desc). Row click opens the drawer. Phone and desktop: on phone the table collapses to cards (name/phone, status, last activity; tap for drawer).

### G.2 Status derivation (evaluate top to bottom; first match wins)

| Status | Rule | Colour/icon/word |
|---|---|---|
| Opted out | `contacts.opted_out = 1` | grey · ban · "Opted out" |
| Handed off | `handoffs.status='active'` | purple · hand · "Handed off" |
| Booked | `appointments.conversation_id = phone` exists | green · check · "Booked" |
| Expired | `followups.status='expired'` or `lead.expired` event, and no appointment | grey · clock · "Expired" |
| Qualified | `lead.qualified` event and no appointment | blue · star · "Qualified" |
| In progress | `sms.customer_replied` event and fields incomplete | amber · dots · "In progress" |
| New | only `call.missed` / `sms.initial_sent` | neutral · dot · "New" |

Same function (`portal_data.conversation_status(store, phone)`) powers the Home list.

### G.3 Search, filter, export

Search box (name, phone digits, email, location; server-side `LIKE`), status filter pills (multi), "Export CSV" (`GET /client/customers.csv?status=…&q=…`, same filters, UTF-8 BOM, columns as the table plus E.164 phone; no message bodies). CSV is produced by the owner session only; no public link.

### G.4 Row drawer

Right-side drawer (full-screen sheet on phone) with tabs: Thread · Timeline · Details.
- Thread: inbound (`inbound_jobs` kind sms, `params_json.body`, `received_at`) and outbound (`sms_outbox` kind ≠ login_code, `body`, `created_at`) merged by time; outbound bubbles show delivery state from `sms_outbox.status`: pending/sending → "Sending", sent → "Sent" (note: carrier 'delivered' is not stored, so never claim "Delivered"), unknown → "Unconfirmed", dead_letter → "Failed" with `last_error`, cancelled → "Not sent".
- Timeline: `outcome_events` for `lead_id = phone`, newest first, event type humanised ("Missed call", "First text sent", "Replied", "Captured: location", "Qualified", "Slot checked (busy)", "Booked", "Confirmed", "Nudge 1 sent", "Expired", "Opted out", "Handed off (reason)").
- Details: fields from `conversation_fields`; calendar: `appointments.start` formatted + link to the `/a/{ref}` links page (`CalendarLinks` ref) and, for Google, `https://calendar.google.com/calendar/u/0/r/eventedit/...` is NOT linkable without the htmlLink, so show "Event {event_id} on {calendar name}"; handoff: `handoffs.reason`, `requested_at`, alert delivery status from `handoff_deliveries` (pending/delivered/dead_letter).
No edits in the drawer (append-only ledger; opt-out is the customer's choice).

### G.5 Opted-out list

Filter "Opted out" shows the list read-only with: phone, when (`lead.opted_out.occurred_at`), and "Keyword" recovered by `JOIN inbound_jobs ON key = 'sms:' || evidence_id` → `params_json.body` (e.g. "STOP"). Caveat line at the top: "The reason isn't stored by the carrier. The word the customer texted is shown when the assistant received it; a STOP handled by the carrier itself may not appear here." No un-opt-out control (the customer re-subscribes by texting START).

### G.6 `customers` table proposal

```sql
CREATE TABLE IF NOT EXISTS customers (
  phone TEXT PRIMARY KEY,                     -- E.164
  name TEXT, service TEXT, location TEXT, preferred_time TEXT, email TEXT, best_phone TEXT,
  first_seen_at TEXT NOT NULL,
  last_activity_at TEXT NOT NULL,
  last_call_sid TEXT,
  appointment_event_id TEXT,
  handoff_reason TEXT,
  opted_out INTEGER NOT NULL DEFAULT 0,
  opt_out_keyword TEXT,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_customers_last_activity ON customers(last_activity_at);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);
-- read-path helpers (idempotent):
CREATE INDEX IF NOT EXISTS idx_sms_outbox_phone ON sms_outbox(phone, created_at);
CREATE INDEX IF NOT EXISTS idx_inbound_jobs_phone ON inbound_jobs(phone, received_at);
```
Status is derived at read time (G.2), not stored, so it can never drift from the ledgers.

Migration pattern (in `Store.__init__`, after the existing tables):
```python
existed = self.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='customers'").fetchone()
self.conn.execute("CREATE TABLE IF NOT EXISTS customers (...)")
if not existed:
    self._backfill_customers()          # one-time
```
Backfill:
```sql
INSERT OR IGNORE INTO customers(phone, first_seen_at, last_activity_at, updated_at)
SELECT phone, MIN(ts), MAX(ts), :now FROM (
  SELECT lead_id AS phone, occurred_at AS ts FROM outcome_events WHERE lead_id LIKE '+%'
  UNION ALL SELECT phone, received_at FROM inbound_jobs
  UNION ALL SELECT phone, created_at FROM sms_outbox WHERE kind <> 'login_code'
  UNION ALL SELECT phone, updated_at FROM conversation_fields
  UNION ALL SELECT phone, updated_at FROM contacts
  UNION ALL SELECT phone, created_at FROM followups
  UNION ALL SELECT phone, requested_at FROM handoffs
  UNION ALL SELECT caller, created_at FROM appointments
) GROUP BY phone;
UPDATE customers SET name=(SELECT value FROM conversation_fields f WHERE f.phone=customers.phone AND field='name'),
  service=(… 'service'), location=(… 'location'), preferred_time=(… 'preferred_time'), email=(… 'email'), best_phone=(… 'phone');
UPDATE customers SET opted_out=1 WHERE phone IN (SELECT phone FROM contacts WHERE opted_out=1);
UPDATE customers SET appointment_event_id=(SELECT event_id FROM appointments a WHERE a.conversation_id=customers.phone);
UPDATE customers SET handoff_reason=(SELECT reason FROM handoffs h WHERE h.phone=customers.phone AND h.status='active');
```
Upsert points (engine), via `Store.touch_customer(phone, *, now, **cols)`:
- `Store.record_outcome` when `lead_id` matches `^\+[1-9]\d{7,14}$` → upsert `first_seen_at` (keep MIN), `last_activity_at = occurred_at`, and for `call.missed` set `last_call_sid = evidence_id`.
- `Store.set_conversation_field` → the matching column.
- `Store.set_opted_out` → `opted_out`; `handle_sms_event` passes the keyword (`body.strip()[:20]`) → `opt_out_keyword`.
- `booking._finish_booking` → `appointment_event_id`; `Store.request_handoff` → `handoff_reason`.
`outcome_events` stays append-only; `customers` is a derived projection, rebuildable from the backfill at any time.

---

## H. Migrations for this build

All in `Store.__init__`, same guard as the existing one (store.py:161-165):
```python
columns = {row[1] for row in self.conn.execute("PRAGMA table_info(client_sessions)")}
if "remember" not in columns:
    self.conn.execute("ALTER TABLE client_sessions ADD COLUMN remember INTEGER NOT NULL DEFAULT 0")
```
1. `client_sessions.remember INTEGER NOT NULL DEFAULT 0` (layer 1).
2. Optional read-path indexes for Home (`CREATE INDEX IF NOT EXISTS idx_sms_outbox_phone ON sms_outbox(phone, created_at)`, `idx_inbound_jobs_phone ON inbound_jobs(phone, received_at)`) — idempotent, layer 1.
3. No other schema changes: every new setting is a `client_settings` row; `customers` is deferred (G.6).
No schema_version table is introduced (keeps the repo's "check, then ALTER" pattern).

---

## I. Layer split

### I.1 Layer 1 — Shell, sign-in/verify, Home, Account

Files created: `src/text_back/portal_ui.py`, `static/portal.css`, `static/portal.js`, `templates/layout.html`, `templates/auth.html`, `templates/components/*.html`, `templates/styleguide.html` (designer); `templates/pages/login.html`, `verify.html`, `home.html`, `account.html`, `legacy.html` (builder); `src/text_back/portal_data.py` (week_counts, recent_conversations, conversation_status, forwarding_checklist, registration_status).
Files changed: `pyproject.toml` (+`jinja2>=3.1`); `app.py` (`app.state.defaults`, `install_static`, `install_styleguide`, route order); `store.py` (H.1, H.2); `client_portal.py` (NAV, `render()` for login/verify/home/account, `/client` → Home page, `_page()` becomes a bridge that wraps old string bodies in `pages/legacy.html` so the old Messages/Business/Calendar pages inherit the shell; drop the inline `COUNT_SCRIPT` since CSP blocks inline scripts; `POST /client/verify` remember; `GET /client/account`; `POST /client/account/remember`; session TTLs).
Routes: `GET /client` (Home), `GET/POST /client/login`, `GET/POST /client/verify`, `GET /client/account`, `POST /client/account/remember`, `POST /client/logout`, `GET /client/static/*`, `GET /client/styleguide`.
Tests to add (`tests/test_portal_shell.py`): landing is `/client` and Home renders the five-or-fewer nav links present in this layer and never `/client/customers`; every portal page carries the CSP + no-store + X-Frame-Options headers; `remember=1` session survives +13h and dies at +31d, plain session dies at +13h; account toggle flips expiry both ways; Home tiles count seeded events in the Monday-to-now window and exclude last week; last-conversations ordering and status pills for seeded phones; registration card omitted when `TEXT_BACK_REGISTRATION_DIR` points nowhere and shown with staged files; static CSS served; verify-page error bodies still byte-identical with the checkbox present.
Existing tests changed: `test_client_portal.sign_in` expects `location == "/client"`; `test_logout…` unchanged; `test_a_pending_login_cookie…` unchanged. Copy scan test added now (DECISIONS): globs `src/text_back/templates/**/*.html` and `static/*.js`, fails on `messages.FORBIDDEN_PHRASES` substrings and `\bAI\b`.

### I.2 Layer 2 — Messages + Scheduling, migrations and enforcement

Files created: `templates/pages/messages.html`, `scheduling.html`; `src/text_back/portal_messages.py` (groups, per-field validation, sample data, counter flags), `portal_scheduling.py` (form parsing, D.6, save), `working_hours.py` (D.1/D.2); builder additions to `static/portal.js` (preview, counter, chips, phone formatting — ≤ ~100 lines).
Files changed: `client_portal.py` (Messages routes use `render`; Reset; NAV gains Scheduling), `client_settings.py` (`apply_scheduling`, called from `apply_settings`), `booking.py` (D.2 insertion), `app.py` (defaults already from layer 1).
Routes: `GET/POST /client/messages`, `GET/POST /client/scheduling`.
Tests to add: `tests/test_portal_messages.py` — groups render in order; default text present when no override; per-field inline error texts for each C.4 case and nothing written; suffix without STOP rejected inline with the exact message; Reset removes one key; `ask_email` markup and the no-"checked" rule; sample data attributes present; trial flag `data-trial` follows registration status. `tests/test_portal_scheduling.py` — defaults rendered as "Default:"; save persists and a new `create_app` on the same DB comes up with them; `app.state.store.sms_policy is app.state.followup_policy` after save; a follow-up due at 22:00 local after setting quiet hours 21:00–08:00 is deferred (reuse test_followup patterns); timezone change changes `parse_preferred_time` output through the engine; each D.6 error text; "Any day, any time" deletes the key. `tests/test_working_hours.py` — unit tests for `slot_within_hours`: inside, ends after close, starts before open, closed day, `24:00` close with end at midnight, cross-midnight rejected, DST spring-forward and fall-back days in America/New_York, `None` hours always true, invalid JSON parses to None. Enforcement tests in `tests/test_conversation_booking.py` (add): with hours Mon–Fri 08–17 a Saturday request yields `slot_unavailable` SMS and clears `preferred_time`, a Monday 10:00 request books; `tests/test_booking_jobs.py` (add): a pending job outside hours on retry sends `slot_unavailable` and finishes the job.
Existing tests changed: `test_signed_in_owner_edits_copy…` asserts "Messages" (h1) instead of "Your messages"; `test_without_a_messages_file…` unchanged in meaning; `test_contact_fields` unchanged.

### I.3 Layer 3 — Calendar + Phone

Files created: `templates/pages/calendar.html`, `phone.html`; `src/text_back/portal_calendar.py`, `portal_phone.py`, `availability.py`.
Files changed: `client_settings.py` (calendar routes use `render`; `/client/business*` → redirects; phone routes; `apply_settings` applies `text_back_number` to `state.business_number` and `telecom.allowed_from_number`), `telecom.py` (`NumberLookup`, `SignalWireTelecom.lookup_number`, `FakeTelecom.owned_numbers/lookups/lookup_number`), `calendars/google.py` (`busy_intervals`, `is_free` refactor), `calendar_stub.py` (`busy_intervals`), `client_portal.py` (NAV final), `portal_ui.py` CSP `form-action` per E.2 decision.
Routes: `GET/POST /client/calendar`, `POST /client/calendar/availability`, `GET/POST /client/phone`, `POST /client/phone/verify`, `POST /client/phone/confirm`, `POST /client/phone/checklist`, redirects from `/client/business*`.
Tests to add: `tests/test_portal_calendar.py` — each E.1 state renders its headline and button; availability with the stub (seeded busy) returns three formatted slots that respect working hours and duration; availability with Google via `FakeHttpTransport` freeBusy body; provider error copy; reauth state hides the button. `tests/test_next_free_slots.py` — skips busy overlaps, honours hours, rounds to the step, returns fewer when the horizon is exhausted, DST day. `tests/test_portal_phone.py` — page shows `value="Oak &amp; Pine Tree Care"`; save persists name/contact/line/carrier and survives restart; texting number: owned + handlers match → saved, `state.business_number` and a fake telecom's `allowed_from_number` updated; not owned → page contains "not a number this account owns" and nothing changes; mismatched handlers → "its voice/SMS handlers do not point at text_back"; telecom without `lookup_number` → "not set up"; same-number error; Verify endpoint saves nothing; mobile change via code (moved test), cancel via POST; checklist evidence ticks 1/2/4 from seeded `call.missed` + `sms.initial_sent` + voice inbound row, 4 requires `business_line`; manual ticks persist; Home card says "Forwarding verified" at 5/5; `/client/business` → 301 `/client/phone`. `tests/test_signalwire_telecom.py` (add) — `lookup_number` with `httpx.MockTransport`: URL, `PhoneNumber` param, basic auth; found → owned with urls; empty → not owned; 500 → `TelecomError`.
Existing tests changed: `test_client_settings` tests 1–3 target `/client/phone` and `/client/phone/confirm`, test 3 posts `cancel=1`; tests 4–6 keep their strings ("disconnected", "Connect Google Calendar", `<strong>Personal</strong>`, "now uses Tree jobs", "Pick one of the calendars", "still being set up", "not set up", "did not grant").

---

## J. Accessibility and copy checklist (reviewer applies to every page)

1. Every input has a `<label for>`; hints are linked by `aria-describedby="hint-{name}"`; errors by `aria-describedby="hint-{name} err-{name}"` plus `aria-invalid="true"`.
2. One `<h1>` per page; `<h2>` for sections, `<h3>` for cards; no skipped levels; the phone frame is `aria-hidden`.
3. Focus order follows the visual order; the account `<details>` closes on Escape (JS) and returns focus to the summary; after a failed save, focus moves to the first field error.
4. Visible focus ring on every interactive element (token `--focus`, 3px, offset 2px), including pills, chips and tab-bar items.
5. Contrast: text tokens ≥ 4.5:1, large text and icons ≥ 3:1 in both light and dark schemes; status colours are never the only signal (icon + word always present).
6. Touch targets ≥ 44×44 CSS px: tab items, pills, chips, Copy/Verify/Reset buttons, switch rows (the whole row is the label).
7. Status/flash regions use `role=status` (success) or `role=alert` (error); toasts `aria-live=polite`.
8. Tables use `<th scope=col>`; stat tiles are `<dl>`; the checklist is an `<ol>` with the step state in text ("Done", "Not yet").
9. `prefers-reduced-motion`: no scroll animation in the preview, no toast slide.
10. Copy: no "AI", no "business line", no promise of a person; labels exactly "Your business number", "Texting number", "Your mobile"; nothing phrased as a question to the owner; sentences ≤ 20 words; buttons are verbs ("Save", "Verify", "Connect Google Calendar", "Check availability now").
11. No inline scripts or styles (CSP `script-src 'self'; style-src 'self'`); no external fonts or CDNs.
12. Page `<title>` = "{Page} · {business name}"; `lang="en"`; viewport meta present.
13. Numbers are shown formatted; never render a full customer number on Home evidence lines (last four digits only).
14. The Messages page contains the word "checked" only inside an on-state checkbox attribute.

---

## Critical Files for Implementation

- `/home/ubuntu/projects/text_back-ui-b/src/text_back/client_portal.py` — sign-in/verify/session code, NAV, Messages routes; every layer touches it.
- `/home/ubuntu/projects/text_back-ui-b/src/text_back/client_settings.py` — `apply_settings` (now also scheduling + texting number), calendar and phone routes, mobile-change flow.
- `/home/ubuntu/projects/text_back-ui-b/src/text_back/booking.py` — the single working-hours enforcement point (D.2), before the first `calendar.is_free`.
- `/home/ubuntu/projects/text_back-ui-b/src/text_back/messages.py` — `validate_templates` messages, `OPT_OUT_REQUIRED`, `PLACEHOLDERS`, render/suffix rule that the preview and counter must mirror.
- `/home/ubuntu/projects/text_back-ui-b/src/text_back/telecom.py` and `/home/ubuntu/projects/text_back-ui-b/src/text_back/calendars/google.py` — `lookup_number` / `FakeTelecom.owned_numbers` and `busy_intervals`.
