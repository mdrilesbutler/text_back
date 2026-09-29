# SignalWire integration

This project uses SignalWire's Compatibility API for outbound SMS and inbound
voice/SMS webhooks. The implementation is local-only until a protected runtime,
credentials, and explicit approval for live traffic exist.

Official references:

- [Compatibility API webhooks](https://signalwire.com/docs/compatibility-api/guides/webhooks)
- [Webhook security](https://signalwire.com/docs/compatibility-api/guides/webhook-security)
- [cXML overview](https://signalwire.com/docs/compatibility-api/cxml)
- [`<Say>`](https://signalwire.com/docs/compatibility-api/cxml/reference/voice/say)
- [`<Hangup>`](https://signalwire.com/docs/compatibility-api/cxml/reference/voice/hangup)

## Runtime configuration

Keep all values in `~/.config/text_back/` for local work or in the deployment
secret store. Never commit a populated environment file.

```dotenv
TEXT_BACK_TELECOM_MODE=signalwire
TEXT_BACK_BUSINESS_NAME=replace-me
TEXT_BACK_TIMEZONE=America/New_York
TEXT_BACK_APPOINTMENT_DURATION_MINUTES=60
TEXT_BACK_HANDOFF_DESTINATION=replace-with-operator-queue-label
TEXT_BACK_PUBLIC_BASE_URL=https://public-host.example
TEXT_BACK_WEBHOOK_SECRET=replace-with-project-signing-key
TEXT_BACK_SIGNALWIRE_SPACE_URL=https://your-space.signalwire.com
TEXT_BACK_SIGNALWIRE_PROJECT_ID=replace-me
TEXT_BACK_SIGNALWIRE_API_TOKEN=replace-me
TEXT_BACK_SIGNALWIRE_FROM_NUMBER=+15551234567
TEXT_BACK_WIRING_MODE=forwarded
```

`TEXT_BACK_WEBHOOK_SECRET` is the SignalWire Project signing key used for
inbound webhook validation. It is distinct from the REST API token.

The configured `TEXT_BACK_PUBLIC_BASE_URL` must be the exact external scheme,
host, and path prefix SignalWire calls. Signature validation reconstructs:

- `https://public-host.example/webhooks/voice`
- `https://public-host.example/webhooks/sms`

A proxy or tunnel that changes the externally visible URL must not leak its
internal URL into this setting.

## Implemented boundary

- SignalWire mode accepts `X-SignalWire-Signature`; a missing, invalid, or
  Twilio-named signature is rejected with HTTP 403 before policy side effects.
- Stub mode retains `X-Twilio-Signature` so existing local fixtures remain
  explicit and isolated from the live-provider boundary.
- Both callbacks use the exact configured public URL and submitted form fields
  for HMAC validation.
- SignalWire SMS callbacks receive a valid empty cXML `<Response>` after
  deterministic STOP/HELP/conversation handling.
- In `forwarded` mode, voice callbacks receive a branded `<Say>` followed by
  `<Hangup>`. The caller is told that a text will follow; no recording is
  retained.
- In `managed` mode, voice callbacks receive an empty cXML response. The
  existing terminal-unanswered policy remains unchanged.
- `call_sid` and `message_sid` idempotency gates remain in front of duplicate
  outbound messages.
- Handoff pauses automated replies and commits a durable operator alert. The
  managed worker delivers configured notices; authenticated operator polling is
  available. Configure a monitored channel before the pilot.

## Messaging registration (10DLC) and Platform Free Trial

Verified against SignalWire's current documentation on 2026-09-28
(`signalwire.com/docs/platform/messaging`, `.../platform-free-trial`,
`.../campaign-registry/registration`). Re-check before any client onboarding.

- US local (10DLC) numbers cannot send application SMS until a Brand and a
  Campaign are approved in The Campaign Registry. SignalWire states: "If you
  do not register, you will not be able to send messages from a local US number
  to another local US number using our platform." Brand review is usually one
  business day; campaign review 3-5 business days; number assignment up to 24
  hours. Brand submission and a monthly campaign fee with a three-month minimum
  apply. Every client pilot after this one needs an approved campaign; treat
  registration as part of TB-RECOVER onboarding, priced into the SKU.
- The only pre-registration path is **Platform Free Trial (PFT)**: one
  SignalWire number may text exactly one verified mobile number, up to 200
  messages per day, each message prefixed `[SignalWire Free Trial]`. The
  pilot number reports the `messaging_integration_test` capability, which is the
  PFT assignment. The paired verified mobile is visible only in the Dashboard
  (Phone Numbers -> Verified caller IDs, or Messaging Campaigns). Removing that
  verified number or the pilot number ends PFT permanently, so never remove or
  re-verify it.
- Consequence for the real-phone pilot: the **caller phone must be the
  PFT-verified mobile**, because Recover texts the original caller. The
  forwarding phone is then a different voice-capable phone. Put only the
  verified mobile in `TEXT_BACK_PILOT_RECIPIENTS`.
- PFT documentation says "SMS integrations with LaML, SWML and Call Flow
  Builder will not work". Recover sends through the Compatibility REST
  `Messages` endpoint and replies to inbound webhooks with empty cXML, which we
  read as outside that restriction. This is an inference until the first live
  send succeeds. If the send returns a definite HTTP 4xx, the outbox records
  `dead_letter` with the error and the fallback is the JSON
  `POST /api/messaging/messages` endpoint (`to`, `from`, `body`,
  `status_callback`), whose status callback is JSON (`id`, `status`) rather
  than form-encoded `MessageSid`/`MessageStatus`.

## Pre-live checklist

1. Run `.venv/bin/pytest tests/` and require a fully green suite.
2. Confirm the runtime environment contains no placeholder values and the
   config/secret file is mode `600`.
3. Confirm `/health` reports `telecom: signalwire`, the intended wiring mode,
   and no secret values.
4. Replace the in-process Calendar stub with the real, credentialed Google
   Calendar adapter. Do not route customer traffic to the stub.
5. Configure and verify monitored operator access to durable handoff alerts.
   Disabled delivery parks alerts; logging alone does not prove monitoring.
6. Expose HTTPS and attach the two exact webhook URLs in SignalWire.
7. Use only approved non-customer test numbers.
8. Complete every live-call check in `docs/ONBOARDING-FORWARDING.md`, including
   caller-ID passthrough, exactly-one SMS behavior, STOP suppression, and
   forwarding deactivation.

Steps 6–8 mutate live telecom configuration or create traffic and therefore
require Michael's explicit approval at execution time.

Durable sends, signed status callbacks, retries, and worker operation are described
in [Recover operations](RECOVER-OPERATIONS.md).
