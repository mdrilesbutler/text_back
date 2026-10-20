"""Redesigned client settings pages: grouping, previews, counts, defaults state,
per-message errors, no-JS reset, security headers and calendar states."""
import json
import re

from text_back.calendars.protocol import CalendarProviderError
from text_back.client_portal import (
    DEFAULT_TEMPLATES,
    FIELD_KEYS,
    GROUPS,
    OPTIONAL_QUESTIONS,
    blame,
    preview_text,
    sms_parts,
)
from test_client_portal import csrf_of, make, sign_in
from test_client_settings import google_fixture

SAMPLE = {"business_name": "Oak & Pine", "service": "tree removal", "when": "Thursday at 4", "location": "12 Elm St",
          "invite_line": "Invite sent.", "calendar_links": "Add to calendar: x", "contact_line": " Contact: (980) 555-0100."}


def card(page_html, key):
    match = re.search(rf"<section class='msg[^']*' id=m_{key} .*?</section>", page_html, re.S)
    assert match, f"no card for {key}"
    return match.group(0)


# --- grouping ---------------------------------------------------------------------

def test_every_message_is_shown_once_in_conversation_order():
    assert sorted(FIELD_KEYS) == sorted(k for k in DEFAULT_TEMPLATES if k != "fields")
    assert len(set(FIELD_KEYS)) == len(FIELD_KEYS)
    assert [heading for _, heading, _, _ in GROUPS] == [
        "Missed call", "The questions", "Booking", "No reply", "You step in", "START, HELP and STOP"]
    assert GROUPS[0][3] == ("intro",)
    questions = GROUPS[1][3]
    assert questions[:3] == ("prompt_service", "prompt_location", "prompt_preferred_time")
    assert questions.index("prompt_name") < questions.index("prompt_phone") < questions.index("prompt_email")
    assert set(OPTIONAL_QUESTIONS) == {"prompt_phone", "prompt_email"}


