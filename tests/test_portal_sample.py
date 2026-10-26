"""The Messages page's example conversation is the real policy code run on a script.

Nothing in a textback bubble is hand-written: every one equals a rendered
template, and the booked example ends with a confirmation that carries the
event id the (stub) calendar actually returned.
"""
import re
from datetime import datetime, timezone

from text_back.messages import DEFAULT_TEMPLATES, MessageSet, validate_templates
from text_back.policy import classify_handoff_request, help_sms
from text_back.portal_sample import SCENARIOS, TEXTING_NUMBER, Bubble, render_scenario, run_script

NOW = datetime(2026, 10, 26, 14, 0, tzinfo=timezone.utc)  # a Monday
BASE = "https://portal.example.test:8443"
BUSINESS = "Oak & Pine Tree Care"
TZ = "America/New_York"


def bubbles(name, *, templates=None, asked=frozenset({"phone", "email"})):
    return render_scenario(name, templates=templates or {}, business_name=BUSINESS, asked=set(asked),
                           now=NOW, public_base_url=BASE, tz_name=TZ)


def textback(items):
    return [b for b in items if b.side == "textback"]


def test_booked_script_ends_with_a_confirmation_carrying_a_real_event_id_and_links():
    templates = {"booking_confirmation": "Booked {service} on {when} at {location} (ref {event_id}). {calendar_links}"}
    items = bubbles("booked", templates=templates)
    assert items[0] == Bubble(side="event", text="Missed call", key=None)
    assert [b.key for b in textback(items)][:2] == ["intro", "prompt_location"]
    last = textback(items)[-1]
    assert last.key == "booking_confirmation"
    assert "ref evt-0001" in last.text, "the event id must come from the calendar, not be typed"
    assert f"{BASE}/a/" in last.text and last.text.count(f"{BASE}/a/") == 3
    assert items[-1] == Bubble(side="event", text="Booked on the calendar", key=None)
    assert [b.text for b in items if b.side == "customer"] == list(SCENARIOS["booked"].script)


def test_steps_back_reply_really_triggers_a_handoff():
    phrase = SCENARIOS["steps_back"].script[-1]
    assert classify_handoff_request(phrase) == "customer_requested"
    items = bubbles("steps_back")
    assert textback(items)[-1].key == "handoff_ack"
    assert "follow up" in textback(items)[-1].text.lower()


def test_safety_reply_triggers_the_safety_ack_with_911():
    phrase = SCENARIOS["safety"].script[-1]
    assert classify_handoff_request(phrase) == "safety"
    last = textback(bubbles("safety"))[-1]
    assert last.key == "handoff_ack_safety"
    assert "911" in last.text


def _template_regex(template: str) -> re.Pattern:
    parts = re.split(r"\{[a-z_]+\}", template)
    return re.compile(r"^\s*" + r".*".join(re.escape(" ".join(p.split())) for p in parts) + r"\s*$", re.S)


def test_every_textback_bubble_equals_a_rendered_template():
    custom = {
        "intro": "Custom hello from {business_name}. What do you need? Reply STOP to opt out.",
        "prompt_location": "Custom: where is the job?",
        "handoff_ack": "Custom: paused, the owner will follow up.",
        "booking_error": "Custom: no booking was made, send another time please.",
    }
    messages = MessageSet(validate_templates(custom))
    seen_keys = set()
    for name in SCENARIOS:
        for bubble in textback(bubbles(name, templates=custom)):
            assert bubble.key is not None, (name, bubble.text)
            seen_keys.add(bubble.key)
            template = messages.templates[bubble.key]
            if bubble.key == "booking_confirmation":
                assert _template_regex(template).match(bubble.text), (name, bubble.key, bubble.text)
            elif bubble.key == "help":
                assert bubble.text == help_sms(BUSINESS, "", TEXTING_NUMBER, messages), (name, bubble.text)
            else:
                assert bubble.text == messages.render(bubble.key, business_name=BUSINESS), (name, bubble.key)
    assert {"intro", "prompt_location", "handoff_ack", "booking_error", "followup_1", "followup_2",
            "opt_in", "help", "opt_out_ack", "preferred_time_reprompt", "phone_reprompt", "email_reprompt"} <= seen_keys


def test_optional_questions_appear_only_when_asked():
    without = bubbles("booked", asked=set())
    keys = [b.key for b in textback(without)]
    assert "prompt_phone" not in keys and "prompt_email" not in keys
    assert "YES" not in [b.text for b in without] and "dana@example.com" not in [b.text for b in without]
    assert keys[-1] == "booking_confirmation"

    with_both = bubbles("booked", asked={"phone", "email"})
    keys = [b.key for b in textback(with_both)]
    assert keys.index("prompt_phone") < keys.index("prompt_email") < keys.index("booking_confirmation")

    unclear = [b.key for b in textback(bubbles("unclear", asked={"phone"}))]
    assert "phone_reprompt" in unclear and "email_reprompt" not in unclear
    assert "preferred_time_reprompt" in unclear


def test_failed_booking_ends_with_booking_error_and_no_event():
    items = bubbles("failed")
    assert textback(items)[-1].key == "booking_error"
    assert "no booking was made" in textback(items)[-1].text.lower()
    assert all(b.text != "Booked on the calendar" for b in items)
    assert all("/a/" not in b.text for b in textback(items))


def test_keywords_scenario_renders_opt_in_help_and_opt_out():
    items = bubbles("keywords")
    assert [b.text for b in items if b.side == "customer"] == ["START", "HELP", "STOP"]
    assert [b.key for b in textback(items)] == ["intro", "opt_in", "help", "opt_out_ack"]
    assert "STOP" in textback(items)[1].text and "STOP" in textback(items)[2].text


def test_noreply_scenario_uses_the_followup_templates_then_stops():
    items = bubbles("noreply")
    assert [b.key for b in textback(items)] == ["intro", "followup_1", "followup_2"]
    assert items[-1] == Bubble(side="event", text="Texting stops here", key=None)
    assert all(b.side != "customer" for b in items)


def test_run_script_uses_the_given_templates_and_public_host():
    items = run_script(templates={"intro": "Hi from {business_name}. Reply STOP to opt out."}, business_name=BUSINESS,
                       asked=set(), script=(), now=NOW, public_base_url=BASE, tz_name=TZ)
    assert [b.text for b in items] == ["Missed call", f"Hi from {BUSINESS}. Reply STOP to opt out."]
    assert DEFAULT_TEMPLATES["intro"] != items[1].text


def test_scenarios_carry_plain_labels():
    assert set(SCENARIOS) == {"booked", "unclear", "noreply", "failed", "steps_back", "safety", "keywords"}
    for scenario in SCENARIOS.values():
        assert scenario.label and "{" not in scenario.label
