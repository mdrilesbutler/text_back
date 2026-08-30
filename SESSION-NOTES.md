# text_back — Session Notes

## 2026-08-29 night — multi-provider calendar layer + Google OAuth DONE (piclaw, Claude)

Michael decided: Google Calendar primary ("everyone has a gmail account"),
with iCloud/Outlook/M365 wired in as options — helps client onboarding. Built
the same night (workflow: design → 3 TDD lanes → verify → adversarial review
→ fix): `src/text_back/calendars/` package — CalendarProvider protocol,
Google adapter (Calendar v3 freebusy + insert, deterministic event ids),
Microsoft Graph adapter (getSchedule + events, covers Outlook.com and M365),
iCloud CalDAV adapter (VFREEBUSY REPORT + PUT .ics, endpoint pinned to
*.icloud.com), all behind an injected transport (no live network in tests, no
new deps, redirect-refusing urllib opener). Review caught and fixed a
critical: idempotency ids were slot-independent, so a returning customer's
second booking could "confirm" against their months-old event — ids now hash
(conversation, slot) and every duplicate response is verified against the
requested slot before an id is returned. Also fixed: production wiring
(SignalWire) now refuses to boot with the stub calendar; iCloud free/busy
fails toward busy on non-multistatus 207s; a crash between event creation and
appointment save is now recoverable. Suite 186 → 302 passed. Separately:
**Google OAuth completed** via the google-oauth-repair skill pattern — a
dedicated calendar-only token (butler account, existing Hermes OAuth client,
browser consent, no password) live-verified and installed at hermes-cloud
`~/.config/text_back/google_token.json`; the stuck-since-08-20 gcloud path is
dead, never to be used again.

## 2026-08-29 evening — signing key stored, no-live-human principle, Cal.com question (piclaw, Claude)

