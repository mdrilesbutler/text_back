"""Add-to-calendar links for a confirmed appointment.

The confirmation text carries three short links on our own host:
/a/<ref>/g (Google), /a/<ref>/o (Outlook) and /a/<ref>/i (an .ics file for
Apple Calendar and everything else). /a/<ref> is a small page with the same
three buttons. <ref> is the appointment row plus an HMAC of its calendar
event id, so links cannot be guessed and never expose the phone number.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

from fastapi import HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response

SIG_CHARS = 12


@dataclass(frozen=True)
class CalendarLinks:
    base_url: str
    secret: str

    def _sig(self, event_id: str) -> str:
        return hmac.new(self.secret.encode(), ("calendar-link:" + event_id).encode(), hashlib.sha256).hexdigest()[:SIG_CHARS]

    def ref(self, rowid: int, event_id: str) -> str:
        return f"{rowid}-{self._sig(event_id)}"

    def valid(self, ref: str, event_id: str) -> bool:
        parts = ref.split("-", 1)
        return len(parts) == 2 and hmac.compare_digest(parts[1], self._sig(event_id))

    def urls(self, rowid: int, event_id: str) -> dict[str, str]:
        root = f"{self.base_url.rstrip('/')}/a/{self.ref(rowid, event_id)}"
        return {"links_page": root, "google_link": root + "/g", "outlook_link": root + "/o", "ical_link": root + "/i"}

    @staticmethod
    def sms_line(urls: dict[str, str]) -> str:
        return f"Add to calendar: Google {urls['google_link']} Outlook {urls['outlook_link']} iCal {urls['ical_link']}"


def links_for_appointment(store, appointment: dict) -> dict[str, str]:
    """Placeholder values for the confirmation template ({calendar_links} etc.)."""
    links = getattr(store, "calendar_links", None)
    if links is None:
        return {"calendar_links": "", "links_page": "", "google_link": "", "outlook_link": "", "ical_link": ""}
    row = store.conn.execute("SELECT rowid FROM appointments WHERE event_id=?", (appointment["event_id"],)).fetchone()
    if row is None:
        return {"calendar_links": "", "links_page": "", "google_link": "", "outlook_link": "", "ical_link": ""}
    urls = links.urls(row[0], appointment["event_id"])
    return {"calendar_links": CalendarLinks.sms_line(urls), **urls}


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _stamp(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%SZ")


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    out, chunk = [], line.encode("utf-8")
    while len(chunk) > 73:
        cut = 73
        while cut > 0 and (chunk[cut] & 0xC0) == 0x80:  # don't split a UTF-8 sequence
            cut -= 1
        out.append(chunk[:cut].decode("utf-8")); chunk = b" " + chunk[cut:]
    out.append(chunk.decode("utf-8"))
    return "\r\n".join(out)


def build_ics(*, event_id: str, summary: str, location: str, description: str, start: datetime, end: datetime, stamp: datetime) -> str:
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//text_back//Recover//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{_ics_escape(event_id)}@text-back",
        f"DTSTAMP:{_stamp(stamp)}", f"DTSTART:{_stamp(start)}", f"DTEND:{_stamp(end)}",
        f"SUMMARY:{_ics_escape(summary)}", f"LOCATION:{_ics_escape(location)}", f"DESCRIPTION:{_ics_escape(description)}",
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def install_routes(app):
    state = app.state

    def lookup(ref: str) -> dict:
        match = re.fullmatch(r"(\d{1,12})-([0-9a-f]{%d})" % SIG_CHARS, ref)
        links = getattr(state.store, "calendar_links", None)
        if not match or links is None:
            raise HTTPException(404, "Unknown appointment link")
        with state.store.lock:
            row = state.store.conn.execute("SELECT * FROM appointments WHERE rowid=?", (int(match.group(1)),)).fetchone()
        if row is None or not links.valid(ref, row["event_id"]):
            raise HTTPException(404, "Unknown appointment link")
        appointment = dict(row)
        start = _utc(appointment["start"])
        appointment["start_utc"] = start
        stored_end = appointment.get("end")
        appointment["end_utc"] = _utc(stored_end) if stored_end else start + timedelta(minutes=state.appointment_duration_minutes)
        appointment["summary"] = f"{state.business_name}: {appointment['service']}"
        appointment["description"] = f"Booked by text with {state.business_name}'s scheduling assistant."
        return appointment

    headers = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Robots-Tag": "noindex"}

    @app.get("/a/{ref}/g", include_in_schema=False)
    def google(ref: str):
        a = lookup(ref)
        query = urlencode({"action": "TEMPLATE", "text": a["summary"], "dates": f"{_stamp(a['start_utc'])}/{_stamp(a['end_utc'])}",
                           "location": a["location"], "details": a["description"]})
        return RedirectResponse("https://calendar.google.com/calendar/render?" + query, status_code=302, headers=headers)

    @app.get("/a/{ref}/o", include_in_schema=False)
    def outlook(ref: str):
        a = lookup(ref)
        query = urlencode({"path": "/calendar/action/compose", "rru": "addevent", "subject": a["summary"],
                           "startdt": a["start_utc"].strftime("%Y-%m-%dT%H:%M:%SZ"), "enddt": a["end_utc"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "location": a["location"], "body": a["description"]})
        return RedirectResponse("https://outlook.live.com/calendar/0/deeplink/compose?" + query, status_code=302, headers=headers)

    @app.get("/a/{ref}/i", include_in_schema=False)
    def ical(ref: str):
        a = lookup(ref)
        now = state.now_provider() if state.now_provider else datetime.now(timezone.utc)
        body = build_ics(event_id=a["event_id"], summary=a["summary"], location=a["location"], description=a["description"],
                         start=a["start_utc"], end=a["end_utc"], stamp=now.astimezone(timezone.utc))
        return Response(body, media_type="text/calendar; charset=utf-8",
                        headers={**headers, "Content-Disposition": 'attachment; filename="appointment.ics"'})

    @app.get("/a/{ref}", include_in_schema=False)
    def page(ref: str):
        a = lookup(ref)
        local = a["start_utc"].astimezone(datetime.fromisoformat(a["start"]).tzinfo or timezone.utc)
        when = local.strftime("%A, %b %d at %I:%M %p").replace(" 0", " ")
        root = f"/a/{quote(ref)}"
        doc = (
            "<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Add to calendar</title><style>body{{font:18px/1.5 system-ui,sans-serif;max-width:30rem;margin:8vh auto;padding:24px;color:#18212b;background:#f6f8fa}}"
            "a.b{display:block;text-align:center;padding:14px;margin:12px 0;border-radius:8px;background:#1b5e9e;color:#fff;text-decoration:none;font-weight:600}</style></head>"
            f"<body><main><h1>{html.escape(a['summary'])}</h1><p>{html.escape(when)}<br>{html.escape(a['location'])}</p>"
            f"<a class=b href='{root}/g'>Add to Google Calendar</a><a class=b href='{root}/o'>Add to Outlook</a>"
            f"<a class=b href='{root}/i'>Download for Apple Calendar (.ics)</a></main></body></html>"
        )
        return HTMLResponse(doc, headers=headers)
