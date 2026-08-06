# text_back — next session prompt (written 2026-08-06, piclaw session)

## Continue-project contract
When Michael starts an agent from this project directory and says “continue project”, “continue”, “pick up”, or equivalent, read this `NEXT-SESSION.md` completely before taking action. Then read the files it names, briefly state the recovered state, and begin the highest-priority open item unless a newer user instruction overrides the handoff.

## Where everything stands (verified)
- Canonical folder: `/home/mdriles/projects/text_back`.
- Requirements and architecture are documented in `PRD.md`.
- No application code, carrier account activation, number purchase, OAuth grant, deployment, production message, or customer traffic exists from this session.
- Cost-first provider recommendation: SignalWire; Twilio is fallback.
- Pilot calendar account: `mdrilesbutler@gmail.com`.
- Application/operator target: Paperclip Hermes on Hostinger.
- Paid telecom and OAuth remain approval gates.

## Open items, in order
1. Recheck live SignalWire pricing/requirements and present the exact first-charge/spend ceiling. Owner: Hermes. Blocker: none.
2. Obtain Michael’s explicit approval for SignalWire purchase/activation and the spending ceiling. Owner: Michael. Blocker: paid external action.
3. Create/verify telecom account and buy one local voice/SMS number. Owner: Hermes + Michael browser approval. Blocker: approval/authentication.
4. Complete Google Calendar OAuth for `mdrilesbutler@gmail.com`. Owner: Hermes + Michael browser approval.
5. Write an implementation plan and build the application test-first, including webhook signature checks, idempotency, conversation state, deterministic policy, Calendar free/busy and booking, confirmation, STOP/HELP, and handoff.
6. Deploy through Paperclip Hermes on Hostinger and run a real-phone end-to-end smoke test only after approval.

## Session gotchas
- Google Voice is not the production carrier backend.
- Trigger text-back only from a terminal unanswered/no-answer call status, not call initiation.
- A forwarded call has inbound and outbound telecom legs.
- SMS is billed per segment and carrier fees/10DLC registration apply.
- AI must not control consent, STOP/HELP, booking truth, or handoff policy.
- Webhook retries can duplicate texts/events unless every side effect is idempotent.
- Pricing snapshots are temporary; refresh before purchase.

## Improvements backlog
- Add a provider adapter so SignalWire and Twilio can be swapped without changing domain logic.
- Add a simulator for call-status and SMS webhook sequences.
- Add a conversation replay/audit view with redaction.
- Add business-hours, service-area, travel-buffer, and appointment-duration configuration.
- Add spend alerts, dead-letter handling, and operator escalation summaries.

## Session recommendations (2026-08-06)

### Hooks (5)
1. Pre-deploy secret scanner — block deployment if keys/tokens appear in tracked files. priority: high; effort: S.
2. Pre-send consent gate — block outbound SMS when contact state is opted-out or outside allowed policy. priority: high; effort: M.
3. Webhook signature pre-handler — reject invalid carrier signatures before parsing actions. priority: high; effort: M.
4. Calendar event post-create verifier — require and persist provider event ID before confirmation. priority: high; effort: S.
5. Session-start handoff loader — read PRD/NEXT-SESSION before project changes. priority: medium; effort: S.

### Automation (5)
1. Daily telecom spend check with alert at 50/80/100% of ceiling. priority: high; effort: M.
2. Scheduled synthetic missed-call journey against a test number, silent on success. priority: high; effort: L.
3. Nightly database backup plus restore-verification artifact. priority: high; effort: M.
4. Daily stuck-conversation/dead-letter report to operator. priority: medium; effort: M.
5. Weekly opt-out/help/handoff compliance audit with counts and anomalies. priority: high; effort: M.

### Workflows (5)
1. Provider activation gate: refresh price → approval → account auth → number purchase → receipt verification. priority: high; effort: S.
2. Client onboarding: business identity → number/calendar ownership → hours/service area → registration → test → launch approval. priority: high; effort: M.
3. Release gate: tests → staging simulator → signature/idempotency checks → real-phone smoke test → production. priority: high; effort: M.
4. Human handoff: pause AI → summarize facts → notify operator → require explicit resume/close. priority: high; effort: M.
5. Incident response: stop outbound automation → preserve logs → notify owner → fix → replay safely. priority: high; effort: M.

### Skills (5)
1. `missed-call-telecom-ops` — provision, configure, and verify SignalWire/Twilio flows safely. priority: high; effort: M.
2. `sms-compliance-gate` — validate STOP/HELP, consent, quiet hours, and registration. priority: high; effort: M.
3. `calendar-booking-integrity` — free/busy, conflict recheck, idempotent event creation, confirmation. priority: high; effort: M.
4. `telecom-webhook-simulator` — replay signed call/SMS event sequences and failure modes. priority: medium; effort: L.
5. `field-service-client-onboarding` — produce and verify per-client configuration without credential leakage. priority: medium; effort: M.

## Resume prompt
```text
Continue-project contract: read /home/mdriles/projects/text_back/NEXT-SESSION.md completely first, then read PRD.md, SESSION-NOTES.md, AGENTS.md, and README.md.

Cold start:
cd /home/mdriles/projects/text_back
Confirm branch, origin, clean/dirty state, and matching local/remote hashes. Do not expose credentials.

Verified state from 2026-08-06: this is an approved missed-call text-back and Google Calendar scheduling project. SignalWire is the cost-first provider recommendation; Twilio is fallback. Paperclip Hermes on Hostinger is the target operator/runtime. No paid telecom activation, number, OAuth grant, application implementation, deployment, or customer traffic was completed.

Exact next work:
1. Refresh official provider pricing and low-volume 10DLC requirements.
2. If Michael has not explicitly approved paid service and a ceiling, request only that approval; do not purchase.
3. After approval, complete provider authentication and Google OAuth with Michael’s browser actions only where required.
4. Before coding, write a test-first implementation plan covering signature validation, idempotency, terminal no-answer detection, state, STOP/HELP, handoff, Calendar conflict recheck, and spend guards.
5. Build and verify locally, deploy through the approved Paperclip/Hostinger route, then run a real-phone end-to-end test only with explicit production approval.

Improvements: use a carrier adapter, event simulator, auditable/redacted conversation state, dead-letter handling, spend alerts, and configurable business rules.

Do not: use Google Voice as backend; send on call initiation; let AI override compliance or booking truth; store secrets in Git/Obsidian; claim booking without Calendar event ID; activate paid service without approval.

Definition of done for the next session: the highest approved gate is completed with evidence, tests/receipts/IDs are recorded without secrets, PRD and NEXT-SESSION are current, Obsidian is mirrored, and local/remote Git hashes match.
```
