# Calendar providers

text_back books against a pluggable calendar provider. The provider is chosen
once at startup by `TEXT_BACK_CALENDAR_PROVIDER`; `create_app` fails closed on
an unknown value, missing credentials, or an absent credential file. `/health`
reports the active provider under the `calendar` key.

Selection: `src/text_back/calendars/factory.py` (`calendar_from_config`) maps
the env value to an adapter. Passing `calendar=` to `create_app` (tests)
bypasses env validation, exactly like `telecom=`.

| Value | Adapter | Status |
|---|---|---|
| `stub` (default) | `CalendarStub` (in-memory) | implemented |
| `google` | `calendars/google.py` (Calendar v3 REST) | implemented |
| `microsoft` | `calendars/microsoft.py` (Graph; Outlook.com + M365) | implemented |
| `icloud` | `calendars/icloud.py` (CalDAV) | implemented |

## Environment variables (values never in git)

| Env var | Provider | Meaning |
|---|---|---|
| `TEXT_BACK_CALENDAR_PROVIDER` | all | `stub` \| `google` \| `microsoft` \| `icloud` |
| `TEXT_BACK_GOOGLE_CALENDAR_ID` | google | Calendar ID (e.g. `mike@example.com`) |
| `TEXT_BACK_GOOGLE_TOKEN_FILE` | google | Path to mode-600 Google authorized-user JSON (legacy one-line tokens supported) |
| `TEXT_BACK_MS_USER` | microsoft | Target mailbox UPN, or `me` for the delegated account |
| `TEXT_BACK_MS_TOKEN_FILE` | microsoft | Path to a mode-600 file holding a current Graph bearer token |
| `TEXT_BACK_ICLOUD_USERNAME` | icloud | Apple ID |
| `TEXT_BACK_ICLOUD_APP_PASSWORD_FILE` | icloud | Path to a mode-600 file holding the app-specific password |
| `TEXT_BACK_ICLOUD_CALENDAR_URL` | icloud | Full HTTPS CalDAV calendar collection URL |

Google refresh and customer reconnection run inside the application. See
[Recover operations](RECOVER-OPERATIONS.md) for the authorized-user JSON format,
Web OAuth client configuration, revocation handling, and reconnect routes.
Microsoft Graph continues to read a current externally refreshed bearer token;
iCloud reads an app-specific password. Neither optional adapter uses Google's
credential lifecycle.

## Product rules (all providers)

- A booking is NEVER confirmed without a provider event ID.
- Free/busy is rechecked immediately before event creation; a provider error
  during either check refuses the booking (no confirmation SMS).
- Event IDs are deterministic per (conversation, slot start)
  (`calendars/ids.py`), so a webhook retry or crash-rerun of the SAME booking
  dedupes at the provider, while a later booking for a different slot can
  never collide with an earlier event's ID.
- A provider "duplicate" signal (Google 409, iCloud 412, Graph 409) is
  verified before it is treated as success: the adapter confirms the existing
  event is live and occupies exactly the requested slot, and refuses the
  booking otherwise (a cancelled tombstone or mismatched event never
  phantom-confirms).
- Crash-window recovery is a real runtime path: when a conversation's fields
  are complete but no appointment is saved, the next inbound message
  re-attempts the booking (`handlers._collect_conversation_field`), which is
  where the deterministic IDs' retry-dedupe is exercised.
- The in-memory `stub` calendar is refused at startup when the telecom
  provider is SignalWire — a production telecom must never confirm bookings
  against a fake calendar.

## Recovered one-time connection design

A business owner connects an existing calendar once through text_back, selects the
calendar, and sees its connection status. Routine use must not require token files,
service-account sharing, or another scheduling account. Google, Outlook/Microsoft 365,
and iCloud stay behind the same connection experience. Exceptional revocation must
fail closed, preserve the lead and offer a reconnect action.

This remains the intended product experience recovered from the August TDD snapshot,
not a claim that every provider's onboarding has shipped. Google already implements
authorized-user refresh, reconnect routes and a private Web-client intake. Unified
provider onboarding, a calendar picker, per-business encrypted connection storage,
expiry/rotation metadata and Microsoft refresh-token rotation remain unfinished.
Secrets must stay out of logs, browser URLs, SMS and Git. Refresh should be automatic,
with bounded retry and atomic credential rotation. iCloud's supported authorization
or one-time app-specific credential must be handled within the onboarding experience.

The recovered Microsoft adapter now uses
[calendarView](https://learn.microsoft.com/en-us/graph/api/calendar-list-calendarview?view=graph-rest-1.0)
for both work/school and delegated personal accounts;
[getSchedule](https://learn.microsoft.com/en-us/graph/api/calendar-getschedule?view=graph-rest-1.0)
does not support delegated personal accounts. It follows bounded Graph pagination,
treats unknown availability as busy, and verifies exact live slot times when recovering
a duplicate event. Optional Microsoft/iCloud connections have offline test coverage;
the live pilot continues to use Google.
