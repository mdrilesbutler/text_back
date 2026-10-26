"""Candidate C, layer 4: Phone & business as one form (mockup d1 round 3, after the panel docked two
save scopes): sections in order, the live first-text preview, one Save for fields and manual checks that
names what changed, the rename offer in the one notice, deck error wording, the save bars, discard, the
carrier codes and the five checks with the shared glyph set and harness-only Example tags."""
import html
import re
from datetime import timedelta

from test_client_portal import OWNER, csrf_of, make, sign_in
from test_portal_c_pages import BUSINESS_LINE, TEXTING, missed


def signed_in(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    client.app.state.business_number = TEXTING
    return client, clock, csrf_of(client.get("/client/home").text)


def form(csrf, **changes):
    data = {"csrf": csrf, "checks_in_form": "1", "business_name": "Oak & Pine Tree Care", "owner_mobile": OWNER,
            "business_line": "", "business_contact": "", "carrier": ""}
    data.update(changes)
    return {k: v for k, v in data.items() if v is not None}


def slot(page):
    match = re.search(r"<div class=status-slot id=notice role=status>(?:<div class=\"notice [^\"]*\" data-notice>.*?"
                      r"<p class=notice__text>(.*?)</p>)?", page, re.S)
    return html.unescape(match.group(1) or "")


def test_one_form_holds_business_numbers_forwarding_and_the_checks_in_order(tmp_path, monkeypatch):
    client, clock, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/phone").text
    assert "<h1>Phone &amp; business</h1>" in page and page.count("<form method=post action=/client/phone ") == 1
    the_form = re.search(r"<form method=post action=/client/phone id=phone-form .*?</form>", page, re.S).group(0)
    heads = re.findall(r"<h2 tabindex=-1>([^<]+)</h2>", the_form)
    assert [html.unescape(h) for h in heads] == ["Business details", "Numbers", "Call forwarding", "Is forwarding working?"]
    for name in ("business_name", "business_contact", "business_line", "owner_mobile", "carrier",
                 "check_answered_no_text", "check_deactivation_saved"):
        assert f"name={name} " in the_form, name
    # The first text sits right under the name and before the HELP number.
    assert the_form.index("id=business_name ") < the_form.index("In the first text") < the_form.index("id=business_contact ")
    assert "data-name-preview" in the_form and "<span class=sms__who data-name-who>Oak &amp; Pine Tree Care</span>" in the_form
    for attr in ("data-track-changes", "data-topsave", 'data-changed-one="1 change"', 'data-changed-many="{n} changes"'):
        assert attr in the_form, attr
    assert '<div class="savebar" data-state=clean data-savebar data-form=phone-form>' in page
    # The texting number is text, never a field, and numbers never break.
    block = re.search(r"<div class=ro data-texting-number>.*?</div>", page, re.S).group(0)
    assert "<span class=nw>(980) 555-0100</span>" in block and "Set up by FluxWorks. It can&#39;t be changed here." in block


def test_one_save_writes_fields_and_ticks_and_names_what_changed(tmp_path, monkeypatch):
    client, clock, csrf = signed_in(tmp_path, monkeypatch)
    page = client.post("/client/phone", data=form(csrf, business_contact="980 555 0111", check_answered_no_text="1")).text
    assert slot(page) == "Saved. You changed “Number in the HELP reply”, “An answered call sent no text”."
    assert re.search(r'class="node node--manual" data-check=3', page)
    assert client.app.state.business_contact == "(980) 555-0111"
    page = client.post("/client/phone", data=form(csrf, business_contact="980 555 0111", check_answered_no_text="1")).text
    assert slot(page) == "Saved."


def test_a_rejected_save_keeps_everything_and_raises_the_save_bars(tmp_path, monkeypatch):
    client, clock, csrf = signed_in(tmp_path, monkeypatch)
    page = client.post("/client/phone", data=form(csrf, owner_mobile="980 555 01", check_deactivation_saved="1")).text
    text = html.unescape(page)
    assert "Not saved. 1 thing needs a change." in text and "Enter your mobile as 10 digits, area code first." in text
    assert 'value="980 555 01"' in page and "aria-invalid=true" in page
    assert re.search(r"id=check_deactivation_saved name=check_deactivation_saved value=1 checked>", page)  # kept as posted
    header = re.search(r'<header class="topbar topbar--dirty" data-topbar>.*?</header>', page, re.S).group(0)
    assert "<span class=topsave__count>Not saved · 2 changes</span>" in header
    assert '<div class="savebar savebar--on" data-state=dirty' in page and "data-dirty-initial" in page
    assert client.app.state.store.setting("forwarding_checks") in (None, "", "{}")
    discarded = client.post("/client/phone", data=form(csrf, business_name="Elm", discard="1")).text
    assert slot(discarded) == "Changes discarded." and client.app.state.business_name == "Oak & Pine Tree Care"


def test_rename_offer_rides_in_the_one_notice(tmp_path, monkeypatch):
    client, clock, csrf = signed_in(tmp_path, monkeypatch)
    client.post("/client/messages", data={"csrf": csrf, "intro": "Oak & Pine Tree Care missed you. What do you need?"})
    page = client.post("/client/phone", data=form(csrf, business_name="Oak and Pine")).text
    notice = re.search(r"<div class=status-slot id=notice role=status>.*?data-notice-dismiss", page, re.S).group(0)
    assert "Saved. You changed “Business name”." in notice and "1 text still says “Oak &amp; Pine Tree Care”" in notice
    assert "action=/client/phone/rename-texts" in notice and "name=csrf value=" in notice
    assert page.index("id=notice") < page.index("<h1>")


def test_carrier_codes_are_ready_for_every_carrier_and_copy_the_dialled_code(tmp_path, monkeypatch):
    client, clock, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/phone").text
    assert re.findall(r"<div class=codes-wrap data-codes=(\w+)>", page) == ["verizon", "tmobile", "att", "cricket", "other"]
    assert 'data-copy="*719805550100" hidden>' in page and "<code class=code__val>*71 980 555 0100</code>" in page
    assert "Only forward busy and unanswered calls." in page


def test_checks_use_the_shared_glyphs_and_example_tags_only_when_the_harness_flags_forwarding(tmp_path, monkeypatch):
    client, clock, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    client.post("/client/phone", data=form(csrf, business_line="980 555 0177"))
    missed(state, "CA-fwd", "+19805550142", clock[0] - timedelta(minutes=10), forwarded_from=BUSINESS_LINE)
    page = client.get("/client/phone").text
    assert [n for n in (1, 2, 4) if re.search(rf'class="node node--done" data-check={n}', page)] == [1, 2, 4]
    assert re.search(r'class="node node--todo" data-check=3', page) and "extag" not in page
    assert "<li class=\"spine__label spine__label--foot\"><p class=field-help data-evidence-note>Checks 1, 2 and 4 tick from calls TextBack recorded.</p>" in page
    assert "from a number ending 0142" in html.unescape(page)
    state.preview_example_setup = {"forwarding"}
    page = client.get("/client/phone").text
    tagged = [n for n in range(1, 6) if re.search(rf'data-check={n}>.*?<span class=extag>Example</span>.*?\n</li>', page, re.S)
              and "extag" in re.search(rf'data-check={n}>.*?\n</li>', page, re.S).group(0)]
    assert tagged == [1, 2, 4]
    assert "In this preview, checks 1, 2 and 4 come from example calls." in page
