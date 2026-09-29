"""Carrier-required opt-out / opt-in / HELP keyword handling (CTIA + FCC 2025)."""

import pytest

from text_back import policy
from text_back.handlers import handle_sms_event, handle_voice_event
from text_back.calendar_stub import CalendarStub
from text_back.handoff import FakeHandoffNotifier
from text_back.store import Store
from text_back.telecom import FakeTelecom

CALLER = "+15551112222"
BUSINESS = "+15553334444"


def _sms(store, telecom, sid, body, **extra):
    return handle_sms_event(
        store=store, calendar=CalendarStub(), telecom=telecom,
        handoff_notifier=FakeHandoffNotifier(), handoff_destination="ops",
        message_sid=sid, from_number=CALLER, to_number=BUSINESS, body=body,
        business_name="Mike's Tree Care", timezone_name="UTC",
        appointment_duration_minutes=60, **extra,
    )


@pytest.mark.parametrize("body", [
    "STOP", "stop", "Stop.", "STOPALL", "UNSUBSCRIBE", "CANCEL", "END", "QUIT",
    "OPTOUT", "REVOKE", "opt out", "Opt-out", "stop please", "please stop texting me",
    "unsubscribe me", "Do not text me",
])
def test_opt_out_keywords_and_phrases(body):
    assert policy.classify_inbound_sms(body) == "stop"


@pytest.mark.parametrize("body", ["START", "start", "UNSTOP", "Unstop!", "SUBSCRIBE"])
def test_opt_in_keywords(body):
    assert policy.classify_inbound_sms(body) == "start"


@pytest.mark.parametrize("body", [
    "Tree removal", "start time 2pm works", "the stump is at the end of the drive",
    "yes", "123 Main St", "do not text before 9", "stop-by Thursday works",
    "unstop all", "please don't text my wife, text me",
])
def test_ordinary_answers_are_conversation(body):
    assert policy.classify_inbound_sms(body) == "conversation"


def test_stop_records_opt_out_evidence_and_start_resubscribes():
    store, telecom = Store(), FakeTelecom()
    assert _sms(store, telecom, "SM-1", "revoke")["action"] == "opt_out"
    assert store.is_opted_out(CALLER)

    result = _sms(store, telecom, "SM-2", "UNSTOP")
    assert result["action"] == "opt_in"
    assert not store.is_opted_out(CALLER)
    assert [m.kind for m in telecom.outbound] == ["opt_out_ack", "opt_in_ack"]
    ack = telecom.outbound[-1].body
    assert "Mike's Tree Care" in ack and "STOP" in ack
    events = [e["event_type"] for e in store.list_outcome_events(CALLER)]
    assert "lead.opted_out" in events and "lead.opted_in" in events


def test_yes_resubscribes_only_an_opted_out_contact():
    store, telecom = Store(), FakeTelecom()
    _sms(store, telecom, "SM-1", "STOP")
    assert _sms(store, telecom, "SM-2", "Yes")["action"] == "opt_in"
    assert not store.is_opted_out(CALLER)


def test_resubscribed_contact_gets_the_next_missed_call_intro():
    store, telecom = Store(), FakeTelecom()
    _sms(store, telecom, "SM-1", "STOP")
    _sms(store, telecom, "SM-2", "START")
    telecom.outbound.clear()
    result = handle_voice_event(
        store=store, telecom=telecom, call_sid="CA-1", call_status="ringing",
        from_number=CALLER, to_number=BUSINESS, wiring_mode="forwarded",
        business_name="Mike's Tree Care",
    )
    assert result["action"] == "sent_intro"
    assert [m.kind for m in telecom.outbound] == ["missed_call_intro"]


def test_help_names_business_contact_rates_and_stop():
    store, telecom = Store(), FakeTelecom()
    _sms(store, telecom, "SM-1", "HELP", business_contact="mikestreecare.com")
    body = telecom.outbound[0].body
    assert "Mike's Tree Care" in body
    assert "mikestreecare.com" in body
    assert "Msg & data rates may apply" in body
    assert "STOP" in body


def test_help_falls_back_to_the_text_number_as_contact():
    body = policy.help_sms("Mike's Tree Care", "", BUSINESS)
    assert "(555) 333-4444" in body
    assert "call" not in body.lower()


def test_help_is_answered_even_for_opted_out_contacts():
    store, telecom = Store(), FakeTelecom()
    _sms(store, telecom, "SM-1", "STOP")
    _sms(store, telecom, "SM-2", "HELP")
    assert [m.kind for m in telecom.outbound] == ["opt_out_ack", "help"]
