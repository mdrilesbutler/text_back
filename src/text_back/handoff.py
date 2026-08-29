from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import ClassVar, Protocol


@dataclass(frozen=True)
class HandoffAlert:
    destination: str
    caller: str
    business_number: str
    reason: str
    latest_message: str
    collected_fields: dict[str, str]
    summary: str


class HandoffNotifier(Protocol):
    provider_name: str

    def notify(self, alert: HandoffAlert) -> str:
        """Accept an operator alert payload and return its stable identifier."""


@dataclass
class FakeHandoffNotifier:
    """In-memory notifier for local work; it never contacts an operator."""

    provider_name: ClassVar[str] = "stub"
    alerts: list[HandoffAlert] = field(default_factory=list)

    def notify(self, alert: HandoffAlert) -> str:
        # Alert IDs key the durable handoff_deliveries outbox (file-backed
        # store), so they must stay unique across process restarts — a
        # process-local counter would collide with a previous life's rows
        # and silently drop a new lead's operator alert.
        self.alerts.append(alert)
        return f"handoff-{uuid.uuid4().hex}"


def build_handoff_summary(
    *,
    caller: str,
    reason: str,
    latest_message: str,
    collected_fields: dict[str, str],
) -> str:
    field_summary = ", ".join(
        f"{field}={collected_fields[field]}" for field in sorted(collected_fields)
    )
    if not field_summary:
        field_summary = "none"
    return (
        f"Handoff ({reason}) for {caller}. "
        f"Collected: {field_summary}. Latest message: {latest_message}"
    )
