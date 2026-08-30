from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from text_back.calendars.ids import icloud_uid, ics_escape
from text_back.calendars.protocol import CalendarProviderError
from text_back.calendars.transport import (
    HttpRequest,
    HttpTransport,
    TokenProvider,
    ics_utc,
)

_DAV_NS = "DAV:"
_CALDAV_NS = "urn:ietf:params:xml:ns:caldav"


@dataclass
class ICloudCalDAVProvider:
    """iCloud CalDAV adapter (stdlib only: xml.etree + base64 + hand-built ICS).

    Free/busy uses the universally-supported calendar-query REPORT rather than
    RFC 4791 free-busy-query (unreliable on iCloud); the server does the
    time-range/recurrence filtering, so no client-side ICS date parsing.
    Event creation PUTs a deterministic-UID .ics resource with If-None-Match: *
    so the server itself enforces idempotency (412 = already created)."""

    provider_name: ClassVar[str] = "icloud"
    username: str  # Apple ID
    password_provider: TokenProvider  # app-specific password (same seam)
    transport: HttpTransport
    calendar_url: str  # HTTPS CalDAV calendar collection URL

    def __post_init__(self) -> None:
        if not self.calendar_url.endswith("/"):
            self.calendar_url = self.calendar_url + "/"

    def is_free(self, start: datetime, end: datetime) -> bool:
        query = (
            '<C:calendar-query xmlns:D="DAV:"'
            ' xmlns:C="urn:ietf:params:xml:ns:caldav">'
            "<D:prop><C:calendar-data/></D:prop>"
            '<C:filter><C:comp-filter name="VCALENDAR">'
            '<C:comp-filter name="VEVENT">'
            f'<C:time-range start="{ics_utc(start)}" end="{ics_utc(end)}"/>'
            "</C:comp-filter></C:comp-filter></C:filter>"
            "</C:calendar-query>"
        )
        response = self.transport(
            HttpRequest(
                method="REPORT",
                url=self.calendar_url,
                headers=(
                    ("Authorization", self._basic_auth()),
                    ("Depth", "1"),
                    ("Content-Type", "application/xml"),
                ),
                body=query.encode("utf-8"),
            )
        )
        if response.status != 207:
            raise CalendarProviderError(
                f"icloud calendar returned HTTP {response.status}"
            )
        try:
            root = ET.fromstring(response.body)
        except ET.ParseError:
            raise CalendarProviderError(
                "icloud calendar multistatus response was not valid XML"
            ) from None
        if root.tag != f"{{{_DAV_NS}}}multistatus":
            # A 207 whose body is not a DAV multistatus (server error page,
            # proxy artifact, schema drift) proves nothing about the window.
            # Fail toward busy — never toward a double-booking.
            raise CalendarProviderError(
                "icloud calendar 207 response was not a DAV multistatus"
            )
        for status in root.iter(f"{{{_DAV_NS}}}status"):
            parts = (status.text or "").split()
            if len(parts) < 2 or not parts[1].startswith("2"):
                raise CalendarProviderError(
                    "icloud calendar multistatus reported a non-success status"
                )
        for calendar_data in root.iter(f"{{{_CALDAV_NS}}}calendar-data"):
            text = calendar_data.text or ""
            if not text.strip():
                continue
            # The server already filtered to VEVENTs overlapping the window;
            # anything returned counts as busy unless explicitly transparent
            # or cancelled. Fail toward "busy" — never toward a double-booking.
            if "TRANSP:TRANSPARENT" in text or "STATUS:CANCELLED" in text:
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
    ) -> str | None:
        uid = icloud_uid(conversation_id, start)
        lines = (
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//text_back//EN",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{ics_utc(start)}",
            f"DTSTART:{ics_utc(start)}",
            f"DTEND:{ics_utc(end)}",
            f"SUMMARY:{ics_escape(summary)}",
            f"LOCATION:{ics_escape(location)}",
            f"X-TEXT-BACK-CONVERSATION-ID:{conversation_id}",
            "END:VEVENT",
            "END:VCALENDAR",
        )
        response = self.transport(
            HttpRequest(
                method="PUT",
                url=f"{self.calendar_url}{uid}.ics",
                headers=(
                    ("Authorization", self._basic_auth()),
                    ("If-None-Match", "*"),
                    ("Content-Type", "text/calendar; charset=utf-8"),
                ),
                body=("\r\n".join(lines) + "\r\n").encode("utf-8"),
            )
        )
        if response.status in (201, 204):
            return uid
        if response.status == 412:
            # If-None-Match: * failed: a resource with this (conversation,
            # slot) UID already exists — but verify it still matches the slot
            # being confirmed (and is not cancelled) before treating the
            # duplicate as success. Never fabricate a confirmation.
            return self._verify_duplicate(uid, start)
        raise CalendarProviderError(
            f"icloud calendar returned HTTP {response.status}"
        )

    def _verify_duplicate(self, uid: str, start: datetime) -> str:
        response = self.transport(
            HttpRequest(
                method="GET",
                url=f"{self.calendar_url}{uid}.ics",
                headers=(("Authorization", self._basic_auth()),),
            )
        )
        if response.status != 200:
            raise CalendarProviderError(
                "icloud calendar duplicate event could not be verified"
            )
        try:
            text = response.body.decode("utf-8")
        except UnicodeDecodeError:
            raise CalendarProviderError(
                "icloud calendar duplicate event could not be verified"
            ) from None
        if "STATUS:CANCELLED" in text:
            raise CalendarProviderError(
                "icloud calendar duplicate event is cancelled"
            )
        if f"DTSTART:{ics_utc(start)}" not in text:
            raise CalendarProviderError(
                "icloud calendar duplicate event does not match the requested slot"
            )
        return uid

    def _basic_auth(self) -> str:
        credentials = f"{self.username}:{self.password_provider()}"
        return "Basic " + base64.b64encode(credentials.encode("utf-8")).decode("ascii")
