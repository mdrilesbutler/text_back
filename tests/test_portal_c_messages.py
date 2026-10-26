"""Messages page, ported from candidate A's tests/test_client_portal_ui.py and tests/test_portal_frontend.py.

Kept: conversation order, previews and the opt-out line, the cost line, chips, standard vs customized,
no-JS reset, rejected saves, friendly reasons, optional-question switches, the form contract, static
files, the byte-identical verify page, the theme cookie and the template copy scan. Dropped with their
routes or modules: the styleguide, the Business page and A's calendar StatusView. Wording follows the
copy deck (section 4)."""
import json
import re
from pathlib import Path

from text_back.messages import DEFAULT_TEMPLATES, FORBIDDEN_PHRASES, MessageTemplateError, validate_templates
from text_back.portal_messages import (
    FIELD_KEYS, KEYWORDS, OPTIONAL_QUESTIONS, STEPS, bill_label, blame, chips_for, count_label, friendly_reason,
    preview_parts, preview_text, sms_parts, to_display, to_template,
)
from text_back.portal_render import TEMPLATE_DIR
from test_client_portal import csrf_of, make, sign_in

SAMPLE = {"business_name": "Oak & Pine", "service": "tree removal", "when": "Thursday at 4", "location": "12 Elm St",
          "invite_line": "Invite sent.", "calendar_links": "Add to calendar: x", "contact_line": " Contact: (980) 555-0100."}


def card(page_html, key):
    match = re.search(rf'<article class="msg[^"]*" id=m_{key} .*?</article>', page_html, re.S)
    assert match, f"no card for {key}"
    return match.group(0)


def messages_form(page_html):
    return re.search(r"<form method=post action=/client/messages id=messages.*?</form>", page_html, re.S).group(0)


# --- order ---------------------------------------------------------------------------------

def test_every_message_is_shown_once_in_conversation_order():
    assert sorted(FIELD_KEYS) == sorted(k for k in DEFAULT_TEMPLATES if k != "fields")
    assert len(set(FIELD_KEYS)) == len(FIELD_KEYS) == 21
    assert [heading for _, heading, _, _ in STEPS] == ["Missed call", "Questions", "Booking", "No reply",
                                                       "When the assistant steps back"]
    assert KEYWORDS[1] == "START, HELP and STOP"
    questions = [key for parent, branches in STEPS[1][3] for key in (parent, *branches)]
    assert questions[:3] == ["prompt_service", "prompt_location", "prompt_preferred_time"]
    assert questions.index("prompt_name") < questions.index("prompt_phone") < questions.index("prompt_email")
    assert set(OPTIONAL_QUESTIONS) == {"prompt_phone", "prompt_email"}


