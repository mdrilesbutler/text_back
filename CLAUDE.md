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
- Runtime: hermes-vcn-0 (`ssh hermes-cloud`) — user-scoped `text-back.service` at 127.0.0.1:8000, stub telecom + real Google Calendar, managed worker and persistent SQLite; restarted and health verified 2026-09-19 with the Web OAuth migration fix. No public URL.
- Credentials: hermes-cloud `~/.config/text_back/{pilot,runtime,signalwire}.env` + `google_token.json`, mode 600, never git. Preserve credentials; verify the existing project signing key before live webhooks, without rotating it.
- SignalWire: FluxWorks space, funded, one voice/SMS/MMS pilot number, no handlers attached, $15/month ceiling.
- Google Calendar: calendar-only authorized-user JSON for mdrilesbutler@gmail.com; refresh and read-only free/busy live-verified 2026-09-18.
- CI: GitHub Actions runs pytest on every push/PR (py3.12/3.13).
- Grok's lane: `deploy/textback-designer/` + `docs/demo/` (designer UI, story film). Claude/Codex never edit or commit those.

## HOW TO WORK WITH RILES
- He does not code. Terse, decisive answers. Recommend; don't hand him option menus.
- Small compartmentalized specs, one layer at a time.
- Michael authorized autonomous completion on 2026-09-16: "continue working until the product is working" and "you don't have to ask for my approval any more." Proceed with routine in-scope inspection, fixes, tests, and verification; do not repeatedly ask for approval already given. Preserve the specific live-service boundaries below and obey tool-enforced permissions.
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

## STATE (as of 2026-09-19; ≤ 10 lines; rewritten every handoff)
- Recover recovery on hermes-vcn-0, branch `local/tdd-core`, implementation commit `e4b9f5a`: the three lost-retry cases have passing regressions; customer SMS outbox, transactional inbound processing, persistent webhook inbox, and managed startup/shutdown worker are wired. Michael authorized publishing all changes; verify live origin for synchronization claims.
- SMS uses bounded definite-failure retries, persisted send ownership, unknown-outcome holds, signed SignalWire status reconciliation, STOP/quiet-hour/cancellation checks, and provider-backed outcome evidence. Operator alerts isolate malformed payloads and protect concurrent final attempts. Google event recovery verifies the provider event after a local-commit interruption.
- Qualified bookings retry calendar outages without another customer reply, pause on reauth, and produce a durable operator handoff after exhaustion. Google authorized-user credentials refresh with file locking/atomic mode-600 persistence; revocation queues reconnect links; browser reconnection uses expiring state, PKCE, cookie binding, and configured-calendar write verification.
- Validation: `.venv/bin/pytest tests/` → 347 passed on 2026-09-19, including signed SignalWire local end-to-end tests and a real ASGI process restart smoke test. New regression proves configuring a Web OAuth client preserves refresh with the token's original client until successful browser reconnect replaces it. Providers in journey tests are fakes.
- Restarted the existing localhost user service with the reviewed `deploy/systemd/text-back.service`; preserved stub telecom, signing key, sender, and routing. Enabled Google Calendar, persisted worker state, credential-directory writes, and a new separate operator API key only where absent. Protected pre-change environment/unit backups remain beside their originals.
- Live read-only verification on 2026-09-19: Google free/busy succeeds; runtime uses google calendar, stub telecom, persistent SQLite and an error-free worker. SignalWire owned-number and project APIs return HTTP 200; existing longcode supports voice/SMS/MMS and reports `messaging_integration_test`. No voice/SMS URLs attached. Brand-list API returns HTTP 200 with an empty complete list. Project API exposes neither trial status nor signing key; these checks do not establish a send restriction. No live traffic, events, purchases, routing changes, credential rotation, or public exposure.
- Concrete missing pilot inputs: intended HTTPS hostname, monitored operator destination, business test phone/carrier and separate approved caller phone. Inspected `~/.config/text_back/`, relevant proxy/service configuration, and completed VS Code session; none supplies those inputs. Google Web OAuth client file is unset and HTTPS callback registration remains unverified. Question sent to Michael; do not infer approval for a recipient from an address book or provider registration. Real-phone pilot unproven.
- Operations: `docs/RECOVER-OPERATIONS.md`, `scripts/pilot_check.py`, `deploy/install_local_runtime.py`, and `deploy/Caddyfile`. Authenticated `/operator/handoffs` exposes durable leads; external alert delivery remains disabled pending a monitored destination. Do not mistake redacted logging or green health for a monitored pilot.
- Preserve landing v1–v6/directions A–C pending Michael's pick/change list and Grok's `deploy/textback-designer/` + `docs/demo/`. Those directories and landing sources were not edited. Michael reiterated on 2026-09-18: stop asking for verification approval; it is already granted.
- VS Code session `01a0ae70-b1e4-73d2-a2bc-bbb8a0dffcd8` completed its last turn at 2026-09-18 21:50 UTC. Absorb its work in this checkout; no unfinished turn to continue or kill. Michael requested committing and pushing all changes; GitHub CLI and existing SSH identity verified as `mdrilesbutler`.

## NEXT (exactly one item)
Complete the real-phone Recover pilot after the pending endpoint/operator/test-phone answer: configure the intended HTTPS endpoint and Google Web OAuth callback, verify the existing SignalWire signing key and any actual provider restrictions, attach the exact handlers, then run forwarding/caller-ID/one-intro/answered-call/STOP/booking-or-handoff/outcome checks. Reuse the owned number. Do not repeat assessment, infer unspecified eligibility blockers, rotate credentials, contact unapproved people, or disturb pending landing/Grok work.

## SPEC
- `docs/PRD-text_back.md` — requirements and architecture; no status log lives there.
- `docs/PRODUCT-MODEL.md`, `docs/COMPETITOR-MATRIX.md`, `docs/gtm/KOERNER-MODEL.md` — product and GTM.
- `docs/SIGNALWIRE-INTEGRATION.md`, `docs/ONBOARDING-FORWARDING.md`, `docs/CALENDAR-PROVIDERS.md`, `docs/OUTCOME-EVENTS.md` — contracts.
- `README.md` — how to run and test.
- Gotchas: `TEXT_BACK_SIGNALWIRE_SPACE_URL` already includes `https://`; SignalWire has no `/Balance.json`; the `!` runner is non-interactive; caller-ID passthrough on forwarded calls is proven only by the live test call.

- canon-allow: `src/text_back/handoff.py` (product code — the customer handoff module, not a state file)
