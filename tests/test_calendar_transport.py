import re
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from text_back.booking import (
    BookingError,
    CalendarEventError,
    book_appointment,
)
from text_back.calendars.ids import (
    google_event_id,
    ics_escape,
    icloud_uid,
    ms_transaction_id,
)
from text_back.calendars.protocol import CalendarProviderError
from text_back.calendars.transport import (
    FakeHttpTransport,
    HttpRequest,
    HttpResponse,
    file_token_provider,
    ics_utc,
    rfc3339_utc,
)
from text_back.store import Store
from text_back.telecom import FakeTelecom


def test_file_token_provider_reads_fresh_value_each_call(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("tok-first\n")
    provider = file_token_provider(str(token_file))

    assert provider() == "tok-first"
    token_file.write_text("tok-rotated\n")
    assert provider() == "tok-rotated"


def test_file_token_provider_empty_file_raises_calendar_provider_error(tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("   \n")
    provider = file_token_provider(str(token_file))

    with pytest.raises(CalendarProviderError):
        provider()

    missing = file_token_provider(str(tmp_path / "does-not-exist"))
    with pytest.raises(CalendarProviderError) as excinfo:
        missing()
    assert str(tmp_path) not in str(excinfo.value)


def test_fake_transport_records_requests_and_pops_responses():
    canned = HttpResponse(status=200, headers=(), body=b"{}")
    transport = FakeHttpTransport([canned])
    request = HttpRequest(method="GET", url="https://example.test/x", headers=())

    response = transport(request)

    assert response is canned
    assert transport.requests == [request]
    with pytest.raises(AssertionError):
        transport(request)


ID_SLOT = datetime(2026, 8, 20, 15, 0, tzinfo=ZoneInfo("UTC"))
ID_OTHER_SLOT = datetime(2026, 9, 5, 10, 0, tzinfo=ZoneInfo("UTC"))


def test_ids_are_deterministic_and_alphabet_safe():
    google = google_event_id("conv-1", ID_SLOT)
    assert re.fullmatch(r"tb[0-9a-f]{40}", google)
    assert google == google_event_id("conv-1", ID_SLOT)
    assert google != google_event_id("conv-2", ID_SLOT)

    ms = ms_transaction_id("conv-1", ID_SLOT)
    assert str(uuid.UUID(ms)) == ms
    assert ms == ms_transaction_id("conv-1", ID_SLOT)
    assert ms != ms_transaction_id("conv-2", ID_SLOT)

    icloud = icloud_uid("conv-1", ID_SLOT)
    assert re.fullmatch(r"tb-[0-9a-f]{32}@text-back\.invalid", icloud)
    assert icloud == icloud_uid("conv-1", ID_SLOT)
    assert icloud != icloud_uid("conv-2", ID_SLOT)


def test_ids_differ_for_a_different_slot_in_the_same_conversation():
    # A second booking attempt for a DIFFERENT slot must never collide with
    # the first event's deterministic id — the provider's duplicate signal is
    # only ever a same-slot retry.
    assert google_event_id("conv-1", ID_SLOT) != google_event_id(
        "conv-1", ID_OTHER_SLOT
    )
    assert ms_transaction_id("conv-1", ID_SLOT) != ms_transaction_id(
        "conv-1", ID_OTHER_SLOT
    )
    assert icloud_uid("conv-1", ID_SLOT) != icloud_uid("conv-1", ID_OTHER_SLOT)


def test_ids_normalize_slot_to_utc_instant():
    # The same instant expressed in another timezone yields the same id.
    eastern = ID_SLOT.astimezone(ZoneInfo("America/New_York"))
    assert google_event_id("conv-1", ID_SLOT) == google_event_id("conv-1", eastern)
    assert ms_transaction_id("conv-1", ID_SLOT) == ms_transaction_id(
        "conv-1", eastern
    )
    assert icloud_uid("conv-1", ID_SLOT) == icloud_uid("conv-1", eastern)


def test_transport_redirect_handler_refuses_all_redirects():
    # stdlib urllib replays Authorization headers on cross-host redirects;
    # the production opener must surface any 3xx as a response instead of
    # following it, so adapters fail closed via their status checks.
    import io
    import urllib.error
    import urllib.request

    from text_back.calendars import transport as transport_module

    handler = transport_module.RedirectRefusingHandler()
    request = urllib.request.Request(
        "https://api.example.test/x",
        headers={"Authorization": "Bearer tok-test"},
    )
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        handler.redirect_request(
            request, io.BytesIO(b""), 302, "Found", {}, "https://evil.example.test/"
        )
    assert excinfo.value.code == 302

    assert any(
        isinstance(h, transport_module.RedirectRefusingHandler)
        for h in transport_module._OPENER.handlers
    )


def test_ics_escape_handles_semicolon_comma_backslash_newline():
    assert ics_escape("a;b,c\\d\ne") == "a\\;b\\,c\\\\d\\ne"


def test_rfc3339_and_ics_formatting_convert_to_utc():
    eastern = datetime(2026, 8, 20, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    assert rfc3339_utc(eastern) == "2026-08-20T15:00:00Z"
    assert ics_utc(eastern) == "20260820T150000Z"


# --- Booking-integration guards ----------------------------------------------

SLOT = datetime(2026, 8, 20, 15, 0, tzinfo=ZoneInfo("UTC"))


class RaisingCalendar:
    provider_name = "raising"

    def __init__(self, *, fail_on: str):
        self.fail_on = fail_on

    def is_free(self, start, end):
        if self.fail_on == "is_free":
            raise CalendarProviderError("calendar transport failure")
        return True

    def create_event(self, **kwargs):
        raise CalendarProviderError("calendar transport failure")


def _book(calendar, telecom, store):
    return book_appointment(
        calendar=calendar,
        store=store,
        telecom=telecom,
        caller="+15551112222",
        business_number="+15553334444",
        service="tree removal",
        location="12 Oak St",
        customer_name="John Smith",
        business_name="Mike",
        timezone_name="UTC",
        start=SLOT,
        duration_minutes=60,
        conversation_id="conv-raise",
    )


def test_provider_error_during_freebusy_refuses_booking_without_sms():
    telecom = FakeTelecom()
    store = Store()

    with pytest.raises(CalendarEventError):
        _book(RaisingCalendar(fail_on="is_free"), telecom, store)

    assert telecom.outbound == []
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "appointment.confirmed" not in events


def test_provider_error_during_create_refuses_confirmation():
    telecom = FakeTelecom()
    store = Store()

    with pytest.raises(BookingError):
        _book(RaisingCalendar(fail_on="create_event"), telecom, store)

    assert telecom.outbound == []
    events = [e["event_type"] for e in store.list_outcome_events("+15551112222")]
    assert "appointment.confirmed" not in events
    assert store.appointment_by_conversation("conv-raise") is None