def test_page_renders_steps_in_order_with_switches_on_the_optional_questions(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/messages").text
    positions = [page.index(f"id=g_{sid}") for sid, _, _, _ in (*STEPS, KEYWORDS)]
    assert positions == sorted(positions)
    for key in FIELD_KEYS:
        assert f"id=m_{key}" in page
    assert "name=ask_phone" in card(page, "prompt_phone") and "name=ask_email" in card(page, "prompt_email")
    assert "name=ask_phone" not in card(page, "intro")
    assert "Off. Customers skip this question." in card(page, "prompt_email")
    assert "data-savebar" in page and "Saves every text at once" in page


def test_jump_chips_are_the_five_step_headings_and_keywords_start_closed(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/messages").text
    jump = re.search(r'<nav class=jump aria-label="On this page">.*?</nav>', page, re.S).group(0)
    assert re.findall(r"href=(\S+?)>([^<]+)<", jump) == [
        ("#g_missed", "Missed call"), ("#g_questions", "Questions"), ("#g_booking", "Booking"),
        ("#g_noreply", "No reply"), ("#g_steps_back", "Steps back")]
    for sid in ("missed", "questions", "booking", "noreply", "steps_back"):
        assert f"<h2 id=h_{sid} tabindex=-1>" in page  # a jump target takes focus
    assert "<details class=anytime__details>" in page and "Required by phone companies." in page
    # The example-conversation select sits in its own GET form, outside the Messages POST form.
    assert "<label class=rail__show for=scenario>Show</label>" in page
    assert "name=scenario" not in messages_form(page) and page.index("id=conversation") > page.index("</form>")
    rail_form = re.search(r"<form method=get action=/client/messages#conversation .*?</form>", page, re.S).group(0)
    assert "name=scenario" in rail_form and "csrf" not in rail_form
    chosen = client.get("/client/messages", params={"scenario": "failed"}).text
    assert "<option value=failed selected>" in chosen and "<option value=booked selected>" not in chosen
    assert "<option value=booked selected>" in client.get("/client/messages", params={"scenario": "nope"}).text


# --- preview and cost line -----------------------------------------------------------------------

def test_preview_fills_details_and_appends_the_opt_out_line_where_carriers_require_it():
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
    # A detail the preview has no value for shows as its label; broken braces never crash the page.
    assert preview_text("intro", {**templates, "intro": "Hi {invite_line}"}, {}).startswith("Hi [Invite sentence]")
    assert preview_text("intro", {**templates, "intro": "Hi {"}, SAMPLE).startswith("Hi {")


def test_text_count_knows_the_gsm_alphabet():
    assert sms_parts("Hello there") == (11, 1, True)
    assert sms_parts("a" * 160) == (160, 1, True)
    assert sms_parts("a" * 161) == (161, 2, True)
    assert sms_parts("a" * 306) == (306, 2, True)
    assert sms_parts("a" * 307) == (307, 3, True)
    assert sms_parts("€" * 80) == (80, 1, True)   # extension characters cost two
    assert sms_parts("€" * 81) == (81, 2, True)
    assert sms_parts("—" + "a" * 69) == (70, 1, False)
    assert sms_parts("—" + "a" * 70) == (71, 2, False)


def test_cost_line_counts_texts_first_and_names_the_symbol_with_a_plain_one_instead():
    assert count_label("Hello") == "1 text · 5 characters"
    assert count_label("a" * 161) == "2 texts · 161 characters"
    assert bill_label("a" * 160) == "" and bill_label("Hi — there") == ""
    assert bill_label("a" * 161) == "Billed as 2 texts. Customers still see one message."
    assert bill_label("€" * 81) == "Billed as 2 texts. Customers still see one message."
    assert bill_label("It’s " + "a" * 70) == \
        'Billed as 2 texts. The "’" symbol makes each text hold only 70 characters. Use "\'" instead.'
    assert bill_label("—" + "a" * 70).endswith('Use "-" instead.')
    assert bill_label("ç" + "a" * 70).endswith("Use a plain letter instead.")
    assert preview_parts("prompt_name", dict(DEFAULT_TEMPLATES), SAMPLE) == (DEFAULT_TEMPLATES["prompt_name"], "")


def test_page_shows_the_rendered_preview_and_cost_line_for_each_message(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/messages").text
    intro = card(page, "intro")
    assert "Oak &amp; Pine Tree Care&#39;s scheduling assistant" in intro
    assert "<span class=sms__suffix>Reply STOP to opt out.</span>" in intro
    assert "STOP line added for you" in intro and "data-optout-note hidden" not in intro
    assert re.search(r"data-count>[23] texts · \d+ characters<", intro) and "data-warn" in intro
    assert "The &#34;—&#34; symbol makes each text hold only 70 characters. Use &#34;-&#34; instead." in intro
    name = card(page, "prompt_name")
    assert re.search(r"data-count>1 text · \d+ characters<", name) and "data-warn" not in name
    assert "STOP line added" not in name
    confirmation = card(page, "booking_confirmation")
    assert 'title="https://example.test/a/' in confirmation and "Add to Google Calendar ›" in confirmation


def test_chips_use_plain_labels_in_the_decks_order_and_leave_out_the_booking_id():
    labels = [label for _, label in chips_for("booking_confirmation")]
    assert labels == ["Business name", "Job", "Day and time", "Address", "Calendar links", "Invite sentence",
                      "Customer's email", "Google Calendar link", "Outlook link", "iCal link", "Calendar links page"]
    assert all(text == f"[{label}]" for text, label in chips_for("booking_confirmation"))
    assert [label for _, label in chips_for("help")] == ["Business name", "Contact number sentence"]
    assert chips_for("opt_out_suffix") == ()
    assert to_display("Booked {service} ref {event_id}") == "Booked [Job] ref [Booking reference]"
    assert to_template("Booked [Job] ref [Booking reference] [not a detail]") == "Booked {service} ref {event_id} [not a detail]"


# --- standard wording, reset, errors -------------------------------------------------------------

def test_standard_versus_customized_and_reset_without_javascript(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/messages").text
    assert page.count("Standard wording</span>") == len(FIELD_KEYS) and "Customized</span>" not in page
    assert "data-reset hidden" in card(page, "intro") and "data-std hidden" not in card(page, "intro")
    csrf = csrf_of(page)
    saved = client.post("/client/messages", data={"csrf": csrf, "intro": "Oak here, missed you. What do you need?"}).text
    intro = card(saved, "intro")
    assert "Customized</span>" in intro and "data-reset>" in intro and "data-std hidden" in intro
    assert saved.count("Customized</span>") == 1
    assert "Oak here, missed you. What do you need? <span class=sms__suffix>Reply STOP to opt out.</span>" in intro
    assert "<span class=msg__reset-js>Reset</span><span class=msg__reset-nojs>Reset and save</span>" in intro
    back = client.post("/client/messages", data={"csrf": csrf, "intro": "Oak here, missed you. What do you need?",
                                                 "reset": "intro"}).text
    assert "Saved" in back and "Standard wording</span>" in card(back, "intro")
    assert json.loads(path.read_text()) == {}


def test_the_standard_wording_posted_back_is_stored_as_standard(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/messages").text)
    data = {"csrf": csrf, **{key: to_display(DEFAULT_TEMPLATES[key]) for key in FIELD_KEYS}}
    data["intro"] = to_display(DEFAULT_TEMPLATES["intro"]).replace(" ", "  ")
    page = client.post("/client/messages", data=data).text
    assert json.loads(path.read_text()) == {}
    assert "Standard wording</span>" in card(page, "intro") and "Customized</span>" not in page


def test_a_rejected_save_marks_the_message_and_keeps_what_was_typed(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/messages").text)
    typed = "Call our business line any time"
    page = client.post("/client/messages", data={"csrf": csrf, "intro": typed, "prompt_name": "Your name?"}).text
    assert "<title>Not saved · Messages · TextBack</title>" in page
    assert ("Not saved. &#34;First text after a missed call&#34; needs a change: Take out &#34;business line&#34;. "
            "Customers stay in the text thread") in page
    assert "<a href=#f_intro data-error-link>Go to that text</a>" in page
    assert "Your other edits are still here. Nothing was saved yet." in page
    assert page.index("id=error-summary") > page.index("<form method=post action=/client/messages")
    intro = card(page, "intro")
    assert "msg--invalid" in intro and f">{typed}</textarea>" in intro and "aria-invalid=true" in intro
    assert "<details class=editor open>" in intro and "<details class=editor open>" not in card(page, "prompt_name")
    assert "Not saved</span>" in intro and "Customized</span>" not in intro
    assert ">Your name?</textarea>" in card(page, "prompt_name")
    assert "data-dirty-pill hidden" not in card(page, "prompt_name") and "data-dirty-pill hidden" in card(page, "prompt_service")
    assert "<details class=anytime__details>" in page
    assert "data-initial=error" in page
    assert not path.exists()
    page = client.post("/client/messages", data={"csrf": csrf, "opt_out_suffix": "Text END to quit"}).text
    assert "<details class=anytime__details open>" in page
    assert "Include the word STOP. Phone companies require it." in card(page, "opt_out_suffix")
    page = client.post("/client/messages", data={"csrf": csrf, "intro": "Hi {a.b}"}).text
    assert ">Hi {a.b}</textarea>" in card(page, "intro") and not path.exists()


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
    assert key == "intro" and text.startswith('Take out "business line".')
    assert reason({"handoff_ack": "Paused."})[1] == 'Add the words "follow up", like "We\'ll follow up with you by text."'
    assert reason({"handoff_ack_safety": "Paused. We will follow up."})[1] == "Tell people to call 911 if anyone is in danger."
    assert reason({"booking_error": "Sorry, call us."})[1] == 'Say "No booking was made" and leave out the word "call".'
    assert reason({"opt_out_suffix": "Text END"})[1] == "Include the word STOP. Phone companies require it."
    bad = "Something typed by hand isn't a detail we can fill in. Use the Insert buttons under the box, or remove it."
    assert reason({"intro": "Hi {"}) == ("intro", bad) and reason({"intro": "Hi {a.b}"}) == ("intro", bad)
    assert reason({"intro": "Hi {nope}"})[1] == bad
    assert reason({"intro": "Hi {service}"})[1] == "This text can't fill in Job. It can use: Business name."
    assert reason({"opt_out_suffix": "Reply STOP {business_name}"})[1] == "This text can't fill in Business name. It fills in no details."
    assert reason({"prompt_service": "a" * 481})[1] == "Shorten it to 480 characters or fewer."


def test_blame_points_at_the_right_message():
    templates = dict(DEFAULT_TEMPLATES)
    assert blame("intro is longer than 480 characters", templates) == ("intro", "is longer than 480 characters")
    assert blame("handoff acknowledgements must promise a follow-up", {**templates, "handoff_ack": "Paused."}) == \
        ("handoff_ack", "must promise a follow-up")
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
    page = client.post("/client/messages", data={"csrf": csrf, "ask_phone": "1", "intro": "Ask for a representative"}).text
    assert "Not saved" in page and "name=ask_phone value=1 checked" in card(page, "prompt_phone")


# --- form contract and front-end invariants ------------------------------------------------------

def test_the_messages_form_always_posts_all_21_texts_and_enter_saves(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    form = messages_form(client.get("/client/messages").text)
    assert form.count("<textarea") == len(FIELD_KEYS) == 21
    assert set(re.findall(r"<textarea [^>]*\bname=(\w+)", form)) == set(FIELD_KEYS)
    assert not re.search(r"\sdisabled[\s>=]", form)
    first_submit = re.search(r"<button type=submit[^>]*>", form).group(0)
    assert "name=save value=1" in first_submit and "class=vh" in first_submit and "aria-hidden=true" in first_submit


def test_without_a_messages_file_the_cards_are_read_only_and_name_who_turns_it_on(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch, messages_file=False)
    sign_in(client, telecom)
    page = client.get("/client/messages").text
    assert "Message editing isn&#39;t turned on for your account yet. FluxWorks sets this up for you." in page
    assert "<textarea" not in page and "Text FluxWorks support" not in page
    client.app.state.support_contact = "+19805550111"
    assert 'href="sms:+19805550111">Text FluxWorks support</a>' in client.get("/client/messages").text


def test_static_files_are_served_with_their_types_and_nosniff(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    for url, kind in (("/client/static/portal.css", "text/css"), ("/client/static/portal.js", "text/javascript"),
                      ("/client/static/fonts/archivo-600-latin.woff2", "font/woff2")):
        response = client.get(url)
        assert response.status_code == 200 and response.headers["content-type"].startswith(kind), url
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["cache-control"] == "no-cache"
    versioned = client.get("/client/static/portal.css?v=abcdefgh")
    assert "immutable" in versioned.headers["cache-control"]


def test_the_verify_page_is_identical_for_an_unknown_number_and_a_wrong_code_and_shows_no_digits(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    client.post("/client/login", data={"mobile": "980 555 9999"}, follow_redirects=False)
    blank = client.get("/client/verify").content
    unknown = client.post("/client/verify", data={"code": "000000"}).content
    client.post("/client/login", data={"mobile": "980 555 0123"}, follow_redirects=False)
    assert client.get("/client/verify").content == blank
    assert client.post("/client/verify", data={"code": "000000"}).content == unknown
    for digits in ("0123", "5550123", "9805550123", "9999"):
        assert digits.encode() not in blank and digits.encode() not in unknown


def test_the_theme_cookie_sets_data_theme_and_anything_else_is_ignored(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    client.cookies.set("tb_theme", "dark")
    assert "<html lang=en class=no-js data-theme=dark>" in client.get("/client/login").text
    client.cookies.set("tb_theme", "blue")
    assert "<html lang=en class=no-js>" in client.get("/client/login").text


def test_no_template_says_ai_or_promises_a_person():
    templates = sorted(Path(TEMPLATE_DIR, "client").glob("*.j2"))
    assert len(templates) >= 16
    for template in templates:
        text = template.read_text(encoding="utf-8")
        assert not re.search(r"\bAI\b", text), template.name
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in text.lower(), (template.name, phrase)
