import base64
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from text_back.booking import (
    CalendarEventError,
    SlotUnavailableError,
    book_appointment,
)
from text_back.calendars.icloud import ICloudCalDAVProvider
from text_back.calendars.ids import icloud_uid
from text_back.calendars.protocol import CalendarProviderError
from text_back.calendars.transport import FakeHttpTransport, HttpResponse
from text_back.store import Store
from text_back.telecom import FakeTelecom

USERNAME = "mike@example.test"
PASSWORD = "fixture-password"
CALENDAR_URL = "https://caldav.example.test/123456/calendars/home/"
CONVERSATION_ID = "conv-icloud-1"
START = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
END = START + timedelta(hours=1)

EXPECTED_BASIC = "Basic " + base64.b64encode(
    f"{USERNAME}:{PASSWORD}".encode()
).decode()

EMPTY_MULTISTATUS = (
    b'<?xml version="1.0" encoding="UTF-8"?>\n'
    b'<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav"/>'
)


def _vcalendar(*extra_vevent_lines: str) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "BEGIN:VEVENT",
        "UID:existing-event@example.test",
        "DTSTART:20260820T150000Z",
        "DTEND:20260820T160000Z",
        "SUMMARY:Existing job",
        *extra_vevent_lines,
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\n".join(lines)


def _multistatus(*calendar_datas: str, status: str = "HTTP/1.1 200 OK") -> bytes:
    responses = "".join(
        "<D:response>"
        "<D:href>/123456/calendars/home/existing.ics</D:href>"
        "<D:propstat>"
        f"<D:prop><C:calendar-data>{data}</C:calendar-data></D:prop>"
        f"<D:status>{status}</D:status>"
        "</D:propstat>"
        "</D:response>"
        for data in calendar_datas
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">'
        f"{responses}</D:multistatus>"
    ).encode()


def _provider(*responses, calendar_url: str = CALENDAR_URL):
    transport = FakeHttpTransport(list(responses))
    provider = ICloudCalDAVProvider(
        username=USERNAME,
        password_provider=lambda: PASSWORD,
        transport=transport,
        calendar_url=calendar_url,
    )
    return provider, transport


def _create(provider, summary="tree removal", location="12 Oak St"):
    return provider.create_event(
        start=START,
        end=END,
        summary=summary,
        location=location,
        caller="+15551112222",
        conversation_id=CONVERSATION_ID,
    )


