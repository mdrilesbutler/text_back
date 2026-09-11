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
- Runtime: hermes-vcn-0 (`ssh hermes-cloud`) — localhost-only `text-back.service` at 127.0.0.1:8000, stub telecom mode, `/health` green. No public URL.
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

## LOCKED (settled — do not re-open)
- Carrier: SignalWire (Twilio fallback). Spend ceiling $15/month (approved 2026-08-20).
- Booking backend: Google Calendar primary (decided 2026-08-29, "everyone has a gmail"); Microsoft Graph and iCloud CalDAV adapters shipped as options. Selected via `TEXT_BACK_CALENDAR_PROVIDER`; production telecom refuses to boot with the stub calendar.
- Customers never get a live human. Escalation = graceful exit + async operator lead. Guard: `tests/test_no_live_human_copy.py`.
- Deterministic policy, never an LLM, owns STOP/HELP, consent, quiet hours, booking truth, and handoff.
- `wiring_mode`: `forwarded` (default; first voice event per call_sid triggers) vs `managed` (terminal unanswered only). Never mix the rules.
- Webhooks verify `X-SignalWire-Signature` and fail closed; every side effect is idempotent via `claim_event`.
- No booking is claimed without a Calendar event ID. Revenue comes only from explicit `revenue.attributed` events with evidence — never inferred from a booking.
- Product order: Recover first. Answer (voice) and Grow (journeys) wait until the real-phone Recover pilot proves conversion.
- GTM: Koerner ladder TB-ASSESS → TB-RECOVER → TB-CARE; sell missed-call recovery, not "AI".
- Google OAuth for text_back is minted with the google-oauth-repair skill pattern (existing Hermes client, butler account) — re-mint in ~5 min if revoked.
- Customer calendar reauth: silent refresh; on true revocation mark the client `reauth_required` and send a reconnect link. Customers never go through the operator OAuth-repair path.
- Credential intake: browser → `~/.config/text_back/` → verified via `/health`. Never chat, git, or Obsidian.
- The live-call verification checklist in `docs/ONBOARDING-FORWARDING.md` is mandatory at every client onboarding.

## KILLED (dead — never resurface as live; deleted from runtime, not archived)
- `cal.com` as booking backend (Google decision 2026-08-29).
- `gcloud` auth / GCP service-account path for Calendar (wrong path; token comes from the skill pattern).
- `google-voice` as telecom backend.
- `live-human` transfer or "call the business line" escalation copy.

## ROADMAP (order is locked; build only the current phase)
- v1 Recover (built locally, TDD): missed call → SMS → qualification → booking or handoff → follow-up sequence → Recovered Revenue Brief.
- v1 live pilot (current): public HTTPS host, attach SignalWire handlers, real-phone smoke test per `docs/ONBOARDING-FORWARDING.md`, first client via per-client config.
- v2 Answer: after-hours/overflow AI voice + directory routing.
- v3 Grow: estimate, no-show, review journeys, separately consent-scoped.
- Optional (money gate): PDF leave-behind, Stripe links for the three SKUs; a `deploy-client` skill for fluxworks.

## STATE (as of 2026-09-11; ≤ 10 lines; rewritten every handoff)
- Last code commit 2026-08-29. 302 tests green on hermes-cloud (verified 2026-09-11).
- Built locally: FastAPI app, signature boundary, idempotency, STOP/HELP, slot filling, time parsing, booking gate, handoff state, outcome ledger, follow-up sequence, Revenue Brief, operator revenue write path, handoff-alert delivery outbox, calendar layer (stub/google/microsoft/icloud).
- No live webhook, message, call, deployment, or customer traffic has ever happened.
- Open defect (2026-08-29 review): `followup.py` claims the event then sends — crash between the two wedges the attempt. Same shape `delivery.py` already fixed.
- Gate (Michael): deployment shape — tunnel smoke test vs durable Caddy+domain on the VPS (deferred 2026-08-28).
- Gate (Michael): live handoff-alert channel (SMS / Telegram / email). Outbox built; channel `disabled`.
- Gate (Michael, browser): SignalWire Platform Free Trial mobile verification. Sole proprietor, LLC pending; no paid Brand/Campaign without reviewing fees.
- Not built: customer `reauth_required` flow (per-client token store, state + outcome event, reconnect-link delivery).
- Conflict: vault project note (2026-08-29) still says "if Cal.com approved" — stale; the later Google decision wins.
- Grok's lane has uncommitted UI work in `deploy/` and `docs/demo/` (2026-09-11); not Claude's to touch.

## NEXT (exactly one item)
Port the persist-attempt-before-send crash-safety pattern from `src/text_back/delivery.py` into `src/text_back/followup.py` (the `claim_event` → `send_sms` block near line 199), TDD with crash-shaped tests; full suite green; commit and push `local/tdd-core`.

## SPEC
- `docs/PRD-text_back.md` — requirements and architecture; no status log lives there.
- `docs/PRODUCT-MODEL.md`, `docs/COMPETITOR-MATRIX.md`, `docs/gtm/KOERNER-MODEL.md` — product and GTM.
- `docs/SIGNALWIRE-INTEGRATION.md`, `docs/ONBOARDING-FORWARDING.md`, `docs/CALENDAR-PROVIDERS.md`, `docs/OUTCOME-EVENTS.md` — contracts.
- `README.md` — how to run and test.
- Gotchas: `TEXT_BACK_SIGNALWIRE_SPACE_URL` already includes `https://`; SignalWire has no `/Balance.json`; the `!` runner is non-interactive; caller-ID passthrough on forwarded calls is proven only by the live test call.
