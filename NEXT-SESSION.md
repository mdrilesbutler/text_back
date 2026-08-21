# text_back — next session prompt (updated 2026-08-21, hermes-vcn-0)

## Continue-project contract
When Michael starts an agent from this project directory and says "continue project", "continue", "pick up", or equivalent, read this `NEXT-SESSION.md` completely before taking action. Then read the files it names, briefly state the recovered state, and begin the highest-priority open item unless a newer user instruction overrides the handoff.

## Where everything stands (verified 2026-08-20, fresh)
- Canonical checkout: `/home/ubuntu/projects/text_back` on hermes-vcn-0 (piclaw mirror path: `/home/mdriles/projects/text_back`).
- Remote: `git@github.com:mdrilesbutler/text_back.git`, branch `local/tdd-core`; completed items are pushed to origin (verify with `git log --oneline -5`).
- Test suite: `.venv/bin/pytest tests/` → **111 passed**, rerun this session after every change.
- Implemented: FastAPI app (`/health`, `/webhooks/voice`, `/webhooks/sms`); fail-closed Twilio-compatible signatures; idempotency via `claim_event`; deterministic STOP/HELP; Calendar stub gating confirmation on event ID; conversation slot-filling (service → location → preferred_time → name); `wiring_mode` = `forwarded` (default, conditional-forwarding attach to a client's existing number) / `managed` (ported number, terminal-unanswered rule).
- Docs: `PRD-text_back.md` (labeled root PRD — bare `PRD.md` no longer exists), `docs/ONBOARDING-FORWARDING.md` (per-carrier conditional-forwarding runbook + mandatory live verification checklist).
- gcloud CLI 581.0.0 installed at `~/google-cloud-sdk` on hermes-vcn-0. **NOT authenticated** — sign-in hit "access blocked" (see gotchas).
- Approvals given by Michael 2026-08-20: SignalWire purchase path with a **$15/month ceiling**; product must attach to customers' actual existing phone numbers (drove `wiring_mode`); everything must be reproducible for the **fluxworks catalog**.
- SignalWire estimate (researched 2026-08-20): ≈ $9.44/month all-in at pilot volume; setup ≈ $12 one-time + $5 minimum funding; 10DLC approval ~1–2 weeks; cheap $1.50/month tier needs an EIN. Details in `PRD-text_back.md` § Cost refresh.
- Environment loader is implemented: `create_app()` reads all documented `TEXT_BACK_*` settings, explicit arguments override environment values, and `/health` reports non-secret effective config.
- SignalWire pilot progress (2026-08-21): Space funded and one local voice/SMS-capable number purchased at $0.50/month. The exact number is config-only in `~/.config/text_back/pilot.env` (mode 600), not Git. A direct Compatibility REST outbound-SMS adapter is implemented and tested, but no API token/signing key is stored, no webhook is attached, and no live message has been sent.
- NOT done: Platform Free Trial mobile verification, SignalWire credentials, Google auth/credentials, deploy, webhook routing, or production traffic.

## Open items, in order
0. **Product model (docs done 2026-08-20):** canonical `docs/PRODUCT-MODEL.md`. Build only the Recover P0 queue next: voicemail response → preferred-time booking → human handoff → append-only outcome events → bounded no-response sequence → Recovered Revenue Brief generator. Voice Answer and Grow journeys wait until the real-phone Recover pilot proves conversion.
0a. **GTM (docs done 2026-08-20):** Koerner model live at `docs/gtm/KOERNER-MODEL.md`. Optional next: PDF leave-behind, Stripe links for TB-ASSESS/RECOVER/CARE (Michael money gate).
1. **Michael (browser)**: enable SignalWire Platform Free Trial under Messaging Campaigns by verifying his personal mobile. This permits REST API test messages only between the purchased pilot number and that one verified mobile (200/day, trial prefix); it does not enable cXML/SWML messaging. Michael is operating as a sole proprietor while an LLC is pending. Do not submit a paid Brand/Campaign yet unless he explicitly chooses that path after seeing the displayed fees.
2. **Michael + agent**: finish Google auth for `mdrilesbutler@gmail.com`. Last attempt: `~/google-cloud-sdk/bin/gcloud auth login --no-launch-browser` run in background with stdin held open; Michael's browser showed "access blocked" (exact wording never reported). Restart the flow fresh (the old background process/scratchpad is disposable). Fallback ladder: (a) plain desktop browser, not an in-app webview; (b) incognito signed in only as mdrilesbutler; (c) Plan B — Michael creates project/SA in console by hand, downloads key; (d) Plan C — `gcloud auth login --no-browser` remote-bootstrap if he has gcloud locally.
3. **Agent (after auth)**: scripted GCP setup — `gcloud projects create <unique-id>`, enable `calendar-json.googleapis.com`, create service account, key to `~/.config/text_back/sa_key.json` (chmod 600, NEVER git); then Michael shares the pilot calendar with the SA email ("Make changes to events").
4. **Agent (done locally 2026-08-21)**: SignalWire callbacks now require `X-SignalWire-Signature`, return cXML, and forwarded calls receive branded `<Say>` + `<Hangup>` with no retained recording. Live attachment/testing remains gated.
5. **Agent (done locally 2026-08-21)**: explicit `preferred_time` input is parsed in the configured timezone; vague/past/DST-unsafe input is re-prompted; the four fields feed free/busy-rechecked Calendar-stub booking; confirmation remains gated on event ID. Live Google Calendar is still pending.
5a. **Agent (done locally 2026-08-21)**: deterministic customer-requested/safety handoff persists active state, pauses SMS and missed-call automation, preserves STOP/HELP, supports explicit resolution, and emits an idempotent concise operator payload to an in-memory notifier. External operator delivery remains unimplemented.
5b. **Agent (done locally 2026-08-21)**: append-only outcome events now capture missed/contacted/engaged/field/qualified/handoff/slot/event/confirmed facts with stable evidence IDs and retry-safe idempotency keys. See `docs/OUTCOME-EVENTS.md`.
5c. **Agent (next unblocked P0 code, TDD)**: implement the bounded no-response sequence with configurable attempts/timing, quiet-hours gating, and immediate cancellation on response/opt-out/booking/handoff/expiry.
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
1. GitHub Actions: pytest on every push to any branch (repo has zero CI; suite is 50 tests and fast). `recommended, priority: high, effort: S`
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

Verified state (2026-08-21): 111 tests pass. Branch local/tdd-core is synced to
origin. The environment loader, forwarded/managed wiring modes, fail-closed
SignalWire signature boundary and cXML, deterministic time parsing and Calendar
stub booking gate, human-handoff state/payload, and append-only outcome ledger
are implemented. One voice/SMS-capable SignalWire pilot number was purchased by
Michael and is config-only in ~/.config/text_back/pilot.env. There are no
SignalWire credentials, live webhooks/messages/calls, Google credentials, real
Calendar adapter, external handoff delivery, or deployment.

Start automatically with the next unblocked Recover P0 item: build a bounded
no-response follow-up sequence using TDD. It must have configurable maximum
attempts and delays, enforce configured timezone/business quiet hours, schedule
only after an accepted initial SMS with provider evidence, and cancel immediately
on any customer response, STOP, successful booking, active handoff, expiry, or
the attempt ceiling. Retries must be idempotent. Record evidence-backed
followup.sent and lead.expired outcome facts without storing raw message bodies.
Use an injected clock/scheduler seam and stub transport only; do not add a live
cron, queue, or provider send. Run focused tests and the full suite, update the
PRD/handoff/docs, commit with the repo's existing author flags, and push
local/tdd-core.

Human gates remain: Michael's Platform Free Trial mobile verification; Google
authentication and Calendar sharing; SignalWire least-privilege credentials;
external operator-notifier choice; deploy/webhook attachment; and the mandatory
non-customer live-call checklist. Record progress if Michael completes one, but
do not wait for a gate before doing the local follow-up-sequence work.

Do not purchase/activate more telecom service, exceed the approved $15/month
SignalWire ceiling, send live/production SMS, route calls, attach webhooks, use
Google Voice, store credentials or the purchased number in Git, let an LLM
control policy, mix forwarded/managed trigger semantics, or claim a booking
without a successful Calendar event ID.

Done for next session = bounded no-response sequence shipped test-first with the
full suite green and pushed, with factual notes updated. If that item finishes
early, begin the deterministic Recovered Revenue Brief generator from the
append-only outcome ledger; never infer revenue from a booking alone.
```
