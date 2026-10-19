"""Optional phone and email questions, chosen per client."""
import json
import re
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.calendar_stub import CalendarStub
from text_back.handlers import handle_sms_event
from text_back.messages import MessageSet, MessageSource, MessageTemplateError, validate_templates
from text_back.policy import EMAIL_SKIPPED, parse_contact_email, parse_contact_phone
from text_back.telecom import FakeTelecom

NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
CALLER = "+15551112222"


@pytest.mark.parametrize(("raw", "expected"), [
    ("yes", CALLER), ("YES", CALLER), ("this one", CALLER), ("Same", CALLER),
    ("704 555 0123", "+17045550123"), ("(704) 555-0123", "+17045550123"), ("17045550123", "+17045550123"),
    ("+44 20 7946 0958", "+442079460958"), ("call me at 7045550123", "+17045550123"),
    ("555", None), ("no number", None),
])
def test_parse_contact_phone(raw, expected):
    assert parse_contact_phone(raw, CALLER) == expected


@pytest.mark.parametrize(("raw", "expected"), [
    ("pat@example.com", "pat@example.com"), ("  Pat.Lee@Example.COM. ", "pat.lee@example.com"),
    ("skip", EMAIL_SKIPPED), ("No thanks", EMAIL_SKIPPED), ("none", EMAIL_SKIPPED),
    ("pat@", None), ("pat at example dot com", None), ("@example.com", None),
])
def test_parse_contact_email(raw, expected):
    assert parse_contact_email(raw) == expected


def test_fields_setting_is_validated():
    assert MessageSet(validate_templates({"fields": "service, location, preferred_time, name, phone, email"})).fields == (
        "service", "location", "preferred_time", "name", "phone", "email")
    assert MessageSet(validate_templates({})).fields == ("service", "location", "preferred_time", "name")
    with pytest.raises(MessageTemplateError, match="unknown question"):
        validate_templates({"fields": "service, location, preferred_time, name, shoe_size"})
    with pytest.raises(MessageTemplateError, match="must include"):
        validate_templates({"fields": "service, name"})
    with pytest.raises(MessageTemplateError, match="twice"):
        validate_templates({"fields": "service, location, preferred_time, name, name"})


def conversation(tmp_path, fields):
    telecom = FakeTelecom()
    calendar = CalendarStub(timezone_name="America/New_York")
    app = create_app(db_path=str(tmp_path / "c.db"), calendar=calendar, telecom=telecom, public_base_url="https://example.test",
                     business_name="Acme", timezone_name="America/New_York", now_provider=lambda: NOW)
    messages = MessageSet(validate_templates({"fields": fields}))
    counter = [0]

    def say(body):
        counter[0] += 1
        return handle_sms_event(store=app.state.store, calendar=calendar, telecom=telecom, handoff_notifier=app.state.handoff_notifier,
                                handoff_destination="ops", message_sid=f"m{counter[0]}", from_number=CALLER, to_number="+15553334444",
                                body=body, business_name="Acme", timezone_name="America/New_York", appointment_duration_minutes=60,
                                now=NOW, messages=messages)
    return app, telecom, say


def test_phone_and_email_are_asked_validated_and_stored_before_booking(tmp_path):
    app, telecom, say = conversation(tmp_path, "service, location, preferred_time, name, phone, email")
    say("tree trimming"); say("12 Oak St"); say("thursday at 4"); say("Pat Lee")
    assert telecom.outbound[-1].body.startswith("Is this the best number")
    assert say("5551") ["action"] == "phone_invalid"
    assert telecom.outbound[-1].kind == "phone_reprompt"
    say("yes")
    assert telecom.outbound[-1].body.startswith("What's your email")
    assert say("pat at example")["action"] == "email_invalid"
    assert telecom.outbound[-1].kind == "email_reprompt"
    result = say("Pat.Lee@example.com")
    assert result["action"] == "booked"
    fields = app.state.store.get_conversation_fields(CALLER)
    assert fields["phone"] == CALLER and fields["email"] == "pat.lee@example.com"
    assert telecom.outbound[-1].kind == "booking_confirmation"


def test_email_can_be_skipped_and_order_is_the_clients(tmp_path):
    app, telecom, say = conversation(tmp_path, "name, email, service, location, preferred_time")
    assert telecom.outbound == []
    say("Pat Lee")
    assert telecom.outbound[-1].body.startswith("What's your email")
    say("skip")
    assert telecom.outbound[-1].body.startswith("What's the job")
    say("trim"); say("12 Oak St")
    assert say("thursday at 4")["action"] == "booked"
    assert app.state.store.get_conversation_fields(CALLER)["email"] == EMAIL_SKIPPED


def test_default_question_list_is_unchanged(tmp_path):
    app, telecom, say = conversation(tmp_path, "service, location, preferred_time, name")
    say("trim"); say("12 Oak St"); say("thursday at 4")
    assert say("Pat")["action"] == "booked"


def test_settings_page_checkboxes_write_the_question_list(tmp_path, monkeypatch):
    monkeypatch.setenv("TEXT_BACK_OWNER_MOBILE", "+19805550123")
    path = tmp_path / "messages.json"
    monkeypatch.setenv("TEXT_BACK_MESSAGES_FILE", str(path))
    telecom = FakeTelecom()
    app = create_app(db_path=str(tmp_path / "p.db"), telecom=telecom, public_base_url="https://example.test",
                     business_name="Acme", now_provider=lambda: NOW)
    client = TestClient(app, base_url="https://example.test")
    client.post("/client/login", data={"mobile": "+19805550123"}, follow_redirects=False)
    code = re.search(r"\b(\d{6})\b", [m for m in telecom.outbound if m.kind == "login_code"][-1].body).group(1)
    client.post("/client/verify", data={"code": code}, follow_redirects=False)
    page = client.get("/client/messages").text
    assert "Also ask for an email address" in page and "checked" not in page
    csrf = re.search(r"name=csrf value='([^']+)'", page).group(1)
    saved = client.post("/client/messages", data={"csrf": csrf, "ask_email": "1"}).text
    assert "Saved" in saved and 'name=ask_email value=1 checked' in saved
    assert json.loads(path.read_text()) == {"fields": "service, location, preferred_time, name, email"}
    assert app.state.messages.current().fields[-1] == "email"
    client.post("/client/messages", data={"csrf": csrf})
    assert json.loads(path.read_text()) == {}
