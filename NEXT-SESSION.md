# text_back — next session prompt (updated 2026-08-29, piclaw, Claude)

## Continue-project contract
When Michael starts an agent from this project directory and says "continue project", "continue", "pick up", or equivalent, read this `NEXT-SESSION.md` completely before taking action. Then read the files it names, briefly state the recovered state, and begin the highest-priority open item unless a newer user instruction overrides the handoff.

## Where everything stands (verified 2026-08-20, fresh)
- Canonical checkout: `/home/ubuntu/projects/text_back` on hermes-vcn-0 (piclaw mirror path: `/home/mdriles/projects/text_back`).
- Remote: `git@github.com:mdrilesbutler/text_back.git`, branch `local/tdd-core`; completed items are pushed to origin (verify with `git log --oneline -5`).
- Test suite: `.venv/bin/pytest tests/` → **301 passed** (verified 2026-08-29), rerun after every change.
- Implemented: FastAPI app (`/health`, `/webhooks/voice`, `/webhooks/sms`); fail-closed Twilio-compatible signatures; idempotency via `claim_event`; deterministic STOP/HELP; Calendar stub gating confirmation on event ID; conversation slot-filling (service → location → preferred_time → name); `wiring_mode` = `forwarded` (default, conditional-forwarding attach to a client's existing number) / `managed` (ported number, terminal-unanswered rule).
- Docs: `PRD-text_back.md` (labeled root PRD — bare `PRD.md` no longer exists), `docs/ONBOARDING-FORWARDING.md` (per-carrier conditional-forwarding runbook + mandatory live verification checklist).
- gcloud CLI exists on hermes-vcn-0 but is irrelevant to customer calendar onboarding; do not revive the superseded service-account path.
- Approvals given by Michael 2026-08-20: SignalWire purchase path with a **$15/month ceiling**; product must attach to customers' actual existing phone numbers (drove `wiring_mode`); everything must be reproducible for the **fluxworks catalog**.
- SignalWire estimate (researched 2026-08-20): ≈ $9.44/month all-in at pilot volume; setup ≈ $12 one-time + $5 minimum funding; 10DLC approval ~1–2 weeks; cheap $1.50/month tier needs an EIN. Details in `PRD-text_back.md` § Cost refresh.
- Environment loader is implemented: `create_app()` reads all documented `TEXT_BACK_*` settings, explicit arguments override environment values, and `/health` reports non-secret effective config.
- SignalWire pilot progress (2026-08-27): Space funded and one voice/SMS/MMS-capable pilot number purchased. Protected credentials exist under `~/.config/text_back/` with mode 600; authenticated Compatibility API discovery returned HTTP 200 and found exactly that configured number. A canonical protected `runtime.env` and enabled localhost-only `text-back.service` now run in safe `stub` mode at `127.0.0.1:8000`; `/health` is green. The number still has no voice/SMS handlers attached, no live message/call has been sent, and SignalWire mode correctly refuses startup without the Project signing key and exact public HTTPS base URL.
- SignalWire re-verified 2026-08-28 (Claude): authenticated Compatibility API shows the pilot number active with voice/SMS/MMS/fax capabilities and `voice_url`/`sms_url` both unset; Michael confirmed the Space holds funds — money is NOT a blocker. Michael explicitly deferred the public-HTTPS deployment decision (tunnel for smoke test vs. durable Caddy+domain on this VPS); do not expose anything until he chooses. API gotchas: `TEXT_BACK_SIGNALWIRE_SPACE_URL` in `runtime.env` already includes `https://` (strip before building URLs); Twilio-style `/Balance.json` 404s on SignalWire.
- NOT done: choose/approve a durable public HTTPS deployment with persistent storage, build the customer-facing one-time calendar connection layer, attach live voice/SMS handlers, run production traffic, or pick a LIVE handoff-alert channel (the delivery outbox/seam is built and default-disabled; Michael must choose the destination).
- 2026-08-29 (piclaw, Claude): worked in a separate worktree lane; Grok's UI lane (`deploy/`, `docs/demo/`) untouched by agreement.
- **Where everything lives (recorded 2026-08-29 at Michael's request):** app code = branch `local/tdd-core` (piclaw worktree `~/projects/text_back-tdd-core`; the plain `~/projects/text_back` checkout is on stale `main`). Credentials/runtime = hermes-vcn-0 (`ssh hermes-cloud`) `~/.config/text_back/{pilot,runtime,signalwire}.env` mode 600 + localhost-only `text-back.service` in stub mode. Michael HAS a SignalWire account (space flux…) with funded pilot number; agents have API access via the stored PT token.
- **Signing key clarification (verified against SignalWire docs 2026-08-29):** `TEXT_BACK_WEBHOOK_SECRET` is the dedicated Project Signing Key, not the PT API token. It is now stored only in hermes-cloud's protected runtime config; never copy its value into Git, Obsidian, or chat.
- **Superseded operator auth attempt:** the earlier headless `gcloud auth login`/service-account path is not customer onboarding and must not be revived as the product design. A pilot Calendar API token later proved the adapter; the sellable flow is the one-time in-app connection described below.
- **SIGNING KEY STORED (2026-08-29 evening):** retrieved from the FluxWorks dashboard (API Credentials → Signing Key) via browser at Michael's order and appended to hermes-cloud `~/.config/text_back/runtime.env` as `TEXT_BACK_WEBHOOK_SECRET` (mode 600); `text-back.service` restarted, `/health` green. SignalWire-mode startup is no longer blocked on it. ROTATE the key in the dashboard at deploy time — the value transited a session transcript (transcripts sync to GitHub nightly).
- **NEW PRODUCT PRINCIPLE (Michael, 2026-08-29): customers never get a live human — that's the whole point.** Escalation = graceful exit + async operator lead, never a transfer or "call the business line". Copy fixed in policy.py/followup.py/cxml.py; guard test `tests/test_no_live_human_copy.py`; PRD § compliance updated.
- **DECIDED (Michael, 2026-08-29) — ONE-TIME CUSTOMER CALENDAR CONNECTION:** a nontechnical owner connects the Google, Microsoft/Outlook, or iCloud calendar already used by the business once inside text_back; normal operation requires nothing else. Provider adapters are hidden plumbing. No Cal.com account, service-account sharing, token files, or recurring credential work is customer-facing. The adapter layer is built and fail-closed; the in-app connection screen, OAuth callbacks, encrypted connection store, automatic refresh broker, and calendar picker are not yet built. See `docs/CALENDAR-PROVIDERS.md`.
- **Pilot Google API proof DONE (2026-08-29 evening):** a dedicated calendar-only pilot token was installed outside Git and Calendar API returned 200. This proves the Google adapter, not the sellable onboarding flow. The production owner experience must be one Connect Calendar action with text_back retaining and refreshing the connection thereafter.

## Open items, in order
0. **Product model (docs done 2026-08-20):** canonical `docs/PRODUCT-MODEL.md`. Build only the Recover P0 queue next: voicemail response → preferred-time booking → human handoff → append-only outcome events → bounded no-response sequence → Recovered Revenue Brief generator. Voice Answer and Grow journeys wait until the real-phone Recover pilot proves conversion.
0a. **GTM (docs done 2026-08-20):** Koerner model live at `docs/gtm/KOERNER-MODEL.md`. Optional next: PDF leave-behind, Stripe links for TB-ASSESS/RECOVER/CARE (Michael money gate).
1. **Michael (browser)**: enable SignalWire Platform Free Trial under Messaging Campaigns by verifying his personal mobile. This permits REST API test messages only between the purchased pilot number and that one verified mobile (200/day, trial prefix); it does not enable cXML/SWML messaging. Michael is operating as a sole proprietor while an LLC is pending. Do not submit a paid Brand/Campaign yet unless he explicitly chooses that path after seeing the displayed fees.
2. **Agent (unblocked local work)**: build the one-time calendar connection domain and UI/API contract TDD — `CalendarConnection`, encrypted credential reference, `connected|degraded|reauth_required` states, Connect Calendar callback seams, calendar picker, and automatic refresh interface. Do not require real provider credentials for deterministic tests.
3. **Agent + Michael only after public-domain approval**: register Google and Microsoft provider apps/redirect URLs and the Apple connection path, then perform one pilot onboarding through the same customer-facing Connect Calendar flow. This is the only calendar setup Michael should see.
4. **Agent (done locally 2026-08-21)**: SignalWire callbacks now require `X-SignalWire-Signature`, return cXML, and forwarded calls receive branded `<Say>` + `<Hangup>` with no retained recording. Live attachment/testing remains gated.
5. **Agent (done locally 2026-08-21)**: explicit `preferred_time` input is parsed in the configured timezone; vague/past/DST-unsafe input is re-prompted; the four fields feed free/busy-rechecked booking; confirmation remains gated on event ID. Live customer onboarding through the one-time connection flow is still pending.
5a. **Agent (done locally 2026-08-21)**: deterministic customer-requested/safety handoff persists active state, pauses SMS and missed-call automation, preserves STOP/HELP, supports explicit resolution, and emits an idempotent concise operator payload to an in-memory notifier. External operator delivery remains unimplemented.
5b. **Agent (done locally 2026-08-21)**: append-only outcome events now capture missed/contacted/engaged/field/qualified/handoff/slot/event/confirmed facts with stable evidence IDs and retry-safe idempotency keys. See `docs/OUTCOME-EVENTS.md`.
5c. **Agent (done locally 2026-08-25, TDD)**: bounded no-response sequence implemented in `src/text_back/followup.py` + `followups` store table. Scheduled only after an accepted intro SMS; configurable `TEXT_BACK_FOLLOWUP_DELAYS_MINUTES` (default `120,1440`), `TEXT_BACK_FOLLOWUP_EXPIRY_MINUTES` (default `2880`), quiet hours `TEXT_BACK_QUIET_HOURS_START/END` (default 21:00/08:00, business tz, overnight-window aware); defers in-quiet sends to quiet-end; cancels on reply/STOP/opt-out/booking/active handoff; idempotent via claim_event; records `followup.sent` + `lead.expired` with evidence. `run_due_followups` is a pure injected-clock seam — NO live cron/queue/provider send exists.
5d. **Agent (done locally 2026-08-25, TDD)**: Recovered Revenue Brief in `src/text_back/brief.py` (`build_brief_data` + `render_brief`): deterministic period projection of the outcome ledger — unique-lead funnel, confirmed-appointment evidence list, revenue summed ONLY from explicit `revenue.attributed` events (integer `amount_cents` + external evidence ID); honest "No attributed revenue recorded" otherwise. `record_outcome` gained optional `occurred_at`.
5e. **Agent (done locally 2026-08-27, TDD)**: operator write path in `src/text_back/operator.py` — `record_job_completed` and `record_revenue_attributed`. Completion requires CRM/job evidence; revenue requires a matching completed job plus invoice/payment evidence and a non-negative integer `amount_cents`. Bookings cannot attribute revenue. Idempotent. No HTTP/CRM connector. Next P0 option: external handoff-alert delivery.
5f. **Agent (done locally 2026-08-29, TDD, adversarially reviewed)**: external handoff-alert delivery seam in `src/text_back/delivery.py` + `handoff_deliveries` store table. Durable outbox enqueued on handoff activation (durable-unique uuid alert IDs; enqueue failure raises — never a silent drop); transport interface with only safe channels (`disabled` default, `log` with PII-masked output); `TEXT_BACK_HANDOFF_DELIVERY_CHANNEL`/`_RETRY_DELAYS_MINUTES` validated fail-closed at `create_app`; pure injected-clock `run_due_deliveries` persists the attempt BEFORE calling the transport (crash mid-delivery re-runs as attempt N+1 — true at-least-once), catches all transport exceptions, bounded backoff, ledger-first dead-letter evidence (`handoff.alert_delivered`/`handoff.alert_dead_lettered`). NO live channel exists — Michael must choose the destination (gate). Also this session: clock-driven quiet-hours tests (`tests/test_quiet_hours_clock.py`: boundaries, DST, expiry interplay) and GitHub Actions CI (`.github/workflows/ci.yml`, least-privilege, py3.12/3.13). Known pre-existing issue found in review, NOT yet fixed: `followup.py:201-204` has the same claim-before-persist crash-wedge shape that delivery.py just fixed — apply the `begin_attempt` pattern there next.
6. Store SignalWire Space URL, least-privilege API token, Project ID, and signing key outside Git; deploy and attach the HTTPS handlers. The outbound REST adapter and inbound boundary are built; live provider configuration and the Calendar adapter remain. Then run a real-phone smoke test per `docs/ONBOARDING-FORWARDING.md`.

## Session gotchas (hard-won)
- The `!` bash-input runner is NOT interactive: `gcloud auth login --no-launch-browser` crashes with EOFError waiting for the code. Fix: `: > code.txt; tail -f code.txt | gcloud auth login --no-launch-browser > login.log 2>&1 &`, hand the URL from the log to Michael, append his verification code to `code.txt`.
- Google "access blocked" on the OAuth page — most common cause is an in-app webview (link tapped in Telegram/email). Have Michael copy the URL into full Chrome/Safari. Unresolved this session.
- No git identity on hermes-vcn-0: commit with `git -c user.name="Michael Riley" -c user.email="mdriles@gmail.com" commit ...` (matches the repo's existing author).
- Trigger semantics are MODE-SPECIFIC: `managed` = text only on terminal unanswered status (`no-answer`/`busy`/`failed`/`canceled`); `forwarded` = the first voice event per `call_sid` triggers, whatever the status, because carrier CF only forwards already-missed calls. Idempotency in both modes comes from `claim_event` keyed on `call_sid` (exactly one SMS across ringing/completed retries). Don't "fix" one mode with the other's rule. See README "Wiring mode" and `tests/test_wiring_mode.py`.
- Caller-ID passthrough on forwarded calls is documented by NO carrier — the live test call in the onboarding checklist is the only proof. Never skip it.
- Conditional forwarding replaces the client's carrier voicemail for missed calls (open item 5 exists because of this).
- SignalWire's live site hides per-unit prices; number/SMS rates were verified from 2026 archive snapshots. Refresh before purchase regardless.
- SMS bills per segment plus carrier passthrough; a forwarded call bills both an inbound and an outbound leg.
- Google Voice is not the production carrier backend. AI never controls consent, STOP/HELP, booking truth, or handoff. Webhook retries duplicate side effects unless idempotent.
- On this host there is no Obsidian vault and no `/home/mdriles`; Codex memory here is sqlite (do not edit directly). The repo + GitHub push IS the cross-machine handoff; vault mirroring happens from piclaw.

## Improvements backlog
- **Calendar connection reliability:** the normal customer contract is connect once and done. text_back silently refreshes/rotates credentials. Only an exceptional provider-initiated revocation may surface one in-app Reconnect Calendar button; customers never handle tokens or repair skills. Needs: per-client token store, `reauth_required` state + outcome event, reconnect-link delivery. Not built yet.
- Env-loader with validation and a startup log of effective (non-secret) config.
- Outcome audit ledger is built for core lifecycle evidence; generic outbound, consent-change, and operational events remain.
- Quiet-hours enforcement has no clock-driven tests; add freeze-time tests.
- External delivery for the tested human-handoff alert payload is unimplemented.
- `docs/ONBOARDING-FORWARDING.md`: add a client-facing one-pager variant per carrier.
- GitHub Actions CI (none exists) running the suite on push.

## Session recommendations (2026-08-20)
### Hooks (5)
1. PostToolUse(Edit|Write on `src/**` or `tests/**` in text_back) → run `.venv/bin/pytest -q`; surface failures immediately. Every lane this session ended with a manual pytest. `recommended, priority: high, effort: S`
2. PreToolUse(Bash `git commit`) secret gate: block if staged files match `.env`, `*sa_key*.json`, `*token*.json`. A service-account key lands next session — one slip is unrecoverable. `recommended, priority: high, effort: S`
3. SessionStart on hermes-vcn-0: warn "no git identity configured; use -c flags" for any repo whose commits would fail. Bit us this session. `recommended, priority: medium, effort: S`
4. Pre-push hook: refuse push if `pytest` fails — keeps the GitHub mirror (the cross-machine sync) always green. `recommended, priority: medium, effort: S`
5. Port piclaw's past-tense-claim hook to hermes-vcn-0 handoff docs — this session had to avoid "has been deployed"-style claims by hand. `recommended, priority: medium, effort: M`

### Automation (5)
1. GitHub Actions pytest on every push/PR — **done** in `.github/workflows/ci.yml`.
2. Add text_back to the piclaw fleet-sync daily pull-before-push sweep so both checkouts converge. `recommended, priority: high, effort: S`
3. Weekly pricing-drift check: re-fetch SignalWire/Twilio rates, diff vs `PRD-text_back.md` cost snapshot, alert only on >10% drift (stale pricing has now needed manual refresh twice). `recommended, priority: medium, effort: M`
4. Once a SignalWire account exists: daily 10DLC registration-status poll during the 1–2 week approval window; notify only on state change (no-status-dumps compliant). `recommended, priority: medium, effort: M`
5. Nightly text_back health cron: pytest + dirty-tree check on both hosts, alert on failure only. `recommended, priority: low, effort: S`

### Workflows (5)
1. Approval ledger: a repo file recording human gates granted (e.g. "SignalWire ≤$15/mo approved 2026-08-20") so no agent re-asks or, worse, assumes. `recommended, priority: high, effort: S`
2. Client onboarding workflow: runbook steps + mandatory live-call verification + recorded sign-off. Runbook `built` this session; sign-off record `recommended`. `priority: high, effort: S`
3. Credential intake: keys go browser → `~/.config/text_back/` → verified via `/health`, never through chat or git; document as the standard for every fluxworks product. `recommended, priority: high, effort: S`
4. Google-auth fallback ladder (paste-code → console click-path → remote-bootstrap) as a reusable doc for all Google integrations; discovered the hard way this session. `recommended, priority: medium, effort: S`
5. Per-client deploy runbook generated from the PRD when fluxworks client #1 signs (mirror the engine-deploy pattern). `recommended, priority: medium, effort: M`

### Skills (5)
1. `deploy-client` (text_back): stamp out a per-client config — number, wiring mode, business identity, calendar, hours — the fluxworks reproducibility requirement made executable. `recommended, priority: high, effort: M`
2. Extend `google-oauth-repair` with the headless `tail -f | gcloud auth login` pattern + access-blocked triage from this session. `recommended, priority: medium, effort: S`
3. `signalwire-ops`: signup checklist, number purchase, 10DLC steps, spend-ceiling verification against the approval ledger. `recommended, priority: medium, effort: M`
4. `carrier-forwarding`: wrap `docs/ONBOARDING-FORWARDING.md` into guided activate/verify/deactivate steps per carrier. `recommended, priority: low, effort: S`
5. Make `next-session` host-aware: detect missing vault/`/home/mdriles` (as on hermes-vcn-0) and degrade gracefully instead of assuming piclaw paths. `recommended, priority: medium, effort: S`

## Resume prompt
```text
Continue-project contract: read /home/ubuntu/projects/text_back/NEXT-SESSION.md completely first (piclaw path: /home/mdriles/projects/text_back).

Cold start:
  cd ~/projects/text_back   # branch local/tdd-core, remote github.com:mdrilesbutler/text_back
  Read in order: AGENTS.md, PRD-text_back.md, NEXT-SESSION.md, SESSION-NOTES.md,
  docs/ONBOARDING-FORWARDING.md, docs/PRODUCT-MODEL.md,
  docs/SIGNALWIRE-INTEGRATION.md, docs/OUTCOME-EVENTS.md.
  Verify git status/log, then run .venv/bin/pytest tests/ before changing code.

Verified state (2026-08-29): 301 tests pass. Branch local/tdd-core has
fail-closed Google, Microsoft/Outlook, and iCloud calendar API adapters plus the
existing telecom, conversation, booking, handoff, follow-up, outcome, brief,
delivery, and CI seams. Microsoft availability uses Graph calendarView so
delegated personal Outlook.com accounts are supported. No customer-facing
one-time calendar connection screen/callback/store exists yet. No live
webhooks/messages/calls, external handoff destination, or deployment exists.

Start automatically with Michael's highest-priority correction: build the
one-time calendar connection domain and local UI/API contract TDD. Add a
persisted CalendarConnection with encrypted-credential references and
connected/degraded/reauth_required state, provider callback seams, a calendar
picker contract, and an automatic refresh interface. Tests must use fakes—do
not register provider apps or use live credentials yet. Then port the
persisted-attempt-before-send crash-safety pattern from delivery.py to
followup.py:201-204. Keep STOP/HELP, consent, and booking gates deterministic.
Run focused tests and the full suite, update docs, commit, and push.

Human gates remain: Michael's Platform Free Trial mobile verification; public
deployment domain and provider-app registrations for the one-time calendar
flow; external operator-notifier choice; deploy/webhook attachment; and the
mandatory non-customer live-call checklist. Do not wait for those gates before
building the local connection domain and fake callback tests.

Do not purchase/activate more telecom service, exceed the approved $15/month
SignalWire ceiling, send live/production SMS, route calls, attach webhooks, use
Google Voice, store credentials or the purchased number in Git, let an LLM
control policy, mix forwarded/managed trigger semantics, or claim a booking
without a successful Calendar event ID.

Done for next session = the one-time calendar connection domain and fake
onboarding flow are green in the full suite; live provider registration remains
gated on the public HTTPS domain. Never infer revenue from a booking alone.
```
