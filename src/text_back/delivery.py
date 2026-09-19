"""Durable outbox + safe transports for operator handoff alerts.

Michael has not chosen a live notifier channel; NO live destination exists
here. 'disabled' (default) parks rows durably; 'log' writes to the process
log; the in-memory transport is for tests. ``run_due_deliveries`` is a pure
function of (store, transport, policy, injected now) — no cron, queue, or
network. Operator alerts are time-critical: quiet hours deliberately do not
apply (quiet hours protect customer SMS in the nurture lane only).

Semantics: at-least-once to the operator, exactly-once in the ledger. Each
attempt is persisted (attempt count + next backoff) BEFORE the transport is
called, so a crash mid-delivery leaves the row pending and re-runnable at its
next_attempt_at instead of wedged. A crash between transport success and the
status flip may re-ping the operator on the next run, but the
``handoff.alert_delivered`` idempotency key carries no attempt number, so the
ledger cannot double-append.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import ClassVar, Protocol

from text_back.handoff import HandoffAlert
from text_back.store import Store


class DeliveryError(RuntimeError):
    """A transport failed to accept an alert; the runner may retry."""


class DeliveryTransport(Protocol):
    channel_name: str

    def deliver(self, alert: HandoffAlert) -> str:
        """Accept the alert and return a stable receipt identifier."""


@dataclass
class DisabledTransport:
    """Durable parking: rows enqueue and stay pending until a channel exists."""

    channel_name: ClassVar[str] = "disabled"

    def deliver(self, alert: HandoffAlert) -> str:
        raise DeliveryError("disabled transport never delivers")


@dataclass
class LogTransport:
    """Writes the operator summary to the process log. No network."""

    channel_name: ClassVar[str] = "log"

    def deliver(self, alert: HandoffAlert) -> str:
        # No customer content or full phone number in the process log: logs
        # outlive the store's PII boundary (rotation, shared infra, backups).
        # The full summary stays retrievable from handoff_deliveries.payload_json.
        digest = hashlib.sha256(alert_payload_json(alert).encode()).hexdigest()[:16]
        logging.getLogger("text_back.delivery").info(
            "HANDOFF ALERT for %s: reason=%s caller=***%s receipt=log-%s",
            alert.destination,
            alert.reason,
            alert.caller[-4:],
            digest,
        )
        return f"log-{digest}"


@dataclass
class InMemoryDeliveryTransport:
    """Test transport; optionally fails the first ``fail_times`` attempts."""

    channel_name: ClassVar[str] = "memory"
    fail_times: int = 0
    delivered: list[HandoffAlert] = field(default_factory=list)
    attempts: int = 0

    def deliver(self, alert: HandoffAlert) -> str:
        self.attempts += 1
        if self.attempts <= self.fail_times:
            raise DeliveryError("simulated transport failure")
        self.delivered.append(alert)
        return f"mem-{len(self.delivered):04d}"


@dataclass(frozen=True)
class DeliveryPolicy:
    retry_minutes: tuple[int, ...]

    def __post_init__(self) -> None:
        if any(
            not isinstance(minutes, int) or minutes <= 0
            for minutes in self.retry_minutes
        ):
            raise ValueError("delivery retry minutes must be positive integers")

    @property
    def max_attempts(self) -> int:
        # Backoff AFTER attempt n lives at index n-1; an empty schedule means
        # exactly one attempt, then dead-letter.
        return len(self.retry_minutes) + 1

    @classmethod
    def from_config(cls, config) -> "DeliveryPolicy":
        try:
            retry_minutes = tuple(
                int(part.strip())
                for part in config.handoff_delivery_retry_minutes.split(",")
                if part.strip()
            )
        except ValueError:
            raise ValueError(
                "TEXT_BACK_HANDOFF_DELIVERY_RETRY_MINUTES must be "
                "comma-separated integers"
            ) from None
        return cls(retry_minutes=retry_minutes)


def transport_from_config(config) -> DeliveryTransport:
    # 'memory' is injection-only (like FakeTelecom vs env), never env-selectable.
    if config.handoff_delivery_channel == "disabled":
        return DisabledTransport()
    if config.handoff_delivery_channel == "log":
        return LogTransport()
    raise ValueError(
        "invalid TEXT_BACK_HANDOFF_DELIVERY_CHANNEL; must be 'disabled' or 'log'"
    )


def alert_payload_json(alert: HandoffAlert) -> str:
    return json.dumps(
        dataclasses.asdict(alert), sort_keys=True, separators=(",", ":")
    )


def alert_from_payload_json(payload_json: str) -> HandoffAlert:
    return HandoffAlert(**json.loads(payload_json))


def enqueue_handoff_alert(
    *, store: Store, alert: HandoffAlert, alert_id: str, now: datetime
) -> bool:
    """Enqueue exactly once per handoff activation; due immediately."""
    return store.enqueue_handoff_delivery(
        alert_id=alert_id,
        phone=alert.caller,
        payload_json=alert_payload_json(alert),
        next_attempt_at=now.isoformat(),
    )


def _dead_letter(
    *,
    store: Store,
    transport: DeliveryTransport,
    alert_id: str,
    phone: str,
    attempts: int,
    last_error: str,
    now: datetime,
) -> None:
    # Ledger BEFORE the status flip, mirroring the delivered path: a crash
    # between the two re-runs this branch, and the UNIQUE idempotency key
    # blocks a duplicate ledger row. Flipping status first could lose the
    # dead-letter evidence forever.
    store.record_outcome(
        lead_id=phone,
        event_type="handoff.alert_dead_lettered",
        idempotency_key=f"handoff_delivery:{alert_id}:dead_letter",
        evidence_id=alert_id,
        metadata={
            "channel": transport.channel_name,
            "attempts": attempts,
            "last_error": last_error[:200],
        },
        occurred_at=now.isoformat(),
    )
    store.dead_letter_handoff_delivery(
        alert_id, attempts=attempts, last_error=last_error
    )


def run_due_deliveries(
    *,
    store: Store,
    transport: DeliveryTransport,
    policy: DeliveryPolicy,
    now: datetime,
) -> list[dict]:
    """Process every pending delivery due at ``now``.

    Pure scheduling seam: the caller owns the clock and invocation cadence.
    The disabled channel parks rows durably without burning attempts.
    """
    if transport.channel_name == "disabled":
        return []
    actions: list[dict] = []
    for row in store.due_handoff_deliveries(now.isoformat()):
        alert_id = row["alert_id"]
        attempt = row["attempts"] + 1
        if attempt > policy.max_attempts:
            # A crash during the final attempt persisted the bump but not the
            # outcome. The schedule is exhausted: dead-letter with evidence
            # (ledger first) so monitoring sees the abandoned alert.
            last_error = row["last_error"] or "attempt interrupted before completion"
            _dead_letter(
                store=store,
                transport=transport,
                alert_id=alert_id,
                phone=row["phone"],
                attempts=row["attempts"],
                last_error=last_error,
                now=now,
            )
            actions.append(
                {
                    "action": "delivery_dead_lettered",
                    "alert_id": alert_id,
                    "attempts": row["attempts"],
                }
            )
            continue
        # Persist the attempt bump (and the next backoff slot) BEFORE the
        # transport call. A crash mid-delivery then re-runs as attempt N+1
        # at next_attempt_at with a fresh row state — never a wedged claim.
        # The optimistic WHERE (status='pending' AND attempts=N) also makes a
        # same-instant rerun of an in-flight attempt skip the row.
        if attempt < policy.max_attempts:
            next_at_iso = (
                now + timedelta(minutes=policy.retry_minutes[attempt - 1])
            ).isoformat()
        else:
            # Final attempt still needs a lease: concurrent workers must not
            # dead-letter an in-flight send. After a minute an interrupted
            # final attempt can be dead-lettered with evidence.
            next_at_iso = (now + timedelta(minutes=1)).isoformat()
        if not store.begin_handoff_delivery_attempt(
            alert_id, attempts=attempt, next_attempt_at=next_at_iso
        ):
            continue
        try:
            alert = alert_from_payload_json(row["payload_json"])
            receipt_id = transport.deliver(alert)
        except Exception as exc:  # noqa: BLE001 - a transport bug must never
            # wedge this row or abort the remaining due rows.
            if attempt >= policy.max_attempts:
                _dead_letter(
                    store=store,
                    transport=transport,
                    alert_id=alert_id,
                    phone=row["phone"],
                    attempts=attempt,
                    last_error=str(exc),
                    now=now,
                )
                actions.append(
                    {
                        "action": "delivery_dead_lettered",
                        "alert_id": alert_id,
                        "attempts": attempt,
                    }
                )
            else:
                # attempts and next_attempt_at were already persisted by
                # begin_handoff_delivery_attempt; this records the error.
                store.retry_handoff_delivery(
                    alert_id,
                    attempts=attempt,
                    next_attempt_at=next_at_iso,
                    last_error=str(exc),
                )
                actions.append(
                    {
                        "action": "delivery_retry_scheduled",
                        "alert_id": alert_id,
                        "attempt": attempt,
                        "next_attempt_at": next_at_iso,
                    }
                )
            continue
        # Ledger BEFORE the status flip: a crash between the two re-delivers
        # (at-least-once), but the UNIQUE key blocks a double ledger row.
        store.record_outcome(
            lead_id=row["phone"],
            event_type="handoff.alert_delivered",
            idempotency_key=f"handoff_delivery:{alert_id}:delivered",
            evidence_id=receipt_id,
            metadata={"channel": transport.channel_name, "attempt": attempt},
            occurred_at=now.isoformat(),
        )
        store.mark_handoff_delivery_delivered(
            alert_id, attempts=attempt, receipt_id=receipt_id
        )
        actions.append(
            {
                "action": "alert_delivered",
                "alert_id": alert_id,
                "receipt_id": receipt_id,
                "attempt": attempt,
            }
        )
    return actions
