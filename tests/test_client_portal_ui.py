"""Redesigned client settings pages: grouping, previews, counts, defaults state,
per-message errors, no-JS reset, security headers and calendar states.

Markup assertions use the stable hooks of docs/notes/ui-compare-a/implementation-plan.md §F
(ids and data-* attributes); tests/test_portal_frontend.py covers the page-wide invariants."""
import json
import re

from text_back.calendars.protocol import CalendarProviderError
from text_back.client_portal import (
    DEFAULT_TEMPLATES,
    FIELD_KEYS,
    GROUPS,
    OPTIONAL_QUESTIONS,
    bill_label,
    blame,
    chips_for,
    count_label,
    friendly_reason,
    preview_parts,
    preview_text,
    sms_parts,
)
from text_back.client_settings import status_view
from text_back.messages import MessageTemplateError, validate_templates
from test_client_portal import csrf_of, make, sign_in
from test_client_settings import google_fixture

SAMPLE = {"business_name": "Oak & Pine", "service": "tree removal", "when": "Thursday at 4", "location": "12 Elm St",
          "invite_line": "Invite sent.", "calendar_links": "Add to calendar: x", "contact_line": " Contact: (980) 555-0100."}


def card(page_html, key):
    match = re.search(rf'<article class="msg[^"]*" id=m_{key} .*?</article>', page_html, re.S)
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
    assert "Save changes" in page and "data-savebar" in page and "data-dirty" in page


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
    assert "Oak &amp; Pine Tree Care&#39;s scheduling assistant" in intro
    assert "<span class=sms__suffix>Reply STOP to opt out.</span>" in intro  # the added line is its own span
    assert "STOP line added for you" in intro and "data-optout-note hidden" not in intro
    # Receipt: texts first; from 2 texts it says why, naming the first symbol outside the plain alphabet.
    assert re.search(r"data-count>[23] texts · \d+ characters<", intro) and "data-warn" in intro
    assert "The \u201c\u2014\u201d symbol limits each text to 70 characters." in intro  # the em dash
    name = card(page, "prompt_name")
    assert re.search(r"data-count>1 text · \d+ characters<", name) and "data-warn" not in name
    assert "STOP line added" not in name  # no opt-out line on a question
    assert "Contact: (980) 555-0100" not in page  # no contact configured: the HELP preview shows the sender instead
    # One speaker, no role badges; a customer bubble in the preview brings them back.
    assert "sms__badge" not in name and "sms__badge>Customer<" in card(page, "preferred_time_reprompt")
    confirmation = card(page, "booking_confirmation")
    assert "<span class=sms__link>http" in confirmation  # links may break anywhere, the rest wraps normally


def test_receipt_labels_count_texts_first_and_explain_billing():
    assert count_label("Hello") == "1 text · 5 characters"
    assert count_label("a" * 161) == "2 texts · 161 characters"
    assert bill_label("a" * 160) == "" and bill_label("Hi \u2014 there") == ""
    assert bill_label("a" * 161) == "Billed as 2 texts. Customers still see one message."
    assert bill_label("\u20ac" * 81) == "Billed as 2 texts. Customers still see one message."  # extension characters stay plain
    assert bill_label("It\u2019s " + "a" * 70) == "Billed as 2 texts. The \u201c\u2019\u201d symbol limits each text to 70 characters."
    assert preview_parts("prompt_name", dict(DEFAULT_TEMPLATES), SAMPLE) == (DEFAULT_TEMPLATES["prompt_name"], "")
    body, added = preview_parts("intro", dict(DEFAULT_TEMPLATES, intro="Hi from {business_name}"), SAMPLE)
    assert (body, added) == ("Hi from Oak & Pine", "Reply STOP to opt out.")


def test_chips_put_the_useful_details_first_and_leave_out_the_event_id():
    names = [name for _, name in chips_for("booking_confirmation")]
    assert names[:5] == ["Job", "Day and time", "Address", "Business name", "Calendar links page"]
    assert "{event_id}" not in [token for token, _ in chips_for("booking_confirmation")]
    assert chips_for("opt_out_suffix") == ()


# --- defaults state, reset, errors --------------------------------------------------------

