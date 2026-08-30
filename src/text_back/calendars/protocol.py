from __future__ import annotations

from datetime import datetime
from typing import Protocol


class CalendarProviderError(RuntimeError):
    """Redacted provider/transport failure. Message must never contain
    credentials, tokens, or response bodies — status + provider name only."""


class CalendarProvider(Protocol):
    provider_name: str

    def is_free(self, start: datetime, end: datetime) -> bool:
        """True iff the window is free. Raises CalendarProviderError on any
        transport/API/malformed-response failure (fail closed — a slot whose
        freeness cannot be proven is not bookable)."""

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
        """Create the event; return the provider's stable event ID.
        Return None ONLY when the provider itself refused/detected a conflict.
        Raises CalendarProviderError on transport/API/malformed response."""
