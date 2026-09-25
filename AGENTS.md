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
Only when Riles says "merge it" / "merge #n": `gh pr merge <n> --squash --delete-branch`, then `git switch <default> && git pull --ff-only`.
Merging is what deploys. Never merge on your own judgment, never because a review said SAFE.

## WHAT THIS IS
Missed-call recovery and scheduling assistant for field-service businesses (arborists, guides). An unanswered call
triggers an SMS conversation that collects service, location, preferred time, name; books a real free calendar slot;
confirms only after a provider event ID exists. Customers never reach a live human — escalation is a graceful exit plus
an async operator lead. Sold per client from the fluxworks catalog: identity, numbers, calendar, hours live in config,
never code. Done = one real-phone Recover pilot proves conversion.

## WHAT'S LIVE
- Repo: git@github.com:mdrilesbutler/text_back.git — app code is branch `local/tdd-core` (`main` is stale). Piclaw worktree: `~/projects/text_back-tdd-core`.
- Runtime: hermes-vcn-0 (`ssh hermes-cloud`) — localhost-only `text-back.service` at 127.0.0.1:8000, stub telecom mode, `/health` green. No public URL, no deploy pipeline yet.
- Credentials: hermes-cloud `~/.config/text_back/{pilot,runtime,signalwire}.env` + `google_token.json`, mode 600, never git. Signing key is in runtime.env — rotate at deploy.
- SignalWire: FluxWorks space, funded, one voice/SMS/MMS pilot number, no handlers attached, $15/month ceiling.
- Google Calendar: calendar-only OAuth token, live-verified as mdrilesbutler@gmail.com (2026-08-29).
- CI: GitHub Actions runs pytest on every push/PR (py3.12/3.13).
- Grok's lane: `deploy/textback-designer/` + `docs/demo/` (designer UI, story film). Claude/Codex never edit or commit those.

## HOW TO WORK WITH RILES
- He does not code. Terse, decisive answers. Recommend; don't hand him option menus.
- Small compartmentalized specs, one layer at a time.
- State key decisions explicitly and get a yes before executing.
- Never cut, kill, demote, or drop scope without his explicit agreement on the specific item.
- Don't re-derive anything under LOCKED.
- No telecom purchase, spend, production message, or call routing without his explicit approval; purchases happen only in his browser.
- Commit on hermes-vcn-0 with `git -c user.name="Michael Riley" -c user.email="mdriles@gmail.com"` (no git identity on host).

## HARD RULES
- State lives only in NOW.md on the `canon-state` branch, and only `canon_state.py` changes it. Never create a NOW.md on a code branch.
  Never write status into this file, a PRD, or Obsidian.
- Obsidian updates itself from GitHub (piclaw mirrors NOW.md every 2 min). Never edit the vault copy.
- Never push to the default branch yourself (GitHub and a local hook both refuse it). Never force-push. Code = branch + PR.
- Don't edit the PRD unless Riles named a requirement change. Docs and code disagree → believe code + tests.
- Scratch notes go in `docs/notes/`. History is git.

## LOCKED (settled — do not re-open)
- Carrier: SignalWire (Twilio fallback). Spend ceiling $15/month (approved 2026-08-20).
- Booking backend: Google Calendar primary (decided 2026-08-29, "everyone has a gmail"); Microsoft Graph and iCloud CalDAV adapters shipped as options. Selected via `TEXT_BACK_CALENDAR_PROVIDER`; production telecom refuses to boot with the stub calendar.
- Customers never get a live human. Escalation = graceful exit + async operator lead. Guard: `tests/test_no_live_human_copy.py`.
- Deterministic policy, never an LLM, owns STOP/HELP, consent, quiet hours, booking truth, and handoff.
- `wiring_mode`: `forwarded` (default; first voice event per call_sid triggers) vs `managed` (terminal unanswered only). Never mix the rules.
- Webhooks verify `X-SignalWire-Signature` and fail closed; every side effect is idempotent via `claim_event`.
- No booking is claimed without a Calendar event ID. Revenue comes only from explicit `revenue.attributed` events with evidence — never inferred from a booking.
- Product order: Recover first — Answer (voice) and Grow (journeys) wait until the real-phone Recover pilot proves conversion. GTM: Koerner ladder TB-ASSESS → TB-RECOVER → TB-CARE; sell missed-call recovery, not "AI".
- More LOCKED items (OAuth mint, customer reauth, credential intake, onboarding checklist, two-lane protocol): `docs/notes/agents-reference.md`.

## KILLED (dead — never resurface; deleted from runtime, not archived)
- `cal.com` as booking backend (Google decision 2026-08-29).
- `gcloud` auth / GCP service-account path for Calendar (wrong path; token comes from the skill pattern).
- `google-voice` as telecom backend.
- `live-human` transfer or "call the business line" escalation copy.

## ROADMAP (order is locked; build only the current phase)
- Done 2026-08-29: v1 Recover (built locally, TDD; 302 tests green) — missed call → SMS → qualification → booking or handoff → follow-up sequence → Recovered Revenue Brief.
- v1 live pilot (current): public HTTPS host, attach SignalWire handlers, real-phone smoke test per `docs/ONBOARDING-FORWARDING.md`, first client via per-client config.
- v2 Answer, v3 Grow, and the money-gated PDF/Stripe extras: `docs/notes/agents-reference.md`.

## SPEC
- `docs/PRD-text_back.md` — requirements and architecture; no status log lives there.
- `docs/PRODUCT-MODEL.md`, `docs/COMPETITOR-MATRIX.md`, `docs/gtm/KOERNER-MODEL.md` — product and GTM.
- `docs/SIGNALWIRE-INTEGRATION.md`, `docs/ONBOARDING-FORWARDING.md`, `docs/CALENDAR-PROVIDERS.md`, `docs/OUTCOME-EVENTS.md` — contracts.
- `README.md` — how to run and test.
- `docs/notes/agents-reference.md` — SignalWire/runner gotchas + LOCKED/ROADMAP overflow from the old CLAUDE.md.
