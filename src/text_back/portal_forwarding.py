"""The five forwarding checks on the Phone page, ticked only from recorded evidence.

Checks 1, 2 and 4 come from the most recent call the carrier forwarded from the business
line (call.missed metadata.forwarded_from). Check 2 counts the first texts sent to that caller in
the ten minutes after the call, across call_sids, so a number forwarded twice shows up. A direct call to the texting number never ticks
them. Checks 3 and 5 are the owner's own ticks and always read "You checked this".
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from text_back.portal_dates import when

DONE, NOT_YET, YOU_CHECKED = "done", "not_yet", "you_checked"
STATE_WORDS = {DONE: "Done", NOT_YET: "Not yet", YOU_CHECKED: "You checked this"}
MANUAL = {3: "answered_no_text", 5: "deactivation_saved"}
LABELS = {  # copy deck, section 7 (check_1..check_5)
    1: "A call to your business number reached TextBack",
    2: "Exactly one text went out",
    3: "An answered call sent no text",
    4: "The caller's own number came through",
    5: "You saved the turn-off code",
}


def _digits(number: str | None) -> str:
    return "".join(ch for ch in (number or "") if ch.isdigit())[-10:]


def _last4(number: str) -> str:
    return "…" + _digits(number)[-4:]


def forwarded_call(store, business_line: str) -> dict | None:
    """The newest call.missed whose carrier ForwardedFrom equals the business line, or None."""
    want = _digits(business_line)
    if not want:
        return None
    with store.lock:
        rows = store.conn.execute(
            "SELECT lead_id, evidence_id, occurred_at, metadata_json FROM outcome_events "
            "WHERE event_type='call.missed' ORDER BY id DESC LIMIT 200").fetchall()
    for row in rows:
        try:
            meta = json.loads(row["metadata_json"] or "{}")
        except ValueError:
            continue
        if _digits(meta.get("forwarded_from")) == want:
            return {"caller": row["lead_id"], "call_sid": row["evidence_id"], "at": row["occurred_at"]}
    return None


FIRST_TEXT_WINDOW = timedelta(minutes=10)


def texts_sent_for(store, call: dict) -> tuple[int, str | None]:
    """How many first texts went out to this call's caller in the 10 minutes after the call
    (any call_sid, so a second leg of the same call counts), and when the first one did.

    Reminders are not first texts and never count; a later call outside the window is a
    separate call."""
    start = _parse(call["at"])
    if start is None:
        return 0, None
    end = start + FIRST_TEXT_WINDOW
    with store.lock:
        rows = store.conn.execute(
            "SELECT key, created_at FROM sms_outbox WHERE kind='missed_call_intro' AND status='sent' AND phone=?",
            (call["caller"],)).fetchall()
        sent = sorted((at, row["key"]) for row in rows if (at := _parse(row["created_at"])) and start <= at <= end)
        if not sent:
            return 0, None
        first_key = sent[0][1]
        call_sid = first_key[: -len(":intro")] if first_key.endswith(":intro") else first_key
        initial = store.conn.execute(
            "SELECT occurred_at FROM outcome_events WHERE event_type='sms.initial_sent' AND idempotency_key=?",
            (f"call:{call_sid}:initial_sms",)).fetchone()
    return len(sent), (initial["occurred_at"] if initial else sent[0][0].isoformat())


def _parse(stamp: str | None) -> datetime | None:
    if not stamp:
        return None
    try:
        value = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def manual_ticks(store) -> dict:
    try:
        ticks = json.loads(store.setting("forwarding_checklist") or "{}")
    except ValueError:
        ticks = {}
    return ticks if isinstance(ticks, dict) else {}


def save_manual_ticks(store, ticks: dict[str, bool], now: datetime) -> None:
    current = manual_ticks(store)
    for name in MANUAL.values():
        if name in ticks:
            current[name] = now.isoformat() if ticks[name] else None
    store.set_setting("forwarding_checklist", json.dumps({k: v for k, v in current.items() if v}), now=now)


def checklist(state, now: datetime) -> dict:
    store = state.store
    tz = getattr(state, "timezone_name", "UTC")
    business_line = store.setting("business_line") or ""
    texting = getattr(state, "business_number", "") or ""
    call = forwarded_call(store, business_line)
    ticks = manual_ticks(store)

    def step(n, state_key, evidence):
        return {"n": n, "label": LABELS[n], "state": state_key, "state_word": STATE_WORDS[state_key],
                "manual": n in MANUAL, "evidence": evidence}

    steps = []
    if call:
        steps.append(step(1, DONE, f"A forwarded call came in {when(call['at'], tz, now)} from a caller ending {_last4(call['caller'])[1:]}."))
        count, first_at = texts_sent_for(store, call)
        if count == 1:
            steps.append(step(2, DONE, f"Sent {when(first_at, tz, now)}."))
        elif count > 1:
            steps.append(step(2, NOT_YET, f"{count} texts went out for one call. Check that the number isn't forwarded twice."))
        else:
            steps.append(step(2, NOT_YET, "No text went out for that call yet."))
    else:
        if not _digits(business_line):
            steps.append(step(1, NOT_YET, "Enter your business number first."))
        else:
            steps.append(step(1, NOT_YET, "No forwarded call recorded yet. Call your business number from another phone and let it ring."))
        steps.append(step(2, NOT_YET, "Waits for check 1."))
    steps.append(step(3, YOU_CHECKED if ticks.get(MANUAL[3]) else NOT_YET,
                      f"Ticked {when(ticks[MANUAL[3]], tz, now)}." if ticks.get(MANUAL[3]) else "Call again and answer it. No text should go out."))
    if call:
        caller_ok = _digits(call["caller"]) not in {_digits(business_line), _digits(texting)}
        steps.append(step(4, DONE if caller_ok else NOT_YET,
                          f"The text went to the caller's number ending {_last4(call['caller'])[1:]}, not your business number or the texting number."
                          if caller_ok else "The call came in as your own number. Ask your carrier about caller ID on forwarded calls."))
    else:
        steps.append(step(4, NOT_YET, "Enter your business number first." if not _digits(business_line) else "Waits for check 1."))
    steps.append(step(5, YOU_CHECKED if ticks.get(MANUAL[5]) else NOT_YET,
                      f"Ticked {when(ticks[MANUAL[5]], tz, now)}." if ticks.get(MANUAL[5]) else "Write the turn-off code down somewhere you'll find it."))
    done = sum(1 for s in steps if s["state"] in (DONE, YOU_CHECKED))
    return {"steps": steps, "done_count": done, "total": len(steps), "all_done": done == len(steps),
            "state_word": "Done" if done == len(steps) else "Needs you"}
