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
| `microsoft` | `calendars/microsoft.py` (Graph; Outlook.com + M365) | placeholder — selecting it raises "not yet implemented" |
| `icloud` | `calendars/icloud.py` (CalDAV) | placeholder — selecting it raises "not yet implemented" |

## Environment variables (values never in git)

| Env var | Provider | Meaning |
|---|---|---|
| `TEXT_BACK_CALENDAR_PROVIDER` | all | `stub` \| `google` \| `microsoft` \| `icloud` |
| `TEXT_BACK_GOOGLE_CALENDAR_ID` | google | Calendar ID (e.g. `mike@example.com`) |
| `TEXT_BACK_GOOGLE_TOKEN_FILE` | google | Path to a mode-600 file holding ONLY a current OAuth2 bearer access token (one line) |
| `TEXT_BACK_MS_USER` | microsoft | Target mailbox UPN |
| `TEXT_BACK_MS_TOKEN_FILE` | microsoft | Path to a mode-600 file holding a current Graph bearer token |
| `TEXT_BACK_ICLOUD_USERNAME` | icloud | Apple ID |
| `TEXT_BACK_ICLOUD_APP_PASSWORD_FILE` | icloud | Path to a mode-600 file holding the app-specific password |
| `TEXT_BACK_ICLOUD_CALENDAR_URL` | icloud | Full HTTPS CalDAV calendar collection URL |

Adapters consume token FILES, not OAuth client credentials. Token refresh runs
in an external refresher (cron/systemd under `~/.config/text_back/`) that
rewrites the token file; the app re-reads the file on every provider call and
never performs an OAuth flow itself. The refresher's own env names
(`TEXT_BACK_MS_TENANT_ID` / `TEXT_BACK_MS_CLIENT_ID` /
`TEXT_BACK_MS_CLIENT_SECRET_FILE`, `TEXT_BACK_GOOGLE_SA_KEY_FILE`) are
documentation-only — `create_app` never reads them.

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
