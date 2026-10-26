"""Candidate C, layer 2b: Messages fixes from the layer-2 review.

FIX 1  the symbol fix only ever offers to change the card's own wording; a symbol from the business name or
       the STOP line is named where it is, with no button.
FIX 2  Replace is local with JavaScript (like Reset); without it the button says "… and save".
FIX 3  an unknown [ … ] in a text is refused with the bad-insert reason; nothing is written.
FIX 4  only TextBack's own calendar links (public base URL + /a/<ref>[/g|o|i]) become labels.
NOTE 1 UCS-2 texts count UTF-16 units; NOTE 2 JS label matching ignores case and spacing; NOTE 3 the
       save bar's live region is only rewritten when its words change.
"""
import html
import json
import re
from pathlib import Path

from text_back import portal_messages as pm
from text_back.messages import DEFAULT_TEMPLATES
from text_back.portal_render import split_links
from test_client_portal import BASE, csrf_of, make, sign_in

JS = (Path(__file__).resolve().parents[1] / "src" / "text_back" / "static" / "portal.js").read_text()
REF = "https://example.test/a/1-5aecf44f8989"


def signed_in(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    return client, path, csrf_of(client.get("/client/home").text)


def card(page, key):
    return re.search(rf'<article class="qset[^"]*" id=card-{key} .*?</article>', page, re.S).group(0)


# --- FIX 1 --------------------------------------------------------------------------------

def test_a_symbol_in_the_business_name_is_named_there_and_offers_no_button(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    client.app.state.business_name = "Dana’s Trees"
    page = client.get("/client/messages").text
    for key in ("help", "followup_1"):
        c = html.unescape(card(page, key))
        bill = re.search(r"<p data-bill-text>(.*?)</p>", c).group(1)
        if key == "followup_1":
            # Its own wording has an em dash: that is the symbol offered, never the ’ in the name.
            assert "“—”" in bill and "Replace — with -" in c
            assert "Replace ’" not in c
        else:
            assert bill.endswith("Your business name has a ’, which makes each text hold only 70 characters."), bill
            assert re.search(r'name=fix value=help data-fix data-symbol="" hidden>', c)
    templates = dict(DEFAULT_TEMPLATES)
    values = {**pm.preview_values(client.app.state, client.app.state.now_provider()), "business_name": "Dana’s Trees"}
    assert pm.bill_info("help", templates, values, notice=False)[1] == ""


def test_a_symbol_in_the_stop_line_is_named_there(tmp_path, monkeypatch):
    templates = dict(DEFAULT_TEMPLATES, opt_out_suffix="Reply STOP to opt out—thanks.", intro="Oak here. What do you need? " + "a" * 40)
    bill, fix = pm.bill_info("intro", templates, {"business_name": "Oak"}, notice=True)
    assert bill.endswith("Your opt-out line has a —, which makes each text hold only 70 characters.") and fix == ""


# --- FIX 2 --------------------------------------------------------------------------------

def test_replace_is_local_with_javascript_and_says_and_save_without_it(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    intro = card(client.get("/client/messages").text, "intro")
    assert ("<span class=msg__fix-js data-fix-label>Replace — with -</span><span class=msg__fix-nojs>Replace — with - and save</span>"
            in intro)
    assert "[data-fix]" in JS and "fix.closest('article[data-card]')" in JS  # the click edits that textarea
    # Without JavaScript the button posts the whole form: another text's unsaved draft is saved with it.
    saved = client.post("/client/messages", data={"csrf": csrf, "fix": "intro", "prompt_name": "Your name, please?"}).text
    assert json.loads(path.read_text())["prompt_name"] == "Your name, please?"
    assert "“Question 4: the name”" in html.unescape(saved) and "Saved. You changed" in html.unescape(saved)


# --- FIX 3 --------------------------------------------------------------------------------

def test_an_unknown_insert_is_refused_and_nothing_is_written(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    page = html.unescape(client.post("/client/messages", data={"csrf": csrf, "handoff_ack": "Thanks [Customer name]! We'll follow up."}).text)
    assert pm.REASON_BAD_INSERT in page and "“When the assistant steps back” needs a change" in page
    assert not path.exists()
    # A known label for this text still works, in any case or spacing.
    client.post("/client/messages", data={"csrf": csrf, "prompt_name": "Name for [business  NAME]?"})
    assert json.loads(path.read_text())["prompt_name"] == "Name for {business_name}?"


# --- FIX 4 --------------------------------------------------------------------------------

def test_only_textbacks_own_calendar_links_become_labels():
    body, links = split_links("Reviews: https://treeco.com/a/reviews and more.", BASE)
    assert body == "Reviews: https://treeco.com/a/reviews and more." and links == ()
    body, links = split_links(f"Add to calendar: Google {REF}/g Outlook {REF}/o iCal {REF}/i", BASE)
    assert body == "" and [label for label, _ in links] == ["Add to Google Calendar ›", "Add to Outlook ›", "Add to iCal ›"]
    body, links = split_links(f"Booked. {REF}/g or {REF}/o.", BASE)
    assert body == "Booked. or." and len(links) == 2  # "or" stays: only the links go
    body, _ = split_links(f"Add to calendar: is how we say it. Then {REF}/g", BASE)
    assert body.startswith("Add to calendar: is how we say it.")  # not directly before the first link: kept
    assert split_links(f"Look: https://other.test/a/1-5aecf44f8989/g", BASE)[1] == ()  # not our base URL


def test_a_typed_url_stays_visible_in_the_card_bubble(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.post("/client/messages", data={"csrf": csrf, "prompt_name": "Name? Reviews at https://treeco.com/a/reviews"}).text
    bubble = re.search(r"<p data-preview=prompt_name>.*?</p>", card(page, "prompt_name")).group(0)
    assert "https://treeco.com/a/reviews" in bubble


def test_the_js_link_match_is_anchored_to_the_public_base_url(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    data = json.loads(html.unescape(re.search(r"<script type=application/json id=tb-data>(.*?)</script>", page).group(1)))
    assert data["sample"]["google_link"].startswith(BASE + "/a/")  # the base JS anchors to, with no other URL in the data
    assert "DATA.sample?.google_link" in JS and r"\d+-[0-9a-f]{12}" in JS


# --- NOTES ----------------------------------------------------------------------------------

def test_ucs2_texts_count_utf16_units():
    text = "a" * 69 + "🙂"
    assert pm.sms_parts(text) == (71, 2, False)  # 69 + 2 units: over 70, two texts
    assert pm.sms_parts("—" + "a" * 69) == (70, 1, False)
    assert "text.length" in JS


def test_js_matches_labels_ignoring_case_and_spacing_and_rewrites_the_bar_only_on_change():
    assert "toLowerCase()" in JS and "LABEL_KEYS" in JS
    assert "savebar.dataset.drawn" in JS
