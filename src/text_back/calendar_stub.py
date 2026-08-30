from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import ClassVar


@dataclass
class CalendarStub:
    provider_name: ClassVar[str] = "stub"
    timezone_name: str = "UTC"
    events: dict[str, dict] = field(default_factory=dict)
    busy: list[tuple[datetime, datetime]] = field(default_factory=list)
    _seq: int = 0

    def is_free(self, start: datetime, end: datetime) -> bool:
        for busy_start, busy_end in self.busy:
            if start < busy_end and end > busy_start:
                return False
        for event in self.events.values():
            if start < event["end"] and end > event["start"]:
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
        if not self.is_free(start, end):
            return None
        self._seq += 1
        event_id = f"evt-{self._seq:04d}"
        self.events[event_id] = {
            "event_id": event_id,
            "start": start,
            "end": end,
            "summary": summary,
            "location": location,
            "caller": caller,
            "conversation_id": conversation_id,
        }
        self.busy.append((start, end))
        return event_id


def slot_end(start: datetime, duration_minutes: int) -> datetime:
    return start + timedelta(minutes=duration_minutes)
