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

## STATE (as of 2026-10-08; ≤ 10 lines; rewritten every handoff)
- Runtime rechecked 2026-10-08 ~06:06 UTC by codex-hermes-vcn-0: applied TEXT_BACK_BUSINESS_NAME='FluxWorks, LLC' in private runtime.env and restarted text-back.service; the running process has that exact value. Public health 200/ok, Google ready, worker running, no errors, pilot_recipient_count=0. Last full provider check at 05:38 verified free/busy and exact handlers. Provider traffic inspected at 04:28: no calls and only two inbound messages dated 2026-08-30; no real-phone pilot evidence exists. Latest suite: 391 passed; code at 105a147 passed CI.
- Read-only SQLite baseline unchanged on 2026-10-08: 0 appointments/booking_jobs/inbound_jobs/handoffs, 2 prior stub outbox rows, 10 outcome events, 1 delivered operator setup alert. Telegram human acknowledgment still pending. Existing runtime, pilot, SignalWire environment and Google token files are mode 600.
- SignalWire trial docs rechecked 2026-10-08: PFT permits SMS only to one assigned verified mobile. Read-only `/api/relay/rest/verified_caller_ids` returned exactly one entry, verified and matching the saved cell; its response has no PFT marker, so voice verification is proven but trial pairing is not. Do not ask Michael to supply or verify that cell again. The trial-role-swap plan conflicted with testing his actual business cell; corrected the onboarding and integration docs. Register messaging on the existing SignalWire number to text other callers while preserving his cell as the business line; no new number is needed.
- Compatibility REST send path is read as outside the trial's "LaML integrations" exclusion; unverified until the first live send. Fallback documented (JSON `/api/messaging/messages`).
- Fixed a real enrollment bug: STOP previously suggested START but opted-out contacts could not restart. Signed whole-message START/UNSTOP now clears application opt-out and sends a branded acknowledgment, preserving active handoffs and cancelled follow-ups. STOP cancels pending enrollment replies; the intro now includes STOP instructions. Eleven additional regression cases pass. No live SMS sent; handset/provider-level enrollment behavior remains unproven.
- Michael confirmed the exact legal business name: FluxWorks, LLC. It is now the pilot's configured business name. Private mode-600 `~/.config/text_back/registration-draft.json` contains matching brand and campaign copy generated from the actual policy functions, plus the already-supplied contact phone. EIN/issuing country, registered address, website, contact email and initial-consent evidence remain unfilled; do not guess or put them in git. SignalWire's saved browser session redirects to login, and the brand API still lists no brands; no registration submitted. Landing privacy/terms remain placeholders and the voice greeting does not collect affirmative initial-text consent. Public registration estimate remains $16.50 upfront plus $1.50/month campaign fee, subject to the authenticated quote and inactivity conditions.
- Google Web client upload deployed at `/operator/setup/google-client`; `TEXT_BACK_SETUP_DIRECTORY=~/.config/text_back/setup` is enabled, runtime.env remains mode 600. Independent purpose-bound, single-use, one-hour invitations stage `google-web-client.pending.json` without replacing the existing token. Tests cover scoped authorization, expiry, malformed/desktop clients, callback mismatch, size limit and no overwrite; isolated Chromium verified mobile layout, fragment removal and upload interaction. Public page 200/no-store; unauthenticated upload 401. Google Web registration remains pending in project sunny-airfoil-489208-r6 with redirect https://hermes-cloud.tailefb1a4.ts.net:8443/calendar/callback. TEXT_BACK_GOOGLE_CLIENT_FILE remains unset; after a real upload, inspect privately, configure it and complete browser reconnection. Dedicated remote setup-browser/proxy were not restarted.
- Branch consolidation 2026-10-08 by codex-hermes-vcn-0: recovered carrier keywords/consent evidence/configurable HELP, Outlook calendarView/pagination and exact duplicate-slot checks, workflow diagrams, and unfinished requirements from old state. Current STOP cancellation, handoff protection, Google setup and designer assets preserved. Audit/exclusions: docs/notes/branch-consolidation-2026-10-08.md. GitHub ruleset 24703349 prevents WIP/state recreation; main remains PR + canon/review protected. Combined suite: 445 passed; additional signed HELP wiring test passes (16 policy tests). CI validates the final 446-test suite; details in audit. Generic canon checker still objects to CLAUDE.md; explicit project exception retained. Final merge/deletion/deployment evidence is attached to the cleanup PR.
- Remaining pilot dependencies: private LLC verification fields and consent evidence for messaging registration on the existing SignalWire number, Google Web client registration (no file uploaded yet), Telegram acknowledgment and physical missed/answered-call checks on Michael's existing cell. Exact legal name, cell and backend number are already supplied; do not repeat those questions or require another forwarding phone. No registration submitted or phone routing changed; allowlist remains explicitly empty pending a supported, approved test recipient.

