"""Candidate C pages: Home truth, the Messages example conversation and notices, Schedule saves,
Phone (read-only texting number, rename offer, checks, mobile two-step) and Calendar next steps."""
import html
from pathlib import Path
import json
import re
from datetime import timedelta

from text_back import client_settings, portal_status
from text_back.handlers import handle_voice_event
from text_back.portal_messages import DESTINATION_OFF, NETWORK_NOTICE
from text_back.portal_render import split_links, url_runs
from text_back.portal_sample import render_scenario
from text_back.portal_scheduling import SAVED as SCHEDULE_SAVED
from text_back.telecom import FakeTelecom
from test_client_portal import OWNER, code_from, csrf_of, make, sign_in
from test_portal_c_words import visible

BUSINESS_LINE, TEXTING = "+19805550177", "+19805550100"


def text_of(response) -> str:
    return html.unescape(response.text)


def signed_in(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    return client, telecom, clock, path, csrf_of(client.get("/client/home").text)


def missed(state, sid, caller, at, forwarded_from=""):
    handle_voice_event(store=state.store, telecom=FakeTelecom(), call_sid=sid, call_status="ringing", from_number=caller,
                       to_number=TEXTING, wiring_mode="forwarded", business_name="Oak", now=at, forwarded_from=forwarded_from)
    with state.store.transaction():
        state.store.conn.execute("UPDATE sms_outbox SET status='sent', created_at=? WHERE key=?", (at.isoformat(), f"{sid}:intro"))
        state.store.record_outcome(lead_id=caller, event_type="sms.initial_sent", idempotency_key=f"call:{sid}:initial_sms",
                                   evidence_id=sid, occurred_at=at.isoformat())


def section(page, cls):
    return re.search(rf"<section class={cls} .*?</section>", page, re.S).group(0)


def node(page, hook):
    """One node of Home's spine, by its data- hook (data-week, data-callers, data-setup=<key>)."""
    return re.search(rf"<li class=\"node node--\w+\" {hook}>.*?\n</li>", page, re.S).group(0)


def slot_text(page):
    """The words in the in-flow notice slot (empty when it holds no notice)."""
    match = re.search(r"<div class=status-slot id=notice role=status>(?:<div class=\"notice [^\"]*\" data-notice>.*?"
                      r"<p class=notice__text>(.*?)</p>)?", page, re.S)
    return html.unescape(match.group(1) or "")


def thread(page, scenario):
    return re.search(rf"<ol class=thread data-scenario={scenario} .*?</ol>", page, re.S).group(0)


# --- Home ------------------------------------------------------------------------------

def test_home_shows_counts_and_rows_from_the_same_window_with_full_dates(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    monday = clock[0]  # Mon Oct 19 2026, 15:00 UTC; the app's zone is UTC
    missed(state, "CA-old", "+19805550199", monday - timedelta(days=3))       # last Friday: outside the window
    missed(state, "CA-1", "+19805550141", monday - timedelta(hours=5))
    clock[0] = monday + timedelta(days=2)                                     # Wednesday
    missed(state, "CA-2", "+19805550142", clock[0] - timedelta(minutes=30))
    sign_in(client, telecom)  # the 12-hour session ended while the clock moved on
    page = client.get("/client/home").text
    week = node(page, "data-week")
    assert "Since Mon, Oct 19. The counts and the list below cover the same days." in re.sub(r"<[^>]+>", "", html.unescape(week))
    assert re.search(r"data-count=missed_calls><dt>Missed calls</dt><dd class=tnum>2</dd>", week)
    assert re.search(r"data-count=customers_texted><dt>Customers texted</dt><dd class=tnum>2</dd>", week)
    callers = node(page, "data-callers")
    rows = [re.sub(r"<[^>]+>", "", row) for row in re.findall(r"<li class=caller>.*?</li>", callers, re.S)]
    assert len(rows) == 2  # the same window as the counts
    assert "(980) 555-0142" in rows[0] and "Wed, Oct 21, 2:30 PM" in rows[0]  # a full date, never "Today"
    assert "(980) 555-0141" in rows[1] and "Mon, Oct 19, 10:00 AM" in rows[1]  # a full date from a datetime
    assert "(980) 555-0199" not in page
    assert "Waiting for a reply" in rows[0]


def test_home_empty_week_and_setup_cards_go_to_the_fix(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    client.app.state.store.set_setting("texting_approval_state", "waiting")
    page = text_of(client.get("/client/home"))
    assert '<p class=status-line data-status-line>Not working yet: 1 step for you, 2 waiting on others.</p>' in page  # P3: calendar waits on FluxWorks
    assert "No callers this week. They appear here after the next missed call." in page
    cards = {key: node(page, f"data-setup={key}") for key in ("calendar", "forwarding", "approval")}
    assert "Waiting on FluxWorks" in cards["calendar"] and "FluxWorks connects your calendar for you." in cards["calendar"]
    assert 'href="/client/phone#checks">Finish forwarding</a>' in cards["forwarding"]  # m22: lands at the checks
    assert "Waiting on phone companies" in cards["approval"] and "<a " not in cards["approval"]


# --- Messages ------------------------------------------------------------------------------

def test_the_example_conversation_is_the_real_product_output_with_the_saved_texts(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    client.post("/client/messages", data={"csrf": csrf, "intro": "[Business name] here, sorry we missed you. What do you need?",
                                          "ask_email": "1"})
    page = client.get("/client/messages").text
    labels = re.findall(r"<option value=(\w+)(?: selected)?>([^<]+)</option>", html.unescape(page))
    assert labels == [("booked", "Books a job"), ("unclear", "Unclear answers"), ("noreply", "No reply"),
                      ("failed", "Booking failed"), ("steps_back", "Asks for the owner"), ("safety", "Mentions danger"),
                      ("keywords", "START, HELP and STOP")]
    for scenario in ("booked", "steps_back", "keywords"):
        expected = render_scenario(scenario, templates=json.loads(path.read_text()), business_name=state.business_name,
                                   asked={"email"}, now=clock[0], public_base_url=state.public_base_url,
                                   tz_name=state.timezone_name)
        rail = thread(page, scenario)
        shown = re.findall(r'<p data-preview=(\w*)>(.*?)</p><ul class=sms__links data-links=\w*( hidden)?>(.*?)</ul>', rail, re.S)
        wanted = []
        for b in expected:
            if b.side != "textback":
                continue
            words, links = split_links(b.text, str(state.public_base_url))
            wanted.append((b.key or "", str(url_runs(words)), "" if links else " hidden",
                           "".join(f'<li><span class=sms__linkbtn title="{html.escape(url, quote=True)}">{label}</span></li>'
                                   for label, url in links)))
        assert shown == wanted, scenario
    booked = thread(page, "booked")
    assert "Oak &amp; Pine Tree Care here, sorry we missed you." in booked  # the SAVED wording, not the default
    assert 'title="https://example.test/a/' in booked and "Add to Google Calendar ›" in booked
    assert "Booked · on the test calendar" in booked  # the stub calendar is named as such
    assert "<h2 class=rail__title id=rail-title tabindex=-1>Example conversation</h2>" in page
    assert "Nothing is sent · names made up" in page


def test_the_steps_back_destination_comes_from_config(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    page = text_of(client.get("/client/messages"))
    card = re.search(r'<article class="qset" id=card-handoff_ack .*?</article>', page, re.S).group(0)
    assert "This text must tell the customer someone will follow up." in card and DESTINATION_OFF in card
    assert "details sent to" not in thread(page, "steps_back")

    class Chat:
        channel_name = "telegram"

    client.app.state.delivery_transport = Chat()
    client.app.state.handoff_destination = "operator-chat"
    page = text_of(client.get("/client/messages"))
    card = re.search(r'<article class="qset" id=card-handoff_ack_safety .*?</article>', page, re.S).group(0)
    assert "What happens next" in card and DESTINATION_OFF not in page
    rail = thread(page, "safety")
    assert "The assistant steps back here" in rail and "Customer's details sent to FluxWorks" in rail


def test_save_notice_names_the_change_in_the_slot_under_the_header(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    saved = client.post("/client/messages", data={"csrf": csrf, "prompt_location": "Where is the job?", "ask_phone": "1"}).text
    # m29: a question switch is a setting, named as one.
    assert slot_text(saved) == "Saved. You changed “Question 2: the address”. You turned on “Best phone number”."
    assert saved.index("id=notice") < saved.index("<h1>Messages</h1>")
    back = client.post("/client/messages", data={"csrf": csrf, "ask_phone": "1"}).text
    assert "Saved. Back to standard wording: “Question 2: the address”." in html.unescape(back)
    same = client.post("/client/messages", data={"csrf": csrf, "ask_phone": "1"}).text
    assert "Saved. No wording changed." in same


def test_network_notice_only_while_not_approved(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    assert text_of(client.get("/client/messages")).count(NETWORK_NOTICE) == 1  # unknown counts as not approved
    client.app.state.store.set_setting("texting_approval_state", "approved")
    assert NETWORK_NOTICE not in text_of(client.get("/client/messages"))


def test_inserts_are_labels_on_screen_and_placeholders_in_the_file(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    assert "This is the scheduling assistant for [Business name]." in page  # the editor shows the label
    assert 'data-insert="[Business name]"' in page and "{business_name}" not in visible(page)
    client.post("/client/messages", data={"csrf": csrf, "prompt_name": "Name for [Business name]?"})
    assert json.loads(path.read_text()) == {"prompt_name": "Name for {business_name}?"}
    wrong = text_of(client.post("/client/messages", data={"csrf": csrf, "prompt_name": "Name for [Job]?"}))
    assert "This text can't fill in Job. It can use: Business name." in wrong
    typed = text_of(client.post("/client/messages", data={"csrf": csrf, "prompt_name": "Name {please}"}))
    assert "Something typed by hand isn't a detail we can fill in." in typed
    assert json.loads(path.read_text()) == {"prompt_name": "Name for {business_name}?"}  # nothing written


# --- Schedule ------------------------------------------------------------------------------

def schedule_form(csrf, **changes):
    form = {"csrf": csrf, "appointment_duration_minutes": "60", "timezone": "UTC", "hours_mode": "any",
            "quiet_hours_start": "21:00", "quiet_hours_end": "08:00", "followup_delay_1": "120",
            "followup_delay_2": "1440", "followup_expiry_minutes": "2880"}
    form.update(changes)
    return form


def test_schedule_save_shows_the_pinned_confirmation_and_persists(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/schedule").text
    assert re.search(r"id=dur-60 value=60 checked[ >]", page) and not re.search(r"id=dur-custom value=custom checked", page)
    saved = client.post("/client/schedule", data=schedule_form(csrf, appointment_duration_minutes="90"))
    assert slot_text(saved.text) == (SCHEDULE_SAVED.format(rules="Appointment length")
                                     + " Applies right away, including customers mid-conversation.")
    state = client.app.state
    assert state.appointment_duration_minutes == 90 and state.store.setting("appointment_duration_minutes") == "90"
    page = client.get("/client/schedule").text
    assert re.search(r"id=dur-90 value=90 checked[ >]", page)
    custom = client.post("/client/schedule", data=schedule_form(csrf, appointment_duration_minutes="custom",
                                                               appointment_duration_custom="75")).text
    assert state.appointment_duration_minutes == 75
    assert re.search(r"id=dur-custom value=custom checked", custom) and "value=60 checked" not in custom
    reset = client.post("/client/schedule", data=schedule_form(csrf, appointment_duration_minutes="custom",
                                                              appointment_duration_custom="75",
                                                              reset="appointment_duration_minutes"))
    assert reset.status_code == 200 and state.appointment_duration_minutes == 60
    assert state.store.setting("appointment_duration_minutes") is None  # the default is stored as no row
    bad = text_of(client.post("/client/schedule", data=schedule_form(csrf, appointment_duration_minutes="custom",
                                                                    appointment_duration_custom="7")))
    assert "Not saved. 1 thing needs a change." in bad and "Appointment length must be 15 to 480 minutes" in bad
    assert state.appointment_duration_minutes == 60


def test_any_time_shows_the_warning_and_the_one_tap_hours_save_nothing(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    page = text_of(client.get("/client/schedule"))
    assert "Customers can be offered times like 1 AM. Set your hours." in page
    assert "Use Mon–Fri, <span class=nw>8 AM–5 PM</span>" in page  # a time range never breaks across lines
    filled = client.post("/client/schedule", data=schedule_form(csrf, suggest_hours="1")).text
    assert client.app.state.store.setting("working_hours") is None  # filled in, not saved
    assert "name=hours_mode value=set checked" in filled and "id=open_mon name=open_mon value=1" in filled
    assert re.search(r"id=open_mon name=open_mon value=1 checked>", filled)
    assert not re.search(r"id=open_sun name=open_sun value=1 checked>", filled)
    assert "<span class=topsave__count>1 rule changed</span>" in filled and "data-dirty-initial" in filled
    client.post("/client/schedule", data=schedule_form(csrf, hours_mode="set", open_mon="1", mon_open="08:00", mon_close="17:00"))
    assert json.loads(client.app.state.store.setting("working_hours"))["mon"] == {"open": "08:00", "close": "17:00"}
    # Set hours are saved: the warning (shown by CSS only while "Any day, any time" is chosen) is off.
    after = client.get("/client/schedule").text
    assert "name=hours_mode value=set checked>" in after and "name=hours_mode value=any checked>" not in after
    assert ".hours-card:has([name=\"hours_mode\"][value=\"set\"]:checked) :is(.any-warning" in \
        (Path(__file__).resolve().parents[1] / "src/text_back/static/portal.css").read_text()


# --- Phone ------------------------------------------------------------------------------

def test_phone_texting_number_is_read_only_text_and_posting_it_changes_nothing(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    state.business_number = TEXTING
    page = text_of(client.get("/client/phone"))
    block = re.search(r"<div class=ro data-texting-number>.*?</div>", page, re.S).group(0)
    assert "(980) 555-0100" in block and "Set up by FluxWorks. It can't be changed here." in block
    assert "<input" not in block and "name=text_back_number" not in page and "name=texting_number" not in page
    client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak & Pine Tree Care", "owner_mobile": OWNER,
                                       "text_back_number": "+19805550999", "texting_number": "+19805550999"})
    assert state.business_number == TEXTING and state.store.setting("text_back_number") is None
    # No carrier picked: the "pick your carrier" line shows and no carrier is checked (CSS shows the codes on a pick).
    assert "data-codes-none>Pick your carrier to see the codes.</p>" in page and "name=carrier id=carrier-verizon value=verizon checked" not in page
    with_codes = text_of(client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak & Pine Tree Care",
                                                            "owner_mobile": OWNER, "carrier": "verizon"}))
    assert 'data-copy="*719805550100"' in with_codes and "*71 980 555 0100" in with_codes  # dialled vs read
    assert "Covers busy and no answer." in with_codes and "id=carrier-verizon value=verizon checked>" in with_codes


def test_rename_offer_updates_the_texts_that_still_say_the_old_name(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    client.post("/client/messages", data={"csrf": csrf, "prompt_name": "Oak & Pine Tree Care needs your name.",
                                          "intro": "Oak & Pine Tree Care missed you. What do you need?"})
    saved = text_of(client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak and Pine", "owner_mobile": OWNER}))
    assert "2 texts still say “Oak & Pine Tree Care”. Update them to the new name?" in saved and "Leave them" in saved
    assert "Saved. You changed “Business name”." in saved and saved.count("data-notice>") == 1  # one notice
    assert "<span class=menu__biz>Oak and Pine</span>" in saved  # the header shows the new name
    assert client.get("/client/phone").text.count("data-rename-offer") == 1  # offered until answered
    done = text_of(client.post("/client/phone/rename-texts", data={"csrf": csrf, "action": "update"}))
    assert "Updated 2 texts." in done and "data-rename-offer" not in done
    assert json.loads(path.read_text()) == {"prompt_name": "Oak and Pine needs your name.",
                                            "intro": "Oak and Pine missed you. What do you need?"}
    assert client.app.state.messages.current().templates["prompt_name"] == "Oak and Pine needs your name."
    # Leaving them clears the offer and keeps the texts.
    client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak", "owner_mobile": OWNER})
    left = client.post("/client/phone/rename-texts", data={"csrf": csrf, "action": "leave"}).text
    assert "data-rename-offer" not in left and json.loads(path.read_text())["intro"].startswith("Oak and Pine")


def test_checklist_ticks_persist_and_never_look_like_evidence(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    saved = text_of(client.post("/client/phone/checks", data={"csrf": csrf, "check_answered_no_text": "1"}))
    assert "Checks saved." in saved
    step3 = re.search(r'<li class="node node--manual" data-check=3>.*?\n</li>', saved, re.S).group(0)
    assert "You checked this" in step3 and "checked>" in step3 and "I checked this" in step3
    page = text_of(client.get("/client/phone"))
    assert "1 of 5 done" in page and re.search(r'class="node node--manual" data-check=3', page)
    assert re.search(r'class="node node--todo" data-check=1', page)
    client.post("/client/phone/checks", data={"csrf": csrf})
    assert re.search(r'class="node node--todo" data-check=3', client.get("/client/phone").text)


def test_forwarded_call_ticks_the_evidence_checks_on_the_page(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    state.business_number = TEXTING
    client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak", "owner_mobile": OWNER,
                                       "business_line": "980 555 0177"})
    missed(state, "CA-direct", "+19805550141", clock[0] - timedelta(hours=1))  # straight to the texting number
    assert re.search(r'class="node node--todo" data-check=1', client.get("/client/phone").text)
    missed(state, "CA-fwd", "+19805550142", clock[0] - timedelta(minutes=10), forwarded_from=BUSINESS_LINE)
    page = client.get("/client/phone").text
    for n in (1, 2, 4):
        assert re.search(rf'class="node node--done" data-check={n}', page), n


def test_owner_mobile_change_is_two_steps_and_keep_is_a_post(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    step = text_of(client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak", "owner_mobile": "980 555 0199"}))
    # m34: the notice says a code went out and nothing moved yet.
    assert "<h1>Confirm your new mobile</h1>" in step and "Code sent to (980) 555-0199. Your mobile changes after you enter it." in step
    assert "We texted a six-digit code to (980) 555-0199." in re.sub(r"<[^>]+>", "", step)  # the number sits in a no-wrap span
    assert "action=/client/phone/keep" in step and "Keep my current mobile" in step
    before = len([m for m in telecom.outbound if m.kind == "login_code"])
    client.post("/client/phone/confirm", data={"csrf": csrf, "action": "resend"})
    assert len([m for m in telecom.outbound if m.kind == "login_code"]) == before + 1
    code, text = code_from(telecom)
    assert text.to == "+19805550199"
    done = text_of(client.post("/client/phone/confirm", data={"csrf": csrf, "code": code}))
    assert "Saved. Sign-in codes now go to (980) 555-0199. Other devices stay signed in." in done
    assert client.app.state.owner_mobile == "+19805550199"


# --- Calendar ------------------------------------------------------------------------------

def test_calendar_not_connected_is_never_a_dead_end(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    page = text_of(client.get("/client/calendar"))
    status = re.search(r'<li class="node node--\w+" id=connection>.*?\n</li>', page, re.S).group(0)
    assert "No calendar yet" in status and "FluxWorks connects your calendar for you." in status  # who does the next step
    client.app.state.support_contact = "+19805550111"
    status = re.search(r'<li class="node node--\w+" id=connection>.*?\n</li>', text_of(client.get("/client/calendar")), re.S).group(0)
    assert 'href="sms:+19805550111" data-support>Text FluxWorks support</a>' in status
    view = {"provider": "google", "status": "none", "calendar_id": "", "can_connect": True}
    monkeypatch.setattr(client_settings, "calendar_status", lambda state: dict(view))
    monkeypatch.setattr(portal_status, "calendar_status", lambda state: dict(view))
    status = re.search(r'<li class="node node--\w+" id=connection>.*?\n</li>', text_of(client.get("/client/calendar")), re.S).group(0)
    assert "<input type=hidden name=action value=connect>" in status and "Connect Google Calendar" in status


def test_calendar_check_lists_free_times_inside_working_hours_on_the_test_calendar(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    client.post("/client/schedule", data=schedule_form(csrf, hours_mode="set", open_tue="1", tue_open="09:00", tue_close="12:00"))
    result = text_of(client.post("/client/calendar", data={"csrf": csrf, "action": "check"}))
    card = re.search(r'<li class="node node--icon" id=availability>.*?\n</li>', result, re.S).group(0)
    assert "Test calendar, not yours" in card and "These times are not from your calendar." in card
    slots = [re.sub(r"<[^>]+>", "", li) for li in re.findall(r'<li class="slot tnum">(.*?)</li>', card)]
    # Finish item: start times only, one row per day, so 30-minute steps never read as overlapping appointments.
    assert slots == ["Tue, Oct 20 · starts at 9:00, 9:30, 10:00 AM"]
