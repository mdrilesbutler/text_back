# Recover operation and recovery

Run one client per process and persistent SQLite database. Configure identity,
numbers, timezone, calendar, and destinations through the environment. Start with
`PYTHONPATH=src .venv/bin/python -m text_back`; the server binds to localhost.
`deploy/systemd/text-back.service` is the user-service template. Its writable
credential directory permits atomic Google token refresh; `UMask=0077` protects
credentials and the database. Back up the database with SQLite's backup API,
not by copying a live database without its WAL.

## Background processing

FastAPI's lifespan starts one worker. It checks credentials, replays persisted
inbound webhooks, retries bookings, advances follow-ups, sends queued SMS, and
delivers operator alerts. Each lane reports failure separately through `/health`.
Shutdown waits for active provider requests before closing the owned database.
Restart resumes the same database. SignalWire mode rejects an in-memory database.

Every verified webhook is stored before processing. The inbound claim, captured
fields, handoff payload, and SMS intent commit together. An interrupted handler
can be replayed without treating the same customer text as a new field. SMS
transports run after the intent transaction commits. Old prompts are cancelled
when a new reply changes the conversation.

Customer SMS attempts use a four-attempt limit with 1-, 5-, and 15-minute retry
delays. Only definite non-acceptance (connection failure or HTTP 429) is retried.
A timeout after transmission, HTTP 5xx, missing receipt, or interrupted send is
held as `unknown`; it is not automatically resent. An interrupted `sending` row
becomes `unknown` after its two-minute lease. This avoids claiming exactly-once
provider delivery, which the SMS provider does not guarantee.

Each SignalWire send carries an intent-specific `StatusCallback`. The signed
`/webhooks/sms-status?key=...` callback reconciles unknown sends using the provider
message ID. Failed/undelivered callbacks record `sms.delivery_failed`; they cannot
invent a booking confirmation. Provider acceptance and handset delivery are
separate facts. Missing callbacks require investigation in SignalWire before any
manual resend. Health exposes counts, never customer content or secrets.

STOP, current handoff, booking, follow-up cancellation, and quiet hours are checked
again before delayed sends. STOP/HELP replies are exempt from quiet hours.
Immediate customer replies remain conversational; delayed retries and worker
messages obey quiet hours. A provider request already authorized and in flight
cannot be recalled by a later STOP. Pending work is cancelled.

A signed inbound whole-message START or UNSTOP restores application SMS
permission and queues a branded confirmation. Phrases containing those words
do not clear an opt-out. Re-enrollment preserves active handoffs, collected
fields and cancelled follow-ups; it does not start a new booking or a new
follow-up sequence. STOP cancels any pending opt-in confirmation. The provider
may handle network-level STOP/UNSTOP separately, so prove both provider and
application behavior during the real-phone checks.

Qualified bookings survive temporary calendar outages. Up to four attempts are
made, followed by a durable operator handoff. Revoked Google credentials pause
booking attempts until reconnection. Google retries verify the deterministic
provider event before treating its occupied slot as a conflict after a crash.
Confirmation is queued only with a provider event ID.

## Operator access

Set a separate `TEXT_BACK_OPERATOR_API_KEY` in the protected environment file.
`GET /operator/handoffs` requires `Authorization: Bearer <key>` and returns the
most recent durable alert payloads. Do not place the key in URLs or public pages.
This supports operator polling; it does not establish that someone is monitoring
alerts. `TEXT_BACK_HANDOFF_DELIVERY_CHANNEL=disabled` parks alerts;
`log` emits redacted notices. A monitored alert destination remains a pilot
requirement. Operator delivery is bounded at-least-once; receipts and outcome
ledger entries are deduplicated. Malformed payloads do not block healthy rows.

