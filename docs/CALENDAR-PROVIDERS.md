# Calendar connection — one-time customer onboarding

## Product rule

A business owner connects the calendar they already use **one time inside
text_back**. After that, text_back reads availability, prevents conflicts, and
creates appointments automatically. The owner does not create a Cal.com
account, copy tokens, manage credential files, share a calendar with a service
account, or repeat setup during normal operation.

This is one customer experience with three behind-the-scenes adapters:

- **Google Calendar / Gmail**
- **Microsoft Outlook / Microsoft 365**
- **Apple iCloud Calendar**

The provider details are implementation plumbing, not choices the owner must
understand beyond selecting the calendar account they already have.

## One-time owner experience

1. During onboarding, select **Connect calendar**.
2. Choose Google, Microsoft/Outlook, or Apple.
3. Sign in to that provider and approve calendar access once.
4. Choose the calendar text_back should use.
5. Return to text_back with **Calendar connected** shown.

From then on, text_back owns access-token refresh, rotated credentials,
connection health, availability checks, and event creation. No Cal.com page or
second scheduling account sits between the owner and their calendar.

If a calendar provider itself revokes a grant or the owner revokes access,
text_back must fail closed on booking, preserve the lead, and present one
**Reconnect calendar** button. That is an exceptional provider security event,
not routine onboarding and never a request to paste tokens or edit files.

## Internal architecture

The app stores one `CalendarConnection` per business:

- provider (`google`, `microsoft`, or `icloud`)
- provider account and selected calendar identifiers
- encrypted refresh credential or encrypted provider credential reference
- access-token expiry and provider-specific rotation metadata
- connection state (`connected`, `degraded`, `reauth_required`)
- timestamps for connection, last successful refresh, and last successful API
  operation

Secrets are encrypted at rest in the deployment secret store and never placed
in Git, Obsidian, logs, SMS bodies, browser URLs, or customer-visible errors.
Short-lived access tokens are refreshed before expiry. Microsoft refresh-token
rotation must be stored atomically. On a provider authentication failure, the
runtime refreshes once and retries the original operation once; it never loops.

`CalendarProvider` remains the provider-neutral booking seam. Every adapter
must implement:

- `is_free(start, end)`
- `create_event(...) -> provider_event_id`

All adapters obey the same deterministic rules:

- recheck free/busy immediately before event creation;
- fail closed when availability cannot be proven;
- use provider-side idempotency so retries do not create duplicates;
- never send a booking confirmation without a real provider event ID.

## Provider implementation notes

### Google

Use an OAuth authorization-code flow with offline access and least-privilege
Calendar scopes. Store the refresh grant encrypted, refresh access tokens
silently, and let the owner select `primary` or another writable calendar.
Michael's local `google-oauth-repair` skill is for operator infrastructure; it
is not the customer connection mechanism.

### Microsoft / Outlook

Use Microsoft identity OAuth with `offline_access` and Calendar permissions.
The same owner flow covers Outlook.com and Microsoft 365. Availability must use
the Graph `calendarView` API because Graph `getSchedule` does not support
delegated personal Microsoft accounts. Event creation uses Graph's
`transactionId` idempotency field.

### Apple iCloud

Keep Apple behind the same **Connect calendar once** experience. Use Apple's
supported third-party calendar authorization when available for the app; a
CalDAV app-specific credential is the fallback. Any Apple credential is
captured once through onboarding and stored encrypted—never exposed as a file
or recurring owner task.

## Current build status

The provider-neutral booking seam and offline-tested Google, Microsoft, and
iCloud API adapters are built. Microsoft availability uses Graph
`calendarView`, which supports delegated personal Outlook.com accounts as well
as Microsoft 365 accounts. The current token-file factory is a development and
pilot scaffold only; it is **not** the sellable onboarding design.

The production in-app connection screen, OAuth callbacks, encrypted connection
store, automatic refresh/rotation broker, calendar picker, and provider app
registrations are not yet built. Until those exist, the product does not yet
meet the one-time human onboarding requirement.

The Cal.com booking embed on the separate FluxWorks marketing website is not
part of text_back and is unchanged.

## Acceptance criteria

- A nontechnical owner connects one existing calendar in one onboarding flow.
- No owner handles API keys, token files, service-account sharing, or Cal.com.
- The connection survives process restarts and normal access-token expiry.
- Google, Outlook.com, Microsoft 365, and iCloud owners receive the same product
  experience.
- A revoked grant cannot create or confirm a phantom booking; the lead remains
  queued and the owner sees one safe reconnect action.
- Every confirmed appointment contains a real provider event ID and repeated
  webhook delivery cannot create a duplicate event.
