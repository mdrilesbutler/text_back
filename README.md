# text_back

Missed-call recovery and scheduling assistant for field-service businesses.

Canonical requirements: `PRD.md`
Cold resume: `NEXT-SESSION.md`
Session history: `SESSION-NOTES.md`
Local implementation plan: `IMPLEMENTATION-PLAN.md`

## Current state (2026-08-14, hermes-cloud)

Local core exists and is tested on this host. No production number, no paid telecom, no Google OAuth.

```bash
cd /home/ubuntu/projects/text_back
.venv/bin/pytest tests/
.venv/bin/python -m text_back   # 127.0.0.1:8000 only
```

Covered locally: webhook signature fail-closed, missed-call intro on terminal no-answer only, idempotent retries, STOP/HELP policy, Calendar stub booking with event-id gate.

Human gates remaining: paid telecom approval + number; Google Calendar OAuth for `mdrilesbutler@gmail.com`.
