import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from text_back.booking import (
    CalendarEventError,
    SlotUnavailableError,
    book_appointment,
)
from text_back.calendars.ids import ms_transaction_id
from text_back.calendars.microsoft import MicrosoftGraphProvider
from text_back.calendars.protocol import CalendarProviderError
from text_back.calendars.transport import FakeHttpTransport, HttpResponse
from text_back.store import Store
from text_back.telecom import FakeTelecom

USER = "mike@example.test"
CONVERSATION_ID = "conv-ms-1"
BASE = "https://graph.microsoft.com/v1.0"
START = datetime(2026, 8, 20, 15, 0, tzinfo=timezone.utc)
END = START + timedelta(hours=1)
TRANSACTION_ID = ms_transaction_id(CONVERSATION_ID, START)
CALENDAR_VIEW_URL = (
    f"{BASE}/users/mike%40example.test/calendar/calendarView"
    "?startDateTime=2026-08-20T15%3A00%3A00Z"
    "&endDateTime=2026-08-20T16%3A00%3A00Z"
    "&%24select=id%2CtransactionId"
)


def _provider(*responses):
    transport = FakeHttpTransport(list(responses))
    provider = MicrosoftGraphProvider(
        user=USER,
        token_provider=lambda: "tok-test",
        transport=transport,
    )
    return provider, transport


def _json_response(status: int, payload: dict) -> HttpResponse:
    return HttpResponse(status=status, headers=(), body=json.dumps(payload).encode())


def _item(status: str, start: str, end: str) -> dict:
    return {
        "status": status,
        "start": {"dateTime": start, "timeZone": "UTC"},
        "end": {"dateTime": end, "timeZone": "UTC"},
    }


def _schedule(items: list[dict]) -> HttpResponse:
    return _json_response(
        200, {"value": [{"scheduleId": USER, "scheduleItems": items}]}
    )


