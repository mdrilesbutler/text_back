from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import ClassVar

from text_back.calendars.ids import ms_transaction_id
from text_back.calendars.protocol import CalendarProviderError
from text_back.calendars.transport import (
    HttpRequest,
    HttpTransport,
    TokenProvider,
    rfc3339_utc,
)

# calendarView supports delegated personal Outlook.com accounts as well as
# work/school Microsoft 365 accounts. Only these two Graph showAs values leave
# the requested slot bookable; missing/unknown values fail toward busy.
_NON_BLOCKING_SHOW_AS = {"free", "workingElsewhere"}


@dataclass
class MicrosoftGraphProvider:
    """One adapter for Outlook.com and Microsoft 365.

    Availability intentionally uses ``calendarView`` rather than
    ``calendar/getSchedule``: Microsoft documents delegated personal accounts
    as unsupported for getSchedule, while calendarView supports both personal
    and work/school accounts.
    """

    provider_name: ClassVar[str] = "microsoft"
    sends_invites: ClassVar[bool] = True
    user: str  # target mailbox UPN (Outlook.com and M365)
    token_provider: TokenProvider
    transport: HttpTransport
    base_url: str = "https://graph.microsoft.com/v1.0"

    def is_free(self, start: datetime, end: datetime) -> bool:
        entries = self._calendar_view_entries(
            start=start,
            end=end,
            select="id,showAs,isCancelled",
        )
        for entry in entries:
            if entry.get("isCancelled") is True:
                continue
            if entry.get("showAs") in _NON_BLOCKING_SHOW_AS:
                continue
            return False
        return True

    def create_event(
        self,
        *,
        start: datetime,
        end: datetime,
        summary: str,
        location: str,
        caller: str,
        conversation_id: str,
        attendee_email: str | None = None,
        description: str | None = None,
    ) -> str | None:
        transaction_id = ms_transaction_id(conversation_id, start)
        payload = {
            "transactionId": transaction_id,
            "subject": summary,
            "location": {"displayName": location},
            "start": {"dateTime": rfc3339_utc(start), "timeZone": "UTC"},
            "end": {"dateTime": rfc3339_utc(end), "timeZone": "UTC"},
            "body": {
                "contentType": "text",
                "content": description or f"text_back conversation {conversation_id}",
            },
        }
        if attendee_email:
            # Graph sends the invitation to required attendees on creation.
            payload["attendees"] = [{"emailAddress": {"address": attendee_email}, "type": "required"}]
        response = self.transport(
            self._request("POST", f"{self._user_url()}/calendar/events", payload)
        )
        if response.status == 409:
            # Graph's duplicate-transactionId signal: an earlier attempt for
            # this (conversation, slot) already created the event. Recover its
            # real ID — never fabricate one.
            return self._lookup_event_id(transaction_id, start, end)
        if response.status != 201:
            raise CalendarProviderError(
                f"microsoft calendar returned HTTP {response.status}"
            )
        body = self._json(response.body)
        event_id = body.get("id") if isinstance(body, dict) else None
        if not isinstance(event_id, str) or not event_id:
            raise CalendarProviderError(
                "microsoft calendar create response did not include an event id"
            )
        return event_id

    def _lookup_event_id(
        self, transaction_id: str, start: datetime, end: datetime
    ) -> str:
        # calendarView returns overlapping events, so transactionId alone is
        # insufficient: a moved/cancelled event must never confirm this slot.
        value = self._calendar_view_entries(
            start=start,
            end=end,
            select="id,transactionId,start,end,isCancelled",
        )
        for entry in value:
            if (
                isinstance(entry, dict)
                and entry.get("transactionId") == transaction_id
            ):
                event_id = entry.get("id")
                if (isinstance(event_id, str) and event_id
                        and entry.get("isCancelled") is False
                        and self._parse_graph_datetime(entry.get("start")) == start.astimezone(timezone.utc)
                        and self._parse_graph_datetime(entry.get("end")) == end.astimezone(timezone.utc)):
                    return event_id
        raise CalendarProviderError(
            "microsoft calendar duplicate lookup did not return the event id"
        )

    def _calendar_view_entries(
        self,
        *,
        start: datetime,
        end: datetime,
        select: str,
    ) -> list[dict]:
        query = urllib.parse.urlencode(
            {
                "startDateTime": rfc3339_utc(start),
                "endDateTime": rfc3339_utc(end),
                "$select": select,
            }
        )
        url = f"{self._user_url()}/calendarView?{query}"
        entries: list[dict] = []
        seen: set[str] = set()
        trusted_prefix = self.base_url.rstrip("/") + "/"

        # A one-slot view should be tiny, but follow bounded Graph pagination so
        # a crowded calendar cannot hide a busy event on page two.
        for _ in range(20):
            if url in seen:
                raise CalendarProviderError(
                    "microsoft calendar pagination was invalid"
                )
            seen.add(url)
            response = self.transport(self._request("GET", url, None))
            if response.status != 200:
                raise CalendarProviderError(
                    f"microsoft calendar returned HTTP {response.status}"
                )
            body = self._json(response.body)
            value = body.get("value") if isinstance(body, dict) else None
            if not isinstance(value, list) or any(
                not isinstance(entry, dict) for entry in value
            ):
                raise CalendarProviderError(
                    "microsoft calendar calendarView response was malformed"
                )
            entries.extend(value)

            next_link = body.get("@odata.nextLink")
            if next_link is None:
                return entries
            if (
                not isinstance(next_link, str)
                or not next_link.startswith(trusted_prefix)
            ):
                raise CalendarProviderError(
                    "microsoft calendar pagination was invalid"
                )
            url = next_link

        raise CalendarProviderError("microsoft calendar pagination exceeded limit")

    def _user_url(self) -> str:
        if self.user == "me":
            return f"{self.base_url}/me"
        return f"{self.base_url}/users/{urllib.parse.quote(self.user, safe='')}"

    def _request(self, method: str, url: str, payload: dict | None) -> HttpRequest:
        headers = [("Authorization", f"Bearer {self.token_provider()}"),
                   ("Prefer", 'outlook.timezone="UTC"')]
        body = None
        if payload is not None:
            headers.append(("Content-Type", "application/json"))
            body = json.dumps(payload).encode("utf-8")
        return HttpRequest(method=method, url=url, headers=tuple(headers), body=body)

    @staticmethod
    def _json(body: bytes) -> dict:
        try:
            return json.loads(body)
        except ValueError:
            raise CalendarProviderError(
                "microsoft calendar response was not valid JSON"
            ) from None

    @staticmethod
    def _parse_graph_datetime(field: object) -> datetime:
        """Parse a Graph dateTimeTimeZone start/end into an aware UTC datetime.
        We request timeZone UTC, so a naive value is UTC; anything unparseable
        raises (fail closed — a slot whose freeness cannot be proven is not
        bookable)."""
        if not isinstance(field, dict):
            raise CalendarProviderError(
                "microsoft calendar schedule item was malformed"
            )
        raw = field.get("dateTime")
        if not isinstance(raw, str):
            raise CalendarProviderError(
                "microsoft calendar schedule item was malformed"
            )
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            raise CalendarProviderError(
                "microsoft calendar schedule item datetime was unparseable"
            ) from None
        if parsed.tzinfo is None:
            if field.get("timeZone") not in ("UTC", "Etc/UTC"):
                raise CalendarProviderError("microsoft calendar event timezone was not UTC")
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
