# text_back — CLAUDE.md (canonical; the only file that carries state)

Read this first. Then run `python3 ~/.claude/skills/canon/scripts/canon_check.py`.
Then start on NEXT. Do not read PRDs, old handoffs, or vault notes to learn state — if it isn't here, ask.

## WHAT THIS IS
Missed-call recovery and scheduling assistant for field-service businesses (arborists, guides). An unanswered call
triggers an SMS conversation that collects service, location, preferred time, name; books a real free calendar slot;
confirms only after a provider event ID exists. Customers never reach a live human — escalation is a graceful exit plus
an async operator lead. Sold per client from the fluxworks catalog: identity, numbers, calendar, hours live in config,
never code. Done = one real-phone Recover pilot proves conversion.

## WHAT'S LIVE
- Repo: git@github.com:mdrilesbutler/text_back.git — app code and all finished work belong on `main` (Michael explicitly reaffirmed 2026-10-08). Historical Piclaw worktree: `~/projects/text_back-tdd-core`; it is not a delivery branch.
- Runtime: hermes-vcn-0 (`ssh hermes-cloud`) — user-scoped `text-back.service` at 127.0.0.1:8000; public HTTPS at `https://hermes-cloud.tailefb1a4.ts.net:8443` through existing Tailscale Funnel. Google Calendar, persistent SQLite, managed worker and private Telegram alerts; SignalWire telecom is enabled with no recipient allowlist (every caller is texted; the STOP list is the only exclusion, Michael's product rule 2026-10-19). Michael's Verizon device numbers are saved privately in ~/.config/text_back/pilot-phones.json.
- Credentials: hermes-cloud `~/.config/text_back/{pilot,runtime,signalwire}.env` + `google_token.json`, mode 600, never git. Preserve credentials; verify the existing project signing key before live webhooks, without rotating it.
- SignalWire: FluxWorks space, funded, one voice/SMS/MMS pilot number with POST voice/SMS handlers attached to Recover, $15/month ceiling.
- Google Calendar: calendar-only authorized-user JSON for mdrilesbutler@gmail.com; refresh and read-only free/busy live-verified 2026-09-18.
- CI: GitHub Actions runs pytest on every push/PR (py3.12/3.13).
- Grok's lane: `deploy/textback-designer/` + `docs/demo/` (designer UI, story film). Claude/Codex never edit or commit those.

## HOW TO WORK WITH RILES
- He does not code. Terse, decisive answers. Recommend; don't hand him option menus.
- Small compartmentalized specs, one layer at a time.
- Michael authorized autonomous completion on 2026-09-16: "continue working until the product is working" and "you don't have to ask for my approval any more." Proceed with routine in-scope inspection, fixes, tests, and verification; do not repeatedly ask for approval already given. Preserve the specific live-service boundaries below and obey tool-enforced permissions.
- On 2026-09-19 Michael said "you need to set that up" when asked for hosting/operator choices. Choose and implement routine hosting, HTTPS, and operator configuration using existing services. Ask him only for account login/2FA and the physical test-phone details that cannot be supplied by engineering. Commit and push the work as requested.
- On 2026-10-08 Michael reaffirmed: "you have my permission for everything." Proceed with the in-scope pilot setup and execution without another conversational approval request; physical-device facts and account login/2FA still require actual evidence. Preserve the existing $15 ceiling and tool-enforced permissions.
- Never cut, kill, demote, or drop scope without his explicit agreement on the specific item.
- Don't re-derive anything under LOCKED.
- No telecom purchase, spend, production message, or call routing without his explicit approval; purchases happen only in his browser.
- Always integrate and test finished work, deliver through a PR with independent review and successful `canon/review`, then delete temporary branches locally/remotely. End on clean `main == origin/main`; `main` is the only permanent branch. Preserve remote changes and never force-push.
- Commit on hermes-vcn-0 with `git -c user.name="Michael Riley" -c user.email="mdriles@gmail.com"` (no git identity on host).

## LOCKED (settled — do not re-open)
- Carrier: SignalWire (Twilio fallback). Spend ceiling $15/month (approved 2026-08-20).
- Booking backend: Google Calendar primary (decided 2026-08-29, "everyone has a gmail"); Microsoft Graph and iCloud CalDAV adapters shipped as options. Selected via `TEXT_BACK_CALENDAR_PROVIDER`; production telecom refuses to boot with the stub calendar.
- Customers never get a live human. Escalation = graceful exit + async operator lead. Guard: `tests/test_no_live_human_copy.py`.
- Deterministic policy, never an LLM, owns STOP/HELP, consent, quiet hours, booking truth, and handoff.
- `wiring_mode`: `forwarded` (default; first voice event per call_sid triggers) vs `managed` (terminal unanswered only). Never mix the rules.
- Michael reaffirmed 2026-10-08: Recover must work on his actual existing cell number and sell to clients without changing their public number. Keep his cell as the business/forwarding line and the already-owned SignalWire number as the backend/SMS sender. No new number purchase, port, or swap of the business cell into the pilot caller role. A test caller uses an existing phone; that is not another business line. Current recovery SMS originates from SignalWire, not the Verizon cell.
- Webhooks verify `X-SignalWire-Signature` and fail closed; inbound claims and local intents commit atomically; durable outboxes own retries, and ambiguous SMS acceptance requires reconciliation.
- No booking is claimed without a Calendar event ID. Revenue comes only from explicit `revenue.attributed` events with evidence — never inferred from a booking.
- Product order: Recover first. Answer (voice) and Grow (journeys) wait until the real-phone Recover pilot proves conversion.
- GTM: Koerner ladder TB-ASSESS → TB-RECOVER → TB-CARE; sell missed-call recovery, not "AI".
- Google OAuth for text_back is minted with the google-oauth-repair skill pattern (existing Hermes client, butler account) — re-mint in ~5 min if revoked.
- Customer calendar reauth: silent refresh; on true revocation mark the client `reauth_required` and send a reconnect link. Customers never go through the operator OAuth-repair path.
- Credential intake: browser → `~/.config/text_back/` → verified via `/health`. Never chat, git, or Obsidian.
- The live-call verification checklist in `docs/ONBOARDING-FORWARDING.md` is mandatory at every client onboarding.
- Two-lane repo protocol: Grok owns `deploy/textback-designer/` + `docs/demo/`; Claude/Codex own everything else (incl. `docs/landing/`). Ordinary commits are `--only`-scoped to named paths, never `-a`; merge commits record the reviewed merge result as a whole. Lane splits are recorded here, not in dated docs files.

## KILLED (dead — never resurface as live; deleted from runtime, not archived)
- `cal.com` as booking backend (Google decision 2026-08-29).
- `gcloud` auth / GCP service-account path for Calendar (wrong path; token comes from the skill pattern).
- `google-voice` as telecom backend.
- `live-human` transfer or "call the business line" escalation copy.

## ROADMAP (order is locked; build only the current phase)
- Done 2026-08-29: v1 Recover (built locally, TDD; 302 tests green) — missed call → SMS → qualification → booking or handoff → follow-up sequence → Recovered Revenue Brief.
- v1 live pilot (current): public HTTPS host, attach SignalWire handlers, real-phone smoke test per `docs/ONBOARDING-FORWARDING.md`, first client via per-client config.
- v2 Answer: after-hours/overflow AI voice + directory routing.
- v3 Grow: estimate, no-show, review journeys, separately consent-scoped.
- Optional (money gate): PDF leave-behind, Stripe links for the three SKUs; a `deploy-client` skill for fluxworks.

## STATE (as of 2026-10-19; ≤ 10 lines; rewritten every handoff)
- PILOT CORE LOOP PROVEN 2026-10-19 06:33-06:41 UTC on Michael's own cell (direct call to +17045695600, forwarded mode): call.missed 4949652d…, intro SMS 413b1b9a… delivered 06:33:40 UTC (carrier status delivered, 2 segments because of the "[SignalWire Free Trial]" prefix), four field replies, lead.qualified, calendar.event_created tbc43cc91db08513debd1916893472376d84cfc152 (verified on the butler Google calendar: 2026-10-20 14:00-15:00 EDT), appointment.confirmed, booking_confirmation SMS cad842a2… sent. Two preferred_time re-prompts happened before the parser upgrade below. Not yet proven: carrier forwarding from the cell with a second caller phone, answered-call suppression, STOP, the brief (all wait for messaging registration, i.e. the EIN).
- Allowlist removed 2026-10-19 by Michael himself (`TEXT_BACK_PILOT_RECIPIENTS` deleted from runtime.env, service restarted): the product texts every caller, the STOP list is the only exclusion; /health shows pilot_recipient_count=null. Runtime backup runtime.env.bak-20261019T* kept, mode 600.
- Google: re-minted 2026-10-18 ~23:20 UTC (consent in Michael's Windows Chrome, butler account; he pasted the localhost:1 redirect URL because the tool layer redacts the code). Hermes token and text_back calendar token share the installed client; /health calendar_credentials=ready. TEXT_BACK_GOOGLE_CLIENT_FILE still unset (Web client only needed for customer self-service reconnect).
- Telegram: acknowledged 2026-10-18 23:25:21 UTC (Hermes gateway log, chat id equals TEXT_BACK_TELEGRAM_CHAT_ID). The gateway long-polls the same bot, so text_back-side getUpdates is always empty; read ~/.hermes/logs/gateway.log instead.
- PR #13 merged and deployed 2026-10-19 (41cf1ca, scripts/deploy.sh local run, suite green, /health healthy): natural day-and-time replies ("this wednesday at 2", "next thursday at 4:00", abbreviations, @, noon, a.m./p.m., fillers), spoken examples in the prompts, confirmation reads "Thursday, Oct 22 at 4:00 PM EDT".
- Michael's 2026-10-19 requirements are listed in docs/notes/client-requests-2026-10-19.md: customizable per-client message copy, client GUI with login to edit it, Google/Outlook/iCal links in the confirmation, info gathering adds phone and email, emailed calendar invite. Build in that order, one layer per PR.
- Business identity: FluxWorks, LLC (SOSID 3401179), registration-draft.json holds the public details; the EIN does not exist yet (Michael, 2026-10-18) and the ~$16.50 registration charge is approved, so Brand/Campaign submission waits only for the EIN.
- Housekeeping: the stray GitKraken zip directory was moved out of the repo to ~/archive-yyCfIq-gitkraken-cli so scripts/deploy.sh sees a clean tree.

## Retained Recover backlog

The branch audit preserves unfinished work in
[the consolidation audit](docs/notes/branch-consolidation-2026-10-08.md#retained-requirements).
These requirements were recovered from historical notes; they do not replace the pilot
as NEXT or reopen the locked Answer/Grow phase order. The one-time calendar connection
contract is retained in docs/CALENDAR-PROVIDERS.md with accurate implementation status.

## NEXT (exactly one item)
Ship Michael's 2026-10-19 Recover requirements one layer per PR, in docs/notes/client-requests-2026-10-19.md order (customizable messages → client login GUI → calendar links → phone/email fields → emailed invite), each deployed with scripts/deploy.sh and re-tested on his cell. When the EIN arrives, submit the 10DLC Brand/Campaign (charge approved), then finish the remaining docs/ONBOARDING-FORWARDING.md checks with a second caller phone: forwarding from his cell, answered-call suppression, STOP and the brief. Preserve credentials, both numbers, landing/Grok work and unrelated services.

## NEXT SESSION PROMPT
Continue text_back on hermes-vcn-0 in /home/ubuntu/projects/text_back, branch main. Read CLAUDE.md and docs/notes/client-requests-2026-10-19.md first; read docs/SIGNALWIRE-INTEGRATION.md, docs/RECOVER-OPERATIONS.md and docs/ONBOARDING-FORWARDING.md when a layer touches them; privately read ~/.config/text_back/pilot-phones.json. Michael has fully authorized implementation, fixes, tests, deployment and commit/push. The core Recover loop is proven on his cell (2026-10-19) and the recipient allowlist is gone by his decision; do not reintroduce it. NEXT is his 2026-10-19 requirement list, one layer per PR in the listed order: customizable per-client message copy (the opt-out suffix is editable text but the word STOP stays mandatory for carriers), then the client login GUI that edits that copy, then Google/Outlook/iCal links in the confirmation, then phone and email fields, then the emailed calendar invite; deploy each with `TEXT_BACK_DEPLOY_LOCAL=1 bash scripts/deploy.sh` and re-test on his cell by having him call +17045695600. The EIN does not exist yet; when Michael supplies it, submit the 10DLC Brand/Campaign (the ~$16.50 charge is approved) and then run the remaining docs/ONBOARDING-FORWARDING.md checks with a second caller phone (forwarding from his cell, answered-call suppression, STOP, the brief). Google calendar credentials were re-minted 2026-10-18 and /health reports ready; if they die again, drive consent in Michael's Windows Chrome via claude-in-chrome (the butler account is signed in there, the Linux server Chrome has no Google account) and ask him to paste the localhost:1 redirect URL. Telegram acknowledgment is done; operator replies land in ~/.hermes/logs/gateway.log, not getUpdates. Never request the signing key again, rotate credentials, buy another number, submit a Brand/Campaign before the EIN, edit deploy/textback-designer/ or docs/demo/, or disturb private 443/public 8443. Run .venv/bin/pytest tests/ and the canon check after changes, record actual evidence here, commit named paths only and push.

## SPEC
- `docs/PRD-text_back.md` — requirements and architecture; no status log lives there.
- `docs/PRODUCT-MODEL.md`, `docs/COMPETITOR-MATRIX.md`, `docs/gtm/KOERNER-MODEL.md` — product and GTM.
- `docs/SIGNALWIRE-INTEGRATION.md`, `docs/ONBOARDING-FORWARDING.md`, `docs/CALENDAR-PROVIDERS.md`, `docs/OUTCOME-EVENTS.md` — contracts.
- `README.md` — how to run and test.
- Gotchas: `TEXT_BACK_SIGNALWIRE_SPACE_URL` already includes `https://`; SignalWire has no `/Balance.json`; the `!` runner is non-interactive; caller-ID passthrough on forwarded calls is proven only by the live test call.

- canon-allow: `src/text_back/handoff.py` (product code — the customer handoff module, not a state file)
