# text_back — AGENTS.md (the only rules file; every agent reads this)

You are one of several agents on this repo: Claude Code, Codex, Grok, Hermes, Cursor.
This file is the constitution. Chat history, Obsidian, old PRDs and other chats do NOT override it.
**Automatic, every session, without being asked:** your first actions are SESSION START, your last are SESSION END.
If Riles just says "go", "start", or "next", that means: do the NOW item.
Scripts live in `~/.claude/skills/canon/scripts/` (below: `$C`; set `C=~/.claude/skills/canon/scripts` in your shell).
Your agent name = `<tool>-<machine>`: `claude-wsl`, `codex-piclaw`, `grokbot`, `hermes-piclaw`.
Codex: run with network access on, or git/gh/claim will fail.

## SESSION START
1. `git status --porcelain` must be empty. If not, stop: tell Riles what's uncommitted. Don't carry it into new work.
2. `git switch <default branch> && git pull --ff-only`. If that fails, stop and tell Riles.
3. Read this file. Then `python3 $C/canon_state.py show` — NOW.md as it is on GitHub right now (it lives on the `canon-state` branch, never here).
4. `python3 $C/canon_state.py claim --agent <you>` → prints your session id (e.g. `claude-wsl#3f9a`); use it for release.
   Exit 2 = another session holds it: change nothing, tell Riles, stop.
5. `python3 $C/canon_check.py --repo . --repo-only`. Fix code-side issues on your branch. NOW.md issues get fixed in your release file.
6. `git switch -c agent/<you>/<short-slug>`. All code goes on this branch. Do only the item under `## NOW`.
   If something isn't in this file or NOW.md, ask Riles. Don't dig through old notes, PRDs or chats.

## SESSION END (output contract)
The status line reports THIS session. NOW.md is the NEXT session's handoff.
- Done (tests pass):
  1. `git push -u origin HEAD`, then `gh pr create --base <default branch> --title "<NOW item>" --body-file <file>` where the body is:
     **What changed** (2 lines, plain English) · **Tests** (n/n) · **Outside the NOW item** (none, or what and why) · **Preview** (link, if the repo gets preview deploys).
  2. `bash $C/canon_review.sh <pr#> <you>` — a different agent comments SAFE TO MERGE / DON'T MERGE on the PR and sets the `canon/review` check GitHub requires before merging.
  3. `NOWF=$(mktemp)`; write the new NOW.md there: STATE gains "<date> PR #n open: <item>", NOW = top item of NEXT (removed from NEXT),
     BLOCKED `none` — or `BLOCKED · <next item> · needs PR #n merged · NEED YOU: merge #n` if the next item depends on it.
     `python3 $C/canon_state.py release --agent <session id> --now-file "$NOWF"` (exit 5 = fix the file and rerun).
  4. Print: `DONE · <item> · tests <n/n> · PR #<n> · review: <first line of the review>`
- Stuck: push the branch if it has work. New NOW.md: NOW unchanged, BLOCKED = the line below. Release the same way. Print:
  `BLOCKED · <item> · <what failed> · NEED YOU: <exact action, or "none — next: <command>">`
- A paragraph, "still working", "see chat", "updated the PRD" = a leak. Not an ending.
- Can't finish properly (lint won't pass, release keeps failing)? Release anyway with the current `show` output plus one BLOCKED line describing it. Never leave the lock held.

## MERGING
Only when Riles says "merge it" / "merge #n": `gh pr merge <n> --squash --delete-branch`,
then `git switch main && git pull --ff-only`, then `bash scripts/deploy.sh` (merging + this script is what deploys).

## WHAT THIS IS
Missed-call recovery for field-service businesses (arborists, guides), modeled on Hatch. Unanswered call → SMS
conversation collects service, location, preferred time, name → books a real free calendar slot → confirms only after
a provider event ID exists. No live human: escalation = graceful exit + async operator lead. Per-client values live in
config, never code. Done = one real-phone Recover pilot proves conversion.

## WHAT'S LIVE (how text_back works)
- Call flow: caller dials the client's real number → carrier conditional-forwards unanswered calls to our SignalWire
  number → `POST /webhooks/voice` (signed) → `<Say>`+`<Hangup>` and one intro SMS intent (keyed on CallSid) →
  replies hit `POST /webhooks/sms` → `policy.py` handles STOP/HELP/handoff, `handlers.py` fills one field per reply →
  `booking.py` rechecks free/busy and creates the Google event → confirmation SMS. No reply → `followup.py` nudges, then expires.
- Durability: every webhook is stored first (`inbox.py`); SMS go through the `sms_outbox` (`sms.py`: intent commits
  before send; ambiguous sends held `unknown`, reconciled by `/webhooks/sms-status`); bookings retry via `booking_jobs`;
  operator alerts via `handoff_deliveries` → Telegram. One worker (`worker.py`) drains all lanes every 5 s.
