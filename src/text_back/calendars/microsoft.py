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

# Graph scheduleItems statuses that block the window. "free" and
# "workingElsewhere" do not.
_BLOCKING_STATUSES = {"busy", "tentative", "oof"}


@dataclass
class MicrosoftGraphProvider:
    """One adapter for both Outlook.com and M365 — identical Graph endpoints;
    only the token audience differs (the external refresher's problem)."""

    provider_name: ClassVar[str] = "microsoft"
    user: str  # target mailbox UPN (Outlook.com and M365)
    token_provider: TokenProvider
    transport: HttpTransport
    base_url: str = "https://graph.microsoft.com/v1.0"

    def is_free(self, start: datetime, end: datetime) -> bool:
        payload = {
            "schedules": [self.user],
            "startTime": {"dateTime": rfc3339_utc(start), "timeZone": "UTC"},
            "endTime": {"dateTime": rfc3339_utc(end), "timeZone": "UTC"},
            "availabilityViewInterval": 15,
        }
        response = self.transport(
            self._request("POST", f"{self._user_url()}/calendar/getSchedule", payload)
        )
        if response.status != 200:
            raise CalendarProviderError(
                f"microsoft calendar returned HTTP {response.status}"
            )
        body = self._json(response.body)
        value = body.get("value") if isinstance(body, dict) else None
        if not isinstance(value, list) or not value:
            raise CalendarProviderError(
                "microsoft calendar getSchedule response was malformed"
            )
        entry = value[0]
        if not isinstance(entry, dict) or "error" in entry:
            raise CalendarProviderError(
                "microsoft calendar getSchedule response reported an error"
            )
        items = entry.get("scheduleItems")
        if not isinstance(items, list):
            raise CalendarProviderError(
                "microsoft calendar getSchedule response was malformed"
            )
        start_utc = start.astimezone(timezone.utc)
        end_utc = end.astimezone(timezone.utc)
        for item in items:
            if not isinstance(item, dict):
                raise CalendarProviderError(
                    "microsoft calendar schedule item was malformed"
                )
            if item.get("status") not in _BLOCKING_STATUSES:
                continue
            item_start = self._parse_graph_datetime(item.get("start"))
            item_end = self._parse_graph_datetime(item.get("end"))
            # Half-open overlap against [start, end).
            if item_start < end_utc and item_end > start_utc:
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
                "content": f"text_back conversation {conversation_id}",
            },
        }
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
        # Graph does not document transactionId as $filter-able, so list the
        # requested window via calendarView and match transactionId client
        # side. Bounding the lookup to [start, end] doubles as slot
        # verification: an event for a different or deleted slot can never be
        # returned here, so a 409 whose event does not occupy the requested
        # window fails closed instead of phantom-confirming.
        query = urllib.parse.urlencode(
            {
                "startDateTime": rfc3339_utc(start),
                "endDateTime": rfc3339_utc(end),
                "$select": "id,transactionId",
            }
        )
        url = f"{self._user_url()}/calendar/calendarView?{query}"
        response = self.transport(self._request("GET", url, None))
        if response.status != 200:
            raise CalendarProviderError(
                f"microsoft calendar returned HTTP {response.status}"
            )
        body = self._json(response.body)
        value = body.get("value") if isinstance(body, dict) else None
        if not isinstance(value, list):
            raise CalendarProviderError(
                "microsoft calendar duplicate lookup did not return the event id"
            )
        for entry in value:
            if (
                isinstance(entry, dict)
                and entry.get("transactionId") == transaction_id
            ):
                event_id = entry.get("id")
                if isinstance(event_id, str) and event_id:
                    return event_id
        raise CalendarProviderError(
            "microsoft calendar duplicate lookup did not return the event id"
        )

    def _user_url(self) -> str:
        return f"{self.base_url}/users/{urllib.parse.quote(self.user, safe='')}"

    def _request(self, method: str, url: str, payload: dict | None) -> HttpRequest:
        headers = [("Authorization", f"Bearer {self.token_provider()}")]
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
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
