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
- Michael supplied both Verizon devices on 2026-09-20: cell ending 5452 is the forwarding phone; iPad line ends 1633. Full E.164 numbers are in `/home/ubuntu/.config/text_back/pilot-phones.json` (mode 600; read privately, never commit). Do not ask for these numbers or carriers again. He expects any number to be able to call his cell; that is distinct from enabling unrestricted customer SMS during the pilot. Apple documents iPad cellular as data-only, with calls/texts relayed through an iPhone; do not assume the iPad line supplies a separate caller identity. SignalWire Recover number is +17045695600: unanswered calls forward FROM his Verizon cell TO this number; Recover texts the original caller FROM SignalWire. No forwarding activation or phone test is established.
- Preserve landing v1–v6/directions A–C pending Michael's pick/change list and Grok's `deploy/textback-designer/` + `docs/demo/`. Those directories and landing sources were not edited. Michael reiterated on 2026-09-18: stop asking for verification approval; it is already granted.
- Checkpoint `a260707` pushed and live-origin verified before this handoff; all 368 tests and canon passed. Full phone-test sequence is in `docs/ONBOARDING-FORWARDING.md`. Google Web callback registration and Telegram human acknowledgment remain pending. Project sunny-airfoil-489208-r6; callback https://hermes-cloud.tailefb1a4.ts.net:8443/calendar/callback; no separate Web client file configured. Preserve working pilot token and submitted matching SignalWire signing key; intake stays disabled, remote browser retired, ports 80/10000 removed. No real-phone test or new booking; prior VS Code turn completed and absorbed. Engineering, testing, deployment and commit/push authorization persists; tool approvals are now disabled.

## NEXT (exactly one item)
Finish the real-phone Recover pilot using the saved Verizon device details: establish an independent caller phone capable of voice/SMS (the iPad data line is not proof), populate only approved pilot recipients, finish Google Web OAuth registration in Michael's normal browser, then complete the phone checklist and operator acknowledgment. Preserve working credentials, existing number, $15 ceiling, landing/Grok work and unrelated services. Do not ask again for supplied numbers/carriers or engineering approval.

## NEXT SESSION PROMPT
Continue text_back on hermes-vcn-0 in /home/ubuntu/projects/text_back, branch local/tdd-core. Read CLAUDE.md, docs/RECOVER-OPERATIONS.md and docs/ONBOARDING-FORWARDING.md; privately read ~/.config/text_back/pilot-phones.json for the supplied Verizon cell and iPad numbers. Michael has fully authorized implementation, fixes, tests, deployment and commit/push; ask only for missing physical-device facts or account actions. His cell is the forwarding phone; the purchased SignalWire number +17045695600 receives unanswered calls and sends Recover SMS to the original caller. Verify a genuinely separate caller/SMS device; iPad cellular service alone is data-only. Any number may call the cell; do not equate that with removing the SMS pilot allowlist. It remains explicitly empty at handoff. Next complete normal-browser Google Web callback registration, approved pilot activation, missed/answered calls, caller ID, one intro, qualification, provider-verified booking or async handoff, STOP, operator receipt and outcome reporting. Preserve existing credentials; never request the signing key again, rotate credentials, buy another number, restart remote-browser setup, edit deploy/textback-designer/ or docs/demo/, or disturb private 443/public 8443. No real-phone pilot has happened. Run .venv/bin/pytest tests/ and the canon check after relevant changes, record actual evidence here, commit named paths only and push.

## SPEC
- `docs/PRD-text_back.md` — requirements and architecture; no status log lives there.
- `docs/PRODUCT-MODEL.md`, `docs/COMPETITOR-MATRIX.md`, `docs/gtm/KOERNER-MODEL.md` — product and GTM.
- `docs/SIGNALWIRE-INTEGRATION.md`, `docs/ONBOARDING-FORWARDING.md`, `docs/CALENDAR-PROVIDERS.md`, `docs/OUTCOME-EVENTS.md` — contracts.
- `README.md` — how to run and test.
- Gotchas: `TEXT_BACK_SIGNALWIRE_SPACE_URL` already includes `https://`; SignalWire has no `/Balance.json`; the `!` runner is non-interactive; caller-ID passthrough on forwarded calls is proven only by the live test call.

- canon-allow: `src/text_back/handoff.py` (product code — the customer handoff module, not a state file)
