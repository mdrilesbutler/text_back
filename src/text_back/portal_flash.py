"""One-time save notices for the owner portal (post / redirect / get).

A portal POST that succeeds answers 303 to its page's GET with a short-lived cookie that holds
a notice id and a few safe params (setting keys, a count, an on/off flag), never text. The cookie
is HMAC-signed with the app secret and bound to the signed-in session, so it can't be forged,
moved to another session or carry words of its own. The GET renders the words server-side from
the id (``flash_text``) and deletes the cookie, so a reload or Back never shows the notice again
and never re-posts the form. A rejected save never redirects: it answers in place so the typed
text is kept.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import timedelta

FLASH_COOKIE = "tb_flash"
FLASH_TTL = timedelta(minutes=2)


def _mac(state, session: dict, body: str) -> str:
    key = str(state.webhook_secret).encode()
    message = f"client-flash:{session['token_hash']}:{body}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def encode(state, session: dict, page: str, notice_id: str, params: dict | None = None) -> str:
    body = base64.urlsafe_b64encode(json.dumps({"p": page, "id": notice_id, "a": params or {}},
                                               separators=(",", ":")).encode()).decode().rstrip("=")
    return f"{body}.{_mac(state, session, body)}"


def decode(state, session: dict, raw: str) -> dict | None:
    """The payload {"p", "id", "a"} when ``raw`` is a cookie this session was given, else None."""
    body, _, mac = (raw or "").partition(".")
    if not body or not mac or not hmac.compare_digest(mac, _mac(state, session, body)):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except (ValueError, TypeError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("a"), dict):
        return None
    return payload


def set_flash(response, state, session: dict, page: str, notice_id: str, params: dict | None = None,
              *, secure: bool) -> None:
    response.set_cookie(FLASH_COOKIE, encode(state, session, page, notice_id, params), secure=secure, httponly=True,
                        samesite="lax", max_age=int(FLASH_TTL.total_seconds()), path="/client")


def take(state, request, session: dict, page: str) -> str:
    """The notice words for ``page`` from the request's flash cookie, or ''."""
    payload = decode(state, session, request.cookies.get(FLASH_COOKIE, ""))
    if not payload or payload.get("p") != page:
        return ""
    return flash_text(state, str(payload.get("id", "")), payload["a"]) or ""


def clear(request, response):
    """Delete a presented flash cookie: the notice shows once, whichever page it was for."""
    if request.cookies.get(FLASH_COOKIE):
        response.delete_cookie(FLASH_COOKIE, path="/client")
    return response


def _keys(params: dict, name: str, allowed) -> list[str]:
    value = params.get(name)
    return [key for key in value if isinstance(key, str) and key in allowed] if isinstance(value, list) else []


def flash_text(state, notice_id: str, params: dict) -> str | None:
    """The words for one notice id. Params are only ever looked up (keys, counts, flags), never shown."""
    from text_back import portal_calendar, portal_messages, portal_phone, portal_scheduling
    from text_back.policy import format_contact_number

    if notice_id == "discarded":
        return portal_messages.DISCARDED
    if notice_id == "messages_saved":
        return portal_messages.saved_text(
            changed=_keys(params, "changed", portal_messages.MESSAGES), back=_keys(params, "back", portal_messages.MESSAGES),
            on=_keys(params, "on", ("phone", "email")), off=_keys(params, "off", ("phone", "email")))
    if notice_id == "schedule_saved":
        return portal_scheduling.saved_text(_keys(params, "rules", portal_scheduling.LABELS))
    if notice_id == "phone_saved":
        checks = params.get("checks") if isinstance(params.get("checks"), list) else []
        from text_back import portal_forwarding
        ticks = portal_forwarding.manual_ticks(state.store)
        return portal_phone.saved_text(_keys(params, "fields", portal_phone.LABELS),
                                       [n for n in checks if isinstance(n, int) and n in portal_phone.MANUAL_CHECKS],
                                       checks_reset=params.get("reset") is True,
                                       ticked={n: bool(ticks.get(key)) for n, key in portal_phone.MANUAL_CHECKS.items()})
    if notice_id == "mobile_code_sent":
        pending = portal_phone.pending_mobile(state)
        return portal_phone.CODE_SENT.format(n=format_contact_number(pending)) if pending else None
    if notice_id == "mobile_confirmed":
        owner = getattr(state, "owner_mobile", "") or ""
        return portal_phone.NEW_MOBILE_SAVED.format(n=format_contact_number(owner)) if owner else None
    if notice_id == "mobile_kept":
        return portal_phone.KEPT
    if notice_id == "checks_saved":
        return portal_phone.CHECKS_SAVED
    if notice_id in ("renamed", "texts_kept"):
        count = params.get("n")
        if not isinstance(count, int) or count < 1:
            return None
        return portal_phone.rename_done_text(count) if notice_id == "renamed" else portal_phone.rename_kept_text(count)
    if notice_id == "calendar_picked":
        from text_back.client_settings import calendar_choices
        names = {entry["id"]: entry.get("summary") or entry["id"] for entry in calendar_choices(state)}
        chosen = params.get("id")
        return portal_calendar.TOAST_PICKED.format(name=names[chosen]) if chosen in names else None
    if notice_id == "remember":
        from text_back.client_portal import REMEMBER_SAVED_OFF, REMEMBER_SAVED_ON
        return REMEMBER_SAVED_ON if params.get("on") is True else REMEMBER_SAVED_OFF
    return None
