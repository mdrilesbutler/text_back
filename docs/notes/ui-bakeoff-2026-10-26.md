# /client portal bake-off: ui/compare-a vs ui/compare-b (2026-10-26)

**Winner: A (`ui/compare-a`, 1f19c77, "conversation spine").** All three blind judges chose it, two of
them seeing it under a different label from the third. The margin is narrow (2–4 points out of 100).
It has to be read together with the coverage gap and the harness notes below.

This report recommends; it does not decide. Per CLAUDE.md NEXT, Michael names the winner. Nothing was
merged or deployed, and neither compare branch was modified.

## Scores

Each judge scored both portals blind on the same screenshots with the same rubric. Labels were
re-drawn per judge; `judges/label-key.json` holds the key.

| Judge (CLI login) | Saw A as | A | B | Verdict |
|---|---|---|---|---|
| Claude, Opus 5.5 (`claude -p --model opus`) | Y | **72** | 70 | A |
| Grok 4.7 (`grok -p`) | Y | **70** | 68 | A |
| Codex, GPT-6 (`codex exec -s read-only`) | X | **70** | 66 | A |
| **Mean** | | **70.7** | 68.0 | **A, 3–0** |

Per-criterion scores, 1–5. Total = 2 × sum.

| Judge | Portal | a1 orient | a2 plain words | b1 coverage | b2 friction | c1 phone layout | c2 phone nav | d1 honesty | d2 safety | e1 coherence | e2 finish |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Claude | A | 4 | 4 | 2 | 4 | 4 | 3 | 3 | 4 | 5 | 3 |
| Claude | B | 4 | 2 | 5 | 4 | 3 | 4 | 2 | 4 | 4 | 3 |
| Grok | A | 4 | 4 | 2 | 3 | 4 | 3 | 3 | 4 | 5 | 3 |
| Grok | B | 4 | 2 | 5 | 4 | 4 | 4 | 2 | 3 | 4 | 2 |
| Codex | A | 4 | 4 | 2 | 4 | 4 | 3 | 4 | 3 | 4 | 3 |
| Codex | B | 4 | 2 | 4 | 4 | 4 | 3 | 2 | 3 | 4 | 3 |

The panel agrees on the shape of the result:
- **A wins** on plain language (4 vs 2 from every judge) and honesty, and on visual coherence for two of the three judges.
- **B wins** on coverage (4–5 vs 2 from every judge).
- **B loses** on jargon: SignalWire tags, `{event_id}`-style tokens, "text_back", "Campaign in review".

The rubric weights coverage at 10 points out of 100, which is why a portal missing half the owner's
jobs can still win.

How the panel was run:
- The rubric (`ui-bakeoff-2026-10-26/judge-prompt.md`) adapts `fluxworks/docs/Fluxworks rebuild competition second/3-judge-prompts/judge-prompt-run-A.md` to a client portal, in five equal areas:
  - clarity for a non-technical owner
  - task completion
  - mobile
  - trust
  - polish
- It keeps the original's 1–5 integer scale, file-anchored observations, a "looks broken" list and a single `VERDICT:` line.
- It drops the Claude-only four-specialist protocol. Each model judged once.
- All three ran on subscription CLI logins, with every `*_API_KEY` variable removed from the environment.
- The Claude CLI's default model, Fable, refused with "out of usage credits", so the Claude judge ran on `--model opus`.
- Raw scorecards are in `judges/`.

## Walkthrough of the running previews

I walked both previews, A at `http://100.124.192.46:8765` and B at `http://100.124.192.46:8003`:
- **Setup:** Chromium/Playwright with the same test client on both (Oak & Pine Tree Care, owner 980 555 0123), signed in by reading `/preview/code`.
- **Widths:** desktop 1280×900 and phone 390×844 at 2×.
- **Capture:** pages were shot by scrolling, so sticky bars render where a person sees them.
- **In this folder:** the first screen of every page is in `ui-bakeoff-2026-10-26/screens/{A,B}/`. The full set of 91 judge-pack images is reproducible with `ui-bakeoff-2026-10-26/tools/walk.py`.

