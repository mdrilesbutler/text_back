"""Add-to-calendar links in the confirmation text and the /a/<ref> routes."""
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.calendar_links import CalendarLinks, build_ics
from text_back.calendar_stub import CalendarStub
from text_back.handlers import handle_sms_event
from text_back.telecom import FakeTelecom

NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
BASE = "https://example.test"


def booked_app(tmp_path):
    telecom = FakeTelecom()
    calendar = CalendarStub(timezone_name="America/New_York")
    app = create_app(db_path=str(tmp_path / "links.db"), calendar=calendar, telecom=telecom, public_base_url=BASE,
                     business_name="Oak & Pine Tree Care", timezone_name="America/New_York", now_provider=lambda: NOW)
    for i, body in enumerate(["tree trimming, two oaks", "12 Oak St, Charlotte", "thursday at 4", "Pat Lee"]):
        handle_sms_event(store=app.state.store, calendar=calendar, telecom=telecom, handoff_notifier=app.state.handoff_notifier,
                         handoff_destination="ops", message_sid=f"m{i}", from_number="+15551112222", to_number="+15553334444",
                         body=body, business_name="Oak & Pine Tree Care", timezone_name="America/New_York",
                         appointment_duration_minutes=60, now=NOW)
    return TestClient(app, base_url=BASE), telecom, app


def test_confirmation_text_carries_three_short_links_on_our_host(tmp_path):
    client, telecom, app = booked_app(tmp_path)
    confirmation = [m for m in telecom.outbound if m.kind == "booking_confirmation"][-1].body
    assert "Add to calendar: Google https://example.test/a/" in confirmation
    assert " Outlook https://example.test/a/" in confirmation and " iCal https://example.test/a/" in confirmation
    assert "+1555" not in confirmation  # links never expose the phone number
    ref = confirmation.split("/a/")[1].split("/")[0]
    assert ref.split("-")[0].isdigit() and len(ref.split("-")[1]) == 12

    google = client.get(f"/a/{ref}/g", follow_redirects=False)
    assert google.status_code == 302
    q = parse_qs(urlsplit(google.headers["location"]).query)
    assert urlsplit(google.headers["location"]).netloc == "calendar.google.com"
    assert q["text"] == ["Oak & Pine Tree Care: tree trimming, two oaks"]
    assert q["dates"] == ["20261022T200000Z/20261022T210000Z"]  # Thu Oct 22 4 PM EDT
    assert q["location"] == ["12 Oak St, Charlotte"]

    outlook = client.get(f"/a/{ref}/o", follow_redirects=False)
    q = parse_qs(urlsplit(outlook.headers["location"]).query)
    assert urlsplit(outlook.headers["location"]).netloc == "outlook.live.com"
    assert q["startdt"] == ["2026-10-22T20:00:00Z"] and q["enddt"] == ["2026-10-22T21:00:00Z"]
    assert q["subject"] == ["Oak & Pine Tree Care: tree trimming, two oaks"]

    ics = client.get(f"/a/{ref}/i")
    assert ics.status_code == 200 and ics.headers["content-type"].startswith("text/calendar")
    assert 'filename="appointment.ics"' in ics.headers["content-disposition"]
    assert "DTSTART:20261022T200000Z" in ics.text and "DTEND:20261022T210000Z" in ics.text
    assert "SUMMARY:Oak & Pine Tree Care: tree trimming\\, two oaks" in ics.text
    assert "LOCATION:12 Oak St\\, Charlotte" in ics.text
    assert ics.text.endswith("END:VCALENDAR\r\n")

    page = client.get(f"/a/{ref}")
    assert page.status_code == 200 and "Thursday, Oct 22 at 4:00 PM" in page.text and "Apple Calendar" in page.text
    assert "+1555" not in page.text


def test_tampered_or_unknown_refs_are_404(tmp_path):
    client, telecom, app = booked_app(tmp_path)
    confirmation = [m for m in telecom.outbound if m.kind == "booking_confirmation"][-1].body
    ref = confirmation.split("/a/")[1].split("/")[0]
    rowid, sig = ref.split("-")
    assert client.get(f"/a/{rowid}-{'0' * 12}/g", follow_redirects=False).status_code == 404
    assert client.get(f"/a/99-{sig}/i").status_code == 404
    assert client.get("/a/not-a-ref").status_code == 404
    assert client.get(f"/a/{ref}/x").status_code == 404


def test_ref_signature_is_keyed_by_the_secret():
    a = CalendarLinks("https://x.test", "secret-a")
    b = CalendarLinks("https://x.test", "secret-b")
    ref = a.ref(7, "evt")
    assert a.valid(ref, "evt") and not b.valid(ref, "evt") and not a.valid(ref, "other")


def test_ics_folds_long_lines_and_escapes():
    text = build_ics(event_id="e;1", summary="S" * 100, location="a,b;c", description="line1\nline2",
                     start=NOW, end=NOW, stamp=NOW)
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))
    assert r"UID:e\;1@text-back" in text and r"LOCATION:a\,b\;c" in text and r"DESCRIPTION:line1\nline2" in text


def test_confirmation_without_an_app_has_no_dangling_links_line(tmp_path):
    from text_back.store import Store
    from text_back.booking import book_appointment
    from zoneinfo import ZoneInfo
    store, telecom, calendar = Store(":memory:"), FakeTelecom(), CalendarStub(timezone_name="America/New_York")
    book_appointment(calendar=calendar, store=store, telecom=telecom, caller="+15551112222", business_number="+15553334444",
                     service="trim", location="12 Oak St", customer_name="Pat", business_name="Acme", timezone_name="America/New_York",
                     start=datetime(2026, 10, 22, 16, 0, tzinfo=ZoneInfo("America/New_York")), duration_minutes=60,
                     conversation_id="+15551112222", now=NOW)
    body = [m for m in telecom.outbound if m.kind == "booking_confirmation"][-1].body
    assert body.endswith("This is the scheduling assistant for Acme.")
