"""Candidate C, layer 2: the Messages page from mockup d1 round 3 (spine order, triggers, cost line with the
network notice, link labels, the one-tap symbol fix, switched-off questions, steps-back destination, the save
bar in the header and at the bottom, and the example conversation)."""
import html
import json
import re

from text_back.messages import DEFAULT_TEMPLATES
from text_back.portal_messages import (
    FIELD_KEYS, KEYWORDS, LINK_NOTE, NEXT_STEPS, NOTICE_MODEL, STEPS, TRIGGERS, sms_parts, to_display,
)
from test_client_portal import csrf_of, make, sign_in
from test_portal_c_words import visible

URL = re.compile(r"https?://[^\s\"'<>]+|ts\.net|:8443")
CALENDAR_LINK = re.compile(r"https?://\S+?/a/[\w-]+(?:/[goi])?$")


def signed_in(tmp_path, monkeypatch, **kw):
    client, telecom, clock, path = make(tmp_path, monkeypatch, **kw)
    sign_in(client, telecom)
    return client, path, csrf_of(client.get("/client/home").text)


def card(page, key):
    match = re.search(rf'<article class="qset[^"]*" id=card-{key} .*?</article>', page, re.S)
    assert match, key
    return match.group(0)


def text(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


# --- order and anatomy -----------------------------------------------------------------------

def test_cards_follow_the_spine_order_and_start_help_stop_is_collapsed(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    assert re.findall(r"id=card-(\w+) ", page) == list(FIELD_KEYS)
    assert FIELD_KEYS[:6] == ("intro", "prompt_service", "prompt_location", "prompt_preferred_time",
                              "preferred_time_reprompt", "prompt_name")
    heads = re.findall(r'<li class="node node--(?:missed|icon)[^"]*" id=(\w+)>\s*<span class=node__dot aria-hidden=true>'
                       r'.*?<h2 tabindex=-1>([^<]+)</h2>', page, re.S)
    assert [(sid, html.unescape(h)) for sid, h in heads] == [
        ("missed_call", "Missed call"), ("questions", "Questions"), ("booking", "Booking"), ("no_reply", "No reply"),
        ("steps_back", "When the assistant steps back"), ("any_time", "START, HELP and STOP")]
    assert 'class="node node--missed" id=missed_call' in page  # the red missed-call dot opens the spine
    assert re.search(r"<details class=anytime>\s*<summary class=anytime__summary>", page)
    assert "<p class=cards__end><span class=tpill>Texts stop here</span></p>" in page
    assert page.index("Optional questions") < page.index("id=card-prompt_phone")


def test_jump_menu_on_phones_and_chips_wider_both_naming_the_five_steps(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    assert '<html lang=en class="no-js has-jump">' in page  # scroll-padding counts the sticky jump control
    menu = re.search(r"<details class=jumpmenu data-jumpmenu>.*?</details>", page, re.S).group(0)
    assert "<span class=jumpmenu__label data-lead=\"Jump to:\">Jump to a step</span>" in menu
    chips = re.search(r'<nav class=jump aria-label="On this page">.*?</nav>', page, re.S).group(0)
    wanted = [("#missed_call", "Missed call"), ("#questions", "Questions"), ("#booking", "Booking"),
              ("#no_reply", "No reply"), ("#steps_back", "Steps back")]
    for block, cls in ((menu, "jumpmenu__link"), (chips, "jump__link")):
        assert re.findall(rf"<a class={cls} href=(#\w+)(?: aria-current=location)?>([^<]+)</a>", block) == wanted


def test_every_fallback_card_shows_the_customer_reply_that_triggers_it(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    for key, reply in TRIGGERS.items():
        c = card(page, key)
        assert "<p class=msg__trigger>When the customer sends something like</p>" in c, key
        assert (f'<div class="sms sms--customer"><span class=sms__who>Customer</span><div class=sms__bubble><p>'
                f"{html.escape(reply, quote=True).replace('&#x27;', '&#39;')}</p>") in c, key
        assert '<span class=sms__who>Oak &amp; Pine Tree Care</span>' in c, key  # the speaker over the reply
    for key in ("intro", "prompt_service", "booking_confirmation", "followup_1"):
        assert "msg__trigger" not in card(page, key) and "sms__who" not in card(page, key), key


# --- cost line, links, the symbol fix -------------------------------------------------------

def test_cost_line_counts_the_network_notice_only_while_it_applies(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    state.store.set_setting("texting_approval_state", "waiting")
    page = client.get("/client/messages").text
    name = DEFAULT_TEMPLATES["prompt_name"]
    chars, parts, _ = sms_parts(NOTICE_MODEL + name)
    assert chars == len(name) + 24
    assert f"<span class=msg__meter data-count>{parts} text · {chars} characters with the notice</span>" in card(page, "prompt_name")
    assert "the network adds a short notice to the start of each text" in html.unescape(page)
    assert "Each text in this example also starts with the network notice." in page
    # The opt-out line is added to other texts, never sent alone: it never carries the notice.
    assert "with the notice" not in re.search(r"data-count>([^<]+)<", card(page, "opt_out_suffix")).group(1)
    state.store.set_setting("texting_approval_state", "approved")
    page = client.get("/client/messages").text
    assert f"<span class=msg__meter data-count>1 text · {len(name)} characters</span>" in card(page, "prompt_name")
    assert "with the notice" not in page and "network notice" not in page
    data = json.loads(html.unescape(re.search(r"<script type=application/json id=tb-data>(.*?)</script>", page).group(1)))
    assert data["notice"] is False


def test_link_labels_never_raw_urls_in_bubbles_or_page_data(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    client.post("/client/messages", data={"csrf": csrf, "ask_email": "1"})
    page = client.get("/client/messages").text
    for bubble in re.findall(r"<div class=sms__bubble>.*?</div>", page, re.S):
        stripped = re.sub(r'title="[^"]*"', "", bubble)  # a calendar link's full address sits only in title
        assert not URL.search(stripped), bubble[:200]
        for title in re.findall(r'title="([^"]*)"', bubble):
            assert CALENDAR_LINK.match(html.unescape(title)), title
    confirmation = card(page, "booking_confirmation")
    labels = re.findall(r"<span class=sms__linkbtn title=\"[^\"]+\">([^<]+)</span>", confirmation)
    assert labels == ["Add to Google Calendar ›", "Add to Outlook ›", "Add to iCal ›"]
    assert f"<p class=msg__linknote data-link-note>{LINK_NOTE}</p>" in confirmation
    assert "Add to calendar:" not in text(confirmation)
    # The count covers the full links the customer is sent.
    count = int(re.search(r"(\d+) characters", text(confirmation)).group(1))
    assert count > len(text(re.search(r"<p data-preview=booking_confirmation>.*?</p>", confirmation).group(0))) + 150
    data = json.loads(html.unescape(re.search(r"<script type=application/json id=tb-data>(.*?)</script>", page).group(1)))

    def strings(value):
        if isinstance(value, dict):
            for v in value.values():
                yield from strings(v)
        elif isinstance(value, str):
            yield value
    for s in strings(data):
        for found in re.findall(r"https?://\S+", s):
            assert CALENDAR_LINK.match(found), found  # only calendar links, which the page draws as labels


def test_invite_sentence_only_while_the_email_question_is_asked(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    off = card(client.get("/client/messages").text, "booking_confirmation")
    assert "calendar invite" not in off
    client.post("/client/messages", data={"csrf": csrf, "ask_email": "1"})
    on = card(client.get("/client/messages").text, "booking_confirmation")
    assert "A calendar invite is on its way to dana@example.com." in html.unescape(on)


def test_replace_the_dash_is_one_tap_and_saves_without_javascript(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    intro = card(page, "intro")
    assert "—" in DEFAULT_TEMPLATES["intro"]
    assert "The “—” symbol makes each text hold only 70 characters. Use “-” instead." in html.unescape(intro)
    assert re.search(r'<button type=submit class="btn btn--ghost msg__fix" name=fix value=intro data-fix>'
                     r"<span data-fix-label>Replace — with -</span><span class=vh> First text after a missed call</span>",
                     intro)
    assert "data-fix hidden" in card(page, "prompt_name")
    saved = client.post("/client/messages", data={"csrf": csrf, "fix": "intro", "prompt_name": "Your name?"}).text
    written = json.loads(path.read_text())
    assert written["intro"] == DEFAULT_TEMPLATES["intro"].replace("—", "-") and written["prompt_name"] == "Your name?"
    intro = card(saved, "intro")
    assert "—" not in re.search(r"<p data-preview=intro>.*?</p>", intro).group(0)
    assert "—" not in re.search(r"<textarea .*?</textarea>", intro, re.S).group(0)
    assert "data-fix hidden" in intro  # nothing left to replace
    assert "Saved. You changed “First text after a missed call”, “Question 4: the name”." in html.unescape(saved)


# --- optional questions, steps back ------------------------------------------------------

def test_switched_off_questions_show_the_question_and_the_off_line(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    for key, field in (("prompt_phone", "phone"), ("prompt_email", "email")):
        c = card(page, key)
        assert 'class="qset qset--off"' in c and "msg--isoff" in c
        assert f"<p class=msg__offq>{html.escape(DEFAULT_TEMPLATES[key], quote=True).replace('&#x27;', '&#39;')}</p>" in c
        assert "<p class=msg__off>Off. Customers skip this question.</p>" in c
        assert f"id=ask_{field} name=ask_{field} value=1>" in c and "<span class=pill data-not-asked>Not asked</span>" in c
        assert f"name={key} " in c  # still posted
    assert "data-branch-off" in card(page, "phone_reprompt") and "name=phone_reprompt" in card(page, "phone_reprompt")
    on = client.post("/client/messages", data={"csrf": csrf, "ask_phone": "1"}).text
    assert "qset--off" not in card(on, "prompt_phone") and "id=ask_phone name=ask_phone value=1 checked>" in on
    assert "data-branch-off" not in card(on, "phone_reprompt")


def test_steps_back_cards_show_what_happens_next_only_where_it_is_true(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state

    class Channel:
        def __init__(self, name):
            self.channel_name = name

    state.delivery_transport, state.handoff_destination = Channel("telegram"), "operator-chat"
    page = client.get("/client/messages").text
    for key in ("handoff_ack", "handoff_ack_safety"):
        c = card(page, key)
        head = c.split("<div class=msg__preview", 1)[0]  # in view, not inside the editor
        assert "<p class=next__title>What happens next</p>" in head
        assert re.findall(r"<li>([^<]+)</li>", re.search(r"<ol class=next__steps>.*?</ol>", head, re.S).group(0)) == \
            [html.escape(s, quote=True).replace("&#x27;", "&#39;") for s in NEXT_STEPS]
    assert "Must tell people to call 911" in card(page, "handoff_ack_safety").split("What happens next")[0]
    state.delivery_transport = Channel("log")
    c = html.unescape(card(client.get("/client/messages").text, "handoff_ack"))
    assert "These go to a log FluxWorks can read. Nobody is alerted. Ask FluxWorks to set up where these should go." in c
    assert "What happens next" not in c and ".." not in text(c)
    state.delivery_transport = Channel("disabled")
    c = html.unescape(card(client.get("/client/messages").text, "handoff_ack"))
    assert "These go nowhere yet. FluxWorks turns this on when your account is set up." in c and "What happens next" not in c


# --- save bar, drafts, discard -------------------------------------------------------------

def test_save_bar_rests_in_flow_and_a_rejected_save_raises_it_in_the_header(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    form = re.search(r"<form method=post action=/client/messages id=messages-form [^>]*>", page).group(0)
    for attr in ("data-track-changes", "data-topsave", 'data-changed-one="1 text changed"',
                 'data-changed-many="{n} texts changed"'):
        assert attr in form, attr
    bar = re.search(r'<div class="savebar" data-state=clean data-savebar data-form=messages-form>.*?</div>\s*</div>', page, re.S).group(0)
    assert 'data-clean="No unsaved changes">Saves every text at once</p>' in bar  # JS swaps in the resting words
    assert "data-savebar-discard hidden" in bar and "data-rest-save" in bar and "<header class=topbar data-topbar>" in page
    typed = "Call our business line any time"
    rejected = client.post("/client/messages", data={"csrf": csrf, "intro": typed, "prompt_name": "Your name?"}).text
    assert "data-dirty-initial" in rejected
    header = re.search(r'<header class="topbar topbar--dirty" data-topbar>.*?</header>', rejected, re.S).group(0)
    assert "<span class=topsave__count>Not saved · 2 texts changed</span>" in header
    assert '<a href="#card-intro">First text after a missed call</a>' in header
    bar = re.search(r'<div class="savebar savebar--on" data-state=dirty .*?</div>\s*</div>', rejected, re.S).group(0)
    assert "<span class=savebar__count>Not saved · 2 texts changed</span>" in bar and "data-savebar-discard>" in bar
    intro = card(rejected, "intro")
    assert "<p class=msg__was data-was><span class=msg__was-k>Was:</span>" in intro and f">{typed}</textarea>" in intro
    assert "<span class=\"pill pill--danger\">Not saved</span>" in intro
    discarded = client.post("/client/messages", data={"csrf": csrf, "intro": typed, "discard": "1"}).text
    assert "Changes discarded." in discarded and not path.exists() and "topbar--dirty" not in discarded


def test_inserts_have_a_typed_fallback_without_javascript(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    c = card(page, "prompt_name")
    assert "<div class=chips role=group aria-label=\"Insert a detail\" data-chips hidden>" in c
    assert "<p class=chips-fallback>Insert a detail: [Business name]</p>" in c
    assert "This text fills in no details." in card(page, "opt_out_suffix")
    client.post("/client/messages", data={"csrf": csrf, "prompt_name": "Name for [Business name]'s visit?"})
    assert json.loads(path.read_text())["prompt_name"] == "Name for {business_name}'s visit?"


def test_example_conversation_caption_sits_under_its_heading(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    rail = re.search(r"<section class=rail id=example .*?</section>", page, re.S).group(0)
    assert re.search(r"<h2 class=rail__title id=rail-title tabindex=-1>Example conversation</h2>\s*"
                     r"<p class=rail__caption><span class=extag>Example</span> Example conversation · nothing is sent · "
                     r"names made up</p>", rail)
    assert "<a class=rail__back href=#main>" in rail and "Back to editing" in rail
    booked = re.search(r"<ol class=thread data-scenario=booked .*?</ol>", rail, re.S).group(0)
    assert "<span class=sms__who>Customer</span>" in booked and "<span class=sms__who>Oak &amp; Pine Tree Care</span>" in booked
    assert "Booked · on the test calendar" in booked and "Add to Google Calendar ›" in booked
    assert not URL.search(re.sub(r'title="[^"]*"', "", booked))


def test_messages_page_words_are_clean_in_every_state(tmp_path, monkeypatch):
    client, path, csrf = signed_in(tmp_path, monkeypatch)
    for response in (client.get("/client/messages"),
                     client.post("/client/messages", data={"csrf": csrf, "intro": "Call our business line"}),
                     client.post("/client/messages", data={"csrf": csrf, "fix": "intro"})):
        shown = visible(response.text)
        assert "{" not in shown and "}" not in shown and "SignalWire" not in shown
        assert "Your messages" not in shown and to_display(DEFAULT_TEMPLATES["intro"]) not in ("",)
    assert [key for *_, keys, opt in (*STEPS, KEYWORDS) for key in (*keys, *opt)] == list(FIELD_KEYS)
