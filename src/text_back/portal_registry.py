"""Texting approval for the owner portal: is the business cleared to text?

The state comes, in order, from the telecom's read-only registry lookup
(cached on the app state for ten minutes; a failed or unreadable lookup only for
a minute), from a stored setting, or is unknown. A stage the phone companies
turned down reads "needs_attention". Only the words in ``approval_words`` are meant for a screen; they
never name a vendor or the approval paperwork.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

CACHE_ATTR = "_texting_approval_cache"
CACHE_TTL = timedelta(minutes=10)
FAILURE_CACHE_TTL = timedelta(seconds=60)
SETTING_KEY = "texting_approval_state"
STATES = ("approved", "waiting", "not_started", "needs_attention", "unknown")

_APPROVED_WORDS = frozenset({"approved", "complete", "completed", "active", "verified", "registered"})
_WAITING_WORDS = frozenset({"pending", "in_review", "in-review", "submitted", "processing", "vetting",
                            "under_review", "review", "queued", "created"})
_FAILED_WORDS = frozenset({"rejected", "failed", "denied", "suspended", "expired", "deactivated",
                           "cancelled", "canceled"})


def _turned_down(stage: str | None) -> bool:
    """A stage word that is, or contains as a part (``vetting_failed``), a turned-down word."""
    return bool(stage) and (stage in _FAILED_WORDS or any(part in _FAILED_WORDS for part in re.split(r"[^a-z]+", stage)))


def _normalize(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def map_registry(registry: dict) -> str:
    """Collapse the per-stage registry words into one portal state."""
    stages = [_normalize(registry.get(stage)) for stage in ("brand", "campaign", "numbers")]
    if all(stage is None for stage in stages):
        return "not_started"
    if any(_turned_down(stage) for stage in stages):
        return "needs_attention"
    if all(stage in _APPROVED_WORDS for stage in stages):
        return "approved"
    if any(stage in _WAITING_WORDS for stage in stages):
        return "waiting"
    # Partly done (a stage approved, the next not yet filed) or a word we do not
    # know: the owner has nothing to do either way, so it reads as waiting.
    return "waiting" if any(stage in _APPROVED_WORDS for stage in stages) else "unknown"


def _cached(state, now: datetime) -> dict | None:
    cached = getattr(state, CACHE_ATTR, None)
    if not cached:
        return None
    checked_at = cached["checked_at"]
    ttl = FAILURE_CACHE_TTL if cached.get("state") == "unknown" else CACHE_TTL
    if checked_at is None or now < checked_at or now - checked_at >= ttl:
        return None
    return dict(cached)


def texting_approval(state, now: datetime) -> dict:
    """``{"state": ..., "checked_at": datetime | None, "source": ...}``.

    Sources: ``registry`` (the telecom looked it up, result cached ten minutes, or 60
    seconds when the lookup failed or returned words we do not know),
    ``setting`` (``store.setting("texting_approval_state")``), ``none``.
    """
    lookup = getattr(getattr(state, "telecom", None), "registry_status", None)
    if callable(lookup):
        cached = _cached(state, now)
        if cached is not None:
            return cached
        try:
            word = map_registry(lookup() or {})
        except Exception as exc:  # a status page must never fail because the registry did
            log.warning("texting approval lookup failed: %s", type(exc).__name__)
            word = "unknown"
        result = {"state": word, "checked_at": now, "source": "registry"}
        try:
            setattr(state, CACHE_ATTR, dict(result))
        except AttributeError:
            pass
        return result
    store = getattr(state, "store", None)
    saved = store.setting(SETTING_KEY) if store is not None and hasattr(store, "setting") else None
    if saved in STATES:
        return {"state": saved, "checked_at": None, "source": "setting"}
    return {"state": "unknown", "checked_at": None, "source": "none"}


def network_notice_applies(state, now: datetime) -> bool:
    """Each text starts with a short network notice until the approval is through."""
    return texting_approval(state, now)["state"] != "approved"


_WORDS: dict[str, tuple[str, str]] = {
    "approved": ("Done", "The phone companies have approved your business for texting."),
    "waiting": ("Waiting on phone companies",
                "Your texting approval is with the phone companies and texts still go out with a short network notice until it clears."),
    "not_started": ("Not started",
                    "Texting approval has not been requested yet and texts still go out with a short network notice."),
    "needs_attention": ("Needs you",
                        "Phone companies turned down the texting approval. FluxWorks is fixing it; "
                        "text FluxWorks support if texts aren't going out."),
    "unknown": ("Couldn't check", "TextBack couldn't check texting approval just now. It will try again soon."),
}


def approval_words(result: dict) -> dict:
    """The state word and one plain sentence for the Home setup card."""
    state_word, detail = _WORDS.get(result.get("state"), _WORDS["unknown"])
    return {"state_word": state_word, "detail": detail}