For private Telegram alerts, select `TEXT_BACK_HANDOFF_DELIVERY_CHANNEL=telegram`
and configure `TEXT_BACK_TELEGRAM_BOT_TOKEN` and `TEXT_BACK_TELEGRAM_CHAT_ID` in the
protected environment. Use an existing bot and an operator-approved chat; verify
the chat identity before enabling delivery. Messages use plain text and disable
link previews so reconnection invitations are not fetched by preview services.
API failures remain in the bounded outbox retry workflow, with token-free error
messages. Telegram acceptance returns a stored receipt; operator acknowledgment
is separate evidence that the destination is monitored.

### Native-browser credential intake

Use the operator's normal browser for provider account sign-in. If the agent
cannot access that browser, the existing SignalWire signing key can be staged
through an optional HTTPS form. Set `TEXT_BACK_SETUP_DIRECTORY` to a protected
directory writable by the service and restart it. Issue an invitation with:

```sh
PYTHONPATH=src .venv/bin/python -m text_back.setup_intake \
  --directory /home/ubuntu/.config/text_back/setup \
  --public-base-url https://hermes-cloud.tailefb1a4.ts.net:8443
```

The generated link authorizes one save for one hour. Its token is carried in the
URL fragment, removed from the visible address after loading, and sent only as
an Authorization header. The form has no external assets, disables caching and
referrers, and requires a matching Origin. The invitation stores only a token
hash. The submitted key is published atomically as a mode-600
`signalwire-signing-key.pending` file; an existing staged key is never replaced.
Saving does not rotate credentials, change routing, or prove the key matches
the provider. Privately apply the staged value to `TEXT_BACK_WEBHOOK_SECRET`,
restart the service, and verify signatures during the real-phone checks.
Remove `TEXT_BACK_SETUP_DIRECTORY` and restart after intake is complete.

The same optional intake supports a Google Web OAuth client JSON without asking
for the existing signing key again. Issue a separate, purpose-bound invitation:

```sh
PYTHONPATH=src .venv/bin/python -m text_back.setup_intake \
  --directory /home/ubuntu/.config/text_back/setup \
  --public-base-url https://hermes-cloud.tailefb1a4.ts.net:8443 \
  --purpose google-client
```

The browser page displays the exact callback URI and accepts a downloaded
**Web application** client JSON. Per Google's current instructions, download
the file when creating the client, since the secret is only shown at creation.
The server validates the client type, Google endpoints and matching redirect URI,
then atomically stages `google-web-client.pending.json` with mode 600. Its upload
token cannot save a signing key, and a signing-key invitation cannot save a
Google client. Uploads are limited to 32 KB; no secret is echoed to the browser.
An existing staged file is never overwritten.

Saving is not Google authorization. Privately inspect the staged client, point
`TEXT_BACK_GOOGLE_CLIENT_FILE` to the protected file and restart the service,
then create a calendar reconnect link and have the operator complete Google
consent. Keep the existing `google_token.json` intact: refresh continues using
its original client until browser reconnection validates calendar write access
and saves the new authorized credentials. Verify Google free/busy afterwards.