def test_is_free_sends_calendar_query_report_with_basic_auth_and_depth_1():
    provider, transport = _provider(
        HttpResponse(status=207, headers=(), body=EMPTY_MULTISTATUS)
    )
    local_start = datetime(2026, 8, 20, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    local_end = datetime(2026, 8, 20, 12, 0, tzinfo=ZoneInfo("America/New_York"))

    assert provider.is_free(local_start, local_end) is True

    request = transport.requests[0]
    assert request.method == "REPORT"
    assert request.url == CALENDAR_URL
    headers = dict(request.headers)
    assert headers["Authorization"] == EXPECTED_BASIC
    assert headers["Depth"] == "1"
    assert headers["Content-Type"] == "application/xml"
    body = request.body.decode()
    # The time-range window is converted to UTC ICS timestamps.
    assert '<C:time-range start="20260820T150000Z" end="20260820T160000Z"/>' in body
    assert 'xmlns:C="urn:ietf:params:xml:ns:caldav"' in body
    assert '<C:comp-filter name="VEVENT">' in body


def test_is_free_true_on_empty_multistatus_false_when_vevent_returned():
    provider, _ = _provider(
        HttpResponse(status=207, headers=(), body=EMPTY_MULTISTATUS),
        HttpResponse(status=207, headers=(), body=_multistatus(_vcalendar())),
    )

    assert provider.is_free(START, END) is True
    assert provider.is_free(START, END) is False


def test_is_free_ignores_transparent_and_cancelled_events():
    provider, _ = _provider(
        HttpResponse(
            status=207,
            headers=(),
            body=_multistatus(
                _vcalendar("TRANSP:TRANSPARENT"),
                _vcalendar("STATUS:CANCELLED"),
            ),
        ),
        HttpResponse(
            status=207,
            headers=(),
            body=_multistatus(_vcalendar("TRANSP:TRANSPARENT"), _vcalendar()),
        ),
    )

    # Only transparent/cancelled events returned: the window is still free.
    assert provider.is_free(START, END) is True
    # A real opaque event beside a transparent one still blocks.
    assert provider.is_free(START, END) is False


def test_is_free_raises_on_non_207_and_on_unparseable_xml():
    provider, _ = _provider(
        HttpResponse(status=200, headers=(), body=EMPTY_MULTISTATUS),
        HttpResponse(status=207, headers=(), body=b"<multistatus>not closed"),
    )

    with pytest.raises(CalendarProviderError) as excinfo:
        provider.is_free(START, END)
    assert PASSWORD not in str(excinfo.value)

    with pytest.raises(CalendarProviderError) as excinfo:
        provider.is_free(START, END)
    assert PASSWORD not in str(excinfo.value)


@pytest.mark.parametrize(
    "body",
    [
        b"<ok/>",
        b"<error>quota exceeded</error>",
        # Well-formed XML, but not a DAV: multistatus at all.
        b'<response xmlns="DAV:"><status>HTTP/1.1 200 OK</status></response>',
    ],
)
def test_is_free_raises_on_207_body_that_is_not_a_dav_multistatus(body):
    # A parseable-but-wrong 207 body proves nothing about the window; treating
    # it as "free" would open a double-booking path. Fail toward busy.
    provider, _ = _provider(HttpResponse(status=207, headers=(), body=body))

    with pytest.raises(CalendarProviderError) as excinfo:
        provider.is_free(START, END)
    assert PASSWORD not in str(excinfo.value)


def test_is_free_raises_on_error_status_inside_multistatus():
    provider, _ = _provider(
        HttpResponse(
            status=207,
            headers=(),
            body=_multistatus(_vcalendar(), status="HTTP/1.1 404 Not Found"),
        )
    )

    with pytest.raises(CalendarProviderError):
        provider.is_free(START, END)


def test_create_event_puts_uid_named_ics_with_if_none_match_star():
    uid = icloud_uid(CONVERSATION_ID, START)
    provider, transport = _provider(HttpResponse(status=201, headers=(), body=b""))

    event_id = _create(
        provider,
        summary="tree removal; big oak, urgent",
        location="12 Oak St; rear",
    )

    assert event_id == uid
    request = transport.requests[0]
    assert request.method == "PUT"
    assert request.url == f"{CALENDAR_URL}{uid}.ics"
    headers = dict(request.headers)
    assert headers["Authorization"] == EXPECTED_BASIC
    assert headers["If-None-Match"] == "*"
    assert headers["Content-Type"] == "text/calendar; charset=utf-8"
    body = request.body
    # CRLF line endings throughout — no bare newlines.
    assert body.count(b"\n") == body.count(b"\r\n")
    text = body.decode()
    lines = text.split("\r\n")
    assert "BEGIN:VCALENDAR" in lines
    assert "BEGIN:VEVENT" in lines
    assert f"UID:{uid}" in lines
    assert "DTSTART:20260820T150000Z" in lines
    assert "DTEND:20260820T160000Z" in lines
    assert "SUMMARY:tree removal\\; big oak\\, urgent" in lines
    assert "LOCATION:12 Oak St\\; rear" in lines
    assert f"X-TEXT-BACK-CONVERSATION-ID:{CONVERSATION_ID}" in lines
    assert "END:VEVENT" in lines
    assert "END:VCALENDAR" in lines


def test_create_event_normalizes_calendar_url_missing_trailing_slash():
    uid = icloud_uid(CONVERSATION_ID, START)
    provider, transport = _provider(
        HttpResponse(status=201, headers=(), body=b""),
        calendar_url=CALENDAR_URL.rstrip("/"),
    )

    assert _create(provider) == uid
    assert transport.requests[0].url == f"{CALENDAR_URL}{uid}.ics"


@pytest.mark.parametrize("status", [201, 204])
def test_create_event_201_and_204_return_uid(status):
    provider, _ = _provider(HttpResponse(status=status, headers=(), body=b""))

    assert _create(provider) == icloud_uid(CONVERSATION_ID, START)


def _existing_ics(dtstart: str = "20260820T150000Z", *extra_lines: str) -> bytes:
    uid = icloud_uid(CONVERSATION_ID, START)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART:{dtstart}",
        "DTEND:20260820T160000Z",
        "SUMMARY:tree removal",
        *extra_lines,
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return ("\r\n".join(lines) + "\r\n").encode()


def test_create_event_412_verifies_existing_resource_before_returning_uid():
    uid = icloud_uid(CONVERSATION_ID, START)
    provider, transport = _provider(
        HttpResponse(status=412, headers=(), body=b"Precondition Failed"),
        HttpResponse(status=200, headers=(), body=_existing_ics()),
    )

    assert _create(provider) == uid
    assert len(transport.requests) == 2
    verify = transport.requests[1]
    assert verify.method == "GET"
    assert verify.url == f"{CALENDAR_URL}{uid}.ics"
    assert dict(verify.headers)["Authorization"] == EXPECTED_BASIC


@pytest.mark.parametrize(
    "verify_response",
    [
        # Cancelled event still occupying the UID resource.
        HttpResponse(
            status=200,
            headers=(),
            body=_existing_ics("20260820T150000Z", "STATUS:CANCELLED"),
        ),
        # Resource holds a different slot than the one being confirmed.
        HttpResponse(status=200, headers=(), body=_existing_ics("20260610T150000Z")),
        # Verification GET itself failed.
        HttpResponse(status=404, headers=(), body=b"Not Found"),
        HttpResponse(status=500, headers=(), body=b"Internal Server Error"),
    ],
)
def test_create_event_412_with_mismatched_or_failed_verify_raises(verify_response):
    # Never confirm against a cancelled event, a different slot, or an
    # unverifiable duplicate.
    provider, _ = _provider(
        HttpResponse(status=412, headers=(), body=b"Precondition Failed"),
        verify_response,
    )

    with pytest.raises(CalendarProviderError) as excinfo:
        _create(provider)
    assert PASSWORD not in str(excinfo.value)


@pytest.mark.parametrize("status", [401, 403, 507])
def test_create_event_raises_on_401_403_507(status):
    provider, _ = _provider(HttpResponse(status=status, headers=(), body=b"denied"))

    with pytest.raises(CalendarProviderError) as excinfo:
        _create(provider)
    message = str(excinfo.value)
    assert PASSWORD not in message
    assert EXPECTED_BASIC not in message


def _book(provider, telecom, store):
    return book_appointment(
        calendar=provider,
        store=store,
        telecom=telecom,
        caller="+15551112222",
        business_number="+15553334444",
        service="tree removal",
        location="12 Oak St",
        customer_name="John Smith",
        business_name="Mike",
        timezone_name="UTC",
        start=START,
        duration_minutes=60,
        conversation_id=CONVERSATION_ID,
    )


def test_busy_race_refuses_booking_end_to_end():
    provider, transport = _provider(
        HttpResponse(status=207, headers=(), body=EMPTY_MULTISTATUS),
        HttpResponse(status=207, headers=(), body=_multistatus(_vcalendar())),
    )
    telecom = FakeTelecom()
    store = Store()

    with pytest.raises(SlotUnavailableError):
        _book(provider, telecom, store)

    # Both free/busy REPORTs hit the wire; the PUT never did.
    assert len(transport.requests) == 2
    assert all(r.method == "REPORT" for r in transport.requests)
    assert telecom.outbound == []
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "appointment.confirmed" not in events


def test_malformed_create_response_refuses_confirmation_no_sms():
    provider, transport = _provider(
        HttpResponse(status=207, headers=(), body=EMPTY_MULTISTATUS),
        HttpResponse(status=207, headers=(), body=EMPTY_MULTISTATUS),
        HttpResponse(status=500, headers=(), body=b"Internal Server Error"),
    )
    telecom = FakeTelecom()
    store = Store()

    with pytest.raises(CalendarEventError):
        _book(provider, telecom, store)

    assert len(transport.requests) == 3
    assert telecom.outbound == []
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "appointment.confirmed" not in events
    assert "calendar.event_created" not in events


def test_booking_end_to_end_confirms_only_with_uid():
    uid = icloud_uid(CONVERSATION_ID, START)
    provider, transport = _provider(
        HttpResponse(status=207, headers=(), body=EMPTY_MULTISTATUS),
        HttpResponse(status=207, headers=(), body=EMPTY_MULTISTATUS),
        HttpResponse(status=201, headers=(), body=b""),
    )
    telecom = FakeTelecom()
    store = Store()

    result = _book(provider, telecom, store)

    assert result == {"booked": True, "event_id": uid, "duplicate": False}
    assert len(transport.requests) == 3
    assert transport.requests[2].method == "PUT"
    assert len(telecom.outbound) == 1
    assert telecom.outbound[0].kind == "booking_confirmation"
    assert telecom.outbound[0].kind == "booking_confirmation"
    assert store.appointment_by_event(uid)  # the id is stored, not texted
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "calendar.event_created" in events
    assert "appointment.confirmed" in events
