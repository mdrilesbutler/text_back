from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from text_back.calendars.transport import rfc3339_utc

"""Deterministic, provider-side idempotency identifiers.

All three IDs are pure functions of (conversation_id, slot start): a retried
booking attempt for the SAME slot regenerates the identical ID, so a duplicate
create is detected by the provider itself, while a later booking for a
DIFFERENT slot in the same conversation can never collide with the first
event. The first dedupe line remains store.appointment_by_conversation; these
cover the crash window between create_event success and save_appointment
(handlers re-attempt booking when fields are complete but no appointment is
saved). Adapters additionally verify a provider duplicate signal against the
requested slot before treating it as success — never confirm against an event
that does not match the promised time.
"""


def _digest(conversation_id: str, start: datetime) -> str:
    key = f"{conversation_id}|{rfc3339_utc(start)}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def google_event_id(conversation_id: str, start: datetime) -> str:
    # hex alphabet is a subset of Google's allowed base32hex charset [0-9a-v];
    # length 42 is within Google's [5, 1024] bounds.
    return "tb" + _digest(conversation_id, start)[:40]


def ms_transaction_id(conversation_id: str, start: datetime) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"text-back:{conversation_id}|{rfc3339_utc(start)}",
        )
    )


def icloud_uid(conversation_id: str, start: datetime) -> str:
    return f"tb-{_digest(conversation_id, start)[:32]}@text-back.invalid"


def ics_escape(text: str) -> str:
    """RFC 5545 TEXT escaping: backslash, semicolon, comma, newline."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )
