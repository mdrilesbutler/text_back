"""Signed local Recover journeys; all telecom/calendar transports are test fakes."""

import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import ClassVar
from urllib.parse import quote
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.brief import build_brief_data
from text_back.calendar_stub import CalendarStub
from text_back.delivery import InMemoryDeliveryTransport
from text_back.store import Store
from text_back.telecom import AmbiguousSmsError, FakeTelecom, RetryableSmsError
from text_back.worker import run_once


NOW = datetime(2026, 9, 17, 14, tzinfo=timezone.utc)
CALLER = "+15551112222"
BUSINESS_NUMBER = "+15553334444"
BASE_URL = "https://recover.example.test"
SECRET = "test-signalwire-e2e-signing-key"


class LocalSignalWire(FakeTelecom):
    provider_name: ClassVar[str] = "signalwire"


def _setup(tmp_path, monkeypatch, *, telecom=None):
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_FROM_NUMBER", BUSINESS_NUMBER)
    monkeypatch.setenv("TEXT_BACK_FOLLOWUP_DELAYS_MINUTES", "1,60")
    monkeypatch.setenv("TEXT_BACK_FOLLOWUP_EXPIRY_MINUTES", "120")
    monkeypatch.setenv("TEXT_BACK_QUIET_HOURS_START", "21:00")
    monkeypatch.setenv("TEXT_BACK_QUIET_HOURS_END", "08:00")
    store = Store(str(tmp_path / "recover.db"))
    calendar, delivery = CalendarStub(), InMemoryDeliveryTransport()
    selected_telecom = telecom if telecom is not None else LocalSignalWire()
    clock = SimpleNamespace(now=NOW)
    app = create_app(
        webhook_secret=SECRET,
        public_base_url=BASE_URL,
        store=store,
        telecom=selected_telecom,
        calendar=calendar,
        delivery_transport=delivery,
        business_name="Recovery Fixture",
        handoff_destination="operator-queue",
        timezone_name="UTC",
        wiring_mode="forwarded",
        now_provider=lambda: clock.now,
    )
    # Deliberately drive the worker manually. Separate lifespan tests cover
    # startup/shutdown without introducing background timing into these flows.
    return SimpleNamespace(
        app=app, store=store, calendar=calendar, delivery=delivery,
        telecom=selected_telecom, clock=clock, client=TestClient(app),
    )


def _signature(path, params):
    text = BASE_URL + path + "".join(key + value for key, value in sorted(params.items()))
    return base64.b64encode(hmac.new(SECRET.encode(), text.encode(), hashlib.sha1).digest()).decode()


def _post(runtime, path, params):
    response = runtime.client.post(
        path, data=params, headers={"X-SignalWire-Signature": _signature(path, params)}
    )
    assert response.status_code == 200, response.text
    assert ElementTree.fromstring(response.text).tag == "Response"
    return response


def _voice(runtime, call_sid):
    return _post(runtime, "/webhooks/voice", {
        "CallSid": call_sid, "CallStatus": "ringing", "From": CALLER, "To": BUSINESS_NUMBER,
    })


def _sms(runtime, message_sid, body):
    return _post(runtime, "/webhooks/sms", {
        "MessageSid": message_sid, "From": CALLER, "To": BUSINESS_NUMBER, "Body": body,
    })


def _events(runtime, event_type):
    return [event for event in runtime.store.list_outcome_events(CALLER) if event["event_type"] == event_type]


def test_signed_missed_call_qualification_booking_and_brief_have_provider_evidence(
    tmp_path, monkeypatch
):
    runtime = _setup(tmp_path, monkeypatch)
    _voice(runtime, "CA-e2e-book")
    _voice(runtime, "CA-e2e-book")
    assert [sms.kind for sms in runtime.telecom.outbound] == ["missed_call_intro"]

    for message_sid, body in (
        ("SM-service", "tree trimming"),
        ("SM-location", "12 Oak St"),
        ("SM-time", "2026-09-18 2:00 PM"),
        ("SM-name", "Test Customer"),
    ):
        _sms(runtime, message_sid, body)
    _sms(runtime, "SM-name", "Test Customer")

    assert len(runtime.calendar.events) == 1
    event_id = next(iter(runtime.calendar.events))
    assert runtime.store.appointment_by_conversation(CALLER)["event_id"] == event_id
    confirmations = [sms for sms in runtime.telecom.outbound if sms.kind == "booking_confirmation"]
    assert len(confirmations) == 1
    assert confirmations[0].kind == "booking_confirmation"  # the event id is stored, not texted
    assert _events(runtime, "calendar.event_created")[0]["evidence_id"] == event_id
    confirmed = _events(runtime, "appointment.confirmed")
    assert len(confirmed) == 1
    assert confirmed[0]["evidence_id"].startswith("SM-")
    assert confirmed[0]["metadata"]["calendar_event_id"] == event_id

    runtime.clock.now = NOW + timedelta(hours=2)
    run_once(runtime.app.state)
    assert runtime.app.state.worker_errors == []
    assert not any(sms.kind == "followup" for sms in runtime.telecom.outbound)
    brief = build_brief_data(
        runtime.store,
        period_start=NOW.replace(hour=0),
        period_end=(NOW + timedelta(days=1)).replace(hour=0),
    )
    assert brief["funnel"] == {
        "missed_calls": 1, "leads_contacted": 1, "leads_engaged": 1,
        "leads_qualified": 1, "appointments_booked": 1, "appointments_confirmed": 1,
        "handoffs": 0, "followups_sent": 0, "leads_expired": 0,
    }
    assert brief["attributed_revenue_cents"] == 0
    assert brief["confirmed_appointments"][0]["calendar_event_id"] == event_id


def test_signed_handoff_delivers_collected_lead_to_async_operator_once(tmp_path, monkeypatch):
    runtime = _setup(tmp_path, monkeypatch)
    _voice(runtime, "CA-e2e-handoff")
    _sms(runtime, "SM-service", "tree trimming")
    _sms(runtime, "SM-handoff", "human please")
    _sms(runtime, "SM-handoff", "human please")

    run_once(runtime.app.state)
    run_once(runtime.app.state)

    assert runtime.app.state.worker_errors == []
    assert len(runtime.delivery.delivered) == 1
    alert = runtime.delivery.delivered[0]
    assert alert.caller == CALLER
    assert alert.collected_fields == {"service": "tree trimming"}
    assert alert.latest_message == "human please"
    assert len(_events(runtime, "lead.handoff_requested")) == 1
    assert len(_events(runtime, "handoff.alert_delivered")) == 1
    assert len([sms for sms in runtime.telecom.outbound if sms.kind == "handoff_ack"]) == 1
    assert runtime.calendar.events == {}
    count = len(runtime.telecom.outbound)
    _sms(runtime, "SM-after-handoff", "another message")
    runtime.clock.now = NOW + timedelta(hours=2)
    run_once(runtime.app.state)
    assert len(runtime.telecom.outbound) == count


def test_signed_stop_cancels_a_followup_already_waiting_for_provider_retry(tmp_path, monkeypatch):
    class RejectFollowup(LocalSignalWire):
        followup_requests = 0

        def send_sms(self, **kwargs):
            if kwargs["kind"] == "followup":
                self.followup_requests += 1
                if self.followup_requests == 1:
                    raise RetryableSmsError("test provider rejected followup before acceptance")
            return super().send_sms(**kwargs)

    telecom = RejectFollowup()
    runtime = _setup(tmp_path, monkeypatch, telecom=telecom)
    _voice(runtime, "CA-e2e-stop")
    runtime.clock.now = NOW + timedelta(minutes=1)
    run_once(runtime.app.state)
    assert telecom.followup_requests == 1
    assert _events(runtime, "followup.sent") == []

    runtime.clock.now = NOW + timedelta(minutes=1, seconds=30)
    _sms(runtime, "SM-stop", "STOP")
    runtime.clock.now = NOW + timedelta(minutes=6)
    run_once(runtime.app.state)

    assert runtime.store.is_opted_out(CALLER)
    assert runtime.store.get_followup(CALLER)["status"] == "cancelled"
    assert telecom.followup_requests == 1
    assert [sms.kind for sms in telecom.outbound] == ["missed_call_intro", "opt_out_ack"]
    assert _events(runtime, "followup.sent") == []
    assert runtime.app.state.worker_errors == []


def test_signed_status_callback_reconciles_unknown_send_and_rejects_forged_receipt(
    tmp_path, monkeypatch
):
    class AcceptedWithoutResponse(LocalSignalWire):
        def send_sms(self, **kwargs):
            super().send_sms(**kwargs)
            raise AmbiguousSmsError("test accepted request lost its HTTP response")

    runtime = _setup(tmp_path, monkeypatch, telecom=AcceptedWithoutResponse())
    _voice(runtime, "CA-e2e-ambiguous")
    key = "CA-e2e-ambiguous:intro"
    assert runtime.store.get_sms(key)["status"] == "unknown"
    assert _events(runtime, "sms.initial_sent") == []
    path = "/webhooks/sms-status?key=" + quote(key, safe="")
    params = {"MessageSid": "SM-provider-receipt", "MessageStatus": "sent"}

    forged = runtime.client.post(path, data=params, headers={"X-SignalWire-Signature": "forged"})
    assert forged.status_code == 403
    assert runtime.store.get_sms(key)["status"] == "unknown"
    _post(runtime, path, params)
    _post(runtime, path, params)

    assert runtime.store.get_sms(key)["status"] == "sent"
    assert runtime.store.get_sms(key)["provider_id"] == "SM-provider-receipt"
    accepted = _events(runtime, "sms.initial_sent")
    assert len(accepted) == 1
    assert accepted[0]["evidence_id"] == "SM-provider-receipt"
    # Replaying the original call cannot submit the ambiguous message again.
    _voice(runtime, "CA-e2e-ambiguous")
    run_once(runtime.app.state)
    assert len(runtime.telecom.outbound) == 1
