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

    sends_invites: bool = False

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
        """Create the event; return the provider's stable event ID.
        attendee_email, when given and the provider supports invitations
        (``sends_invites``), is added as a guest so the provider emails an invite.
        Return None ONLY when the provider itself refused/detected a conflict.
        Raises CalendarProviderError on transport/API/malformed response."""