def test_is_free_posts_getschedule_for_configured_user():
    provider, transport = _provider(_schedule([]))
    local_start = datetime(2026, 8, 20, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    local_end = datetime(2026, 8, 20, 12, 0, tzinfo=ZoneInfo("America/New_York"))

    assert provider.is_free(local_start, local_end) is True

    request = transport.requests[0]
    assert request.method == "POST"
    assert request.url == f"{BASE}/users/mike%40example.test/calendar/getSchedule"
    headers = dict(request.headers)
    assert headers["Authorization"] == "Bearer tok-test"
    assert headers["Content-Type"] == "application/json"
    body = json.loads(request.body)
    assert body["schedules"] == [USER]
    assert body["startTime"] == {
        "dateTime": "2026-08-20T15:00:00Z",
        "timeZone": "UTC",
    }
    assert body["endTime"] == {"dateTime": "2026-08-20T16:00:00Z", "timeZone": "UTC"}
    assert body["availabilityViewInterval"] == 15


@pytest.mark.parametrize(
    ("status", "expected_free"),
    [
        ("free", True),
        ("workingElsewhere", True),
        ("busy", False),
        ("tentative", False),
        ("oof", False),
    ],
)
def test_is_free_ignores_free_and_workingelsewhere_but_blocks_busy_tentative_oof(
    status, expected_free
):
    provider, _ = _provider(
        _schedule([_item(status, "2026-08-20T15:30:00", "2026-08-20T16:30:00")])
    )

    assert provider.is_free(START, END) is expected_free


def test_is_free_true_when_blocking_items_do_not_overlap_window():
    # One busy item ends exactly at window start, another begins exactly at
    # window end — [start, end) overlaps neither.
    provider, _ = _provider(
        _schedule(
            [
                _item("busy", "2026-08-20T14:00:00", "2026-08-20T15:00:00"),
                _item("oof", "2026-08-20T16:00:00", "2026-08-20T17:00:00"),
            ]
        )
    )

    assert provider.is_free(START, END) is True


def test_is_free_accepts_graph_fractional_seconds_and_zulu_suffix():
    provider, _ = _provider(
        _schedule(
            [_item("busy", "2026-08-20T15:30:00.0000000", "2026-08-20T16:30:00Z")]
        )
    )

    assert provider.is_free(START, END) is False


@pytest.mark.parametrize(
    "payload",
    [
        {"value": [{"scheduleId": USER, "error": {"message": "boom"}}]},
        {"value": []},
        {"value": "nope"},
        {"unexpected": "shape"},
        {"value": [{"scheduleId": USER, "scheduleItems": "nope"}]},
        {
            "value": [
                {
                    "scheduleId": USER,
                    "scheduleItems": [
                        _item("busy", "not-a-datetime", "2026-08-20T16:00:00")
                    ],
                }
            ]
        },
        {"value": [{"scheduleId": USER, "scheduleItems": [{"status": "busy"}]}]},
    ],
)
def test_is_free_raises_on_schedule_error_entry_and_malformed_value(payload):
    provider, _ = _provider(_json_response(200, payload))

    with pytest.raises(CalendarProviderError) as excinfo:
        provider.is_free(START, END)
    assert "tok-test" not in str(excinfo.value)


@pytest.mark.parametrize("status", [401, 429, 503])
def test_is_free_raises_on_http_401_429_503(status):
    provider, _ = _provider(
        HttpResponse(status=status, headers=(), body=b'{"error": "denied"}')
    )

    with pytest.raises(CalendarProviderError) as excinfo:
        provider.is_free(START, END)
    assert "tok-test" not in str(excinfo.value)
    assert str(status) in str(excinfo.value)


def test_is_free_raises_on_non_json_body():
    provider, _ = _provider(
        HttpResponse(status=200, headers=(), body=b"<html>not json</html>")
    )

    with pytest.raises(CalendarProviderError):
        provider.is_free(START, END)


def test_create_event_sends_deterministic_transaction_id_and_returns_graph_id():
    provider, transport = _provider(_json_response(201, {"id": "AAMkGraphEvent123"}))

    event_id = provider.create_event(
        start=START,
        end=END,
        summary="tree removal for John Smith (+15551112222)",
        location="12 Oak St",
        caller="+15551112222",
        conversation_id=CONVERSATION_ID,
    )

    assert event_id == "AAMkGraphEvent123"
    request = transport.requests[0]
    assert request.method == "POST"
    assert request.url == f"{BASE}/users/mike%40example.test/calendar/events"
    headers = dict(request.headers)
    assert headers["Authorization"] == "Bearer tok-test"
    body = json.loads(request.body)
    assert body["transactionId"] == TRANSACTION_ID
    assert body["subject"] == "tree removal for John Smith (+15551112222)"
    assert body["location"] == {"displayName": "12 Oak St"}
    assert body["start"] == {"dateTime": "2026-08-20T15:00:00Z", "timeZone": "UTC"}
    assert body["end"] == {"dateTime": "2026-08-20T16:00:00Z", "timeZone": "UTC"}
    assert body["body"] == {
        "contentType": "text",
        "content": f"text_back conversation {CONVERSATION_ID}",
    }


def test_create_event_409_recovers_id_via_calendar_view_lookup():
    # transactionId is not documented as $filter-able in Graph, so recovery
    # lists the requested window via calendarView and matches transactionId
    # client-side — which also verifies the event occupies the promised slot.
    provider, transport = _provider(
        _json_response(409, {"error": {"code": "ErrorDuplicateTransactionId"}}),
        _json_response(
            200,
            {
                "value": [
                    {"id": "AAMkUnrelated", "transactionId": "someone-else"},
                    {"id": "AAMkOriginalEvent", "transactionId": TRANSACTION_ID},
                ]
            },
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

    assert event_id == "AAMkOriginalEvent"
    assert len(transport.requests) == 2
    lookup = transport.requests[1]
    assert lookup.method == "GET"
    assert lookup.url == CALENDAR_VIEW_URL
    assert lookup.body is None
    assert dict(lookup.headers)["Authorization"] == "Bearer tok-test"


@pytest.mark.parametrize(
    "lookup_response",
    [
        _json_response(200, {"value": []}),
        # Events in the window, but none carrying OUR transactionId — the
        # duplicate belongs to a different slot/attempt.
        _json_response(
            200, {"value": [{"id": "AAMkOther", "transactionId": "not-ours"}]}
        ),
        _json_response(200, {"value": [{"id": "", "transactionId": TRANSACTION_ID}]}),
        _json_response(200, {"value": [{"subject": "no id here"}]}),
        _json_response(200, {"unexpected": "shape"}),
        HttpResponse(status=200, headers=(), body=b"not json"),
        _json_response(500, {"error": "boom"}),
    ],
)
def test_create_event_409_with_empty_or_broken_lookup_raises(lookup_response):
    # Never fabricate an event ID: a 409 whose lookup cannot produce the real
    # id must raise, so booking is refused rather than phantom-confirmed.
    provider, _ = _provider(
        _json_response(409, {"error": {"code": "ErrorDuplicateTransactionId"}}),
        lookup_response,
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
        HttpResponse(status=401, headers=(), body=b'{"error": "unauthorized"}'),
        HttpResponse(status=403, headers=(), body=b'{"error": "forbidden"}'),
        HttpResponse(status=500, headers=(), body=b'{"error": "boom"}'),
        HttpResponse(status=503, headers=(), body=b'{"error": "unavailable"}'),
        HttpResponse(status=201, headers=(), body=b'{"subject": "no id"}'),
        HttpResponse(status=201, headers=(), body=b'{"id": ""}'),
        HttpResponse(status=201, headers=(), body=b"not json"),
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


def test_busy_race_on_recheck_refuses_before_any_post_events():
    provider, transport = _provider(
        _schedule([]),
        _schedule([_item("busy", "2026-08-20T15:00:00", "2026-08-20T16:00:00")]),
    )
    telecom = FakeTelecom()
    store = Store()

    with pytest.raises(SlotUnavailableError):
        _book(provider, telecom, store)

    # Both getSchedule checks hit the wire; the events POST never did.
    assert len(transport.requests) == 2
    assert all(r.url.endswith("/calendar/getSchedule") for r in transport.requests)
    assert telecom.outbound == []
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "appointment.confirmed" not in events


def test_booking_end_to_end_confirms_only_with_event_id():
    provider, transport = _provider(
        _schedule([]),
        _schedule([]),
        _json_response(201, {"id": "AAMkGraphEvent123"}),
    )
    telecom = FakeTelecom()
    store = Store()

    result = _book(provider, telecom, store)

    assert result == {
        "booked": True,
        "event_id": "AAMkGraphEvent123",
        "duplicate": False,
    }
    assert len(transport.requests) == 3
    assert len(telecom.outbound) == 1
    assert telecom.outbound[0].kind == "booking_confirmation"
    assert "AAMkGraphEvent123" in telecom.outbound[0].body
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "calendar.event_created" in events
    assert "appointment.confirmed" in events


@pytest.mark.parametrize(
    "create_response",
    [
        HttpResponse(status=201, headers=(), body=b"not json"),
        HttpResponse(status=201, headers=(), body=b'{"subject": "no id"}'),
        HttpResponse(status=401, headers=(), body=b'{"error": "unauthorized"}'),
        HttpResponse(status=500, headers=(), body=b'{"error": "boom"}'),
    ],
)
def test_malformed_or_failed_create_refuses_confirmation_no_sms(create_response):
    provider, _ = _provider(_schedule([]), _schedule([]), create_response)
    telecom = FakeTelecom()
    store = Store()

    with pytest.raises(CalendarEventError):
        _book(provider, telecom, store)

    assert telecom.outbound == []
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "appointment.confirmed" not in events
    assert "calendar.event_created" not in events
