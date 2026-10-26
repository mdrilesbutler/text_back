"""Candidate C fix pass: the verification list (FIXES-verify.md), behaviour first.

M1  every successful portal POST answers 303 to its page with a one-time notice (signed, bound to the session,
    an id and safe params, never text); reload and Back never re-post; a rejected save renders in place.
M2  equal quiet-hours times are refused; Off then On brings back the last custom times.
M3  forwarding codes: Copy shown on plain http, with an execCommand fallback; codes stack below 480px.
M7  business name: { } < > refused; the 70-character symbol line; long names wrap.
M8  without JavaScript every Messages step ends with the form's Save.
P1..P5, the rejected-save phone bug and the m-items that carry logic.
"""
import html
import json
import re
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from text_back import portal_flash, portal_messages as pm, portal_phone, portal_scheduling as ps, portal_status
from text_back.messages import DEFAULT_TEMPLATES, FORBIDDEN_PHRASES, validate_templates
from text_back.portal_flash import FLASH_COOKIE
from text_back.portal_render import STATIC_DIR, TEMPLATE_DIR
from test_client_portal import BASE, OWNER, code_from, csrf_of, make, sign_in

JS = (STATIC_DIR / "portal.js").read_text()
CSS = (STATIC_DIR / "portal.css").read_text()
BUSINESS_LINE = "+17045550123"


