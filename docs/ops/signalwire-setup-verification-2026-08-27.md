# text_back SignalWire setup verification — 2026-08-27

Host: `hermes-vcn-0` (`hermes-cloud`)

## Verified

- Protected source files: `~/.config/text_back/pilot.env` and `signalwire.env`, both mode `0600`.
- Canonical protected runtime: `~/.config/text_back/runtime.env`, mode `0600`.
- SignalWire Compatibility API authentication: HTTP 200.
- Account resources: exactly one purchased number; configured pilot number matched it.
- Capabilities reported by SignalWire: voice, SMS, MMS, fax.
- Existing number handlers: no voice URL and no SMS URL attached.
- Local service: `text-back.service`, enabled and active, bound only to `127.0.0.1:8000`.
- Health: status `ok`, telecom `stub`, wiring `forwarded`, timezone `America/New_York`.
- Unsigned inbound SMS test: HTTP 403 (fail closed).
- SignalWire-mode startup without the Project signing key: rejected as designed.
- Test suite: all tests passed.
- No real SMS, call, forwarding, webhook attachment, or provider traffic was created.

## Live blockers

1. SignalWire Project signing key is dashboard-only and is not stored on this host.
2. This Oracle host is tailnet-only and cannot be made a public webhook server. A durable public HTTPS deployment with persistent storage must be selected and approved.
3. Google Calendar remains a stub; Google auth and the real adapter are incomplete.
4. Human handoff delivery remains an in-memory stub.
5. Messaging registration/trial eligibility has not been proven by a live provider test; number capability alone is not delivery authorization.

## Exact future handlers

Once the signing key and approved deployment exist:

- Voice: `https://<approved-host>/webhooks/voice`, method POST
- Messaging: `https://<approved-host>/webhooks/sms`, method POST

Changing the purchased number's live handlers and sending the first owned-number smoke test require Michael's immediate explicit approval after the exact target, rollback, and any cost are shown.