| Page | A | B |
|---|---|---|
| Sign in / enter code | yes | yes ("Remember this phone for 30 days") |
| Home / status | — (lands on Messages) | yes: calendar, forwarding and registration cards, week counts, last 10 callers |
| Messages | yes: one long page in conversation order, rendered bubbles, sticky preview rail, jump links | yes: one long page of plain textareas with `{tokens}`, sticky save bar, live phone preview |
| Scheduling | **— none** | yes: appointment length, time zone, working hours, quiet hours, nudges |
| Calendar | yes | yes, plus "Check availability now" |
| Phone numbers | partial: Business page has name, HELP number and owner mobile | yes: business line, texting number, owner mobile, HELP number, carrier forwarding codes, 5-step check list |
| Account / sign out | only in the header account menu | yes: Account page, Sign out, remember-device toggle |

What the walkthrough found:
- **Mechanics.** Every page on both returned 200 at both widths. Neither had console errors, failed requests or sideways page scroll at 390 px. A's jump-link strip scrolls sideways inside itself, by design.
- **Saves.** On private localhost copies of both harnesses (so the previews were not changed), every form saved and kept its value after a reload:
  - **A:** Messages, Business name, and the owner-mobile change, which texts a code to the new number and offers "Keep my current mobile".
  - **B:** Messages, Scheduling, Calendar availability, Phone, and the forwarding checklist.

Looks broken or wrong, as seen on screen:
- **B, Phone check list contradicts itself.** Step 1 shows "A test call rang through · Done" while step 2 says "No call recorded yet". Step 1 is satisfied by any missed call, including a direct call to the SignalWire number with no forwarding set up (`portal_data.py:256-289`). Michael's 2026-10-19 direct call would tick it in production.
- **B, availability offers 1–3 AM slots.** "Next free times" offers Mon 1:00, 1:30 and 2:00 AM under the default "Any day, any time" hours, beside the claim "A real read of the calendar".
- **B, internal names reach the client.** The sidebar footer reads "text_back · missed-call recovery", Calendar says "Ask text_back to connect it", and every message card says "Includes the '[SignalWire Free Trial]' tag".
- **B, desktop sidebar truncation.** The sidebar cuts the business name to "Oak & Pine Tre…".
- **B, fonts.** B ships no web fonts and renders in the system font. The FluxWorks system is Archivo + Source Sans, which A ships.
- **B, phone Messages page.** Save bar, preview button and bottom nav together take about a fifth of the phone screen, and there are no jump links across twelve screens.
- **A, no Scheduling, forwarding or status pages.** Sign out is hidden in the account menu; none of the three judges found it.
- **A, desktop nav scrolls away.** The left nav scrolls off on long pages, leaving an empty column.
- **A, wrong hand-off sample.** The sample reply "Can I just talk to the owner about pricing?" is shown triggering a hand-off, but `classify_handoff_request` returns `None` for it. Separately, and also on main, "I need to talk to the owner" is not classified as a hand-off request.
- **A, "you get a lead" copy.** Leads go to the operator's Telegram, not the client.

### Harness artifacts the judges scored

These come from the preview scripts, not from either branch. They cut against B more than A:
- **B's Home** shows seeded customers (Dana Whitfield, Marcus Lee) with no "sample" label, plus "Booked … Thursday, Oct 23", although Oct 23, 2026 is a Friday. All three judges docked B's honesty (d1) for this. In production those rows would be real callers, so a label would be wrong. The wrong weekday is in the harness's seed text.
- **B's "Campaign in review" card** reads fake files the harness writes. The card itself is branch code (see the B findings below).
- **A's Business page** keeps the old name in "IN THE FIRST TEXT" after a rename. A's harness pins a customized intro that hard-codes the name. The copy "Used in every text" is still misleading whenever the intro is customized.
- **A's booking preview** shows `hermes-cloud…ts.net:8765/a/…` links. That host is the real public base URL pattern, so customers get it on both branches. The judges counted it against A only because only A renders the full confirmation.
- **Business names ending "(desktop 043715)"** in `save-*` shots are my test inputs.

## Production readiness (branch diffs vs main)