Reference: [Google Web application credentials](https://developers.google.com/identity/protocols/oauth2/web-server#creatingcred).

Test this flow through a separate temporary directory with dummy data. Never
consume a live invitation during verification or put a signing key in chat,
logs, source, or documentation.

Revenue reporting uses `brief.build_brief_data` / `brief.render_brief` and explicit
operator evidence through `operator.record_job_completed` and
`operator.record_revenue_attributed`. Bookings alone never produce revenue.

## Calendar reconnection

Google supports authorized-user JSON credentials with `token`, `expiry`,
`refresh_token`, `client_id`, and `client_secret`. Refresh uses a file lock and
atomic mode-600 replacement. Transient outages preserve credentials;
`invalid_grant` persists `reauth_required`. A 401 causes one refresh and retry.
Legacy one-line access tokens remain readable for compatibility but cannot
refresh themselves; use authorized-user JSON for an operating client.

Customer reconnection uses Google browser consent, not host OAuth-repair tools.
A revoked calendar queues an operator alert containing a connection link. An
operator can also request one with authenticated `POST /operator/calendar/reconnect`.
Links expire after one day; the browser flow uses a 15-minute, single-use state,
PKCE, and a Secure/HttpOnly cookie. The callback verifies write access to the
configured calendar before saving new credentials.

Configure a Google **Web application** OAuth client with the exact redirect URI
`<TEXT_BACK_PUBLIC_BASE_URL>/calendar/callback`. Use
`TEXT_BACK_GOOGLE_CLIENT_FILE` to point to its protected client JSON if it differs
from the client embedded in the current token file. An installed/desktop OAuth
client used for the pilot token is not proof that this HTTPS callback is registered.
Refresh continues using the client embedded in the existing token file until a
successful browser reconnection saves credentials for the new Web client.
Public HTTPS, client registration, and a monitored reconnect delivery channel
must be verified during onboarding.

## Pilot preparation and verification

`scripts/pilot_check.py --env-file <protected-runtime-file>` reports configuration
without printing secrets. Add `--health` to check the running localhost worker. Add `--providers` for read-only Google free/busy and
SignalWire number/handler checks. Google refresh may update the credential file.
SignalWire checks also report owned-number capabilities, available project
verification fields, and brand registration states. Missing API fields mean
unknown, not a confirmed account restriction; capabilities alone do not prove
delivery to a handset.
The script never creates an appointment, sends an SMS, purchases a number, or
changes routing. An explicit `--google-token-file` and `--google-calendar-id`
can verify credentials before switching runtime configuration.

The localhost installer `deploy/install_local_runtime.py --google-calendar-id <id>`
requires existing stub telecom and a localhost public URL. It backs up the prior
unit/environment, installs the reviewed service, enables the supplied Google
calendar, and creates an operator API secret only if none exists. Existing
telecom and signing credentials are preserved. Reload the user service manager
and restart `text-back.service` after running the tests, or pass `--restart` to the installer.

Before live traffic: choose and register the HTTPS endpoint (`deploy/Caddyfile` is the uninstalled proxy template), configure the OAuth
callback, establish monitored operator alerts, check SignalWire account/trial and
messaging-registration requirements, then attach the exact voice/SMS handlers.
Use only approved pilot numbers and follow every check in
`ONBOARDING-FORWARDING.md`. A passing local suite, working provider credentials,
or green health check does not prove caller-ID forwarding or a real-phone pilot.

For the pilot, set `TEXT_BACK_PILOT_RECIPIENTS` to a comma-separated list of
explicitly approved E.164 mobile numbers. An explicitly empty value blocks all
pilot recipients; an absent variable leaves normal service behavior unchanged.
Malformed numbers fail startup. After signature verification, voice/SMS requests
from other numbers return empty cXML without persisting work. The SignalWire
transport also blocks queued outbound messages to numbers outside the list.
Health reports only the count. Keep the list empty until the operator supplies
the approved test phones; never infer approval from account records.

### HTTPS using existing Tailscale Funnel

When Funnel is already allowed for the host, it can provide pilot HTTPS without
buying a domain or installing Caddy. Check `tailscale serve status --json` first
and preserve existing services. Use an unused allowed port such as `8443`:

```sh
sudo tailscale funnel --bg --https=8443 http://127.0.0.1:8000
```

Set `TEXT_BACK_PUBLIC_BASE_URL` to the exact printed HTTPS origin, including the
port, and restart `text-back.service`. The Google redirect URI is that origin
plus `/calendar/callback`; SignalWire handlers use `/webhooks/voice` and
`/webhooks/sms`. Verify health through the public DNS address, since a tailnet
connection alone does not prove public reachability. Confirm `AllowFunnel`
contains only the intended public port. Roll back only the Recover listener with
`sudo tailscale funnel --https=8443 off`; never reset the entire Serve config.

Account setup browsers must remain private. A temporary browser dashboard can
use a separate **Serve** listener restricted to the tailnet; never expose an
authenticated setup browser through Funnel. Remove its listener after setup.

Use `deploy/systemd/text-back-setup-browser.service` for a dedicated setup
browser on this host. Its mode-700 profile lives outside the repository and its
debugging port binds to localhost. Start it as a temporary user service; wait
for `http://127.0.0.1:9224/json/version` before attaching. The host's global
`agent-browser` wrapper shares a different Chrome instance with a one-hour
lifetime, so use the native executable for this setup:

```sh
/home/ubuntu/.local/lib/node_modules/agent-browser/bin/agent-browser-linux-arm64 --namespace text-back --session recover-login --cdp 9224 open https://fluxworks.signalwire.com
/home/ubuntu/.local/lib/node_modules/agent-browser/bin/agent-browser-linux-arm64 --namespace text-back --session recover-login --cdp 9224 set viewport 1280 720
/home/ubuntu/.local/lib/node_modules/agent-browser/bin/agent-browser-linux-arm64 --namespace text-back dashboard start --port 4849
node deploy/setup_browser_proxy.mjs
```

The proxy binds to localhost 4850; use the temporary user-service template
`deploy/systemd/text-back-setup-proxy.service` to manage it in the background.
Point the private Serve listener at it:

```sh
sudo tailscale serve --bg --https=10000 http://127.0.0.1:4850
```

Agent-browser 0.34.0 incorrectly uses character codes as Windows virtual key
codes: a period becomes Delete (46 rather than 190). The scoped proxy patches
that dashboard bundle to use the browser's keyboard event code. It refuses to
start if the expected implementation changes, forwards API/WebSocket traffic,
and does not log keyboard input. It leaves the installed shared agent-browser
package untouched. Asset cache busting loads the corrected bundle on refresh.
Run `node --test deploy/setup_browser_proxy.test.mjs` and verify a period through
an isolated dashboard client before asking the operator to reload. Stop the
temporary proxy service along with the setup browser when setup is complete.

The private dashboard requires Tailscale connected on the viewing device. Check
both `/api/sessions` and the session WebSocket stream through HTTPS; an HTTP 200
alone does not prove that the browser viewport works. Explicitly set the viewport
after opening or selecting each login tab. When attaching to existing Chrome,
agent-browser can report its default 1280×720 while the page and streamed image
are actually 780×493; the dashboard then sends clicks to incorrect coordinates.
Verify `innerWidth`/`innerHeight`, decoded canvas dimensions, and stream status
agree. Test a click and a harmless character through the dashboard, confirm the
intended input received it, and clear it without submitting. Frame delivery alone
does not establish working interaction. Keep other Serve listeners
and shared browser sessions intact. After account setup, stop this dedicated
browser and dashboard and remove only the temporary port-10000 Serve listener.

If the browser reports that the connection unexpectedly closed, check the
`tailscaled` journal for `handleIngress` rejection of the private port. That
means the request reached public Funnel ingress instead of the private Serve
listener, for example because the browser used public DNS. Do not make the
account browser public to work around it. A temporary TCP forward on an unused
tailnet port can bypass hostname resolution:

```sh
sudo tailscale serve --bg --tcp=80 tcp://127.0.0.1:4850
```

Open `http://<host-tailscale-ip>/` from the connected device. This HTTP connection
travels inside the encrypted Tailscale tunnel; the browser itself does not use
HTTPS for this fallback. TCP forwarding is necessary because the HTTP Serve
handler matches the configured hostname and returns 404 for an IP-address Host.
Verify session listing, tabs with the matching Referer, and streamed frames at
the IP origin, then obtain device confirmation. Preserve the public Recover
listener and existing private services. Remove this temporary fallback with
`sudo tailscale serve --tcp=80 off` after setup.

Protocol references:
[Google OAuth web-server flow](https://developers.google.com/identity/protocols/oauth2/web-server),
[SignalWire status callbacks](https://signalwire.com/docs/compatibility-api/rest/messages/webhooks/sms-status-callback),
[SignalWire number inspection](https://signalwire.com/docs/compatibility-api/rest/incoming-phone-numbers/list-incoming-phone-numbers).
