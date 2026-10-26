"""Candidate C, layer 5: the Calendar page from mockup d1 round 3 with the review fixes: the connected card
names the account ("Connected as …", left out when unknown), "Use a different calendar" opens the picker in
place, Reconnect is a link-styled post; not connected uses Home's words with Connect, Text FluxWorks support
or the sentence naming who sets it up; the free-times card on the spine."""
import html
import re
from datetime import datetime, timezone

from text_back import portal_calendar as pc
from text_back.portal_render import ASSET_VERSION, ENV
from test_portal_calendar import google_state, remember

NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)


def render(state, **extra):
    context = {"title": "Calendar", "business_name": state.business_name, "nav": (("calendar", "Calendar"),),
               "nav_active": "calendar", "csrf": "t", "signed_in_with": "(980) 555-0123", "notice": "", "tz": "UTC",
               "now": NOW, "tb_data": None, "topsave": None, "page_error": "", "picker_error": "", "support_contact": "",
               **pc.page_context(state), **extra}
    return ENV.get_template("client/calendar.html.j2").render(asset_v=ASSET_VERSION, theme=None, **context)


def node(page, nid):
    return re.search(rf'<li class="node node--\w+" id={nid}>.*?\n</li>', page, re.S).group(0)


def test_connected_card_names_the_account_opens_the_picker_and_reconnects_by_link(tmp_path, monkeypatch):
    state, _, _ = google_state(tmp_path, monkeypatch)
    remember(state)
    page = render(state)
    card = node(page, "connection")
    assert 'class="node node--done" id=connection' in card and '<span class="pill state state--done pill--success">Connected</span>' in card
    assert "Bookings go here: Tree jobs. Connected as owner@example.test." in html.unescape(card)
    picker = re.search(r"<details class=picker id=picker>.*?</details>", card, re.S).group(0)
    assert '<summary class="btn btn--secondary picker__summary">Use a different calendar</summary>' in picker
    assert "Which calendar should the assistant use?" in picker and 'name=calendar_id value="jobs@group.calendar.google.com" checked' in picker
    reconnect = re.search(r"<form method=post action=/client/calendar data-connect class=status__link>.*?</form>", card, re.S).group(0)
    assert "<button type=submit class=linkbtn" in reconnect and "Reconnect Google Calendar" in reconnect
    assert "<details class=picker id=picker open>" in render(state, picker_error=pc.PICKER_ERROR)  # an error opens it
    avail = node(page, "availability")
    assert "Next free times on Tree jobs" in avail


def test_not_connected_uses_homes_words_with_connect_and_what_google_will_ask(tmp_path, monkeypatch):
    state, _, _ = google_state(tmp_path, monkeypatch, status="none")
    monkeypatch.setattr("text_back.client_settings.calendar_status",
                        lambda s: {"provider": "google", "status": "none", "calendar_id": "", "can_connect": True})
    card = node(render(state), "connection")
    text = html.unescape(card)
    assert 'class="node node--needs" id=connection' in card and "No calendar yet" in text
    assert "No calendar of yours yet. Until you connect one, bookings go on a test calendar you can't see." in text
    assert pc.WHY_CONNECT in text and "Connect Google Calendar" in text
    asks = re.search(r"<details class=asks open>.*?</details>", card, re.S).group(0)
    assert "<span class=field__label>What Google will ask:</span>" in asks
    assert [html.unescape(x) for x in re.findall(r"<li>([^<]+)</li>", asks)] == list(pc.CONSENT_STEPS)


def test_not_connected_without_connect_offers_support_or_names_who_sets_it_up(tmp_path, monkeypatch):
    state, _, _ = google_state(tmp_path, monkeypatch, status="none", client_file=False)
    monkeypatch.setattr("text_back.client_settings.calendar_status",
                        lambda s: {"provider": "google", "status": "none", "calendar_id": "", "can_connect": False})
    card = html.unescape(node(render(state), "connection"))
    assert pc.BODY_NO_WEB in card and "Text FluxWorks support" not in card and "asks" not in card
    state.support_contact = "+19805550111"
    card = node(render(state), "connection")
    assert 'href="sms:+19805550111" data-support>Text FluxWorks support</a>' in card
    assert "Test calendar, not yours" in node(render(state), "availability")