- Evidence: append-only `outcome_events` (`docs/OUTCOME-EVENTS.md`); `brief.py` renders the Recovered Revenue Brief.
- Runs on hermes-vcn-0 (`ssh ubuntu@100.124.192.46`, Tailscale; alias `hermes-cloud` on piclaw): user unit
  `text-back.service` → `~/projects/text_back` on `main`, `.venv`, 127.0.0.1:8000; public HTTPS via Tailscale Funnel
  `https://hermes-cloud.tailefb1a4.ts.net:8443`; SQLite `~/.local/state/text_back/pilot.sqlite3`.
- Deploy: never edit hermes-cloud's clone. Merge to `main`, then `bash scripts/deploy.sh` from any host: it SSHes in,
  refuses a dirty tree, fast-forwards `main`, installs, runs tests, restarts, and checks `/health`.
- Env var NAMES (values only in hermes-cloud `~/.config/text_back/runtime.env`, mode 600): TEXT_BACK_ + TELECOM_MODE,
  PUBLIC_BASE_URL, DB_PATH, WEBHOOK_SECRET (SignalWire signing key), SIGNALWIRE_{SPACE_URL,PROJECT_ID,API_TOKEN,FROM_NUMBER},
  BUSINESS_{NAME,CONTACT}, TIMEZONE, APPOINTMENT_DURATION_MINUTES, WIRING_MODE, CALENDAR_PROVIDER, GOOGLE_{CALENDAR_ID,TOKEN_FILE,
  CLIENT_FILE}, FOLLOWUP_{DELAYS,EXPIRY}_MINUTES, QUIET_HOURS_{START,END}, HANDOFF_{DESTINATION,DELIVERY_CHANNEL},
  TELEGRAM_{BOT_TOKEN,CHAT_ID}, OPERATOR_API_KEY, PILOT_RECIPIENTS (explicit allowlist; empty = texts nobody).
  Full list with comments: `.env.example`. Never invent a credential; missing one = park the slice.
- Test: `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/pytest`. CI runs the same on every
  push/PR. Live checks: `scripts/pilot_check.py --env-file <runtime.env> --health --providers` (read-only).
- 10DLC: pilot number is on SignalWire's Platform Free Trial — SMS reaches only Riles's one verified mobile. Brand +
  Campaign registration is Riles's job in his browser; build as if approved. Only ever text Riles's verified number.

## HOW TO WORK WITH RILES
- He does not code. Terse, decisive answers. Recommend; don't hand him option menus. Settings, not questions:
  anything he may tweak later is a setting with a Hatch-like default.
- Never cut, kill, demote, or drop scope without his explicit agreement. Don't re-derive anything under LOCKED.
- No telecom purchase, spend, account upgrade, or call routing change without his explicit approval; purchases happen
  only in his browser. Cost cap $15/month.

## HARD RULES
- State lives only in NOW.md on `canon-state`, changed only by `canon_state.py`; never a NOW.md on a code branch, never the vault copy.
- Never delete files; supersede them. Never push to `main` yourself. Never force-push. Code = branch + PR. Never stack PRs.
- Don't edit the PRD unless Riles named a requirement change. Docs and code disagree → believe code + tests.
- Scratch notes go in `docs/notes/`. History is git. Grok owns `deploy/textback-designer/` + `docs/demo/`; others never touch them.

## LOCKED (settled — do not re-open)
- Carrier SignalWire (Twilio fallback); $15/month ceiling. Booking: Google Calendar primary; Microsoft/iCloud adapters optional
  via `TEXT_BACK_CALENDAR_PROVIDER`; production telecom refuses to boot with the stub calendar.
- Customers never get a live human (guard: `tests/test_no_live_human_copy.py`). Deterministic policy, never an LLM, owns
  STOP/HELP, consent, quiet hours, booking truth, and handoff.
- `wiring_mode`: `forwarded` (default; first voice event per CallSid triggers) vs `managed` (terminal unanswered only).
- Webhooks verify `X-SignalWire-Signature` and fail closed; side effects idempotent; no booking claimed without a Calendar
  event ID; revenue only from explicit `revenue.attributed` evidence.
- Product order: Recover first; Answer (voice) and Grow (journeys) wait for the pilot. GTM: TB-ASSESS → TB-RECOVER → TB-CARE.
- More LOCKED items (OAuth mint, reauth, credential intake, onboarding checklist, gotchas): `docs/notes/agents-reference.md`.

## KILLED (dead — never resurface)
- `cal.com` booking backend · `gcloud`/service-account Calendar auth · `google-voice` telecom · `live-human` transfer copy.

## SPEC
`docs/PRD-text_back.md` (requirements) · `docs/PRODUCT-MODEL.md` (Recover P0/P1) · `docs/SIGNALWIRE-INTEGRATION.md` ·
`docs/ONBOARDING-FORWARDING.md` · `docs/RECOVER-OPERATIONS.md` · `docs/OUTCOME-EVENTS.md` · `docs/CALENDAR-PROVIDERS.md`.