def signed_in(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    return client, telecom, clock, path, csrf_of(client.get("/client/home").text)


def text(response) -> str:
    return html.unescape(response.text)


def slot(page: str) -> str:
    match = re.search(r"<div class=status-slot id=notice role=status>(.*?)</div>\s*<button type=button", page, re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", match.group(1))).strip() if match else ""


def session_of(client):
    state = client.app.state
    token = client.cookies.get("text_back_client")
    from text_back.client_portal import _session

    class _Req:
        cookies = {"text_back_client": token}
    return _session(state, _Req())


def schedule_form(csrf, **changes):
    form = {"csrf": csrf, "appointment_duration_minutes": "60", "appointment_duration_custom": "60",
            "appointment_duration_shown": "60", "timezone": "UTC", "hours_mode": "any", "quiet_switch": "1",
            "quiet_on": "1", "quiet_hours_start": "21:00", "quiet_hours_end": "08:00", "followup_delay_1": "120",
            "followup_delay_2": "1440", "followup_expiry_minutes": "2880"}
    form.update(changes)
    return {k: v for k, v in form.items() if v is not None}


def phone_form(csrf, **changes):
    form = {"csrf": csrf, "business_name": "Oak & Pine Tree Care", "business_line": "", "owner_mobile": "(980) 555-0123",
            "business_contact": "", "carrier": "", "checks_in_form": "1"}
    form.update(changes)
    return form


# --- M1: post / redirect / get ------------------------------------------------------------

def test_a_successful_save_redirects_and_the_notice_shows_once(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    posted = client.post("/client/messages", data={"csrf": csrf, "prompt_name": "Your name, please?"}, follow_redirects=False)
    assert posted.status_code == 303 and posted.headers["location"] == "/client/messages"
    assert FLASH_COOKIE in posted.headers["set-cookie"] and "httponly" in posted.headers["set-cookie"].lower()
    assert "Your name" not in posted.headers["set-cookie"]  # the cookie carries keys, never words
    first = client.get("/client/messages")
    assert slot(first.text) == "Saved. You changed “Question 4: the name”."
    assert 'tb_flash=""' in first.headers["set-cookie"]  # used up
    mtime = path.stat().st_mtime_ns
    again = client.get("/client/messages")  # reload: the saved page, no notice, nothing posted again
    assert slot(again.text) == "" and path.stat().st_mtime_ns == mtime


def test_every_portal_save_answers_with_a_redirect(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    cases = [
        ("/client/messages", {"csrf": csrf, "discard": "1"}, "/client/messages", "Changes discarded."),
        ("/client/schedule", schedule_form(csrf, appointment_duration_minutes="90", appointment_duration_custom="90"),
         "/client/schedule", "Saved. You changed “Appointment length”. Applies right away, including customers mid-conversation."),
        ("/client/schedule", {"csrf": csrf, "discard": "1"}, "/client/schedule", "Changes discarded."),
        ("/client/phone", phone_form(csrf, carrier="verizon"), "/client/phone", "Saved. You changed “Your carrier”."),
        ("/client/phone/checks", {"csrf": csrf, "check_answered_no_text": "1"}, "/client/phone#checks", "Checks saved."),
        ("/client/account/remember", {"csrf": csrf, "remember": "1"}, "/client/account",
         "Saved. This device now stays signed in for 30 days."),
        ("/client/account/remember", {"csrf": csrf}, "/client/account", "Saved. This device now signs out after 12 hours."),
    ]
    for url, data, target, notice in cases:
        posted = client.post(url, data=data, follow_redirects=False)
        assert posted.status_code == 303 and posted.headers["location"] == target, url
        assert slot(client.get(target.split("#")[0]).text) == notice, url


def test_a_rejected_save_renders_in_place_with_the_typed_text(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    rejected = client.post("/client/messages", data={"csrf": csrf, "intro": "Call our business line any time"},
                           follow_redirects=False)
    assert rejected.status_code == 200 and "Call our business line any time" in text(rejected)
    assert FLASH_COOKIE not in rejected.headers.get("set-cookie", "") and not path.exists()


def test_the_notice_never_reflects_request_text(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    session = session_of(client)
    # Even a correctly signed cookie only ever names keys the page knows; anything else is dropped.
    forged = portal_flash.encode(state, session, "/client/messages", "messages_saved",
                                 {"changed": ["<b>evil</b>", "intro"], "on": ["<script>"]})
    client.cookies.set(FLASH_COOKIE, forged, path="/client")
    page = client.get("/client/messages").text
    assert slot(page) == "Saved. You changed “First text after a missed call”." and "evil" not in page and "<script>" not in page
    # A tampered cookie, an unknown id, another page's notice and a query string all show nothing.
    for raw in (forged[:-2] + "00", portal_flash.encode(state, session, "/client/messages", "say_anything", {"t": "hi"}),
                portal_flash.encode(state, session, "/client/phone", "discarded")):
        client.cookies.set(FLASH_COOKIE, raw, path="/client")
        assert slot(client.get("/client/messages").text) == ""
    assert slot(client.get("/client/messages", params={"notice": "Saved. Pay us"}).text) == ""


def test_a_notice_from_another_session_is_ignored(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    posted = client.post("/client/messages", data={"csrf": csrf, "discard": "1"}, follow_redirects=False)
    raw = re.search(rf"{FLASH_COOKIE}=([^;]+)", posted.headers["set-cookie"]).group(1)
    other = TestClient(client.app, base_url=BASE)
    sign_in(other, telecom)
    other.cookies.set(FLASH_COOKIE, raw, path="/client")
    assert slot(other.get("/client/messages").text) == ""


# --- M2: quiet hours ---------------------------------------------------------------------------

def test_equal_quiet_times_are_refused_and_off_then_on_keeps_the_custom_times(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    same = client.post("/client/schedule", data=schedule_form(csrf, quiet_hours_start="22:00", quiet_hours_end="22:00"))
    assert ps.ERR_QUIET_SAME in text(same) and state.store.setting("quiet_hours_start") is None
    assert ps.ERR_QUIET_SAME == "Start and end can't be the same time. To turn quiet hours off, use the switch."
    client.post("/client/schedule", data=schedule_form(csrf, quiet_hours_start="22:00", quiet_hours_end="06:00"))
    client.post("/client/schedule", data=schedule_form(csrf, quiet_on=None, quiet_hours_start="22:00", quiet_hours_end="06:00"))
    assert state.followup_policy.quiet_start == state.followup_policy.quiet_end  # off
    page = client.get("/client/schedule").text
    assert "id=quiet_on name=quiet_on value=1>" in page  # the switch is off
    assert re.search(r'id=quiet_hours_start [^>]*>.*?<option value="22:00" selected>', page, re.S)
    assert re.search(r'id=quiet_hours_end [^>]*>.*?<option value="06:00" selected>', page, re.S)


# --- M3, M7, M8 --------------------------------------------------------------------------------

def test_copy_works_without_the_async_clipboard_and_codes_stack_on_small_screens():
    assert "document.execCommand('copy')" in JS and "button.hidden = false" in JS
    assert "button.hidden = !navigator.clipboard" not in JS
    small = CSS.split("@media (max-width: 479.98px)", 1)[1].split("}\n  }", 1)[0]
    assert "grid-template-columns: minmax(0, 1fr)" in small and "overflow-wrap: anywhere" in small


def test_business_name_refuses_braces_and_angle_brackets_and_names_a_billing_symbol(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    for bad in ("Oak {Pine}", "Oak <b>"):
        page = text(client.post("/client/phone", data=phone_form(csrf, business_name=bad)))
        assert portal_phone.ERR_NAME_SYMBOLS in page and client.app.state.business_name == "Oak & Pine Tree Care"
    client.post("/client/phone", data=phone_form(csrf, business_name="Dana’s Trees"))
    page = text(client.get("/client/phone"))
    assert "This name has a ’, which makes each text hold only 70 characters." in page
    assert portal_phone.name_symbol_line("Oak & Pine") == ""
    assert re.search(r"\.sms__who, \.phone__name[^}]*\) \{ overflow-wrap: anywhere; \}", CSS)


def test_without_javascript_every_messages_step_ends_with_save(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    form = re.search(r"<form method=post action=/client/messages id=messages-form.*?</form>", page, re.S).group(0)
    saves = re.findall(r'<p class=step-save><button type=submit class="btn btn--secondary" name=save value=1>Save every text</button></p>', form)
    assert len(saves) == 6  # five steps and START, HELP and STOP, all inside the one form
    assert ":where(.js) .step-save { display: none; }" in CSS
    assert "Reset and save" in page and "and save</span>" in page


# --- the rejected-save phone bug ---------------------------------------------------------------

def test_a_rejected_phone_save_touching_only_the_mobile_lists_one_change(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    client.post("/client/phone", data=phone_form(csrf, business_line="704 555 0123", business_contact="704-555-0199"))
    # Typed exactly as the page shows them ("(704) 555-0123"), with a bad mobile.
    page = client.post("/client/phone", data=phone_form(csrf, business_line="(704) 555-0123",
                                                        business_contact="(704) 555-0199", owner_mobile="12345")).text
    header = re.search(r'<header class="topbar topbar--dirty" data-topbar>.*?</header>', page, re.S).group(0)
    assert "<span class=topsave__count>Not saved · 1 change</span>" in header
    assert re.findall(r'<li><a href="([^"]+)">([^<]+)</a></li>', header) == [("#owner_mobile", "Your mobile")]


# --- P1..P5 ------------------------------------------------------------------------------------

P1 = {
    "intro": "Hey, sorry we missed your call. This is the scheduling assistant for {business_name}. What were you calling about?",
    "followup_1": "Hi again from the scheduling assistant for {business_name}. Still happy to get you on the calendar. What job do you need done?",
    "followup_2": "Last check-in from the scheduling assistant for {business_name}. Reply with the job you need and we'll set a time.",
    "booking_confirmation": "Booked: {service} on {when} at {location}. This is the scheduling assistant for {business_name}. {invite_line} {calendar_links}",
    "opt_in": "You're subscribed to scheduling texts from {business_name}. Msg & data rates may apply. Reply HELP for help or STOP to opt out.",
    "help": "This is the scheduling assistant for {business_name}. Reply with the job type, location, and a time that works. Anything we can't handle by text, the owner follows up on.{contact_line} Msg & data rates may apply.",
    "prompt_service": "What's the job you need done? For example: tree removal, trimming or stump grinding.",
}


def test_p1_default_texts_have_no_possessive_and_no_em_dash_and_pass_every_rule():
    for key, wording in P1.items():
        assert " ".join(DEFAULT_TEMPLATES[key].split()) == wording, key
    merged = validate_templates(dict(DEFAULT_TEMPLATES))  # the only validator, every default stated explicitly
    assert merged == {k: " ".join(v.split()) if k != "fields" else v for k, v in DEFAULT_TEMPLATES.items()}
    for key, wording in DEFAULT_TEMPLATES.items():
        assert "—" not in wording and "–" not in wording and "'s scheduling" not in wording, key
        assert not any(phrase in wording.lower() for phrase in FORBIDDEN_PHRASES), key
        assert pm.sms_parts(pm.fill(wording, {"business_name": "Arborists"}))[2], key  # plain alphabet
    assert "Arborists's" not in pm.preview_text("intro", dict(DEFAULT_TEMPLATES), {"business_name": "Arborists"})


def test_p2_the_first_line_skips_example_cards_and_carries_no_tag(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    client.app.state.preview_example_setup = {"forwarding", "approval"}
    page = client.get("/client/home").text
    line = re.search(r"<p class=status-line data-status-line>(.*?)</p>", page).group(1)
    assert line == "Set up on your side. Waiting on FluxWorks to connect your calendar." and "extag" not in line
    assert page.count("<span class=extag>Example</span>") == 2  # the two example cards keep their own tag


def test_p3_a_calendar_fluxworks_connects_waits_and_offers_support(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    client.app.state.support_contact = "+17045550199"
    home = text(client.get("/client/home"))
    card = re.search(r'<li class="node node--waiting" data-setup=calendar>.*?\n</li>', home, re.S).group(0)
    assert "Waiting on FluxWorks" in card and "FluxWorks connects your calendar for you." in card
    assert '<a class="btn btn--secondary setup__btn" href="sms:+17045550199">Text FluxWorks support</a>' in card
    assert "Not working yet: 1 step left." in home  # forwarding only; the calendar is not the owner's step
    calendar = text(client.get("/client/calendar"))
    node = re.search(r'<li class="node node--waiting" id=connection>.*?\n</li>', calendar, re.S).group(0)
    assert "Waiting on FluxWorks" in node and 'href="sms:+17045550199" data-support>Text FluxWorks support</a>' in node
    preview = (Path(__file__).resolve().parents[1] / "docs/notes/ui-compare-c/preview.py").read_text()
    assert '"TEXT_BACK_SUPPORT_CONTACT": "+17045550199"' in preview


def test_p4_a_caller_who_asked_for_a_person_gets_call_and_text(tmp_path, monkeypatch):
    from text_back import inbox, worker

    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    caller = "+19805550177"
    inbox.submit_event(state=state, kind="voice", params=dict(call_sid="CA-p4", call_status="no-answer", from_number=caller,
                                                              to_number=state.business_number))
    worker.run_once(state)
    for sid, body in (("SM-p4-1", "Stump grinding"), ("SM-p4-2", "Can you have someone call me instead?")):
        inbox.submit_event(state=state, kind="sms", params=dict(message_sid=sid, from_number=caller,
                                                                to_number=state.business_number, body=body))
        worker.run_once(state)
    page = client.get("/client/home").text
    row = re.search(r"<li class=caller>.*?</li>", page, re.S).group(0)
    assert "Wants to talk to you" in row
    assert '<a class="btn btn--secondary caller__act" href="tel:+19805550177">' in row
    assert '<a class="btn btn--secondary caller__act" href="sms:+19805550177">' in row
    assert "min-height: var(--tap)" in CSS.split(".caller__act {", 1)[1].split("}", 1)[0]


def test_p5_the_sample_values_match_the_mockup(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    page = html.unescape(client.get("/client/messages").text)
    booked = re.search(r"<ol class=thread data-scenario=booked .*?</ol>", page, re.S).group(0)
    for value in ("Tree trimming", "412 Maple St, Charlotte", "Dana Whitfield", "Thursday at 10"):
        assert value in booked, value
    assert (pm.SAMPLE_SERVICE, pm.SAMPLE_LOCATION) == ("Tree trimming", "412 Maple St, Charlotte")


# --- m-items with logic ----------------------------------------------------------------------

def test_m2_replace_dash_adds_spaces_only_where_missing():
    assert pm.apply_fix("call—this") == "call - this"
    assert pm.apply_fix("call — this") == "call - this"
    assert pm.apply_fix("call —this") == "call - this"
    assert pm.apply_fix("Thanks—") == "Thanks -"
    assert pm.apply_fix("“Hi”") == '"Hi”'  # other symbols swap one for one
    assert "function plainSwap(text, symbol)" in JS and "plainSwap(ta.value || card.dataset.default, symbol)" in JS


def test_m1_insert_chip_spacing_lives_in_the_insert_handler():
    handler = JS.split("const chip = e.target.closest('[data-insert]');", 1)[1].split("return;\n    }", 1)[0]
    assert "chip.dataset.insert" in handler and "? ' ' : ''" in handler


def test_m5_m7_sign_out_and_a_mobile_change(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    step = client.post("/client/phone", data=phone_form(csrf, owner_mobile="980 555 0199"))
    assert "Code sent to (980) 555-0199. Your mobile changes after you enter it." in text(step)  # m34
    code, _ = code_from(telecom)
    done = text(client.post("/client/phone/confirm", data={"csrf": csrf, "code": code}))
    assert "Saved. Sign-in codes now go to (980) 555-0199. Other devices stay signed in." in done
    account = re.sub(r"<[^>]+>", "", text(client.get("/client/account")))
    assert "Signed in as (980) 555-0199" in account and "(980) 555-0123" not in account  # m7: the current number
    out = client.post("/client/logout", data={"csrf": csrf})
    assert "You signed out." in text(out) and out.url.path == "/client/login"


def test_m8_m9_rate_limit_keeps_the_number_and_links_back_and_both_pages_allow_a_typo(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    hint = "If you don't get a text within a minute, check the number and send a new code."
    for _ in range(3):
        client.post("/client/login", data={"mobile": "980 555 0123"}, follow_redirects=False)
    assert hint in text(client.get("/client/verify"))
    limited = text(client.post("/client/login", data={"mobile": "980 555 0123"}))
    assert hint in limited and 'value="980 555 0123"' in limited
    assert "<a class=auth__link href=/client/verify>Enter the code you got</a>" in limited


def test_m10_m15_the_save_notices_say_what_the_rule_notes_say(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    hours = text(client.post("/client/schedule", data=schedule_form(csrf, hours_mode="set", open_mon="1",
                                                                     mon_open="08:00", mon_close="17:00")))
    assert slot(hours) == ("Saved. You changed “Working hours”. Applies right away to times the assistant offers. "
                           "Bookings already made stay as they are.")
    assert "mid-conversation" not in slot(hours)
    client.post("/client/phone", data=phone_form(csrf, business_line="704 555 0123"))
    moved = text(client.post("/client/phone", data=phone_form(csrf, business_line="704 555 0177")))
    assert slot(moved) == "Saved. You changed “Your business number”. Checks start again because the business number changed."


def test_m11_schedule_reset_is_local_with_javascript_and_hidden_at_the_default(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    client.post("/client/schedule", data=schedule_form(csrf, appointment_duration_minutes="90", appointment_duration_custom="90"))
    page = client.get("/client/schedule").text
    duration = re.search(r'<button type=submit class="btn btn--ghost rule-foot__reset" name=reset '
                         r'value=appointment_duration_minutes data-reset-values="([^"]*)"( hidden)?>', page)
    assert duration.group(2) is None  # not at its default: Reset shows
    assert json.loads(html.unescape(duration.group(1))) == {"appointment_duration_custom": "60", "appointment_duration_minutes": "60"}
    assert re.search(r'value=timezone data-reset-values="[^"]*" hidden>', page)  # at its default: hidden
    assert "function initScheduleReset()" in JS and "e.preventDefault();" in JS.split("function initScheduleReset()", 1)[1]


def test_m13_m14_forms_validate_on_the_server_and_the_one_tap_hours_land_on_the_rule(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    schedule = client.get("/client/schedule").text
    assert re.search(r"<form method=post action=/client/schedule id=schedule-form novalidate ", schedule)
    assert re.search(r"<form method=post action=/client/phone id=phone-form novalidate ", client.get("/client/phone").text)
    assert 'formaction="/client/schedule#working-hours" data-suggest-hours' in schedule
    assert '<li class="node node--icon" id=working-hours>' in schedule and "$('#working-hours h2')" in JS


def test_m16_m17_m18_carrier_other_and_the_rename_offer(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    page = text(client.post("/client/phone", data=phone_form(csrf, carrier="other")))
    assert "Ask your carrier how to turn off forwarding, and write it down." in page
    path.write_text(json.dumps({"prompt_name": "Name for Oak & Pine Tree Care?"}))
    client.app.state.messages.current()
    offer = text(client.post("/client/phone", data=phone_form(csrf, business_name="Oak & Pine Co", carrier="other")))
    assert "1 text still says “Oak & Pine Tree Care”. Update it to the new name?" in offer
    assert ">Update it</button>" in offer and ">Leave it</button>" in offer
    kept = client.post("/client/phone/rename-texts", data={"csrf": csrf, "action": "leave"}, follow_redirects=False)
    assert kept.status_code == 303
    assert slot(client.get("/client/phone").text) == "Kept the text as it is."


def test_m20_the_help_number_takes_us_numbers_only(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    for bad in ("+44 20 7946 0958", "555 0123", "+1 704 555 01234"):
        assert portal_phone.ERR_CONTACT in text(client.post("/client/phone", data=phone_form(csrf, business_contact=bad))), bad
    client.post("/client/phone", data=phone_form(csrf, business_contact="+1 704 555 0199"))
    assert client.app.state.business_contact == "(704) 555-0199"


def test_m27_a_missing_portal_page_is_a_portal_page(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    anonymous = client.get("/client/nope")
    assert anonymous.status_code == 404 and anonymous.headers["content-type"].startswith("text/html")
    assert "<h1>That page doesn't exist.</h1>" in text(anonymous) and "href=/client/home>" in anonymous.text
    sign_in(client, telecom)
    signed = client.get("/client/settings/old")
    assert signed.status_code == 404 and "That page doesn't exist." in text(signed) and "<nav class=nav" in signed.text
    assert client.get("/client/static/nope.css").status_code == 404
    assert client.get("/not-the-portal").headers["content-type"].startswith("application/json")


def test_m28_an_expired_messages_form_keeps_what_was_typed(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.post("/client/messages", data={"csrf": "stale", "prompt_name": "Your name, please?"})
    assert page.status_code == 400 and not path.exists()
    shown = text(page)
    assert "This page was open a long time. Check your changes and press Save again." in shown
    assert ">Your name, please?</textarea>" in shown and f"name=csrf value='{csrf}'" in page.text
    assert "data-dirty-initial" in page.text  # the save bar is up


def test_m29_a_question_switch_is_one_setting(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    saved = client.post("/client/messages", data={"csrf": csrf, "ask_email": "1"})
    assert slot(saved.text) == "Saved. You turned on “Email address”."
    assert pm.changed_words(0, 1) == "1 setting changed" and pm.changed_words(2, 1) == "3 changes"
    rejected = client.post("/client/messages", data={"csrf": csrf, "intro": "Call our business line", "ask_phone": "1",
                                                     "ask_email": "1"}).text
    assert "<span class=topsave__count>Not saved · 2 changes</span>" in rejected


def test_m30_m31_m32_plain_words(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    pages = "".join(text(client.get(url)) for url in ("/client/home", "/client/messages", "/client/phone"))
    assert "FluxWorks operator" not in pages and "Contact number sentence" not in pages and "Assistant stepped back" not in pages
    assert "[Your HELP number]" in pages and "<dt>Wants to talk to you</dt>" in pages
    assert "This is the number customers call. TextBack never changes it." in pages
    confirmation = re.search(r'<article class="qset[^"]*" id=card-booking_confirmation .*?</article>', pages, re.S).group(0)
    bill = re.search(r"<p data-bill-text>(.*?)</p>", confirmation).group(1)
    assert re.fullmatch(r"Billed as [23] texts\. The calendar links make this text long\. Customers still see one message\.", bill)
    assert 'name=fix value=booking_confirmation data-fix data-symbol="" hidden>' in confirmation


def test_m36_without_javascript_the_touched_length_control_wins(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    client.post("/client/schedule", data=schedule_form(csrf, appointment_duration_minutes="90"))  # chip tapped, box untouched
    assert state.appointment_duration_minutes == 90
    client.post("/client/schedule", data=schedule_form(csrf, appointment_duration_minutes="90", appointment_duration_custom="75",
                                                       appointment_duration_shown="90"))  # box typed, chip untouched
    assert state.appointment_duration_minutes == 75
    both = text(client.post("/client/schedule", data=schedule_form(csrf, appointment_duration_minutes="30",
                                                                   appointment_duration_custom="50",
                                                                   appointment_duration_shown="75")))
    assert ps.ERR_DURATION_BOTH in both and state.appointment_duration_minutes == 75


def test_finish_items_with_markup(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    messages = client.get("/client/messages").text
    assert 'aria-label="Insert Business name"' in messages and 'aria-label="Edit wording: Question 4: the name"' in messages
    assert "STOP line added for you<span class=msg__sep> · </span>" in messages
    assert "<title>Messages · Oak &amp; Pine Tree Care · TextBack</title>" in messages
    assert pm.MESSAGES["handoff_ack"][0] == "Steps-back text" and "When the assistant steps back" in messages
    shell = messages.split("<main", 1)
    assert shell[0].index("<a class=skip") < shell[0].index("<header") and "<nav class=nav" in shell[1].split("</main>", 1)[1]
    account = text(client.get("/client/account"))
    assert "#i-monitor-smartphone" in account and "Yes, sign out everywhere" in account
    assert "addEventListener('keydown'" in JS.split("function initJump()", 1)[1].split("function ", 1)[0]
    assert "channel: 'count', debounce: 1000" in JS
    assert "location.hash !== '#availability'" in JS and 'action="/client/calendar#availability"' in client.get("/client/calendar").text
    sample = [(Path(TEMPLATE_DIR) / "client" / name).read_text() for name in ("home.html.j2", "messages.html.j2")]
    for template in sample:
        assert not any(phrase in template.lower() for phrase in FORBIDDEN_PHRASES)
    assert portal_status.headline([{"state_word": "Waiting on FluxWorks"}, {"state_word": "Waiting on phone companies"}]) == \
        portal_status.HEADLINE_WAITING_BOTH
    clock[0] += timedelta(seconds=1)  # (keeps the session clock moving like the other page tests)
    assert OWNER
