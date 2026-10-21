"""Messages page: grouping, inline validation, Reset, switches, sample data, trial flag, segment math."""
import html as html_lib
import json
import re

from test_client_portal import csrf_of, make as _make, sign_in

from text_back import portal_messages as pm
from text_back.messages import DEFAULT_TEMPLATES

GROUP_TITLES = ("First text", "Questions", "Confirmation", "Follow-ups", "STOP and HELP")


def make(tmp_path, monkeypatch, **kwargs):
    monkeypatch.setenv("TEXT_BACK_REGISTRATION_DIR", str(tmp_path / "no-such-dir"))
    return _make(tmp_path, monkeypatch, **kwargs)


def _page(client):
    page = client.get("/client/messages")
    assert page.status_code == 200
    return page.text


def _error_under(html, key):
    match = re.search(rf'<p class="error" id="{key}-error">.*?<span>(.*?)</span>', html, re.S)
    return html_lib.unescape(match.group(1)) if match else None


# --- rendering ------------------------------------------------------------------------

def test_groups_render_in_order_with_defaults_and_no_key_leaks(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    html = _page(client)
    assert "<h1>Messages</h1>" in html and html.count("<h1") == 1
    positions = [html.index(f">{title}") for title in GROUP_TITLES]
    assert positions == sorted(positions)
    assert "Hey, sorry we missed your call" in html  # the default is the placeholder
    # Nothing is overridden: every field says so and offers no Reset (it would do nothing).
    assert html.count("Standard wording.") == len(pm.EDITABLE_KEYS) and "Default:" not in html and 'name="reset"' not in html
    assert "STOP stays in. Carriers require the word STOP." in html
    assert "Save messages" in html and 'class="sticky-save"' in html
    assert '<h2 id="g-first">First text</h2>' in html  # the "n edited" pill is never inside the heading
    assert '<details class="preview-sheet" id="preview-sheet">' in html and 'class="sheet-summary"' in html
    # Counters are described, not announced: no live region, the count id rides on aria-describedby.
    assert 'aria-live' not in html.split('id="toasts"')[0]
    assert 'aria-describedby="intro-hint intro-count"' in html
    assert 'aria-describedby="opt_out_suffix-hint opt_out_suffix-count opt_out_suffix-lock"' in html
    assert 'aria-describedby="slot_unavailable-count"' in html  # no hint on that one
    assert '<div class="chips" role="group" aria-label="Fill-ins for this text">' in html
    assert 'data-key="intro"' in html and 'data-allowed="business_name"' in html
    assert re.search(r'id="intro"[^>]*data-suffix-required="1"', html)
    assert re.search(r'id="prompt_name"[^>]*data-suffix-required="0"', html)
    assert '<span>Business name</span> <code>{business_name}</code>' in html
    assert "No fill-ins in this text." in html
    for key in pm.EDITABLE_KEYS:  # owner copy names fields by label, never by key
        assert f"{key} must" not in html and f"{key} is" not in html
    assert "AI" not in re.sub(r"<[^>]+>", " ", html).split()
    assert "Sent 2 hours after the first text" in html and "Sent 1 day after the first nudge" in html


def test_preview_carries_sample_data_and_hides_optional_bubbles(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    html = _page(client)
    sample = json.loads(re.search(r"data-sample='([^']+)'", html).group(1))
    assert sample["business_name"] == "Oak & Pine Tree Care" and sample["service"] == "tree removal"
    assert sample["calendar_links"].startswith("Add to calendar: Google https://example.test/a/1-000000000000/g")
    assert sample["invite_line"] == "" and sample["invited_email"] == ""
    assert 'data-key="prompt_phone" data-when="ask_phone" hidden' in html
    assert 'data-key="prompt_email" data-when="ask_email" hidden' in html
    assert 'data-key="booking_confirmation"' in html and "Missed call from Dana" in html
    assert html.index('data-key="intro"') < html.index('data-key="booking_confirmation"') < html.index('data-key="followup_1"')
    assert 'aria-hidden="true" data-sample=' in html
    assert "Reply STOP to opt out." in html.split('data-key="intro">')[1].split("</div>")[0]  # suffix appended in the bubble


def test_switch_markup_and_the_no_checked_rule(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    html = _page(client)
    assert "checked" not in html and "name=ask_phone value=1" in html and "name=ask_email value=1" in html
    csrf = csrf_of(html)
    saved = client.post("/client/messages", data={"csrf": csrf, "ask_phone": "1", "ask_email": "1"}).text
    assert "name=ask_phone value=1 checked" in saved and "name=ask_email value=1 checked" in saved
    assert saved.count("checked") == 2
    assert 'data-key="prompt_phone" data-when="ask_phone">' in saved  # no longer hidden
    sample = json.loads(re.search(r"data-sample='([^']+)'", saved).group(1))
    assert sample["invite_line"] == "A calendar invite is on its way to dana@example.com."
    assert json.loads(path.read_text()) == {"fields": "service, location, preferred_time, name, phone, email"}


def test_trial_flag_follows_registration_status(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    html = _page(client)
    assert 'data-trial="1"' in html and "Includes the &#39;[SignalWire Free Trial]&#39; tag" in html
    assert '<span class="prefix">[SignalWire Free Trial]</span>' in html
    staged = tmp_path / "registration"
    staged.mkdir()
    for name in ("brand", "campaign", "order"):
        (staged / f"{name}-response.json").write_text(json.dumps({"id": name, "state": "complete"}))
    monkeypatch.setenv("TEXT_BACK_REGISTRATION_DIR", str(staged))
    html = _page(client)
    assert 'data-trial="0"' in html and "Free Trial" not in html


def test_without_a_messages_file_everything_is_read_only(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch, messages_file=False)
    sign_in(client, telecom)
    html = _page(client)
    assert "turned on for this account yet" in html and "Save messages" not in html
    assert html.count("<textarea") == len(pm.EDITABLE_KEYS) == len(re.findall(r"<textarea[^>]* disabled", html))
    assert len(re.findall(r"type=checkbox[^>]* disabled", html)) == 2  # both switches
    chips = re.findall(r"<button type=\"button\" data-insert=[^>]*>", html)
    assert chips and all(" disabled>" in chip for chip in chips)  # read-only page: no live chip writes into a disabled box


# --- saving, validation, reset ------------------------------------------------------------

def test_every_rejection_is_shown_beside_its_field_and_nothing_is_written(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(_page(client))
    page = client.post("/client/messages", data={
        "csrf": csrf,
        "intro": "Call our business line any time",
        "opt_out_suffix": "Reply END to end",
        "handoff_ack": "The owner will be in touch.",
        "handoff_ack_safety": "We will follow up shortly.",
        "booking_error": "No booking was made. Please call us.",
        "prompt_name": "Your name, {customer}?",
        "prompt_service": "Hi {",
        "prompt_location": "x" * 481,
    })
    html = page.text
    assert page.status_code == 200 and not path.exists()
    assert "Not saved: First text after a missed call: can&#39;t contain &#39;business line&#39;." in html
    assert _error_under(html, "intro") == "First text after a missed call: can't contain 'business line'."
    assert _error_under(html, "opt_out_suffix") == "Opt-out line must tell the customer to reply STOP."
    assert "lock-note err" in html
    assert _error_under(html, "handoff_ack") == "This text must promise a follow up (those two words)."
    assert "911" in _error_under(html, "handoff_ack_safety")
    assert _error_under(html, "booking_error") == "When the calendar can't be reached: must say no booking was made and must not contain the word call."
    assert _error_under(html, "prompt_name") == "The name: {customer} isn't a fill-in for this text. You can use {business_name}."
    assert _error_under(html, "prompt_service") == "The job: a { is missing its }."
    assert _error_under(html, "prompt_location") == "The location is longer than 480 characters."
    assert html.count('aria-invalid="true"') == 8
    assert 'aria-describedby="intro-error intro-hint intro-count"' in html  # error, hint and counter all described
    for word in ("template", "placeholder", "keep the customer texting"):
        assert word not in re.sub(r"<[^>]+>", " ", html)
    assert "opt_out_suffix must" not in html and "handoff_ack must" not in html
    assert 'id="intro"' in html and ">Call our business line any time</textarea>" in html  # draft kept
    assert "Call our business line any time Reply END to end" in html  # the preview shows the attempted text


def test_save_then_reset_one_field_keeps_the_rest(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(_page(client))
    saved = client.post("/client/messages", data={"csrf": csrf, "intro": "Oak & Pine here. What do you need?", "prompt_name": "And your name?"}).text
    assert "Saved. New conversations use these messages from now on." in saved
    assert saved.count("1 edited") == 2 and 'aria-invalid' not in saved  # one per group: First text, Questions
    assert '<h2 id="g-first">First text</h2><span class="pill-status info">' in saved
    # Only the two overridden fields show their default and a named Reset.
    assert saved.count('name="reset"') == 2 and saved.count("Standard wording.") == len(pm.EDITABLE_KEYS) - 2
    assert 'name="reset" value="intro" aria-label="Reset First text after a missed call"' in saved
    assert "Default: Hey, sorry we missed your call" in saved and "Default: Reply STOP to opt out." not in saved
    assert json.loads(path.read_text()) == {"intro": "Oak & Pine here. What do you need?", "prompt_name": "And your name?"}
    reset = client.post("/client/messages", data={"csrf": csrf, "reset": "intro", "intro": "Oak & Pine here. What do you need?", "prompt_name": "And your name?"}).text
    assert "Reset to the standard wording." in reset and reset.count("1 edited") == 1
    assert 'name="reset" value="intro"' not in reset and 'name="reset" value="prompt_name" aria-label="Reset The name"' in reset
    assert json.loads(path.read_text()) == {"prompt_name": "And your name?"}
    assert client.app.state.messages.current().render("intro", business_name="x").startswith("Hey, sorry we missed your call")


# --- pure helpers --------------------------------------------------------------------------

def test_segments_follow_gsm7_and_ucs2_rules():
    assert pm.segments("a" * 160)["segments"] == 1 and pm.segments("a" * 161)["segments"] == 2
    assert pm.segments("a" * 306)["segments"] == 2 and pm.segments("a" * 307)["segments"] == 3
    assert pm.segments("[" * 80)["segments"] == 1 and pm.segments("[" * 81)["segments"] == 2  # extension chars count twice
    dash = pm.segments("—" + "a" * 69)
    assert dash["ucs2"] and dash["special"] == "—" and dash["segments"] == 1
    assert pm.segments("—" + "a" * 70)["segments"] == 2
    assert pm.segments(pm.TRIAL_PREFIX)["chars"] == 24
    assert pm.segments("\U0001F642 hi")["chars"] == 5  # UTF-16 units, the same count portal.js reports


def test_render_sample_mirrors_the_engine_rules():
    samples = {"business_name": "Oak & Pine"}
    text, suffixed = pm.render_sample("intro", "Hi from {business_name}. {bogus}  Reply?", samples, "Reply STOP to opt out.", False)
    assert text == "Hi from Oak & Pine. Reply? Reply STOP to opt out." and suffixed
    text, suffixed = pm.render_sample("intro", "Hi, text STOP to end", samples, "Reply STOP to opt out.", True)
    assert text == "[SignalWire Free Trial] Hi, text STOP to end" and not suffixed
    text, suffixed = pm.render_sample("prompt_name", "Name? {business_name}", samples, "Reply STOP to opt out.", False)
    assert text == "Name? Oak & Pine" and not suffixed
    assert pm.describe("intro", DEFAULT_TEMPLATES["intro"], samples, "Reply STOP to opt out.", False).startswith("1")
    assert "Includes the opt-out line." in pm.describe("intro", DEFAULT_TEMPLATES["intro"], samples, "Reply STOP to opt out.", False)
    assert "Over the 480-character limit." in pm.describe("intro", "a" * 481, samples, "Reply STOP to opt out.", False)


def test_owner_reason_uses_labels_and_full_stops():
    assert pm.owner_reason("opt_out_suffix must tell the customer to reply STOP") == "Opt-out line must tell the customer to reply STOP."
    assert pm.owner_reason("handoff acknowledgements must promise a follow-up") == "This text must promise a follow up (those two words)."
    assert pm.owner_reason("unbalanced { or } in template", "prompt_service") == "The job: a { is missing its }."
    assert pm.owner_reason("unbalanced { or } in template") == "A { is missing its }."
    assert pm.owner_reason("placeholders must look like {business_name}", "intro") == "First text after a missed call: fill-ins look like {business_name}."
    assert pm.owner_reason("prompt_name uses unsupported placeholder(s) {customer}; allowed: {business_name}") == \
        "The name: {customer} isn't a fill-in for this text. You can use {business_name}."
    assert pm.owner_reason("prompt_name uses unsupported placeholder(s) {a}, {b}; allowed: {business_name}") == \
        "The name: {a}, {b} aren't fill-ins for this text. You can use {business_name}."
    assert pm.owner_reason("opt_out_suffix uses unsupported placeholder(s) {x}; allowed: none") == \
        "Opt-out line: {x} isn't a fill-in for this text. This text has no fill-ins."
    assert pm.owner_reason("intro must not promise a person or the business line ('call us back')") == \
        "First text after a missed call: can't contain 'call us back'."
    assert pm.owner_reason("booking_error must say no booking was made and keep the customer texting") == \
        "When the calendar can't be reached: must say no booking was made and must not contain the word call."
