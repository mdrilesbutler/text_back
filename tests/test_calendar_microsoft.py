import json
from datetime import datetime, timedelta, timezone
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
DUPLICATE_LOOKUP_URL = (
    f"{BASE}/users/mike%40example.test/calendarView"
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


def _event(show_as: str, *, cancelled: bool = False) -> dict:
    return {"id": "AAMkEvent", "showAs": show_as, "isCancelled": cancelled}


def _calendar_view(items: list[dict], **extra) -> HttpResponse:
    return _json_response(200, {"value": items, **extra})


def test_is_free_gets_calendar_view_for_configured_user():
    provider, transport = _provider(_calendar_view([]))

    assert provider.is_free(START, END) is True

    request = transport.requests[0]
    assert request.method == "GET"
    assert request.url == (
        f"{BASE}/users/mike%40example.test/calendarView"
        "?startDateTime=2026-08-20T15%3A00%3A00Z"
        "&endDateTime=2026-08-20T16%3A00%3A00Z"
        "&%24select=id%2CshowAs%2CisCancelled"
    )
    headers = dict(request.headers)
    assert headers["Authorization"] == "Bearer tok-test"
    assert "Content-Type" not in headers
    assert request.body is None


def test_personal_outlook_connection_uses_me_calendar_view():
    transport = FakeHttpTransport([_calendar_view([])])
    provider = MicrosoftGraphProvider(
        user="me", token_provider=lambda: "tok-test", transport=transport
    )

    assert provider.is_free(START, END) is True
    assert transport.requests[0].url.startswith(f"{BASE}/me/calendarView?")


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
def test_is_free_ignores_free_and_workingelsewhere_but_blocks_every_other_state(
    status, expected_free
):
    provider, _ = _provider(_calendar_view([_event(status)]))

    assert provider.is_free(START, END) is expected_free


def test_is_free_ignores_cancelled_events():
    provider, _ = _provider(_calendar_view([_event("busy", cancelled=True)]))

    assert provider.is_free(START, END) is True


def test_is_free_fails_closed_on_missing_or_unknown_show_as():
    provider, _ = _provider(_calendar_view([{"id": "AAMkUnknown"}]))

    assert provider.is_free(START, END) is False


@pytest.mark.parametrize(
    "payload",
    [
        {"value": "nope"},
        {"unexpected": "shape"},
        {"value": ["not-an-event"]},
    ],
)
def test_is_free_raises_on_malformed_calendar_view(payload):
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


def test_is_free_follows_graph_pagination_before_declaring_slot_free():
    next_url = f"{BASE}/users/mike%40example.test/calendarView?$skiptoken=next"
    provider, transport = _provider(
        _calendar_view([], **{"@odata.nextLink": next_url}),
        _calendar_view([_event("busy")]),
    )

    assert provider.is_free(START, END) is False
    assert [request.url for request in transport.requests] == [
        (
            f"{BASE}/users/mike%40example.test/calendarView"
            "?startDateTime=2026-08-20T15%3A00%3A00Z"
            "&endDateTime=2026-08-20T16%3A00%3A00Z"
            "&%24select=id%2CshowAs%2CisCancelled"
        ),
        next_url,
    ]


def test_is_free_rejects_untrusted_graph_next_link():
    provider, _ = _provider(
        _calendar_view([], **{"@odata.nextLink": "https://evil.example/events"})
    )

    with pytest.raises(CalendarProviderError, match="pagination"):
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
    assert lookup.url == DUPLICATE_LOOKUP_URL
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
        _calendar_view([]),
        _calendar_view([_event("busy")]),
    )
    telecom = FakeTelecom()
    store = Store()

    with pytest.raises(SlotUnavailableError):
        _book(provider, telecom, store)

    # Both calendarView checks hit the wire; the events POST never did.
    assert len(transport.requests) == 2
    assert all("/calendarView?" in r.url for r in transport.requests)
    assert telecom.outbound == []
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "appointment.confirmed" not in events


def test_booking_end_to_end_confirms_only_with_event_id():
    provider, transport = _provider(
        _calendar_view([]),
        _calendar_view([]),
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
    provider, _ = _provider(
        _calendar_view([]), _calendar_view([]), create_response
    )
    telecom = FakeTelecom()
    store = Store()

    with pytest.raises(CalendarEventError):
        _book(provider, telecom, store)

    assert telecom.outbound == []
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "appointment.confirmed" not in events
    assert "calendar.event_created" not in events
