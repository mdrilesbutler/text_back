"""Candidate C, final-panel round 3: the header is the save bar at every width (nothing floats at the bottom
on desktop), the example rail's faded edge with "Scroll for the rest", the Custom appointment length, and the
Phone & business wording. Free-time ranges are covered in test_next_free_slots / test_portal_calendar."""
import html
import re
from pathlib import Path

from test_client_portal import csrf_of, make, sign_in
from test_portal_c_pages import schedule_form

STATIC = Path(__file__).resolve().parents[1] / "src" / "text_back" / "static"
CSS = (STATIC / "portal.css").read_text()
JS = (STATIC / "portal.js").read_text()
ROUND3 = CSS[CSS.index("/* Round-3 fix 1:"):]


def signed_in(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    return client, csrf_of(client.get("/client/home").text)


def _media(block: str, query: str) -> str:
    """The body of the first `@media (<query>) { ... }` in block (brace-matched)."""
    start = block.index(f"@media ({query})")
    i, depth = block.index("{", start), 0
    for j in range(i, len(block)):
        depth += {"{": 1, "}": -1}.get(block[j], 0)
        if depth == 0:
            return block[i + 1:j]
    raise AssertionError(query)


def test_the_header_is_the_save_bar_at_every_width_and_nothing_floats_on_desktop():
    # Outside any media query: the dirty header shows the save bar at every width.
    head = ROUND3.split("@media", 1)[0]
    assert ".topbar--dirty .topsave { display: flex;" in head and ".topbar--dirty { background: var(--bg);" in head
    wide = _media(ROUND3, "min-width: 1024px")
    # Desktop: the business-name menu steps aside for the bar; TextBack stays.
    assert ".topbar--dirty > .menu { display: none; }" in wide and ".brand" not in wide
    # The form-end bar stays in flow while dirty: never sticky or fixed, so it never covers the next card.
    rule = re.search(r"\.savebar--on, \.savebar\[data-state=\"dirty\"\] \{(.*?)\}", wide, re.S).group(1)
    assert "position: static" in rule and "box-shadow: none" in rule
    assert "scroll-padding-bottom: var(--space-4)" in wide  # no bottom chrome left to clear
    # The old sticky desktop bar is overridden by the later layer; the phone hides the form-end bar while dirty.
    assert "@layer app" in CSS[CSS.index(".savebar--on { position: sticky;"):]


def test_a_rejected_save_renders_the_header_bar_and_an_in_flow_form_end_bar(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    rejected = client.post("/client/messages", data={"csrf": csrf, "intro": "Call our business line"}).text
    header = re.search(r'<header class="topbar topbar--dirty" data-topbar>.*?</header>', rejected, re.S).group(0)
    assert "data-topsave-server" in header and "form=messages-form" in header and "data-topsave-discard" in header
    assert '<div class="savebar savebar--on" data-state=dirty data-savebar data-form=messages-form>' in rejected
    # The leave-page guard still covers every data-topsave form, at every width.
    guard = JS[JS.index("if ('topsave' in form.dataset) {"):]
    assert "beforeunload" in guard.split("update();", 1)[0] and "WIDE" not in guard.split("update();", 1)[0]


def test_the_example_rail_fades_its_bottom_edge_and_says_when_more_is_below(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    rail = re.search(r"<section class=rail id=example .*?</section>", page, re.S).group(0)
    hint = re.search(r"<p class=rail__more [^>]*>.*?</p>", rail, re.S).group(0)
    assert "aria-hidden=true" in hint and "data-rail-more" in hint and hint.endswith("Scroll for the rest</p>")
    # The hint sits in the phone screen beside the scrolled log, not inside it.
    assert rail.index("data-rail-log") < rail.index("data-rail-more")
    wide = _media(ROUND3[ROUND3.index("Round-3 fix 2"):], "min-width: 1024px")
    assert "calc(100% - 32px), transparent" in wide and "scroll-padding-block: 16px 3rem" in wide
    assert ".phone__screen:has(.phone__log[data-more]) .rail__more { display: flex; }" in wide
    assert ".rail__more { display: none; }" in ROUND3  # without JavaScript (no data-more) and on phones
    assert "log.toggleAttribute('data-more'" in JS and "log.scrollHeight - log.clientHeight - log.scrollTop > 16" in JS


def test_the_minutes_field_shows_only_for_custom_with_javascript(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/schedule").text
    field = re.search(r"<div class=field id=rule-duration .*?<p class=applies>", page, re.S).group(0)
    # Without JavaScript both show, as before: the number field and every chip including Custom.
    assert "id=appointment_duration_custom" in field and "id=dur-custom value=custom" in field and "id=dur-60" in field
    assert ":where(.js) #rule-duration:has(#dur-custom:not(:checked)) > .inline-field:not(:focus-within) { display: none; }" in ROUND3
    # Under the chips in the DOM, so focus order matches what is seen (Custom, then the minutes).
    assert field.index("id=dur-custom") < field.index("id=appointment_duration_custom")
    sched = JS[JS.index("function initSchedule()"):JS.index("const suggest")]
    assert "number.focus();" in sched and "focusField(number)" not in sched
    # The chip follows typing at once; the field stays while it has focus, so it never hides at "60".
    assert ".inline-field:not(:focus-within) { display: none; }" in ROUND3
    # A saved custom length checks Custom, so the field shows on load.
    client.post("/client/schedule", data=schedule_form(csrf, appointment_duration_minutes="custom",
                                                       appointment_duration_custom="50", appointment_duration_shown="60"))
    again = client.get("/client/schedule").text
    assert re.search(r"id=dur-custom value=custom checked", again)


def test_phone_numbers_intro_and_hints_say_exactly_what_each_field_is(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/phone").text
    numbers = re.search(r"<li class=\"node node--icon\" id=numbers>.*?</li>", page, re.S).group(0)
    assert ("<p class=node__blurb>Three numbers: the one customers call, the one TextBack texts from, "
            "and your own mobile.</p>") in numbers
    line_help = re.search(r"<p class=field-help id=business_line-help>(.*?)</p>", page, re.S).group(1)
    assert html.unescape(line_help).startswith("This is the number customers call. TextBack never changes it.")
    name_help = html.unescape(re.search(r"<p class=field-help id=business_name-help>(.*?)</p>", page, re.S).group(1))
    assert name_help == "Used in the texts that name your business, like the first text and the booking confirmation."
    assert "Used in every text" not in page


def test_free_time_ranges_and_weekday_spans_never_break_across_lines():
    from text_back.portal_render import nw
    assert str(nw("Mon, Oct 26 · 11:30 AM–12:30 PM")) == "<span class=nw>Mon, Oct 26</span> · <span class=nw>11:30 AM–12:30 PM</span>"
    assert str(nw("Tue, Oct 27 · 9:00–10:00 AM")).endswith("<span class=nw>9:00–10:00 AM</span>")
    assert "<span class=nw>Mon–Fri</span>" in str(nw("working hours Mon–Fri 8:00 AM–5:00 PM"))