## Retained Recover backlog

The branch audit preserves unfinished work in
[the consolidation audit](docs/notes/branch-consolidation-2026-10-08.md#retained-requirements).
These requirements were recovered from historical notes; they do not replace the pilot
as NEXT or reopen the locked Answer/Grow phase order. The one-time calendar connection
contract is retained in docs/CALENDAR-PROVIDERS.md with accurate implementation status.

## NEXT (exactly one item)
Complete the real-phone Recover pilot on Michael's actual existing cell: resolve messaging registration for the already-owned SignalWire number using accurate business details and the approved $15 ceiling, finish Google Web OAuth/operator setup, then configure conditional forwarding from his cell to +17045695600 and execute every `docs/ONBOARDING-FORWARDING.md` check with an approved caller using an existing phone. Set the allowlist only for that supported test recipient. Prove missed-call recovery, answered-call suppression, booking or async handoff, STOP and the brief. Preserve credentials, both existing numbers, landing/Grok work and unrelated services; no replacement number or trial-driven role swap.

## NEXT SESSION PROMPT
Continue text_back on hermes-vcn-0 in /home/ubuntu/projects/text_back, branch main. Read CLAUDE.md, docs/SIGNALWIRE-INTEGRATION.md (10DLC/PFT section), docs/RECOVER-OPERATIONS.md and docs/ONBOARDING-FORWARDING.md; privately read ~/.config/text_back/pilot-phones.json. Michael has fully authorized implementation, fixes, tests, deployment and commit/push. He explicitly requires his existing cell to remain the public business/forwarding number; the already-owned SignalWire number is the backend and SMS sender. The API already confirms his saved cell is voice-verified. Do not repeat the phone inventory question, require another forwarding phone or swap roles to accommodate the trial. Resolve messaging registration for other callers with actual business details and fees, complete Google Web callback registration and operator acknowledgment, then the full real-phone checklist and brief. Never request the signing key again, rotate credentials, buy another number, submit a Brand/Campaign without his explicit approval, restart remote-browser setup, edit deploy/textback-designer/ or docs/demo/, or disturb private 443/public 8443. Run .venv/bin/pytest tests/ and the canon check after changes, record actual evidence here, commit named paths only and push.

## SPEC
- `docs/PRD-text_back.md` — requirements and architecture; no status log lives there.
- `docs/PRODUCT-MODEL.md`, `docs/COMPETITOR-MATRIX.md`, `docs/gtm/KOERNER-MODEL.md` — product and GTM.
- `docs/SIGNALWIRE-INTEGRATION.md`, `docs/ONBOARDING-FORWARDING.md`, `docs/CALENDAR-PROVIDERS.md`, `docs/OUTCOME-EVENTS.md` — contracts.
- `README.md` — how to run and test.
- Gotchas: `TEXT_BACK_SIGNALWIRE_SPACE_URL` already includes `https://`; SignalWire has no `/Balance.json`; the `!` runner is non-interactive; caller-ID passthrough on forwarded calls is proven only by the live test call.

- canon-allow: `src/text_back/handoff.py` (product code — the customer handoff module, not a state file)
