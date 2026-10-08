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
- Repo: git@github.com:mdrilesbutler/text_back.git — app code is branch `local/tdd-core` (`main` is stale). Piclaw worktree: `~/projects/text_back-tdd-core`.
- Runtime: hermes-vcn-0 (`ssh hermes-cloud`) — user-scoped `text-back.service` at 127.0.0.1:8000; public HTTPS at `https://hermes-cloud.tailefb1a4.ts.net:8443` through existing Tailscale Funnel. Google Calendar, persistent SQLite, managed worker and private Telegram alerts; SignalWire telecom is enabled with an explicitly empty pilot-recipient allowlist. Michael supplied his Verizon device numbers; they are saved privately for pilot setup, not yet applied to runtime.
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
- Commit on hermes-vcn-0 with `git -c user.name="Michael Riley" -c user.email="mdriles@gmail.com"` (no git identity on host).

## LOCKED (settled — do not re-open)
- Carrier: SignalWire (Twilio fallback). Spend ceiling $15/month (approved 2026-08-20).
- Booking backend: Google Calendar primary (decided 2026-08-29, "everyone has a gmail"); Microsoft Graph and iCloud CalDAV adapters shipped as options. Selected via `TEXT_BACK_CALENDAR_PROVIDER`; production telecom refuses to boot with the stub calendar.
- Customers never get a live human. Escalation = graceful exit + async operator lead. Guard: `tests/test_no_live_human_copy.py`.
- Deterministic policy, never an LLM, owns STOP/HELP, consent, quiet hours, booking truth, and handoff.
- `wiring_mode`: `forwarded` (default; first voice event per call_sid triggers) vs `managed` (terminal unanswered only). Never mix the rules.
- Webhooks verify `X-SignalWire-Signature` and fail closed; inbound claims and local intents commit atomically; durable outboxes own retries, and ambiguous SMS acceptance requires reconciliation.
- No booking is claimed without a Calendar event ID. Revenue comes only from explicit `revenue.attributed` events with evidence — never inferred from a booking.
- Product order: Recover first. Answer (voice) and Grow (journeys) wait until the real-phone Recover pilot proves conversion.
- GTM: Koerner ladder TB-ASSESS → TB-RECOVER → TB-CARE; sell missed-call recovery, not "AI".
- Google OAuth for text_back is minted with the google-oauth-repair skill pattern (existing Hermes client, butler account) — re-mint in ~5 min if revoked.
- Customer calendar reauth: silent refresh; on true revocation mark the client `reauth_required` and send a reconnect link. Customers never go through the operator OAuth-repair path.
- Credential intake: browser → `~/.config/text_back/` → verified via `/health`. Never chat, git, or Obsidian.
- The live-call verification checklist in `docs/ONBOARDING-FORWARDING.md` is mandatory at every client onboarding.
- Two-lane repo protocol: Grok owns `deploy/textback-designer/` + `docs/demo/`; Claude/Codex own everything else (incl. `docs/landing/`). Every commit is `--only`-scoped to named paths, never `-a`. Lane splits are recorded here, not in dated docs files.

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

