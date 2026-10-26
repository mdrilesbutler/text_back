# fixture.json: what the candidate C mockups render from (2026-10-26)

Both directions (d1, d2) read this one file, so their content is identical. Every visible string is the
copy deck's text column verbatim with `[placeholders]` filled from the facts below. No string holds a
brace: inserts are `wording` parts of the form `insert: Business name`. Dates come from one helper.

- `meta` — today Mon 2026-10-26, now 2:40 PM Eastern; "Oak & Pine Tree Care"; owner mobile 980 555 0123;
  business line (704) 555-0123; texting number (704) 555-0100 (read-only); HELP number; public base URL;
  the date format; the text-count rule behind every cost line.
- `sign_in`, `enter_code` — all strings of the signed-out pages incl. errors and notices; field empty.
- `shell` — skip link, header (product, wrapping business name, Account trigger), five nav items,
  account menu lines, foot, 170 px sticky budget.
- `home` — "Not working yet: 2 steps left."; Calendar Needs you (Connect calendar); Call forwarding
  Needs you (3 of 5 checks done, Finish forwarding); Texting approval Waiting on phone companies;
  counts 3/3/1/1 and three Example callers all dated Mon, Oct 26, so counts equal rows; empty state.
- `messages` — title, intro, network notice (shown), jump chips, six steps with their keys, 21 `cards`
  by message id: title, when-line, badge, `wording` parts, `default_wording`, `preview` (name filled,
  STOP line added where required), computed `cost` (amber on followup_1, handoff_ack, help,
  booking_confirmation), chips, rules, destination line "These go to the FluxWorks operator.",
  switches off for phone and email; `intro` and `prompt_location` Customized. `example` = Books a job
  as ordered bubbles (side customer / textback / event); the confirmation bubble carries three link
  labels with hrefs. Then `save_bar`, `toasts`, `errors` (summary and every reason), `not_enabled`.
- `schedule` — length 60 with chips 30/45/60/90/120/Custom plus `variant_custom` 50; Eastern (New York);
  Mon–Fri 8:00 AM–5:00 PM as a seven-row grid plus the any-time warning variant; quiet 9:00 PM–8:00 AM;
  reminders 2 hours / 1 day / stop 2 days; every default line, error, consequence note, save toast.
- `calendar` — `connected` (Oak & Pine jobs, picker, availability), `not_connected_with_connect`
  (Connect button, What Google will ask, Test calendar with three free times inside working hours),
  `not_connected_without_connect` (Text FluxWorks support, nothing under it: open item); other states.
- `phone` — business name with preview and rename offer; numbers (texting number read-only, exact note);
  owner mobile with invalid entry "980 555 01"; confirm-new-mobile step (980 555 0199, Keep my current
  mobile); forwarding warning; carrier codes from docs/ONBOARDING-FORWARDING.md with the texting number
  filled in (AT&T, Cricket unverified); five checks with evidence (1, 2, 4 Done; 3, 5 Not yet).
- `account` — signed in as, two device rows, remember switch on, sign-out-everywhere dialog, Sign out.
- `shared` — toast position rule, every save toast, unsaved bar strings, errors, expired page.
- `states` — 27 named states both directions must render, each with the page and what is open.
