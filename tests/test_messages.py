"""Per-client message copy: defaults, overrides, validation, hot reload."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from text_back import policy
from text_back.followup import followup_sms
from text_back.handlers import handle_sms_event, handle_voice_event
from text_back.calendar_stub import CalendarStub
from text_back.handoff import FakeHandoffNotifier
from text_back.messages import (
    DEFAULT_MESSAGES,
    DEFAULT_TEMPLATES,
    MessageSource,
    MessageTemplateError,
    load_message_file,
    validate_templates,
    write_message_file,
)
from text_back.store import Store
from text_back.telecom import FakeTelecom

NOW = datetime(2026, 10, 19, 10, 0, tzinfo=ZoneInfo("America/New_York"))


def test_defaults_match_the_policy_copy():
    assert policy.intro_sms("Acme") == DEFAULT_MESSAGES.render("intro", business_name="Acme")
    assert "Reply STOP to opt out." in policy.intro_sms("Acme")
    assert followup_sms("Acme", 2) == DEFAULT_MESSAGES.render("followup_2", business_name="Acme")
    assert policy.conversation_prompt("service") == DEFAULT_TEMPLATES["prompt_service"]


def test_custom_intro_without_stop_gets_the_opt_out_suffix_appended():
    messages = validate_templates({"intro": "Hi, {business_name} here. Missed you! What do you need?"})
    from text_back.messages import MessageSet
    text = MessageSet(messages).render("intro", business_name="Acme")
    assert text == "Hi, Acme here. Missed you! What do you need? Reply STOP to opt out."


def test_custom_opt_out_suffix_is_used_and_must_mention_stop():
    from text_back.messages import MessageSet
    custom = MessageSet(validate_templates({"intro": "Missed your call. What's up?", "opt_out_suffix": "Txt STOP to end."}))
    assert custom.render("intro", business_name="Acme").endswith("What's up? Txt STOP to end.")
    with pytest.raises(MessageTemplateError, match="STOP"):
        validate_templates({"opt_out_suffix": "Reply END to end."})


@pytest.mark.parametrize(
    ("templates", "match"),
    [
        ({"intro": "Call our business line any time"}, "business line"),
        ({"bogus": "x"}, "unknown message keys"),
        ({"intro": "Hi {customer_name}"}, "unsupported placeholder"),
        ({"intro": ""}, "cannot be empty"),
        ({"intro": "x" * 481}, "longer than"),
        ({"intro": 5}, "must be text"),
        ({"handoff_ack_safety": "We'll follow up soon."}, "911"),
        ({"booking_error": "Please call us"}, "no booking was made"),
        ({"intro": "Hi {}"}, "placeholders must look like"),
        ({"intro": "Hi {business_name"}, "unbalanced"),
        ({"prompt_name": "Name} please"}, "unbalanced"),
    ],
)
def test_bad_templates_are_rejected(templates, match):
    with pytest.raises(MessageTemplateError, match=match):
        validate_templates(templates)


def test_message_file_round_trip_writes_only_overrides(tmp_path):
    path = tmp_path / "messages.json"
    write_message_file(path, {**DEFAULT_TEMPLATES, "prompt_name": "And your name?"})
    assert json.loads(path.read_text()) == {"prompt_name": "And your name?"}
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    loaded = load_message_file(path)
    assert loaded.field_prompt("name") == "And your name?"
    assert loaded.render("intro", business_name="Acme") == DEFAULT_MESSAGES.render("intro", business_name="Acme")


def test_source_reloads_on_change_and_keeps_last_good_copy_on_a_bad_edit(tmp_path):
    path = tmp_path / "messages.json"
    path.write_text(json.dumps({"prompt_service": "What can we do for you?"}))
    source = MessageSource(str(path))
    assert source.current().field_prompt("service") == "What can we do for you?"
    import os, time
    path.write_text(json.dumps({"prompt_service": "Tell us the job."}))
    os.utime(path, (time.time() + 5, time.time() + 5))
    assert source.current().field_prompt("service") == "Tell us the job."
    path.write_text("{not json")
    os.utime(path, (time.time() + 10, time.time() + 10))
    assert source.current().field_prompt("service") == "Tell us the job."
    assert "JSON" in source.last_error


def test_source_without_a_file_uses_defaults_and_a_bad_file_fails_closed_at_boot(tmp_path):
    assert MessageSource(None).current() is DEFAULT_MESSAGES
    assert MessageSource(str(tmp_path / "missing.json")).current() is DEFAULT_MESSAGES
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"intro": "talk to a human"}))
    with pytest.raises(MessageTemplateError):
        MessageSource(str(bad))


def test_handlers_send_the_custom_copy():
    from text_back.messages import MessageSet
    messages = MessageSet(validate_templates({
        "intro": "{business_name} missed you. What do you need?",
        "prompt_location": "Where is the job?",
        "opt_out_ack": "Done, no more texts from {business_name}.",
    }))
    store = Store(":memory:")
    telecom = FakeTelecom()
    handle_voice_event(store=store, telecom=telecom, call_sid="CA1", call_status="ringing",
                       from_number="+15551112222", to_number="+15553334444", wiring_mode="forwarded",
                       business_name="Acme", now=NOW, messages=messages)
    assert telecom.outbound[-1].body == "Acme missed you. What do you need? Reply STOP to opt out."
    common = dict(store=store, calendar=CalendarStub(timezone_name="America/New_York"), telecom=telecom,
                  handoff_notifier=FakeHandoffNotifier(), handoff_destination="ops",
                  from_number="+15551112222", to_number="+15553334444", business_name="Acme",
                  timezone_name="America/New_York", appointment_duration_minutes=60, now=NOW, messages=messages)
    handle_sms_event(message_sid="SM1", body="tree removal", **common)
    assert telecom.outbound[-1].body == "Where is the job?"
    handle_sms_event(message_sid="SM2", body="STOP", **common)
    assert telecom.outbound[-1].body == "Done, no more texts from Acme."


def test_business_name_containing_stop_still_gets_the_opt_out_line():
    from text_back.messages import MessageSet
    custom = MessageSet(validate_templates({"intro": "{business_name} missed your call. What do you need?"}))
    text = custom.render("intro", business_name="Pitstop Tire")
    assert text.endswith("What do you need? Reply STOP to opt out.")
    with pytest.raises(MessageTemplateError, match="STOP"):
        validate_templates({"opt_out_suffix": "Pitstop says bye."})


def test_render_never_raises_on_a_template_that_slipped_past_validation():
    from text_back.messages import MessageSet
    broken = MessageSet({**DEFAULT_TEMPLATES, "prompt_service": "Hi {business_name"})
    assert broken.field_prompt("service", business_name="Acme") == DEFAULT_TEMPLATES["prompt_service"]


def test_booking_retry_lane_uses_the_client_copy(tmp_path):
    """A slot taken during a deferred calendar retry must text the client's wording."""
    from datetime import timedelta, timezone
    from text_back.app import create_app
    from text_back.calendars.protocol import CalendarProviderError
    from text_back.worker import run_once

    class FlakyThenBusy(CalendarStub):
        mode = "outage"

        def is_free(self, start, end):
            if self.mode == "outage":
                raise CalendarProviderError("temporary outage")
            return False  # slot taken once the calendar is back

    path = tmp_path / "messages.json"
    path.write_text(json.dumps({"slot_unavailable": "That slot is gone. Another day and time?"}))
    now = datetime(2026, 9, 17, 14, tzinfo=timezone.utc)
    clock = [now]
    calendar = FlakyThenBusy()
    app = create_app(db_path=str(tmp_path / "b.db"), calendar=calendar, telecom=FakeTelecom(), now_provider=lambda: clock[0])
    app.state.messages = MessageSource(str(path))
    for i, body in enumerate(["trimming", "Oak St", "2026-09-18 14:00", "Pat"]):
        handle_sms_event(store=app.state.store, calendar=calendar, telecom=app.state.telecom,
                         handoff_notifier=app.state.handoff_notifier, handoff_destination="queue",
                         message_sid=f"m{i}", from_number="+15551112222", to_number="+15553334444", body=body,
                         business_name="Acme", timezone_name="UTC", appointment_duration_minutes=60, now=now,
                         messages=app.state.messages.current())
    assert not app.state.store.appointment_by_conversation("+15551112222")
    calendar.mode = "busy"
    clock[0] += timedelta(minutes=2)
    run_once(app.state)
    bodies = [m.body for m in app.state.telecom.outbound if m.kind == "slot_unavailable"]
    assert bodies == ["That slot is gone. Another day and time?"]