## STATE (as of 2026-10-08; ≤ 10 lines; rewritten every handoff)
- Runtime rechecked 2026-10-08 ~04:24 UTC by codex-hermes-vcn-0: text-back.service active since 2026-09-20 08:33 UTC, public health 200/ok, Google ready, worker running, no errors, pilot_recipient_count=0. `pilot_check --health --providers`: Google free/busy verified; SignalWire account Full/active; number found, voice/SMS handlers match the public URLs exactly; brand list empty. Fast-forwarded local/tdd-core to upstream 7107639 (two crash-recovery tests); `.venv/bin/pytest tests/` → 370 passed. No real-phone pilot evidence exists; provider traffic was last inspected 2026-09-28.
- Read-only SQLite baseline unchanged on 2026-10-08: 0 appointments/booking_jobs/inbound_jobs/handoffs, 2 prior stub outbox rows, 10 outcome events, 1 delivered operator setup alert. Telegram human acknowledgment still pending. Existing runtime, pilot, SignalWire environment and Google token files are mode 600.
- 10DLC finding (SignalWire docs verified 2026-09-28, now in `docs/SIGNALWIRE-INTEGRATION.md`): unregistered US long codes cannot send SMS at all. The pilot number's `messaging_integration_test` capability is the Platform Free Trial assignment: SMS reaches only the ONE verified mobile paired in the Dashboard, prefixed `[SignalWire Free Trial]`, 200/day. Removing that verified number ends the trial permanently. So the pilot CALLER must be the verified mobile (most likely Michael's cell ending 5452, verified at signup — confirm in Dashboard, the API does not expose it), and the FORWARDING phone must be a different voice-capable phone. Every later client needs a Brand + Campaign (fees, ~1 week); treat as onboarding scope.
- Compatibility REST send path is read as outside the trial's "LaML integrations" exclusion; unverified until the first live send. Fallback documented (JSON `/api/messaging/messages`).
- Google token is an installed-client authorized-user JSON; TEXT_BACK_GOOGLE_CLIENT_FILE remains unset on 2026-10-08. Web OAuth callback registration in Michael's browser remains pending (project sunny-airfoil-489208-r6, redirect https://hermes-cloud.tailefb1a4.ts.net:8443/calendar/callback, then save client JSON to ~/.config/text_back/ and set TEXT_BACK_GOOGLE_CLIENT_FILE). Dedicated setup-browser and setup-proxy services are inactive/dead; no setup session was restarted.
- Canon check still reports five existing format issues: four missing AGENTS.md sections and CLAUDE.md as a second constitution. Followed this checkout's explicit CLAUDE.md state instructions; no canon migration performed.
- Blocked on Michael: (1) confirm which mobile is PFT-verified in the SignalWire Dashboard, (2) name a second voice-capable phone to be the forwarding phone (or approve swapping roles), (3) Google Web client registration, (4) Telegram acknowledgment. TEXT_BACK_PILOT_RECIPIENTS stays explicitly empty until (1) is confirmed.

## NEXT (exactly one item)
Run the real-phone Recover pilot once Michael confirms the PFT-verified mobile and a separate forwarding phone: set TEXT_BACK_PILOT_RECIPIENTS to that single verified mobile, restart the service, verify health shows count 1, then walk the `docs/ONBOARDING-FORWARDING.md` checklist (forward from the second phone to +17045695600, missed call from the verified mobile, one intro, qualification, provider-verified booking or async handoff, STOP, brief) and record evidence here. Google Web OAuth registration and Telegram acknowledgment complete in the same sitting. Preserve credentials, the existing number, the $15 ceiling, landing/Grok work and unrelated services.

## NEXT SESSION PROMPT
Continue text_back on hermes-vcn-0 in /home/ubuntu/projects/text_back, branch local/tdd-core. Read CLAUDE.md, docs/SIGNALWIRE-INTEGRATION.md (10DLC/PFT section), docs/RECOVER-OPERATIONS.md and docs/ONBOARDING-FORWARDING.md; privately read ~/.config/text_back/pilot-phones.json. Michael has fully authorized implementation, fixes, tests, deployment and commit/push; ask only for physical-device facts and account actions. SignalWire Platform Free Trial means the pilot caller must be the Dashboard-verified mobile and the forwarding phone must be a different phone; do not remove or re-verify any SignalWire number. Populate TEXT_BACK_PILOT_RECIPIENTS only with the confirmed verified mobile. Then complete Google Web callback registration in his browser, the phone checklist, STOP, operator receipt and the brief. Never request the signing key again, rotate credentials, buy another number, submit a Brand/Campaign without his explicit approval, restart remote-browser setup, edit deploy/textback-designer/ or docs/demo/, or disturb private 443/public 8443. Run .venv/bin/pytest tests/ and the canon check after changes, record actual evidence here, commit named paths only and push.

## SPEC
- `docs/PRD-text_back.md` — requirements and architecture; no status log lives there.
- `docs/PRODUCT-MODEL.md`, `docs/COMPETITOR-MATRIX.md`, `docs/gtm/KOERNER-MODEL.md` — product and GTM.
- `docs/SIGNALWIRE-INTEGRATION.md`, `docs/ONBOARDING-FORWARDING.md`, `docs/CALENDAR-PROVIDERS.md`, `docs/OUTCOME-EVENTS.md` — contracts.
- `README.md` — how to run and test.
- Gotchas: `TEXT_BACK_SIGNALWIRE_SPACE_URL` already includes `https://`; SignalWire has no `/Balance.json`; the `!` runner is non-interactive; caller-ID passthrough on forwarded calls is proven only by the live test call.

- canon-allow: `src/text_back/handoff.py` (product code — the customer handoff module, not a state file)
