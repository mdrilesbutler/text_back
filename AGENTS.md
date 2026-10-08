# text_back — AGENTS.md (the only rules file; every agent reads this)

You are one of several agents on this repo: Claude Code, Codex, Grok, Hermes, Cursor.
This file is the constitution. Current user instructions take precedence over repository workflow defaults.
**Automatic, every session, without being asked:** your first actions are SESSION START, your last are SESSION END.
If Riles just says "go", "start", or "next", that means: do the NEXT item in CLAUDE.md.
Scripts live in `~/.claude/skills/canon/scripts/` (below: `$C`; set `C=~/.claude/skills/canon/scripts` in your shell).
Your agent name = `<tool>-<machine>`: `claude-wsl`, `codex-piclaw`, `grokbot`, `hermes-piclaw`.
Codex: run with network access on, or git/gh/claim will fail.

## SESSION START
1. Read `CLAUDE.md`; it is the canonical project state. Resume from NEXT and NEXT SESSION PROMPT.
2. Inspect `git status --short --branch`; preserve existing work and ownership boundaries.
3. Work from `main`, fetching and integrating `origin/main` without force-pushing or discarding local changes.
4. Run `python3 $C/canon_check.py`. Preserve the explicitly required CLAUDE.md state even if the generic checker recommends migrating it.

## SESSION END
1. Run checks appropriate to the change and record actual evidence in `CLAUDE.md`.
2. Commit only named, reviewed paths with the identity recorded in CLAUDE.md. A merge commit records the reviewed merge result as a whole.
3. Push completed work to `origin/main`; verify the remote commit. Never leave finished work only on a development branch.
4. Run `bash $C/canon_wrapup.sh --now` and report its fleet summary plus one DONE/BLOCKED line.

## MERGING
Michael explicitly instructed on 2026-10-08: always push finished work to `main`.
Integrate existing remote changes, test, and push `main` without another approval question.
Use a normal merge when histories diverge; never force-push. If GitHub requires a PR, use that path to deliver to `main`.
Deploy merged application changes with `bash scripts/deploy.sh`; preserve private configuration and unrelated services.

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
- Deploy: merge to `main`, then `bash scripts/deploy.sh` from any host: it SSHes in,
  refuses a dirty tree, fast-forwards `main`, installs, runs tests, restarts, and checks `/health`.
- Env var NAMES (values only in hermes-cloud `~/.config/text_back/runtime.env`, mode 600): TEXT_BACK_ + TELECOM_MODE,
  PUBLIC_BASE_URL, DB_PATH, WEBHOOK_SECRET (SignalWire signing key), SIGNALWIRE_{SPACE_URL,PROJECT_ID,API_TOKEN,FROM_NUMBER},
  BUSINESS_NAME, TIMEZONE, APPOINTMENT_DURATION_MINUTES, WIRING_MODE, CALENDAR_PROVIDER, GOOGLE_{CALENDAR_ID,TOKEN_FILE,
  CLIENT_FILE}, FOLLOWUP_{DELAYS,EXPIRY}_MINUTES, QUIET_HOURS_{START,END}, HANDOFF_{DESTINATION,DELIVERY_CHANNEL},
  TELEGRAM_{BOT_TOKEN,CHAT_ID}, OPERATOR_API_KEY, PILOT_RECIPIENTS (explicit allowlist; empty = texts nobody).
  Full list with comments: `.env.example`. Never invent a credential; missing one = park the slice.
- Test: `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]' && .venv/bin/pytest`. CI runs the same on every
  push/PR. Live checks: `scripts/pilot_check.py --env-file <runtime.env> --health --providers` (read-only).
- 10DLC: preserve the existing business cell as the public/forwarding number and the existing SignalWire number as the backend.
  Follow the actual registration and consent prerequisites in CLAUDE.md; never swap phone roles to fit trial restrictions.
  Keep the runtime allowlist empty until a supported, approved test recipient is established.

## HOW TO WORK WITH RILES
- He does not code. Terse, decisive answers. Recommend; don't hand him option menus. Settings, not questions:
  anything he may tweak later is a setting with a Hatch-like default.
- Never cut, kill, demote, or drop scope without his explicit agreement. Don't re-derive anything under LOCKED. Before retiring anything, run /salvage.
- No telecom purchase, spend, account upgrade, or call routing change without his explicit approval; purchases happen
  only in his browser. Cost cap $15/month.

## HARD RULES
- State lives in `CLAUDE.md`, per the explicit project instructions. Keep it current; do not use the historical `canon-state` branch as current state.
- Preserve other agents' work. Always deliver completed work to `main`. Never force-push.
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
- More LOCKED items (OAuth mint, reauth, credential intake, onboarding checklist, gotchas): `CLAUDE.md`.

## KILLED (dead — never resurface)
- `cal.com` booking backend · `gcloud`/service-account Calendar auth · `google-voice` telecom · `live-human` transfer copy.

## SPEC
`docs/PRD-text_back.md` (requirements) · `docs/PRODUCT-MODEL.md` (Recover P0/P1) · `docs/SIGNALWIRE-INTEGRATION.md` ·
`docs/ONBOARDING-FORWARDING.md` · `docs/RECOVER-OPERATIONS.md` · `docs/OUTCOME-EVENTS.md` · `docs/CALENDAR-PROVIDERS.md`.
