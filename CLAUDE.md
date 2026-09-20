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
- Runtime: hermes-vcn-0 (`ssh hermes-cloud`) — user-scoped `text-back.service` at 127.0.0.1:8000; public HTTPS at `https://hermes-cloud.tailefb1a4.ts.net:8443` through existing Tailscale Funnel. Google Calendar, persistent SQLite, managed worker and private Telegram alerts; SignalWire telecom is enabled with an empty pilot-recipient allowlist, so no customer SMS can send until Michael approves test numbers.
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

## STATE (as of 2026-09-20; ≤ 10 lines; rewritten every handoff)
- Recover recovery on hermes-vcn-0, branch `local/tdd-core`, implementation commit `e4b9f5a`: the three lost-retry cases have passing regressions; customer SMS outbox, transactional inbound processing, persistent webhook inbox, and managed startup/shutdown worker are wired. Michael authorized publishing all changes; verify live origin for synchronization claims.
- SMS uses bounded definite-failure retries, persisted send ownership, unknown-outcome holds, signed SignalWire status reconciliation, STOP/quiet-hour/cancellation checks, and provider-backed outcome evidence. Operator alerts isolate malformed payloads and protect concurrent final attempts. Google event recovery verifies the provider event after a local-commit interruption.
- Qualified bookings retry calendar outages without another customer reply, pause on reauth, and produce a durable operator handoff after exhaustion. Google authorized-user credentials refresh with file locking/atomic mode-600 persistence; revocation queues reconnect links; browser reconnection uses expiring state, PKCE, cookie binding, and configured-calendar write verification.
- Validation: `.venv/bin/pytest tests/` → 368 passed on 2026-09-20; canon clean. Seven pilot-recipient regressions cover empty/explicit allowlists, inbound rejection before persisted work, outbound transport blocking, and malformed configuration. Five credential-intake tests cover authentication, origin, expiry, private atomic storage, durable single use, input limits and overwrite protection; native form submission verified using an isolated dummy key. Two Node keyboard-proxy regressions pass. Signed local journey/restart, Web OAuth and Telegram tests remain green. Journey providers are fakes; real-phone pilot remains unproven.
- Runtime rechecked 2026-09-20 around 10:00 UTC: user service active since 08:33 UTC, public health HTTP 200/status ok, Google ready, worker running without errors, pilot_recipient_count=0. TEXT_BACK_PILOT_RECIPIENTS remains explicitly empty and credential intake disabled. Read-only SQLite baseline: zero inbound/booking jobs or appointments, two prior stub sends, nine outcome events, one delivered operator setup alert. Earlier public signed boundary checks were synthetic, not a real-phone pilot. Backups remain protected; private 443→5176 and public 8443 preserved.
- Live provider evidence on 2026-09-20: Google free/busy succeeds. SignalWire Compatibility account API HTTP 200 reports type Full/status active. Existing number supports voice/SMS/MMS; brand list empty, no account-specific send restriction established. Existing number update returned HTTP 200; readback verifies POST voice/SMS URLs exactly https://hermes-cloud.tailefb1a4.ts.net:8443/webhooks/voice and /webhooks/sms. Actual carrier signature/handset delivery still unproven.
- Private Telegram destination discovered from existing Hermes home channel, matched allowed user, verified by Telegram `getChat` as Michael/private. Managed worker delivered setup alert `operator-channel-check-2026-09-19` on first attempt; receipt `telegram-35a40e374ec2-632`. Human acknowledgment remains pending. Test is an operator setup check, not a real customer lead or phone pilot.
- Michael submitted the existing SignalWire signing key via native HTTPS intake; it matched the configured value and was privately applied, never rotated. Intake is disabled; temporary remote browser services and ports 80/10000 remain retired. On continuation, requested approved caller mobiles, forwarding cell/carrier, Telegram acknowledgment, and normal-browser Google Web callback registration; answers still pending. Project sunny-airfoil-489208-r6; callback https://hermes-cloud.tailefb1a4.ts.net:8443/calendar/callback. No separate Google client file is configured; working embedded pilot credentials remain preserved. Never send Michael back to the remote browser.
- Preserve landing v1–v6/directions A–C pending Michael's pick/change list and Grok's `deploy/textback-designer/` + `docs/demo/`. Those directories and landing sources were not edited. Michael reiterated on 2026-09-18: stop asking for verification approval; it is already granted.
- Continuation began from clean `40ed82b` on `local/tdd-core`; all 368 tests and canon passed again. Expanded `docs/ONBOARDING-FORWARDING.md` with the complete real-phone evidence sequence, STOP checks and outcome reconciliation. No real-phone test, provider send, booking, routing change or credential rotation performed during this continuation. Prior VS Code session was completed and absorbed; no unfinished turn to kill.

## NEXT (exactly one item)
Finish the real-phone Recover pilot once Michael supplies the approved SMS mobile and forwarding phone details: populate the pilot allowlist, finish Google Web OAuth callback registration through his normal laptop browser, then verify missed/answered call behavior, caller-ID passthrough, exactly one intro, qualification, real Calendar booking or asynchronous handoff, STOP and outcome reporting. SignalWire handlers and existing signing key are now configured; preserve the working Google token, purchased number and $15 ceiling. Operator alert receipt needs human acknowledgment. Do not ask for implementation/testing approval again; keep landing/Grok work untouched.

## SPEC
- `docs/PRD-text_back.md` — requirements and architecture; no status log lives there.
- `docs/PRODUCT-MODEL.md`, `docs/COMPETITOR-MATRIX.md`, `docs/gtm/KOERNER-MODEL.md` — product and GTM.
- `docs/SIGNALWIRE-INTEGRATION.md`, `docs/ONBOARDING-FORWARDING.md`, `docs/CALENDAR-PROVIDERS.md`, `docs/OUTCOME-EVENTS.md` — contracts.
- `README.md` — how to run and test.
- Gotchas: `TEXT_BACK_SIGNALWIRE_SPACE_URL` already includes `https://`; SignalWire has no `/Balance.json`; the `!` runner is non-interactive; caller-ID passthrough on forwarded calls is proven only by the live test call.

- canon-allow: `src/text_back/handoff.py` (product code — the customer handoff module, not a state file)
