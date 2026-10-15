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
- Callers outside an explicit `TEXT_BACK_PILOT_RECIPIENTS` allowlist create no
  inbound job, intent or SMS. In `forwarded` mode they still hear the branded
  greeting that does not promise a text, so a forwarded line never answers
  with dead air; `managed` mode and SMS callbacks stay empty.
- `call_sid` and `message_sid` idempotency gates remain in front of duplicate
  outbound messages.
- Handoff pauses automated replies and commits a durable operator alert. The
  managed worker delivers configured notices; authenticated operator polling is
  available. Configure a monitored channel before the pilot.

## Messaging registration (10DLC) and Platform Free Trial

Verified against SignalWire's current documentation on 2026-09-28
(`signalwire.com/docs/platform/messaging`, `.../platform-free-trial`,
`.../campaign-registry/registration`). Re-check before any client onboarding.
The [trial restrictions](https://signalwire.com/docs/platform/messaging/platform-free-trial),
[registration process](https://signalwire.com/docs/platform/messaging/campaign-registry/registration)
and [verified caller-ID response](https://signalwire.com/docs/apis/rest/verified-caller-id/list-verified-caller-ids)
were rechecked on 2026-10-08 when clarifying the existing-number pilot.

- US local (10DLC) numbers cannot send application SMS until a Brand and a
  Campaign are approved in The Campaign Registry. SignalWire states: "If you
  do not register, you will not be able to send messages from a local US number
  to another local US number using our platform." Brand review is usually one
  business day; campaign review 3-5 business days; number assignment up to 24
  hours. Brand submission and a monthly campaign fee with a three-month minimum
  apply. Every pilot reaching callers outside PFT needs an approved campaign; treat
  registration as part of TB-RECOVER onboarding, priced into the SKU.
- The only pre-registration path is **Platform Free Trial (PFT)**: one
  SignalWire number may text exactly one verified mobile number, up to 200
  messages per day, each message prefixed `[SignalWire Free Trial]`. The
  pilot number reports the `messaging_integration_test` capability, which is the
  PFT assignment. The paired verified mobile is visible only in the Dashboard
  (Phone Numbers -> Verified caller IDs, or Messaging Campaigns). Removing that
  verified number or the pilot number ends PFT permanently, so never remove or
  re-verify it.
- A trial-only SMS check can reach only the PFT-verified mobile. That does not
  prove recovery of missed calls to the owner's existing business cell. Keep
  that cell as the public business number and forwarding source. If it is also
  the trial recipient, register the existing SignalWire number for messaging
  before the end-to-end pilot with another caller. The caller can use an
  existing phone; no additional business line or number purchase is required.
  Keep the pilot allowlist limited to the approved test recipient(s).
- The verified-caller-ID API can confirm that a saved cell is verified for
  outbound voice caller ID. That is distinct from the PFT messaging pairing:
  the documented response has no trial marker. Do not ask the owner to repeat
  voice verification or remove/re-add the number to inspect its trial status.
- PFT documentation says "SMS integrations with LaML, SWML and Call Flow
  Builder will not work". Recover sends through the Compatibility REST
  `Messages` endpoint and replies to inbound webhooks with empty cXML, which we
  read as outside that restriction. This is an inference until the first live
  send succeeds. If the send returns a definite HTTP 4xx, the outbox records
  `dead_letter` with the error and the fallback is the JSON
  `POST /api/messaging/messages` endpoint (`to`, `from`, `body`,
  `status_callback`), whose status callback is JSON (`id`, `status`) rather
  than form-encoded `MessageSid`/`MessageStatus`.

## Registration worksheet for existing-number Recover

Use the existing SignalWire number as the campaign sender and the owner's
existing cell as the public business/forwarding number. A marketing name or
SignalWire Space name is not evidence of the legal business name or EIN.
Enter the legal identity, address, website and owner contact details directly
in the provider's protected form; do not put EINs or home addresses in git.

For an ordinary privately held, for-profit LLC, use the managed-brand private
company path (`PRIVATE_PROFIT` in the API), its exact registered legal name and
its actual EIN. LLC status alone does not supply those values. Keep the marketing
name/DBA in `name` and the registered name in `company_name`; do not append LLC to
the marketing name unless that is the actual legal name. See the provider's
[brand fields](https://signalwire.com/docs/apis/rest/campaign-registry/brands/create-brand).

Recommended pilot classification to confirm in the registration wizard:
`LOW_VOLUME_MIXED`, with `CUSTOMER_CARE` and `ACCOUNT_NOTIFICATION`. The draft
campaign name is **Recover — missed-call scheduling**. The business named in
messages must match the approved brand/DBA; configure `TEXT_BACK_BUSINESS_NAME`
to that identity before generating final samples.

Draft description:

> The business keeps its existing public phone number. Unanswered calls forward
> to its dedicated SignalWire number. Recover texts the caller about the service
> they requested, collects job type, location, preferred appointment time and
> name, and confirms an appointment only after a calendar event exists. Requests
> requiring the owner create an asynchronous lead notification. Bounded
> no-response follow-ups stop on a reply, opt-out, booking, handoff or expiry.
> This campaign does not send marketing promotions or sell customer leads.

Describe lead recovery accurately when answering the provider's
`lead_generation` question; do not automatically set it false merely because
messages are not promotional. The actual campaign description and provider
classification must agree.

Generate message samples from the deployed policy functions, replacing only the
business name with the confirmed brand/DBA:

| Registration field | Implementation source |
|---|---|
| Initial missed-call text / sample 1 | `policy.intro_sms(business_name)` |
| No-response follow-up / sample 2 | `followup.followup_sms(business_name, 1)` |
| Opt-in confirmation | `policy.opt_in_sms(business_name)` |
| Opt-out confirmation | `policy.OPT_OUT_ACK` |
| HELP response | `policy.help_sms(business_name)` |
| Application opt-in keywords | Whole-message `START`, `UNSTOP` |
| Application opt-out keywords | `STOP`, `STOPALL`, `UNSUBSCRIBE`, `CANCEL`, `END`, `QUIT` |
| Application HELP keywords | `HELP`, `INFO` |

The application does not treat START/UNSTOP as a job description. They restore
SMS permission without clearing an active handoff or restarting a cancelled
follow-up sequence. A later STOP cancels a queued opt-in acknowledgment.
SignalWire's network-level STOP/UNSTOP behavior is separate: verify which
keywords and acknowledgments actually reach the application in the live pilot.

For the `message_flow` field, document the actual consent mechanism and its
evidence. A voice call is not proof of a consumer-initiated SMS conversation.
The existing voice handler announces a text and hangs up; it does not collect
an affirmative consent response. For an allowlisted pilot, record the tester's
explicit agreement to scheduling texts before sending. Describe the implemented
customer consent process for a broader deployment; do not claim an online
checkbox, recorded verbal agreement or published legal pages that do not exist.
The provider's [messaging requirements](https://share.signalwire.com/hubfs/PDFs/Messaging-Requirements-and-Code-of-Conduct.pdf)
distinguish consumer-initiated texts from business-initiated informational texts
and require consent appropriate to the message type. Re-enrollment support does
not establish permission for the original missed-call intro.

Fees from the [public rate deck](https://signalwire.com/pricing/rates), checked
2026-10-08: brand $4.50 once, DCA vetting $7.50 per campaign submission, Low Volume
Mixed $1.50/month. With three months prepaid, the initial registration estimate
is $16.50, excluding usage, number rental, taxes and any additional charges.
This is not an authenticated quote. The same deck lists a $250 fee after 60
consecutive inactive days; establish an appropriate campaign closure process
before leaving a paid pilot inactive. Compare the actual wizard quote and
recurring total against the approved $15/month ceiling before submission.

The [registration process](https://signalwire.com/docs/platform/messaging/campaign-registry/registration)
requires verified business identity before campaign approval and number
assignment. Submission is not delivery readiness: verify approval and assignment
for the already-owned number, then execute the full phone checklist. Account
terms and the final consent description must be reviewed as actual commitments,
not automatically populated from this worksheet.

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
