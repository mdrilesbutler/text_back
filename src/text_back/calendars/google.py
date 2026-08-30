from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from text_back.calendars.ids import google_event_id
from text_back.calendars.protocol import CalendarProviderError
from text_back.calendars.transport import (
    HttpRequest,
    HttpTransport,
    TokenProvider,
    rfc3339_utc,
)


@dataclass
class GoogleCalendarProvider:
    provider_name: ClassVar[str] = "google"
    calendar_id: str
    token_provider: TokenProvider
    transport: HttpTransport
    base_url: str = "https://www.googleapis.com/calendar/v3"

    def is_free(self, start: datetime, end: datetime) -> bool:
        payload = {
            "timeMin": rfc3339_utc(start),
            "timeMax": rfc3339_utc(end),
            "items": [{"id": self.calendar_id}],
        }
        response = self.transport(
            self._request("POST", f"{self.base_url}/freeBusy", payload)
        )
        if response.status != 200:
            raise CalendarProviderError(
                f"google calendar returned HTTP {response.status}"
            )
        body = self._json(response.body)
        try:
            entry = body["calendars"][self.calendar_id]
        except (KeyError, TypeError):
            raise CalendarProviderError(
                "google calendar free/busy response missing calendar entry"
            ) from None
        if entry.get("errors"):
            raise CalendarProviderError(
                "google calendar free/busy response reported errors"
            )
        busy = entry.get("busy")
        if not isinstance(busy, list):
            raise CalendarProviderError(
                "google calendar free/busy response was malformed"
            )
        return busy == []

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
        deterministic_id = google_event_id(conversation_id, start)
        payload = {
            "id": deterministic_id,
            "summary": summary,
            "location": location,
            "description": "text_back booking",
            "start": {"dateTime": rfc3339_utc(start)},
            "end": {"dateTime": rfc3339_utc(end)},
            "extendedProperties": {
                "private": {
                    "text_back_conversation_id": conversation_id,
                    "text_back_caller": caller,
                }
            },
        }
        encoded_calendar = urllib.parse.quote(self.calendar_id, safe="")
        response = self.transport(
            self._request(
                "POST",
                f"{self.base_url}/calendars/{encoded_calendar}/events",
                payload,
            )
        )
        if response.status == 409:
            # Our deterministic (conversation, slot) event ID already exists.
            # That SHOULD mean an earlier attempt for this exact slot landed,
            # but Google also 409s on the ID of a cancelled (tombstoned)
            # event — so verify before confirming, never fabricate success.
            return self._verify_duplicate(
                encoded_calendar, deterministic_id, start, end
            )
        if response.status not in (200, 201):
            raise CalendarProviderError(
                f"google calendar returned HTTP {response.status}"
            )
        body = self._json(response.body)
        event_id = body.get("id") if isinstance(body, dict) else None
        if not isinstance(event_id, str) or not event_id:
            raise CalendarProviderError(
                "google calendar create response did not include an event id"
            )
        return event_id

    def _verify_duplicate(
        self,
        encoded_calendar: str,
        deterministic_id: str,
        start: datetime,
        end: datetime,
    ) -> str:
        """A 409 on our deterministic ID is only success if the existing event
        is live and occupies exactly the requested slot. Anything else —
        cancelled tombstone, mismatched times, lookup failure — refuses the
        booking (fail closed, never phantom-confirm)."""
        response = self.transport(
            self._request(
                "GET",
                f"{self.base_url}/calendars/{encoded_calendar}/events/"
                f"{deterministic_id}",
                None,
            )
        )
        if response.status != 200:
            raise CalendarProviderError(
                "google calendar duplicate event could not be verified"
            )
        body = self._json(response.body)
        if not isinstance(body, dict) or body.get("status") == "cancelled":
            raise CalendarProviderError(
                "google calendar duplicate event is cancelled or malformed"
            )
        if not (
            self._same_instant(body.get("start"), start)
            and self._same_instant(body.get("end"), end)
        ):
            raise CalendarProviderError(
                "google calendar duplicate event does not match the requested slot"
            )
        return deterministic_id

    @staticmethod
    def _same_instant(field: object, expected: datetime) -> bool:
        if not isinstance(field, dict):
            return False
        raw = field.get("dateTime")
        if not isinstance(raw, str):
            return False
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return False
        if parsed.tzinfo is None:
            return False
        return parsed == expected

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
                "google calendar response was not valid JSON"
            ) from None