def test_standard_versus_customized_state_and_reset_without_javascript(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/messages").text
    assert page.count("Standard wording</span>") == len(FIELD_KEYS) and "Customized</span>" not in page
    assert "data-reset hidden" in card(page, "intro") and "data-std hidden" not in card(page, "intro")
    csrf = csrf_of(page)
    saved = client.post("/client/messages", data={"csrf": csrf, "intro": "Oak here, missed you. What do you need?"}).text
    intro = card(saved, "intro")
    assert "Customized</span>" in intro and "data-reset>" in intro and "data-reset hidden" not in intro
    assert "data-std hidden" in intro and saved.count("Customized</span>") == 1
    assert "Oak here, missed you. What do you need? <span class=sms__suffix>Reply STOP to opt out.</span>" in intro
    # Without JS the reset posts the whole form, so its visible label says so (CSS swaps it).
    assert "<span class=msg__reset-js>Reset</span><span class=msg__reset-nojs>Reset and save</span>" in intro
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
    assert "<title>Not saved · Messages · TextBack</title>" in page
    assert ("Not saved. \u201cFirst text after a missed call\u201d needs a change: Take out \u201cbusiness line\u201d. "
            "Customers stay in the text thread") in page
    assert "<a href=#f_intro data-error-link>Go to that text</a>" in page
    assert "Your other edits are still here; nothing was saved yet." in page
    # The summary opens the card list column, not the full width under the rail.
    assert page.index("id=error-summary") > page.index("<form method=post action=/client/messages")
    intro = card(page, "intro")
    assert "msg--invalid" in intro and "business line" in intro and f">{typed}</textarea>" in intro
    assert "aria-invalid=true" in intro and "msg--invalid" not in card(page, "prompt_name")
    assert "Not saved</span>" in intro and "Customized</span>" not in intro  # the danger pill replaces the others
    assert ">Your name?</textarea>" in card(page, "prompt_name")  # the other edit survives the round trip
    # Every card whose box differs from the saved wording shows Unsaved on load.
    assert "data-dirty-pill hidden" not in card(page, "prompt_name") and "data-dirty-pill hidden" in card(page, "prompt_service")
    assert "<details class=anytime__details>" in page  # nothing wrong in Any time: it stays closed
    assert not path.exists()
    page = client.post("/client/messages", data={"csrf": csrf, "handoff_ack_safety": "Paused. Call 911 if in danger."}).text
    assert "msg--invalid" in card(page, "handoff_ack_safety") and "Add the words \u201cfollow up\u201d" in card(page, "handoff_ack_safety")
    page = client.post("/client/messages", data={"csrf": csrf, "booking_error": "Oops {"}).text
    assert "msg--invalid" in card(page, "booking_error") and "isn\u2019t a detail we can fill in" in card(page, "booking_error")
    # A rejected Any time card renders its disclosure open, so the error is in view without JavaScript.
    page = client.post("/client/messages", data={"csrf": csrf, "opt_out_suffix": "Text END to quit"}).text
    assert "<details class=anytime__details open>" in page
    assert "Include the word STOP. Phone companies require it." in card(page, "opt_out_suffix")


def test_friendly_reasons_reword_every_validator_message():
    def reason(overrides):
        templates = dict(DEFAULT_TEMPLATES, **overrides)
        try:
            validate_templates(overrides)
        except MessageTemplateError as exc:
            key, raw = blame(str(exc), {k: templates[k] for k in FIELD_KEYS})
            return key, friendly_reason(raw, key)
        raise AssertionError(f"{overrides} was accepted")

    key, text = reason({"intro": "Call our business line"})
    assert key == "intro" and text.startswith("Take out \u201cbusiness line\u201d.")
    assert reason({"handoff_ack": "Paused."})[1].startswith("Add the words \u201cfollow up\u201d")
    assert reason({"handoff_ack_safety": "Paused. The owner will follow up."})[1] == "Tell people to call 911 if anyone is in danger."
    assert reason({"booking_error": "Sorry, call us."})[1] == "Say \u201cNo booking was made\u201d and leave out the word \u201ccall\u201d."
    assert reason({"opt_out_suffix": "Text END"})[1] == "Include the word STOP. Phone companies require it."
    braces = "Something in { } isn\u2019t a detail we can fill in. Use the buttons under the box to add one, or remove the { }."
    assert reason({"intro": "Hi {"}) == ("intro", braces) and reason({"intro": "Hi {a.b}"}) == ("intro", braces)
    assert reason({"intro": "Hi {service}"})[1] == "This text can\u2019t fill in {service}. It can use: Business name."
    assert reason({"prompt_service": "a" * 481})[1] == "Shorten it to 480 characters or fewer."
    assert friendly_reason("questions must include name", None) == "Questions must include name"


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

def test_every_page_sends_the_security_headers_and_loads_only_its_own_assets(tmp_path, monkeypatch):
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
        assert response.headers["content-security-policy"].startswith("default-src 'self'")
        text = response.text
        assert "src=http" not in text and "src='http" not in text and 'src="http' not in text
        assert "href=http" not in text and 'href="http' not in text and "fonts.googleapis" not in text
        assert "<style" not in text and "style=" not in text  # one stylesheet, served by the app
        assert text.count("<link rel=stylesheet") == 1 and '<link rel=stylesheet href="/client/static/portal.css?v=' in text
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
    stepper = re.search(r"<ol class=stepper .*?</ol>", step, re.S).group(0)
    done, current = re.findall(r"<li .*?</li>", stepper, re.S)
    assert "stepper__step--done" in done and "Details saved" in done
    assert "aria-current=step" in current and "Confirm number" in current
    assert "autocomplete=one-time-code" in step and "Keep my current mobile" in step
    # The code field is described by the lead and sits on the page like sign-in, not in a card.
    assert "<p class=lead id=confirm-help>" in step and 'aria-describedby="confirm-help"' in step
    assert '<div class=card>' not in step
    bad = client.post("/client/business", data={"csrf": csrf, "business_name": "", "business_contact": "", "owner_mobile": ""}).text
    assert "<title>Not saved · Business · TextBack</title>" in bad
    # The HELP number's placeholder is the number customers would see instead (none configured here: no placeholder).
    assert 'id=business_contact' in page and 'placeholder="704 555 0123"' not in page.split("id=business_contact", 1)[1].split(">", 1)[0]


# --- calendar states ------------------------------------------------------------------

def test_calendar_page_shows_test_mode_when_no_calendar_is_connected(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/calendar").text
    assert "No calendar connected</h2>" in page and "Test mode</span>" in page and "data-status=none" in page
    assert "Connect Google Calendar" not in page and "name=calendar_id" not in page
    assert "still being set up by FluxWorks" in page and "your operator" not in page  # the next step, in the block


def test_managed_calendars_are_named_for_people():
    outlook = status_view({"provider": "microsoft", "status": "managed"}, "x")
    assert outlook.title == "Outlook (Microsoft 365) connected"
    assert outlook.detail == "Your Outlook calendar is connected and managed by FluxWorks." and not outlook.calendar
    assert status_view({"provider": "icloud", "status": "managed"}, "x").title == "iCloud Calendar connected"
    assert status_view({"provider": "google", "status": "ready"}, "Personal").calendar == "Personal"
    assert not status_view({"provider": "google", "status": "reauth_required"}, "Personal").calendar


def test_calendar_page_shows_reconnect_needed_unreadable_and_connected_with_a_radio_picker(tmp_path, monkeypatch):
    client, telecom, credentials, transport = google_fixture(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/calendar").text
    assert "Reconnect needed" in page and "data-status=reauth_required" in page and "Connect Google Calendar" in page
    assert "What Google will ask" in page and "Nothing else in that account is read" in page
    status = re.search(r"<section class=status .*?</section>", page, re.S).group(0)
    assert "action=/client/calendar data-connect" in status  # the primary action sits inside the status block
    assert "<details class=asks open>" in page  # not connected: the explanation starts open

    monkeypatch.setattr(credentials, "status", lambda: (_ for _ in ()).throw(CalendarProviderError("boom")))
    page = client.get("/client/calendar").text
    assert "could not be read" in page and "data-status=unavailable" in page and "Reconnect Google Calendar" not in page
    monkeypatch.undo()

    monkeypatch.setattr(credentials, "status", lambda: "ready")
    from text_back.client_settings import remember_calendars
    remember_calendars(client.app.state, [{"id": "a@x", "summary": "Personal", "primary": True}, {"id": "b@x", "summary": "Tree jobs"}], clock_now())
    page = client.get("/client/calendar").text
    assert "Connected to Google Calendar" in page and "data-status=ready" in page and "Reconnect Google Calendar" in page
    assert page.count("name=calendar_id") == 2 and "class=choice" in page and "Use this calendar" in page
    status = re.search(r"<section class=status .*?</section>", page, re.S).group(0)
    assert "Free times come from this calendar and every booking is added to it." in status
    # The picker names the calendar in use, so the meta line is left out; screen readers still hear the name.
    assert "status__meta" not in status
    assert "<p class=vh>Google Calendar is connected and uses <strong>Personal</strong>.</p>" in status
    # Reconnect is a secondary action inside the status block; "What Google will ask" is a closed, form-free disclosure.
    assert "action=/client/calendar data-connect" in status and '"btn btn--secondary btn--block-phone" data-loading="Opening Google…"' in status
    asks = re.search(r'<section class="card card--asks".*?</section>', page, re.S).group(0)
    assert "<details class=asks>" in asks and "<form" not in asks
    # "Use this calendar" is secondary; portal.js holds it aria-disabled until another calendar is checked.
    assert '<form method=post action=/client/calendar class=card data-picker>' in page
    assert 'class="btn btn--secondary btn--block-phone" data-loading="Saving…" data-picker-save>Use this calendar<' in page

    # With one writable calendar there is no picker, so the status block names it on the meta line.
    remember_calendars(client.app.state, [{"id": "a@x", "summary": "Personal", "primary": True}], clock_now())
    status = re.search(r"<section class=status .*?</section>", client.get("/client/calendar").text, re.S).group(0)
    assert "<dt>Calendar</dt><dd><strong>Personal</strong></dd>" in status and "class=vh" not in status


def clock_now():
    from test_client_settings import NOW
    return NOW


def test_messages_page_jump_row_any_time_rail_select_and_save_toast(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/messages").text
    jump = re.search(r'<nav class=jump aria-label="Jump to">.*?</nav>', page, re.S).group(0)
    assert [href for href in re.findall(r"href=(\S+?)>", jump)] == [
        "#g_missed", "#g_questions", "#g_booking", "#g_noreply", "#g_owner", "#g_keywords", "#conversation"]
    assert "<details class=anytime__details>" in page and "Required by phone companies." in page
    # The scenario switcher is a native select outside the form (never posted), labelled "Show".
    assert "<label class=rail__show for=scenario>Show</label>" in page and "data-scenario-select" in page
    labels = re.findall(r"<option value=\w+(?: selected)?>([^<]+)</option>", page)
    assert labels == ["Books a job", "Unclear answers", "No reply", "Booking failed", "Asks for you", "Safety", "STOP and HELP"]
    assert 'aria-label="Sample messages"' in page and "Back to editing" in page and "name=scenario" not in page
    assert 'role=group aria-label="Insert a detail"' in page and ">Insert<" not in page
    assert "Saves every message at once" in page  # the save bar without JavaScript
    csrf = csrf_of(page)
    saved = client.post("/client/messages", data={"csrf": csrf, "intro": "Oak here. What do you need?", "ask_email": "1"}).text
    # One line: "Saved." and the changed list after it.
    assert ('<p class=notice__text>Saved. <span class=notice__detail>Changed: First text after a missed call, '
            'Email address (switched on).</span></p>') in saved and "New conversations use" not in saved
    back = client.post("/client/messages", data={"csrf": csrf, "intro": "", "ask_email": "1"}).text
    assert "Back to standard wording: First text after a missed call." in back


def test_the_code_field_names_its_format(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    client.post("/client/login", data={"mobile": "980 555 0123"}, follow_redirects=False)
    assert 'title="Six digits"' in client.get("/client/verify").text