Michael's corrections drove three changes. (1) **Product principle: customers
never get a live human** — escalation copy no longer promises a person or
points at the unanswered business line; handoff acks promise an owner
follow-up (911 kept), booking errors keep the customer in-thread; guard test
`tests/test_no_live_human_copy.py`; PRD updated; suite 186 passed. (2) **The
SignalWire Project signing key was retrieved from the FluxWorks dashboard via
browser** (at Michael's explicit order) and stored on hermes-cloud in
`runtime.env` as `TEXT_BACK_WEBHOOK_SECRET`; service restarted, /health green;
rotate at deploy (value transited a session transcript). (3) **Cal.com vs
Google Calendar is now an open decision** — Michael asked "aren't we using
cal.com?"; recommendation is Cal.com (kills the OAuth blocker); gcloud OAuth
flow stays parked on hermes-cloud until he decides. Also recorded: where all
code/credentials/gates live, in NEXT-SESSION and the Obsidian project note.

## 2026-08-29 — handoff-alert delivery seam, quiet-hours tests, CI (piclaw, Claude)

Built the external handoff-alert delivery seam (`src/text_back/delivery.py` +
`handoff_deliveries` table): durable outbox enqueued on handoff activation,
uuid alert IDs stable across restarts, enqueue failure raises instead of
silently dropping an operator alert, transport interface with only safe
channels (`disabled` default, PII-masked `log`), fail-closed
`TEXT_BACK_HANDOFF_DELIVERY_*` config, injected-clock `run_due_deliveries`
that persists each attempt BEFORE the transport call (crash-safe
at-least-once), bounded backoff, ledger-first dead-letter evidence. No live
channel exists — destination choice is Michael's gate. Also: clock-driven
quiet-hours tests (boundaries, DST, expiry interplay) and GitHub Actions CI
(least-privilege, py3.12/3.13). Two major defects (crash-wedged outbox rows;
restart alert-ID collision losing a safety handoff) were caught by the
adversarial review pass with executed repros and fixed with regression
tests. Suite: 182 passed (was 148). Found but not fixed: `followup.py`
carries the same pre-existing claim-before-persist wedge shape — next
session's first item. Work done in a worktree lane; Grok's UI lane
(`deploy/`, `docs/demo/`) untouched.

## 2026-08-27 — operator job/revenue write path

Added `src/text_back/operator.py` so completed jobs and attributed revenue can
enter the outcome ledger only from operator/CRM evidence. Revenue refuses
string/boolean/negative amounts and refuses attribution unless a matching
`job.completed` event exists for the lead. Bookings stay pipeline. Suite: 148
passed. Live SignalWire/Google/deploy gates are unchanged.

## 2026-08-21 — durable handoff and next-session focus

Refreshed the canonical resume prompt after the SignalWire boundary, booking,
handoff, and outcome-ledger work. The next unblocked Recover P0 build is a
test-driven bounded no-response follow-up sequence: configurable attempts and
timing, quiet-hours deferral, deterministic cancellation, retry idempotency, and
evidence-backed `followup.sent` / `lead.expired` facts. It must use injected
clock/scheduler and stub-transport seams only; no live cron, provider send, call
routing, webhook attachment, or deployment is authorized by this handoff.

Human gates remain Platform Free Trial mobile verification, Google auth and
real Calendar sharing, SignalWire least-privilege credentials, an external
handoff-notifier choice, deployment, and the mandatory non-customer live-call
verification checklist. The full local suite was green at 111 tests before this
documentation-only handoff.

## 2026-08-21 — SignalWire pilot number and outbound REST adapter

Michael purchased one local voice/SMS-capable SignalWire pilot number for
$0.50/month under the existing $15/month approval. The exact number is stored
only in `~/.config/text_back/pilot.env` with mode 600; no business-specific
number, token, or signing key was added to Git.

Implemented a direct SignalWire Compatibility REST outbound-SMS adapter for
the Platform Free Trial path. It enforces HTTPS, scopes the configured sender,
uses environment-injected credentials, requires a provider message ID, and
redacts provider response bodies and credentials from errors. The app selects
`stub` or `signalwire` through `TEXT_BACK_TELECOM_MODE` and fails closed when
SignalWire configuration is incomplete. `/health` reports only the provider
name.

The local inbound boundary now requires `X-SignalWire-Signature` against the
exact configured public URL and returns valid cXML. Forwarded calls receive a
business-configured `<Say>` followed by `<Hangup>`; no recording is retained.
SMS and voice copy now receive identity from `TEXT_BACK_BUSINESS_NAME` rather
than embedding a client identity in policy code. The protected runtime and
pre-live contract is documented in `docs/SIGNALWIRE-INTEGRATION.md`.

Explicit preferred times now parse deterministically in the configured IANA
timezone. The parser accepts documented date/time forms and `tomorrow at TIME`,
while rejecting vague, past, nonexistent, and DST-ambiguous values. The SMS
flow sends all four collected fields through the existing double free/busy
check, creates one Calendar-stub event, persists its ID, and only then sends a
business-configured confirmation. Timezone and appointment duration are env
configuration. The stub remains test-only; no Google Calendar adapter or
credential is configured.

Deterministic handoff now recognizes explicit human requests and bounded safety
terms, stores active/resolved state, pauses subsequent SMS collection and
missed-call intros, and preserves STOP/HELP precedence. It produces one concise
operator payload containing the reason, caller, latest message, and fields
collected so far. `TEXT_BACK_HANDOFF_DESTINATION` is config-only and `/health`
reveals only whether it is configured. The notifier is in-memory; no external
operator alert was sent.

An append-only `outcome_events` ledger now records missed calls, accepted
initial SMS, customer replies, field captures, qualification, handoff alerts,
slot checks, calendar event creation, and appointment confirmation. Every fact
has a unique idempotency key and non-empty call/message/alert/slot/calendar
evidence ID. Raw message bodies are not copied into event metadata. A failed
confirmation transport produces no `appointment.confirmed` event. The contract
is documented in `docs/OUTCOME-EVENTS.md`.

Full suite: `.venv/bin/pytest tests/` — 111 passed.

No live SMS was sent, no provider callback was received, and no webhook was
attached. Next human action: verify
Michael's personal mobile in SignalWire Messaging Campaigns to enable Platform
Free Trial. PFT is REST-only between the assigned SignalWire number and that
verified mobile; cXML/SWML messaging remains unavailable until registration.

## 2026-08-20 — product model synthesized from Podium, Hatch, Goodcall, Koerner, and Tra brief

Created the canonical `docs/PRODUCT-MODEL.md` and `docs/COMPETITOR-MATRIX.md` from primary public product pages (fetched 2026-08-20), with citation evidence verified. Product decision:

- **Recover first:** missed call → immediate SMS → deterministic qualification → Calendar booking or human handoff → outcome brief.
- **Answer later:** optional after-hours/overflow AI voice + directory routing.
- **Grow later:** estimate/no-show/review journeys, separately consent-scoped.
- Borrow Podium conversation continuity, Hatch speed-to-conversion + bounded persistence, Goodcall structured logic/routing, and Koerner assessment → install → care.
- Borrow only the reporting structure from the supplied Tra macro brief: snapshot, drivers, what to watch, bottom line, evidence appendix.
- Added `docs/gtm/RECOVERED-REVENUE-BRIEF-TEMPLATE.md`; revenue is never claimed from a booking alone.

No product code changed in this decision pass. The full suite remains the verification gate.

## 2026-08-20 — Koerner GTM model adopted for text_back commercial packaging

Michael pointed at https://www.youtube.com/watch?v=g4-3AxelI_Y
(*This Might Be the Easiest Way to Sell AI to Businesses*, Chris Koerner).
Full YouTube captions remain blocked from this cloud IP.

Adopted commercial model from matching public Koerner materials
(assessment ladder + speed-to-lead as highest-ROI SMB install):

- Canonical: `docs/gtm/KOERNER-MODEL.md`
- Templates: `docs/gtm/assessment-template.md`, `docs/gtm/leave-behind.md`
- PRD section + README pointer updated
- SKUs: `TB-ASSESS` ($500–$1k) → `TB-RECOVER` ($1.5–3k) → `TB-CARE` ($200–500/mo)
- Positioning: sell missed-call recovery / calendar booking, not “AI agents”

No product code changes required — GTM maps onto existing forwarded wiring + deterministic policy.

## 2026-08-20 — environment-backed app configuration

Added an environment loader for every documented `TEXT_BACK_*` setting.
`create_app()` now reads webhook secret, public base URL, SQLite path, and
`wiring_mode` from the process environment while preserving explicit keyword
arguments as the higher-precedence test/adapter seam. The SQLite path is wired
into `Store`, and `/health` reports only non-secret effective configuration.

### Evidence
- Focused configuration tests: 2 passed.
- Full suite: `.venv/bin/pytest tests/` — 52 passed.
- No credentials or production values added to the repository.

## 2026-08-20 — wiring_mode: attach to a client's existing number via forwarding

Added `wiring_mode` support so text_back can wire onto a client's existing
public phone number via conditional call forwarding, instead of requiring
the client to hand out our number directly. Test-first (RED confirmed
before implementation).

### Implemented
- `policy.py`: `WIRING_MODE_FORWARDED` ("forwarded"), `WIRING_MODE_MANAGED`
  ("managed"), `WIRING_MODES`.
- `app.py`: `create_app(..., wiring_mode: str = WIRING_MODE_FORWARDED)` —
  same config-flow pattern as `webhook_secret`/`public_base_url`; invalid
  values raise `ValueError`; `app.state.wiring_mode` is threaded into
  `handle_voice_event`; `/health` now reports `wiring_mode`.
- `handlers.py`: `handle_voice_event` takes `wiring_mode` as a required
  keyword argument. In `managed` mode, behavior is unchanged from before —
  only a terminal-unanswered `CallStatus` triggers the intro SMS. In
  `forwarded` mode, the terminal-status check is skipped entirely: the
  first voice webhook for a given `call_sid` triggers exactly one intro SMS
  regardless of `CallStatus`, because the carrier only ever forwards to us
  after no-answer/busy on the client's real line — an inbound call to our
  number already IS a missed call. Exactly-once delivery across
  ringing/completed webhook retries for the same call still comes from the
  existing `store.claim_event("voice", call_sid, "missed_call_intro")`
  idempotency gate (unchanged). Opt-out suppression and the
  from/to direction (text the original caller, from our number) are
  unchanged and apply in both modes.
- `.env.example`: documented `TEXT_BACK_WIRING_MODE` (forwarded/managed).
- `README.md`: new "Wiring mode" section.
- `NEXT-SESSION.md`: gotcha that "terminal status only" is a `managed`-mode
  rule; `forwarded` mode triggers on arrival.
- No LLM — deterministic mode dispatch only, per project non-goals.

### Evidence
- `.venv/bin/pytest tests/` — 50 passed (38 prior + 12 new, in
  `tests/test_wiring_mode.py`) on 2026-08-20. Existing
  `tests/test_webhooks.py` now pins `wiring_mode="managed"` explicitly
  since it documents the (unchanged) legacy/managed behavior; the app-level
  default flipped to `forwarded`.

### Not done
- No env-var loader reads `TEXT_BACK_WIRING_MODE` yet — same as the other
  `.env.example` values, which are documented but not yet parsed from the
  environment anywhere in this repo (see `__main__.py`); wiring env parsing
  is a pre-existing gap, not introduced here.

## 2026-08-20 — conversation field collection (deterministic)

Added slot-filling collection of service, location, preferred time, and name
to inbound SMS "conversation" replies. Test-first (RED confirmed before
implementation).

### Implemented
- `policy.py`: `CONVERSATION_FIELDS` (fixed order: service, location,
  preferred_time, name), `FIELD_PROMPTS`, `next_missing_field()`,
  `conversation_prompt()`, `conversation_summary_sms()`.
- `store.py`: `conversation_fields` table keyed `(phone, field)`; added
  `get_conversation_fields`, `set_conversation_field`, `clear_conversation_fields`.
- `handlers.py`: `_collect_conversation_field()` — each non-STOP/HELP,
  non-opted-out inbound SMS is treated as the verbatim answer to the next
  missing field, in fixed order. STOP/HELP/opt-out still short-circuit ahead
  of field collection (unchanged). Blank replies re-prompt the same field
  without storing an empty value. Once all four fields are collected, further
  replies neither overwrite fields nor re-prompt.
- No LLM or NLP extraction — deterministic sequencing only, per project
  non-goals.

### Evidence
- `.venv/bin/pytest tests/` — 38 passed (19 prior + 19 new) on 2026-08-20.

### Not done
- No wiring from collected fields into `booking.py` (still requires a
  parsed `datetime`, which `preferred_time` is deliberately kept as raw
  text, not parsed). No conversation reset after a booking is made.

## 2026-08-14 — hermes-cloud local TDD core

Built and verified locally on `hermes-vcn-0`. No paid telecom, number, OAuth, or production SMS.

### Implemented
- FastAPI app with `GET /health`, `POST /webhooks/voice`, `POST /webhooks/sms`
- Twilio-compatible signature verification; missing/invalid signatures return 403
- Terminal unanswered (`no-answer`/`busy`/`failed`/`canceled`) sends exactly one intro SMS
- Ringing/initiated does not text
- Idempotency via SQLite `(source, event_id, action)`
- Deterministic STOP/HELP policy; STOP suppresses later missed-call intros
- Calendar stub: free/busy, recheck, persist event ID, confirmation only after event ID
- Opt-out blocks booking confirmation

### Evidence
- `.venv/bin/pytest tests/` — 19 passed on 2026-08-14

### External actions not taken
No number purchased, paid service activated, credentials stored, OAuth grant created, production traffic sent, or Hostinger deploy.

## 2026-08-06 — Project creation

Michael approved `text_back` as a legitimate project under `/home/mdriles/projects`.

### Decisions
- Build a missed-call text-back and Google Calendar scheduling product for arborists, guides, and similar field services.
- Host and operate the application through Paperclip Hermes on Hostinger.
- Use a programmable carrier number; do not use Google Voice.
- Use `mdrilesbutler@gmail.com` for the pilot Google Calendar integration.
- Prefer SignalWire on cost; keep Twilio as fallback.
- Recommended initial telecom cap: $15/month with no purchase until Michael explicitly approves.

### Pricing snapshot
SignalWire’s public pricing produced an estimated base of $8.04/month for 100 calls at three forwarded minutes each plus 400 SMS segments, before carrier fees and AI use. Listed setup fees for a low-volume 10DLC campaign total approximately $12. Pricing must be refreshed before purchase.

### Compliance baseline
Transactional scheduling only. Enforce STOP/HELP, quiet hours, consent, carrier registration, deterministic booking rules, signature validation, idempotency, and human handoff.

### External actions not taken
No number purchased, paid service activated, credentials stored, OAuth grant created, production traffic sent, or deployment performed.
