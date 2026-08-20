# text_back — next session prompt (updated 2026-08-14, hermes-cloud)

## Continue-project contract
When Michael starts an agent from this project directory and says “continue project”, “continue”, “pick up”, or equivalent, read this `NEXT-SESSION.md` completely before taking action. Then read the files it names, briefly state the recovered state, and begin the highest-priority open item unless a newer user instruction overrides the handoff.

## Where everything stands (verified 2026-08-20)
- Canonical folder on this host: `/home/ubuntu/projects/text_back` (piclaw path remains `/home/mdriles/projects/text_back`).
- Local TDD core exists: webhooks, signature fail-closed, idempotency, STOP/HELP, Calendar stub, `wiring_mode` (forwarded/managed).
- Evidence: `.venv/bin/pytest tests/` → 50 passed on 2026-08-20 (see below).
- No carrier account activation, number purchase, OAuth grant, deployment, production message, or customer traffic.
- Cost-first provider recommendation: SignalWire; Twilio is fallback.
- Pilot calendar account: `mdrilesbutler@gmail.com`.
- Application/operator target: Paperclip Hermes on Hostinger (not done).

## Open items, in order
1. Michael: explicit approval for SignalWire purchase/activation and a spend ceiling (recommended $15/month). Owner: Michael. Blocker: paid external action.
2. After approval: refresh live SignalWire pricing/10DLC requirements, then create/verify telecom account and buy one local voice/SMS number. Owner: Hermes + Michael browser. Do not purchase from hermes-cloud without approval.
3. Complete Google Calendar OAuth for `mdrilesbutler@gmail.com`. Owner: Hermes + Michael browser.
4. Replace Calendar stub with live free/busy + event create; keep confirmation gated on provider event ID.
5. ~~Add conversation field collection (service, location, preferred time, name) still under deterministic policy.~~ Done 2026-08-20: sequential slot-filling in `handlers.py`/`policy.py`/`store.py`, no LLM/NLP extraction. See SESSION-NOTES.md.
6. ~~Add `wiring_mode` (forwarded/managed) so text_back can attach to a client's existing number via conditional call forwarding.~~ Done 2026-08-20: `app.py`/`handlers.py`/`policy.py`, default is `forwarded`. See SESSION-NOTES.md and `tests/test_wiring_mode.py`.
7. Deploy through Paperclip Hermes on Hostinger and run a real-phone end-to-end smoke test only after approval.

## Session gotchas
- Google Voice is not the production carrier backend.
- The "terminal unanswered/no-answer call status only" trigger rule applies
  to `wiring_mode="managed"` only (our number is the client's own number).
  In `wiring_mode="forwarded"` (the default, added 2026-08-20), the carrier
  only ever forwards to us after no-answer/busy on the client's real line,
  so ANY first voice webhook for a call_sid is already a missed call —
  trigger on arrival regardless of CallStatus. Idempotency still comes from
  `claim_event` keyed on `call_sid`, guaranteeing exactly one SMS across
  ringing/completed webhook retries for the same call. See README.md
  "Wiring mode" section and `tests/test_wiring_mode.py`.
- A forwarded call has inbound and outbound telecom legs.
- SMS is billed per segment and carrier fees/10DLC registration apply.
- AI must not control consent, STOP/HELP, booking truth, or handoff policy.
- Webhook retries can duplicate texts/events unless every side effect is idempotent.
- Pricing snapshots are temporary; refresh before purchase.

## Resume prompt
```text
Continue-project contract: read NEXT-SESSION.md completely first, then PRD.md, SESSION-NOTES.md, AGENTS.md, README.md.

Local core is implemented and tested. Remaining work is human gates (paid telecom + Google OAuth) then live adapters.

Do not: buy a number; send production SMS; use Google Voice; store secrets in Git; claim booking without a Calendar event ID.
```
