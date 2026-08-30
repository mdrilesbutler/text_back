import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from text_back.booking import SlotUnavailableError, book_appointment
from text_back.calendars.google import GoogleCalendarProvider
from text_back.calendars.ids import google_event_id
from text_back.calendars.protocol import CalendarProviderError
from text_back.calendars.transport import FakeHttpTransport, HttpResponse
from text_back.store import Store
from text_back.telecom import FakeTelecom

CALENDAR_ID = "mike@example.test"
CONVERSATION_ID = "conv-google-1"
START = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
END = START + timedelta(hours=1)


def _provider(*responses):
    transport = FakeHttpTransport(list(responses))
    provider = GoogleCalendarProvider(
        calendar_id=CALENDAR_ID,
        token_provider=lambda: "tok-test",
        transport=transport,
    )
    return provider, transport


def _json_response(status: int, payload: dict) -> HttpResponse:
    return HttpResponse(status=status, headers=(), body=json.dumps(payload).encode())


def _freebusy(busy: list[dict]) -> HttpResponse:
    return _json_response(200, {"calendars": {CALENDAR_ID: {"busy": busy}}})


def test_is_free_posts_freebusy_with_utc_window_and_bearer_token():
    provider, transport = _provider(_freebusy([]))
    local_start = datetime(2026, 8, 20, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    local_end = datetime(2026, 8, 20, 12, 0, tzinfo=ZoneInfo("America/New_York"))

    assert provider.is_free(local_start, local_end) is True

    request = transport.requests[0]
    assert request.method == "POST"
    assert request.url == "https://www.googleapis.com/calendar/v3/freeBusy"
    headers = dict(request.headers)
    assert headers["Authorization"] == "Bearer tok-test"
    assert headers["Content-Type"] == "application/json"
    body = json.loads(request.body)
    assert body["timeMin"] == "2026-08-20T15:00:00Z"
    assert body["timeMax"] == "2026-08-20T16:00:00Z"
    assert body["items"] == [{"id": CALENDAR_ID}]


def test_is_free_true_on_empty_busy_and_false_on_overlap():
    provider, _ = _provider(
        _freebusy([]),
        _freebusy(
            [{"start": "2026-08-20T15:30:00Z", "end": "2026-08-20T16:30:00Z"}]
        ),
    )

    assert provider.is_free(START, END) is True
    assert provider.is_free(START, END) is False


def test_is_free_raises_on_calendar_errors_entry():
    provider, _ = _provider(
        _json_response(
            200,
            {
                "calendars": {
                    CALENDAR_ID: {
                        "errors": [{"domain": "global", "reason": "notFound"}],
                        "busy": [],
                    }
                }
            },
        )
    )

    with pytest.raises(CalendarProviderError):
        provider.is_free(START, END)


def test_is_free_raises_on_missing_calendar_entry():
    provider, _ = _provider(_json_response(200, {"calendars": {}}))

    with pytest.raises(CalendarProviderError):
        provider.is_free(START, END)


def test_is_free_raises_on_http_500_and_on_non_json_body():
    provider, _ = _provider(
        HttpResponse(status=500, headers=(), body=b"Internal Server Error"),
        HttpResponse(status=200, headers=(), body=b"<html>not json</html>"),
    )

    with pytest.raises(CalendarProviderError) as excinfo:
        provider.is_free(START, END)
    assert "tok-test" not in str(excinfo.value)

    with pytest.raises(CalendarProviderError) as excinfo:
        provider.is_free(START, END)
    assert "tok-test" not in str(excinfo.value)


def _event_body(
    event_id: str,
    start: str = "2026-08-20T15:00:00Z",
    end: str = "2026-08-20T16:00:00Z",
    **extra,
) -> dict:
    return {
        "id": event_id,
        "status": "confirmed",
        "start": {"dateTime": start},
        "end": {"dateTime": end},
        **extra,
    }


def test_create_event_sends_deterministic_id_and_returns_provider_id():
    expected_id = google_event_id(CONVERSATION_ID, START)
    provider, transport = _provider(_json_response(200, {"id": expected_id}))

    event_id = provider.create_event(
        start=START,
        end=END,
        summary="tree removal for John Smith (+15551112222)",
        location="12 Oak St",
        caller="+15551112222",
        conversation_id=CONVERSATION_ID,
    )

    assert event_id == expected_id
    request = transport.requests[0]
    assert request.method == "POST"
    assert request.url == (
        "https://www.googleapis.com/calendar/v3/calendars/"
        "mike%40example.test/events"
    )
    body = json.loads(request.body)
    assert body["id"] == expected_id
    assert body["summary"] == "tree removal for John Smith (+15551112222)"
    assert body["location"] == "12 Oak St"
    assert body["start"] == {"dateTime": "2026-08-20T15:00:00Z"}
    assert body["end"] == {"dateTime": "2026-08-20T16:00:00Z"}
    private = body["extendedProperties"]["private"]
    assert private["text_back_conversation_id"] == CONVERSATION_ID
    assert private["text_back_caller"] == "+15551112222"


def test_create_event_409_verifies_existing_event_before_returning_id():
    expected_id = google_event_id(CONVERSATION_ID, START)
    provider, transport = _provider(
        HttpResponse(status=409, headers=(), body=b'{"error": "duplicate"}'),
        _json_response(200, _event_body(expected_id)),
    )

    event_id = provider.create_event(
        start=START,
        end=END,
        summary="tree removal",
        location="12 Oak St",
        caller="+15551112222",
        conversation_id=CONVERSATION_ID,
    )

    assert event_id == expected_id
    assert len(transport.requests) == 2
    verify = transport.requests[1]
    assert verify.method == "GET"
    assert verify.url == (
        "https://www.googleapis.com/calendar/v3/calendars/"
        f"mike%40example.test/events/{expected_id}"
    )
    assert verify.body is None
    assert dict(verify.headers)["Authorization"] == "Bearer tok-test"


def test_create_event_409_accepts_offset_datetime_for_same_instant():
    expected_id = google_event_id(CONVERSATION_ID, START)
    provider, _ = _provider(
        HttpResponse(status=409, headers=(), body=b'{"error": "duplicate"}'),
        _json_response(
            200,
            _event_body(
                expected_id,
                start="2026-08-20T11:00:00-04:00",
                end="2026-08-20T12:00:00-04:00",
            ),
        ),
    )

    event_id = provider.create_event(
        start=START,
        end=END,
        summary="tree removal",
        location="12 Oak St",
        caller="+15551112222",
        conversation_id=CONVERSATION_ID,
    )

    assert event_id == expected_id


@pytest.mark.parametrize(
    "verify_response",
    [
        # Tombstone: Google keeps 409ing on a deleted event's id forever.
        _json_response(
            200,
            _event_body("whatever", status="cancelled"),
        ),
        # Different slot than the one being confirmed right now.
        _json_response(
            200,
            _event_body(
                "whatever",
                start="2026-06-10T15:00:00Z",
                end="2026-06-10T16:00:00Z",
            ),
        ),
        # Missing/unparseable times.
        _json_response(200, {"id": "whatever", "status": "confirmed"}),
        _json_response(
            200,
            {
                "id": "whatever",
                "status": "confirmed",
                "start": {"dateTime": "not-a-datetime"},
                "end": {"dateTime": "not-a-datetime"},
            },
        ),
        # Lookup itself failed.
        HttpResponse(status=404, headers=(), body=b'{"error": "gone"}'),
        HttpResponse(status=500, headers=(), body=b'{"error": "boom"}'),
        HttpResponse(status=200, headers=(), body=b"not json"),
    ],
)
def test_create_event_409_with_mismatched_or_failed_verify_raises(verify_response):
    # Never confirm a booking against an event that is cancelled, occupies a
    # different slot, or cannot be verified.
    provider, _ = _provider(
        HttpResponse(status=409, headers=(), body=b'{"error": "duplicate"}'),
        verify_response,
    )

    with pytest.raises(CalendarProviderError) as excinfo:
        provider.create_event(
            start=START,
            end=END,
            summary="tree removal",
            location="12 Oak St",
            caller="+15551112222",
            conversation_id=CONVERSATION_ID,
        )
    assert "tok-test" not in str(excinfo.value)


@pytest.mark.parametrize(
    "response",
    [
        HttpResponse(status=400, headers=(), body=b'{"error": "bad"}'),
        HttpResponse(status=403, headers=(), body=b'{"error": "forbidden"}'),
        HttpResponse(status=500, headers=(), body=b'{"error": "boom"}'),
        HttpResponse(status=200, headers=(), body=b'{"status": "confirmed"}'),
        HttpResponse(status=200, headers=(), body=b'{"id": ""}'),
        HttpResponse(status=200, headers=(), body=b"not json"),
    ],
)
def test_create_event_raises_on_errors_and_missing_id_in_body(response):
    provider, _ = _provider(response)

    with pytest.raises(CalendarProviderError) as excinfo:
        provider.create_event(
            start=START,
            end=END,
            summary="tree removal",
            location="12 Oak St",
            caller="+15551112222",
            conversation_id=CONVERSATION_ID,
        )
    assert "tok-test" not in str(excinfo.value)


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


def test_busy_race_end_to_end():
    provider, transport = _provider(
        _freebusy([]),
        _freebusy(
            [{"start": "2026-08-20T15:00:00Z", "end": "2026-08-20T16:00:00Z"}]
        ),
    )
    telecom = FakeTelecom()
    store = Store()

    with pytest.raises(SlotUnavailableError):
        _book(provider, telecom, store)

    # Both freebusy checks hit the wire; the insert never did.
    assert len(transport.requests) == 2
    assert all(r.url.endswith("/freeBusy") for r in transport.requests)
    assert telecom.outbound == []
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "appointment.confirmed" not in events


def test_booking_end_to_end_confirms_only_with_event_id():
    expected_id = google_event_id(CONVERSATION_ID, START)
    provider, transport = _provider(
        _freebusy([]),
        _freebusy([]),
        _json_response(201, {"id": expected_id}),
    )
    telecom = FakeTelecom()
    store = Store()

    result = _book(provider, telecom, store)

    assert result == {"booked": True, "event_id": expected_id, "duplicate": False}
    assert len(transport.requests) == 3
    assert len(telecom.outbound) == 1
    assert telecom.outbound[0].kind == "booking_confirmation"
    assert expected_id in telecom.outbound[0].body
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "calendar.event_created" in events
    assert "appointment.confirmed" in events