def test_page_renders_groups_in_order_with_toggles_on_the_optional_questions(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/messages").text
    positions = [page.index(f"id=g_{gid}") for gid, _, _, _ in GROUPS]
    assert positions == sorted(positions)
    for key in FIELD_KEYS:
        assert f"id=m_{key}" in page
    assert "name=ask_phone" in card(page, "prompt_phone") and "name=ask_email" in card(page, "prompt_email")
    assert "name=ask_phone" not in card(page, "intro")
    assert "Save messages" in page and "data-dirty" in page


# --- preview and counts ---------------------------------------------------------------

def test_preview_fills_placeholders_and_appends_the_opt_out_line_where_carriers_require_it():
    templates = dict(DEFAULT_TEMPLATES)
    intro = preview_text("intro", templates, SAMPLE)
    assert intro.startswith("Hey, sorry we missed your call—this is Oak & Pine's scheduling assistant.")
    assert intro.endswith("Reply STOP to opt out.")
    templates["intro"] = "Oak here. Txt STOP to end."
    assert preview_text("intro", templates, SAMPLE) == "Oak here. Txt STOP to end."
    templates["opt_out_suffix"] = "Text STOP any time."
    templates["intro"] = "{business_name} missed you!"
    assert preview_text("intro", templates, SAMPLE) == "Oak & Pine missed you! Text STOP any time."
    assert "Reply STOP" not in preview_text("prompt_name", templates, SAMPLE)
    confirmation = preview_text("booking_confirmation", templates, SAMPLE)
    assert "tree removal on Thursday at 4 at 12 Elm St" in confirmation and "Add to calendar: x" in confirmation
    assert "Contact: (980) 555-0100." in preview_text("help", templates, SAMPLE)
    # A placeholder the preview has no value for, or broken braces, never crash the page.
    assert preview_text("intro", {**templates, "intro": "Hi {nope}"}, SAMPLE).startswith("Hi {nope}")
    assert preview_text("intro", {**templates, "intro": "Hi {"}, SAMPLE).startswith("Hi {")


def test_segment_count_knows_the_gsm_alphabet():
    assert sms_parts("Hello there") == (11, 1, True)
    assert sms_parts("a" * 160) == (160, 1, True)
    assert sms_parts("a" * 161) == (161, 2, True)
    assert sms_parts("a" * 306) == (306, 2, True)
    assert sms_parts("a" * 307) == (307, 3, True)
    assert sms_parts("€" * 80) == (80, 1, True)   # extension characters cost two
    assert sms_parts("€" * 81) == (81, 2, True)
    assert sms_parts("—" + "a" * 69) == (70, 1, False)
    assert sms_parts("—" + "a" * 70) == (71, 2, False)


def test_page_shows_the_rendered_preview_and_count_for_each_message(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/messages").text
    intro = card(page, "intro")
    assert "Oak &amp; Pine Tree Care&#x27;s scheduling assistant" in intro and "Reply STOP to opt out." in intro
    assert re.search(r"data-count>\d+ characters · [23] texts \(symbols like — shorten each text\)<", intro)  # the em dash
    assert re.search(r"data-count>\d+ characters · 1 text<", card(page, "prompt_name"))
    assert "Contact: (980) 555-0100" not in page  # no contact configured: the HELP preview shows the sender instead


# --- defaults state, reset, errors --------------------------------------------------------

def test_standard_versus_customized_state_and_reset_without_javascript(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/messages").text
    assert page.count("Standard wording</span>") == len(FIELD_KEYS) and "Customized</span>" not in page
    assert "data-reset hidden" in card(page, "intro")
    csrf = csrf_of(page)
    saved = client.post("/client/messages", data={"csrf": csrf, "intro": "Oak here, missed you. What do you need?"}).text
    intro = card(saved, "intro")
    assert "Customized</span>" in intro and "data-reset>" in intro and "data-reset hidden" not in intro
    assert saved.count("Customized</span>") == 1
    assert "Oak here, missed you. What do you need? Reply STOP to opt out." in intro  # preview of the custom text
    # The reset button is a real submit: posting reset=intro with the old text still in the field clears it.
    back = client.post("/client/messages", data={"csrf": csrf, "intro": "Oak here, missed you. What do you need?", "reset": "intro"}).text
    assert "Saved" in back and "Standard wording</span>" in card(back, "intro")
    assert json.loads(path.read_text()) == {}


def test_a_rejected_save_marks_the_message_and_keeps_what_was_typed(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/messages").text)
    typed = "Call our business line any time"
    page = client.post("/client/messages", data={"csrf": csrf, "intro": typed, "prompt_name": "Your name?"}).text
    assert "Not saved. Fix <a href=#m_intro>First text after a missed call</a>" in page
    intro = card(page, "intro")
    assert "class='msg bad'" in intro and "business line" in intro and f">{typed}</textarea>" in intro
    assert "aria-invalid=true" in intro and "class='msg bad'" not in card(page, "prompt_name")
    assert ">Your name?</textarea>" in card(page, "prompt_name")  # the other edit survives the round trip
    assert not path.exists()
    page = client.post("/client/messages", data={"csrf": csrf, "handoff_ack_safety": "Paused. Call 911 if in danger."}).text
    assert "class='msg bad'" in card(page, "handoff_ack_safety") and "follow-up" in card(page, "handoff_ack_safety")
    page = client.post("/client/messages", data={"csrf": csrf, "booking_error": "Oops {"}).text
    assert "class='msg bad'" in card(page, "booking_error") and "unbalanced" in card(page, "booking_error")


def test_blame_points_at_the_right_message():
    templates = dict(DEFAULT_TEMPLATES)
    assert blame("intro is longer than 480 characters", templates) == ("intro", "is longer than 480 characters")
    assert blame("opt_out_suffix must tell the customer to reply STOP", templates) == ("opt_out_suffix", "must tell the customer to reply STOP")
    assert blame("handoff_ack_safety must direct emergencies to 911", templates) == ("handoff_ack_safety", "must direct emergencies to 911")
    assert blame("handoff acknowledgements must promise a follow-up", {**templates, "handoff_ack": "Paused."}) == ("handoff_ack", "must promise a follow-up")
    assert blame("unbalanced { or } in template", {**templates, "followup_2": "Hi }"}) == ("followup_2", "unbalanced { or } in template")
    assert blame("questions must include name", templates) == (None, "questions must include name")


def test_optional_questions_are_switched_on_from_their_own_cards(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/messages").text)
    page = client.post("/client/messages", data={"csrf": csrf, "ask_email": "1"}).text
    assert json.loads(path.read_text()) == {"fields": "service, location, preferred_time, name, email"}
    assert "name=ask_email value=1 checked" in card(page, "prompt_email") and "name=ask_phone value=1 checked" not in page
    page = client.post("/client/messages", data={"csrf": csrf, "ask_email": "1", "ask_phone": "1"}).text
    assert json.loads(path.read_text()) == {"fields": "service, location, preferred_time, name, phone, email"}
    # A rejected save keeps the toggles as submitted.
    page = client.post("/client/messages", data={"csrf": csrf, "ask_phone": "1", "intro": "Ask for a representative"}).text
    assert "Not saved" in page and "name=ask_phone value=1 checked" in card(page, "prompt_phone")


# --- frame, sign-in, security ---------------------------------------------------------

def test_every_page_is_self_contained_and_sends_the_security_headers(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    pages = [client.get("/client/login")]
    client.post("/client/login", data={"mobile": "980 555 0123"}, follow_redirects=False)
    pages.append(client.get("/client/verify"))
    sign_in(client, telecom)
    pages += [client.get(url) for url in ("/client/messages", "/client/business", "/client/calendar")]
    for response in pages:
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["x-frame-options"] == "DENY"
        text = response.text
        assert "<link" not in text and "src=http" not in text and "src='http" not in text and 'src="http' not in text
        assert "fonts.googleapis" not in text and "@import" not in text
        assert text.count("<style>") == 1
        assert "width=device-width" in text


def test_sign_in_pages_lead_with_the_business_and_autofill_the_code(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    login = client.get("/client/login").text
    assert "<h1>Oak &amp; Pine Tree Care</h1>" in login and "autocomplete=tel" in login
    client.post("/client/login", data={"mobile": "980 555 0123"}, follow_redirects=False)
    verify = client.get("/client/verify").text
    assert "autocomplete=one-time-code" in verify and "inputmode=numeric" in verify and "Check your phone" in verify
    assert "0123" not in verify  # the page never echoes the number, on file or not


def test_business_page_explains_each_field_and_the_mobile_change_is_a_step(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/business").text
    assert "Sign-in codes come to this number" in page and "texts HELP" in page
    csrf = csrf_of(page)
    step = client.post("/client/business", data={"csrf": csrf, "business_name": "Oak", "business_contact": "", "owner_mobile": "980 555 0199"}).text
    assert "class='step done'>1. Details saved" in step and "class='step now'>2. Confirm the new number" in step
    assert "autocomplete=one-time-code" in step and "Keep my current mobile" in step


# --- calendar states ------------------------------------------------------------------

def test_calendar_page_shows_test_mode_when_no_calendar_is_connected(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/calendar").text
    assert "Test mode: no calendar connected" in page and "class='status none'" in page
    assert "Connect Google Calendar" not in page and "<input type=radio" not in page


def test_calendar_page_shows_reconnect_needed_unreadable_and_connected_with_a_radio_picker(tmp_path, monkeypatch):
    client, telecom, credentials, transport = google_fixture(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/calendar").text
    assert "Reconnect needed" in page and "class='status warn'" in page and "Connect Google Calendar" in page
    assert "What Google will ask" in page and "Nothing else in that account is read" in page

    monkeypatch.setattr(credentials, "status", lambda: (_ for _ in ()).throw(CalendarProviderError("boom")))
    page = client.get("/client/calendar").text
    assert "could not be read" in page and "class='status err'" in page and "Reconnect Google Calendar" not in page
    monkeypatch.undo()

    monkeypatch.setattr(credentials, "status", lambda: "ready")
    from text_back.client_settings import remember_calendars
    remember_calendars(client.app.state, [{"id": "a@x", "summary": "Personal", "primary": True}, {"id": "b@x", "summary": "Tree jobs"}], clock_now())
    page = client.get("/client/calendar").text
    assert "Connected to Google Calendar" in page and "class='status ok'" in page and "Reconnect Google Calendar" in page
    assert page.count("<input type=radio") == 2 and "class=choice" in page and "Use this calendar" in page


def clock_now():
    from test_client_settings import NOW
    return NOW