Both branches fork from 3b3f0b0 and merge cleanly into current main. Neither has a BLOCKER.
- **Tests:** A 630 passed (main collects 594), B 692 passed.
- **Packaging:** both add jinja2 as a hard dependency, which the production `.venv` lacks today. `scripts/deploy.sh` reinstalls `-e .[dev]` before restarting, so a normal deploy is safe; a bare restart would not be.

Findings with "verified" were re-checked against the code after the reviewers reported them.

**A: fake data or would not work in production**
- **FIX, packaging (verified):** the branch adds 49.6 MB of new blobs, mostly screenshot PNGs plus a discarded first variant (f361093). Squash-merge or drop the PNGs, or main's history carries them forever.
- **FIX, fake data (verified):** the hand-off sample shows a reply that never triggers a hand-off (`client_portal.py:169,198`).
- **FIX, fake data:** the "Question 1: the job" card says it is asked as soon as the customer replies. In fact the first reply *is* the job; `prompt_service` only goes out on an empty reply. The sample transcript repeats the error. Main's label had the same mistake.
- **FIX, copy:** "you get a lead / an urgent lead" (`client_portal.py:80,101,199,202`) is not true for clients; leads go to the operator channel.
- **NOTE:** `/client/styleguide` ships to production. It needs sign-in and posts nothing, but it is about 900 lines with no product value; put it behind a dev flag.
- **NOTE:** sample values (tree removal, 12 Elm St, Alex Rivera, a fixed "Thursday, Oct 22") live in code, not config. They are labelled as samples, but they are arborist-specific and the date goes stale.
- **NOTE:** `/client/business/keep` is now unlinked and changes state on a GET with no CSRF check. That is also true on main; delete the route.
- **NOTE:** the segment counter ignores the "[SignalWire Free Trial]" prefix. The default texts' em dashes make them bill as 2–3 texts, which A shows as a warning.

Real in A:
- every save is a real form POST that works with JavaScript off
- no schema changes and no new env vars
- strict CSP, CSRF on every POST, autoescaped Jinja
- server-side message validation untouched (STOP, 911, "follow up")
- the live messages.json round-trips byte-identical

**B: fake data or would not work in production**
- **FIX, locked rule (verified):** an owner can retype "Texting number". If a read-only SignalWire GET confirms the account owns that number, saving swaps the live sender (`portal_phone.py:173-189`). The code makes no SignalWire writes, but the swap conflicts with "no number swap without Michael's approval". Make the field read-only or operator-set.
- **FIX, fake data (verified):** the forwarding check list ticks from any missed call (see the walkthrough).
- **FIX, stale state:** the registration card and the trial-tag decision read the `*-response.json` files, which are written only at submit time. `registration.py`'s status steps never rewrite them, so the card freezes and the "[SignalWire Free Trial]" preview never clears.
- **FIX, fake data:** `/client/styleguide` renders invented customers, 555 numbers and the hard-coded `https://hermes-cloud.tailefb1a4.ts.net:8443` to any signed-in client.
- **FIX, production break:** `appointments` stores no end time. Once Scheduling changes the length, every calendar link sent before the change shows the wrong end time.
- **FIX, booking safety:** the working-hours check runs before `find_event` recovery on the retry path. If the owner narrows the hours while a booking retry is pending, the retry is refused even though the calendar event already exists, leaving an orphaned event and a customer with no confirmation. Run recovery first.
- **FIX, SMS copy:** an out-of-hours request gets "That time is unavailable" without being told the hours, so a weekend-only customer can loop.
- **NOTE:** "Remember" stretches a session to 30 days, and the checkbox is pre-ticked by one global default. That is weaker than main's 12-hour cap.
- **NOTE:** "Verify" on the business number only checks the format.
- **NOTE:** Home reads every ledger row on each load.

Real in B:
- Scheduling settings are validated and applied live.
- Working hours are enforced in `book_appointment` on both the live and retry paths.
- Google freeBusy reads are real and fail closed.
- Home counts come from the ledgers, and "Booked" means `calendar.event_created`; no revenue is inferred.
- The owner-mobile change still needs a code sent to the new number.
- The no-live-human guard gained a template/JS scan, and nothing was removed.

