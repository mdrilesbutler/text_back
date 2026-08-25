"""Bounded no-response follow-up sequence for the Recover journey.

Deterministic policy only: a sequence is scheduled after an accepted intro SMS
(with provider evidence), sends at most ``len(delays_minutes)`` follow-ups on a
fixed timetable, defers sends that land inside configured business quiet hours,
and cancels immediately on customer reply, opt-out, booking, active handoff, or
expiry. No live cron/queue/provider send lives here — ``run_due_followups`` is
a pure function of (store, telecom, policy, now) driven by an injected clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from text_back.store import Store
from text_back.telecom import Telecom


@dataclass(frozen=True)
class FollowupPolicy:
    delays_minutes: tuple[int, ...]
    expiry_minutes: int
    quiet_start: time
    quiet_end: time
    timezone_name: str

    def __post_init__(self) -> None:
        if not self.delays_minutes:
            raise ValueError("followup policy requires at least one delay")
        if any(delay <= 0 for delay in self.delays_minutes):
            raise ValueError("followup delays must be positive minutes")
        if self.expiry_minutes <= 0:
            raise ValueError("followup expiry must be positive minutes")
        try:
            ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError:
            raise ValueError(
                "followup policy timezone must be a valid IANA timezone"
            ) from None

    @property
    def max_attempts(self) -> int:
        return len(self.delays_minutes)

    @classmethod
    def from_config(cls, config) -> "FollowupPolicy":
        try:
            delays = tuple(
                int(part.strip())
                for part in config.followup_delays_minutes.split(",")
                if part.strip()
            )
        except ValueError:
            raise ValueError(
                "TEXT_BACK_FOLLOWUP_DELAYS_MINUTES must be comma-separated integers"
            ) from None
        return cls(
            delays_minutes=delays,
            expiry_minutes=int(config.followup_expiry_minutes),
            quiet_start=_parse_hhmm(config.quiet_hours_start, "TEXT_BACK_QUIET_HOURS_START"),
            quiet_end=_parse_hhmm(config.quiet_hours_end, "TEXT_BACK_QUIET_HOURS_END"),
            timezone_name=config.timezone_name,
        )


def _parse_hhmm(value: str, name: str) -> time:
    try:
        hour, minute = value.strip().split(":")
        return time(int(hour), int(minute))
    except (ValueError, AttributeError):
        raise ValueError(f"{name} must be HH:MM") from None


def _in_quiet_hours(local_time: time, start: time, end: time) -> bool:
    if start == end:
        return False
    if start < end:
        return start <= local_time < end
    # Overnight window (e.g. 21:00 -> 08:00).
    return local_time >= start or local_time < end


def next_allowed_send_time(at: datetime, policy: FollowupPolicy) -> datetime:
    """Return ``at`` unchanged when sending is allowed, else the next moment
    quiet hours end in the business timezone (converted back to UTC)."""
    zone = ZoneInfo(policy.timezone_name)
    local = at.astimezone(zone)
    if not _in_quiet_hours(local.time(), policy.quiet_start, policy.quiet_end):
        return at
    allowed_local = local.replace(
        hour=policy.quiet_end.hour,
        minute=policy.quiet_end.minute,
        second=0,
        microsecond=0,
    )
    if allowed_local <= local:
        allowed_local += timedelta(days=1)
    return allowed_local.astimezone(at.tzinfo)


def followup_sms(business_name: str, attempt: int) -> str:
    if attempt == 1:
        return (
            f"Hi again from {business_name}'s scheduling assistant—still happy "
            "to get you on the calendar. What job do you need done? "
            "Reply STOP to opt out."
        )
    return (
        f"Last check-in from {business_name}'s scheduling assistant. Reply with "
        "the job you need and we'll set a time, or call the business line. "
        "Reply STOP to opt out."
    )


def schedule_followup_sequence(
    *,
    store: Store,
    policy: FollowupPolicy,
    phone: str,
    call_sid: str,
    now: datetime,
) -> None:
    """Start (or restart, if no active sequence exists) the sequence for a lead
    whose intro SMS the provider just accepted."""
    first_due = now + timedelta(minutes=policy.delays_minutes[0])
    store.start_followup(
        phone=phone,
        call_sid=call_sid,
        next_action="followup",
        next_action_at=first_due.isoformat(),
    )


def cancel_followup(store: Store, phone: str, reason: str) -> bool:
    return store.cancel_followup(phone, reason)


def _cancel_reason_at_send_time(store: Store, phone: str) -> str | None:
    if store.is_opted_out(phone):
        return "opted_out"
    if store.active_handoff(phone) is not None:
        return "handoff_active"
    if store.appointment_by_conversation(phone) is not None:
        return "booked"
    return None


def run_due_followups(
    *,
    store: Store,
    telecom: Telecom,
    policy: FollowupPolicy,
    business_name: str,
    business_number: str,
    now: datetime,
) -> list[dict]:
    """Process every active sequence whose next action is due at ``now``.

    Pure scheduling seam: the caller owns the clock and invocation cadence.
    Re-running at the same instant is a no-op (idempotent via claim_event and
    the persisted next_action_at).
    """
    actions: list[dict] = []
    for sequence in store.due_followups(now.isoformat()):
        phone = sequence["phone"]
        cancel_reason = _cancel_reason_at_send_time(store, phone)
        if cancel_reason is not None:
            store.cancel_followup(phone, cancel_reason)
            actions.append(
                {"action": "followup_cancelled", "phone": phone, "reason": cancel_reason}
            )
            continue

        if sequence["next_action"] == "expire":
            if not store.expire_followup(phone):
                continue
            store.record_outcome(
                lead_id=phone,
                event_type="lead.expired",
                idempotency_key=f"followup:{sequence['call_sid']}:expired",
                evidence_id=sequence["call_sid"],
                metadata={"attempts_sent": sequence["attempts_sent"]},
            )
            actions.append({"action": "lead_expired", "phone": phone})
            continue

        allowed_at = next_allowed_send_time(now, policy)
        if allowed_at > now:
            store.defer_followup(phone, allowed_at.isoformat())
            actions.append(
                {
                    "action": "followup_deferred",
                    "phone": phone,
                    "deferred_to": allowed_at.isoformat(),
                }
            )
            continue

        attempt = sequence["attempts_sent"] + 1
        claim_key = f"{sequence['call_sid']}:attempt:{attempt}"
        if not store.claim_event("followup", claim_key, "send"):
            continue
        message_id = telecom.send_sms(
            to=phone,
            body=followup_sms(business_name, attempt),
            from_number=business_number,
            kind="followup",
        )
        store.record_outcome(
            lead_id=phone,
            event_type="followup.sent",
            idempotency_key=f"followup:{sequence['call_sid']}:sent:{attempt}",
            evidence_id=message_id,
            metadata={"attempt": attempt},
        )
        if attempt < policy.max_attempts:
            next_due = now + timedelta(minutes=policy.delays_minutes[attempt])
            store.advance_followup(
                phone,
                attempts_sent=attempt,
                next_action="followup",
                next_action_at=next_due.isoformat(),
            )
        else:
            expiry_due = now + timedelta(minutes=policy.expiry_minutes)
            store.advance_followup(
                phone,
                attempts_sent=attempt,
                next_action="expire",
                next_action_at=expiry_due.isoformat(),
            )
        actions.append(
            {"action": "followup_sent", "phone": phone, "attempt": attempt}
        )
    return actions