## Why A

1. **The blind panel was unanimous and position-independent.** Two judges saw A as Y, one as X, and all three chose it for the same reasons: an owner reads the texts customers actually get, as bubbles in conversation order, with "STOP line added for you", plain-word billing warnings and labelled samples.
2. **A is pure UI.** It has no backend, schema or telecom change and no locked-rule conflict. B changes booking behaviour and lets a client swap the live sender number.
3. **A follows the FluxWorks design system:** Archivo + Source Sans, one green accent, the TextBack name.
4. **B's lead is coverage, and coverage ports.** Its extra pages are separable modules: `working_hours.py`, `availability.py`, `portal_scheduling.py`, `portal_phone.py`, `portal_data.py`. They can land on A one reviewed PR at a time, matching "one layer at a time".

Michael leaned B on 2026-10-21. If coverage matters more to him than the rubric's 10 points, B is the defensible pick. In that case, port A's Messages page and design tokens into it, and clear the B FIX list first.

## Three ideas from B worth porting (all three judges named the same three)

1. **Scheduling page** (`ui-bakeoff-2026-10-26/screens/B/05-scheduling-*`): appointment length with quick picks, time zone, working hours, quiet hours, nudge delays, and "Default: … · Reset" on every rule. Bring the backend with it: working hours enforced in `book_appointment`, plus tests. Fix the end-time and out-of-hours-copy findings while porting.
2. **Phone & forwarding page** (`ui-bakeoff-2026-10-26/screens/B/07-phone-*`): business line, texting number and owner mobile with distinct roles, carrier picker with conditional-forwarding codes and the "only forward busy and unanswered calls" warning, and the 5-step check list. Port it with the check list fixed (tick only from a call whose caller and forwarded-from line prove forwarding) and the texting number made read-only.
3. **Home status board** (`ui-bakeoff-2026-10-26/screens/B/03-home-*`): set-up cards with one action each (calendar, forwarding, registration), this week's ledger counts, and the last ten callers. Drop vendor names from the copy, and drive the registration card from live status rather than submit-time files.

## Before A ships (in the ship PR)

1. Squash-merge, or drop the 49.6 MB of PNGs.
2. Fix the hand-off sample and the "Question 1" timing. Replace "you get a lead" with what actually happens.
3. Make Sign out visible outside the account menu, and keep the desktop nav sticky.
4. Put `/client/styleguide` behind a dev flag. Delete `/client/business/keep`.

## Before B ships (if Michael names B)

All of B's FIX items above, in the ship PR, each with a test:
1. Texting number read-only (locked number-swap rule).
2. Forwarding check list ticks only from evidence of a forwarded call.
3. `find_event` recovery before the working-hours check, so no orphaned calendar events.
4. Store each appointment's end time so links sent before a length change stay right.
5. Registration card and trial-tag preview from live status, not submit-time files.
6. `/client/styleguide` behind a dev flag; out-of-hours SMS states the hours.
7. Then A's plain-language and honesty fixes: no vendor names or `{tokens}` on screen, label sample data.

## Files

- **In `ui-bakeoff-2026-10-26/`:**
  - `judge-prompt.md`: the identical rubric given to every judge.
  - `design-prompt-100.md`: where every point went, and a paste-ready prompt for the portal that would score 5 on all ten criteria.
  - `judges/{claude,grok,codex}.md`: the raw scorecards, as written, under their blind labels.
  - `judges/label-key.json`: the per-judge X/Y mapping.
  - `screens/{A,B}/`: the first screen of every page at both widths.
  - `tools/walk.py`: sign-in and capture. Run it with any Python that has Playwright, e.g. `../text_back-ui-a/.venv/bin/python`.
  - `tools/smoke.py`: the save checks. Run it against a private copy of a harness, never the shared previews.
  - `tools/build_packs.py`, `tools/run_judges.sh`: the blind packs and the three CLI runs. They run from a scratch folder holding `view/`, `smoke/` and `judge-prompt.md`.
- **Previews:** sign-in is limited to 3 codes per number per 15 minutes. This run used it twice and it has since cleared.
