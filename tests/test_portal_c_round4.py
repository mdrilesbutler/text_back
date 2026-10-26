"""Candidate C, final-panel round 4 (every remaining judge deduction):

c2  Account is one tap from the header on every page; Messages, Schedule and Phone & business open with their
    sections as a grid of one-tap buttons, and a compact sticky "Jump to" takes over once the grid scrolls away;
    Messages keeps the main-path texts open and puts each step's branch texts in one disclosure.
c1  The bottom tab bar steps aside while scrolling down; pages end with room for it; short labels never strand a word.
a2  Owner-facing words say TextBack, never "the assistant"; plain words for the HELP number and resent texts.
e2  The desktop example rail: no floating pill over a bubble (a plain line under the frame instead), and it follows
    the step on screen. Phone: a rename that left the old name in the first text says so under its preview.
"""
import html
import json
import re

from markupsafe import escape

from text_back import portal_messages as pm, portal_phone, portal_scheduling as ps
from text_back.portal_render import STATIC_DIR
from test_client_portal import OWNER, csrf_of, make, sign_in

CSS = (STATIC_DIR / "portal.css").read_text()
JS = (STATIC_DIR / "portal.js").read_text()
ROUND4 = CSS[CSS.index("Round-4 fixes (final panel round 3)"):]
PAGES = ("/client/home", "/client/messages", "/client/schedule", "/client/calendar", "/client/phone", "/client/account")


def signed_in(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    return client, telecom, clock, path, csrf_of(client.get("/client/account").text)


def header_of(page: str) -> str:
    return re.search(r"<header class=\"?topbar[^>]*>.*?</header>", page, re.S).group(0)


def _media(block: str, query: str) -> str:
    """The body of the first `@media (<query>) { ... }` in block (brace-matched)."""
    start = block.index(f"@media ({query})")
    i, depth = block.index("{", start), 0
    for j in range(i, len(block)):
        depth += {"{": 1, "}": -1}.get(block[j], 0)
        if depth == 0:
            return block[i + 1:j]
    raise AssertionError(query)


def owner_words(page: str) -> str:
    """Visible owner-facing words: customer texts (bubbles, the editor boxes, "Was:" lines) are the owner's to edit."""
    page = re.sub(r"(?is)<(script|style|svg|textarea)\b.*?</\1>", " ", page)
    page = re.sub(r"(?s)<div class=sms__bubble>.*?</div>", " ", page)
    page = re.sub(r"(?s)<p class=msg__was .*?</p>", " ", page)
    page = re.sub(r"(?s)<[^>]+>", " ", page)
    return " ".join(html.unescape(page).split())


# --- c2: Account in one tap ------------------------------------------------------------------

def test_the_header_has_an_account_button_with_its_word_and_marks_the_account_page(tmp_path, monkeypatch):
    client, *_ = signed_in(tmp_path, monkeypatch)
    for url in PAGES:
        header = header_of(client.get(url).text)
        account = re.search(r"<a class=acct href=/client/account( aria-current=page)?>(.*?)</a>", header, re.S)
        assert account, url
        assert 'href="#i-user-round"' in account.group(2) and "<span class=acct__label>Account</span>" in account.group(2)
        assert bool(account.group(1)) == (url == "/client/account"), url
        # No dropdown left in the header: sign out lives on the Account page.
        assert "<details" not in header and "data-menu" not in header and "/client/logout" not in header, url
    account_page = client.get("/client/account").text
    assert "action=/client/logout" in account_page and "Signed in as <span class=nw>(980) 555-0123</span>" in account_page
    # The desktop sidebar keeps its Account row.
    assert '<a class="nav__item nav__item--wide" href=/client/account aria-current=page>' in account_page


def test_the_business_name_sits_under_textback_and_wraps(tmp_path, monkeypatch):
    client, *_ = signed_in(tmp_path, monkeypatch)
    long_name = "Oak & Pine's Tree Care and Stump Grinding of the Carolinas, Inc."
    client.app.state.business_name = long_name
    header = header_of(client.get("/client/home").text)
    brand = re.search(r"<a class=brand href=/client/home>(.*?)</a>", header, re.S).group(1)
    assert brand.index("TextBack") < brand.index(f"<span class=brand__biz>{escape(long_name)}</span>")
    rule = re.search(r"\.brand__biz \{[^}]*\}", ROUND4).group(0)
    assert "overflow-wrap" in rule and "ellipsis" not in rule and "nowrap" not in rule


def test_the_account_button_is_a_44px_target_highlighted_like_a_current_tab():
    rule = re.search(r"\.acct \{[^}]*\}", ROUND4).group(0)
    assert "min-height: var(--tap)" in rule and "min-width: var(--tap)" in rule
    current = re.search(r"\.acct\[aria-current=\"page\"\][^{]*\{[^}]*\}", ROUND4).group(0)
    assert "var(--accent" in current
    # Below 1024 px the header save bar replaces it while a form has unsaved changes; on desktop the sidebar has Account.
    assert ".topbar--dirty > .acct" in _media(ROUND4, "max-width: 1023.98px")
    assert ".acct { display: none; }" in _media(ROUND4, "min-width: 1024px")


# --- c2: one-tap sections at the top, sticky "Jump to" once they scroll away -----------------

SECTIONS = {
    "/client/messages": [("missed_call", "Missed call"), ("questions", "Questions"), ("booking", "Booking"),
                         ("no_reply", "No reply"), ("steps_back", "Steps back")],
    "/client/schedule": [("appointments", "Appointments"), ("working-hours", "Working hours"),
                         ("quiet_hours", "Quiet hours"), ("reminders", "Reminders")],
    "/client/phone": [("business", "Business details"), ("numbers", "Numbers"), ("forwarding", "Call forwarding"),
                      ("checks", "Checks")],
}


def test_messages_schedule_and_phone_open_with_a_grid_of_one_tap_sections_and_a_sticky_jump(tmp_path, monkeypatch):
    client, *_ = signed_in(tmp_path, monkeypatch)
    for url, sections in SECTIONS.items():
        page = client.get(url).text
        assert re.search(r"<html lang=en class=\"no-js has-jump\"", page), url  # scroll-padding counts the bar
        grid = re.search(r'<nav class=stepgrid aria-label="On this page" data-stepgrid>.*?</nav>', page, re.S).group(0)
        links = re.findall(r"<a class=stepgrid__link href=#([\w-]+)>([^<]+)</a>", grid)
        assert links == sections, url
        bar = re.search(r"<div class=jumpbar data-jumpbar>\s*<details class=jumpmenu data-jumpmenu>.*?</details>\s*</div>",
                        page, re.S).group(0)
        assert '<span class=jumpmenu__label data-lead="Jump to:">Jump to a section</span>' in bar, url
        assert re.findall(r"<a class=jumpmenu__link href=#([\w-]+)", bar) == [sid for sid, _ in sections], url
        for sid, _ in sections:
            assert f"id={sid}" in page, (url, sid)
        # The grid comes first, then the bar, then the sections.
        assert page.index("data-stepgrid") < page.index("data-jumpbar") < page.index(f"id={sections[0][0]}"), url


def test_the_section_grid_wraps_into_44px_buttons_and_never_scrolls_sideways():
    rule = re.search(r"\.stepgrid__list \{[^}]*\}", ROUND4).group(0)
    assert "display: grid" in rule and "repeat(auto-fill, minmax(" in rule
    link = re.search(r"\.stepgrid__link \{[^}]*\}", ROUND4).group(0)
    assert "min-height: var(--tap)" in link and "nowrap" not in link
    assert "overflow-x" not in re.search(r"\.stepgrid \{[^}]*\}", ROUND4).group(0)
    assert ".jump " not in ROUND4 and "jump__list" not in ROUND4  # the sideways chip row is gone


def test_the_sticky_jump_appears_only_once_the_grid_has_scrolled_away_and_stays_without_javascript():
    phone = _media(ROUND4, "max-width: 1023.98px")
    assert ".jumpbar { position: sticky;" in phone and "height: 0" in phone  # overlays, never shifts the page
    assert ":where(.no-js) .jumpbar { height: auto; }" in phone  # without JavaScript the bar sits in flow
    assert ".jumpbar { display: none; }" in _media(ROUND4, "min-width: 1024px")
    jump = JS[JS.index("function initJump"):JS.index("// ---------------------------------------------------------------- unsaved")]
    assert "IntersectionObserver" in jump and "[data-stepgrid]" in jump and "bar.hidden" in jump
    assert "stepgrid__link" in jump and "tb:step" in jump  # the step on screen, for the grid, the bar and the rail


# --- c2: Messages main path open, branch texts in one disclosure per step -----------------------

def branches_of(page: str, step: str) -> str:
    node = re.search(rf'<li class="node node--\w+" id={step}>.*?(?=<li class="node|</ol>)', page, re.S).group(0)
    found = re.search(r"<details class=branches[^>]*>.*?</article></div>\s*</details>", node, re.S)
    return found.group(0) if found else ""


def test_branch_texts_sit_in_one_closed_disclosure_per_step(tmp_path, monkeypatch):
    client, *_ = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/messages").text
    questions, booking = branches_of(page, "questions"), branches_of(page, "booking")
    assert questions.startswith("<details class=branches data-branches>")  # closed
    assert booking.startswith("<details class=branches data-branches>")
    assert re.findall(r"data-card=(\w+)", questions) == ["preferred_time_reprompt", "phone_reprompt", "email_reprompt"]
    assert re.findall(r"data-card=(\w+)", booking) == ["slot_unavailable", "booking_error"]
    # The count is the texts a customer can get: the phone and email re-asks wait for their questions.
    summary = html.unescape(re.search(r"<summary class=branches__summary>(.*?)</summary>", questions, re.S).group(1))
    assert "If the answer is unclear · <span data-branch-count>1 text</span>" in summary
    titles = html.unescape(re.search(r"<span class=branches__titles[^>]*>(.*?)</span>", questions, re.S).group(1))
    assert titles == "If the time couldn't be understood"
    summary = html.unescape(re.search(r"<summary class=branches__summary>(.*?)</summary>", booking, re.S).group(1))
    assert "If the time is taken or the calendar fails · <span data-branch-count>2 texts</span>" in summary
    # The main path stays open: none of its cards is inside a disclosure.
    for key in ("intro", "prompt_service", "prompt_location", "prompt_preferred_time", "prompt_name",
                "booking_confirmation", "followup_1", "followup_2", "handoff_ack"):
        card = page.index(f"data-card={key} ")
        assert page.rfind("<details class=branches", 0, card) <= page.rfind("</details>", 0, card), key
    danger = branches_of(page, "steps_back")
    assert re.findall(r"data-card=(\w+)", danger) == ["handoff_ack_safety"]
    assert "If a text mentions danger · <span data-branch-count>1 text</span>" in danger
    assert not branches_of(page, "missed_call") and not branches_of(page, "no_reply")


def test_a_branch_disclosure_counts_the_asked_questions(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    client.post("/client/messages", data={"csrf": csrf, "ask_phone": "1"})
    questions = branches_of(client.get("/client/messages").text, "questions")
    assert "<span data-branch-count>2 texts</span>" in questions
    assert html.unescape(re.search(r"<span class=branches__titles[^>]*>(.*?)</span>", questions, re.S).group(1)) == \
        "If the time couldn't be understood · If the phone number couldn't be read"


def test_a_branch_disclosure_opens_for_a_customized_unsaved_or_rejected_text(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    # Customized (saved): open.
    client.post("/client/messages", data={"csrf": csrf, "slot_unavailable": "That time is taken. Pick another?"})
    page = client.get("/client/messages").text
    assert branches_of(page, "booking").startswith("<details class=branches data-branches open>")
    assert branches_of(page, "questions").startswith("<details class=branches data-branches>")
    # Rejected: the text with the error opens its disclosure; a typed change in another branch opens that one too.
    rejected = client.post("/client/messages", data={
        "csrf": csrf, "booking_error": "Sorry, call us instead.",
        "preferred_time_reprompt": "What day and time works? Like Friday at 4pm."}).text
    assert branches_of(rejected, "booking").startswith("<details class=branches data-branches open>")
    assert branches_of(rejected, "questions").startswith("<details class=branches data-branches open>")


def test_links_into_a_closed_disclosure_open_it(tmp_path, monkeypatch):
    opener = JS[JS.index("function openAround"):]
    opener = opener[:opener.index("// ----")]
    assert "hashchange" in opener and "closest('details')" in opener and "a[href^=\"#\"]" in opener
    # The step's count follows the question switches live.
    assert "data-branch-count" in JS and "branches__titles" in JS


def test_the_phone_spine_gutter_is_at_most_32px():
    phone = _media(ROUND4, "max-width: 639.98px")
    root = re.search(r":root \{([^}]*)\}", phone).group(1)
    col = float(re.search(r"--spine-col: ([\d.]+)rem", root).group(1))
    gap = float(re.search(r"--spine-gap: ([\d.]+)rem", root).group(1))
    assert (col + gap) * 16 <= 32 and "--node: 1.5rem" in root


# --- c1: the bottom tab bar steps aside while scrolling down ------------------------------------

def test_the_tab_bar_hides_on_scroll_down_and_returns_on_scroll_up_top_end_and_focus():
    nav = JS[JS.index("function initNavHide"):]
    nav = nav[:nav.index("\n}\n")]
    for hook in ("data-away", "scrollY", "lastY", "scrollHeight", "focusin", "nav.contains(document.activeElement)"):
        assert hook in nav, hook
    assert "initNavHide" in JS[JS.index("// ---------------------------------------------------------------- start"):]
    phone = _media(ROUND4, "max-width: 1023.98px")
    assert ".nav[data-away] { transform: translateY(" in phone and "transition: transform" in phone
    assert "@media (prefers-reduced-motion: reduce) { .nav { transition: none; } }" in ROUND4
    # Pages end with the bar's height plus 24 px, so the last control always clears it.
    assert ".page { padding-bottom: calc(var(--tabbar-h) + env(safe-area-inset-bottom) + 24px); }" in phone


def test_short_labels_never_strand_one_word():
    rule = re.search(r":is\(\.switch-row__text[^{]*\{[^}]*\}", ROUND4).group(0)
    assert "text-wrap: pretty" in rule and ".field__label" in rule and ".field-help" in rule


# --- a2: plain words ---------------------------------------------------------------------------

def test_owner_facing_words_say_textback_never_the_assistant(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    for url in PAGES:
        words = owner_words(client.get(url).text)
        assert not re.search(r"(?i)\bassistant\b", words), (url, re.findall(r".{40}assistant.{40}", words, re.I))
        assert "HELP reply" not in words and "retried" not in words, url
    assert "When TextBack steps back" in owner_words(client.get("/client/messages").text)
    assert ps.CONSEQUENCES["quiet_hours"].startswith("Reminders and texts TextBack sends again wait until quiet hours end.")
    assert portal_phone.LABELS["business_contact"] == "The number customers get when they text HELP"
    assert pm.DIVIDER_STEPS_BACK == "TextBack steps back here"


def test_a_ticked_check_saves_as_a_recorded_check_not_a_change(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    form = {"csrf": csrf, "business_name": "Oak & Pine Tree Care", "business_line": "", "owner_mobile": OWNER,
            "business_contact": "", "carrier": "", "checks_in_form": "1", "check_answered_no_text": "1"}
    page = html.unescape(client.post("/client/phone", data=form).text)
    assert "Saved. You ticked “An answered call sent no text”." in page
    form.pop("check_answered_no_text")
    page = html.unescape(client.post("/client/phone", data=dict(form, business_contact="704 555 0199")).text)
    assert "Saved. You changed “The number customers get when they text HELP”. You unticked “An answered call sent no text”." in page


def test_the_business_number_says_why_it_is_editable(tmp_path, monkeypatch):
    client, *_ = signed_in(tmp_path, monkeypatch)
    page = html.unescape(client.get("/client/phone").text)
    hint = re.search(r"<p class=field-help id=business_line-help>(.*?)</p>", page, re.S).group(1)
    assert "Typing it here doesn't change your phone service" in hint


def test_the_one_tap_hours_button_reads_as_one_phrase(tmp_path, monkeypatch):
    client, *_ = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/schedule").text
    button = re.search(r"<button [^>]*data-suggest-hours>(.*?)</button>", page, re.S).group(1)
    assert button.startswith("<span class=btn__text>") and button.endswith("</span>")  # one flex item, no gaps


def test_a_field_with_an_error_shows_one_ring_when_focused():
    rule = re.search(r":is\(\.input, \.textarea\)\[aria-invalid=\"true\"\]:is\(:focus, \.is-focus\) \{[^}]*\}", ROUND4).group(0)
    assert "outline-color: var(--danger-fg)" in rule and "outline-offset: 0" in rule


# --- e2: the example rail -------------------------------------------------------------------------

def test_the_rail_says_more_is_below_under_the_frame_never_over_a_bubble(tmp_path, monkeypatch):
    client, *_ = signed_in(tmp_path, monkeypatch)
    rail = re.search(r"<section class=rail .*?</section>", client.get("/client/messages").text, re.S).group(0)
    screen = re.search(r"<div class=phone>.*?<a class=rail__back", rail, re.S).group(0)
    assert "rail__more" not in screen.split("</div>\n  </div>", 1)[0]  # nothing floats inside the phone frame
    assert "Scroll for the rest" not in rail
    line = re.search(r"<p class=rail__more data-rail-more>(.*?)</p>", rail, re.S).group(1)
    assert line == "More below. Scroll the conversation."
    assert rail.index("<div class=phone>") < rail.index("data-rail-more")
    wide = _media(ROUND4, "min-width: 1024px")
    assert ".rail:has(.phone__log[data-more]) .rail__more { display: block; }" in wide
    assert "position: absolute" not in re.search(r"\.rail__more \{[^}]*\}", ROUND4).group(0)


def test_the_rail_follows_the_step_on_screen_and_the_card_being_edited():
    rail = JS[JS.index("function initRail"):JS.index("// ---------------------------------------------------------------- Schedule: length")]
    assert "tb:step" in rail and "followStep" in rail and "REDUCED" in rail
    assert "'toggle'" in rail  # an editor opening counts, like focus
    assert "dataset.current" in rail  # the edited card's bubble keeps its ring


def test_a_rename_that_left_the_old_name_in_the_first_text_says_so_under_its_preview(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    client.post("/client/messages", data={"csrf": csrf, "intro": "Oak & Pine Tree Care missed you. What do you need?"})
    form = {"csrf": csrf, "business_name": "Oak and Pine", "owner_mobile": OWNER}
    page = html.unescape(client.post("/client/phone", data=form).text)
    preview = page[page.index("<p class=eyebrow>In the first text</p>"):]
    line = re.search(r"<p class=\"field-help preview-stale\" data-rename-stale>(.*?)</p>", preview, re.S)
    assert line and line.group(1) == "This text still says “Oak & Pine Tree Care”. Update it above."
    assert page.index("data-rename-offer") < page.index("data-rename-stale")  # the offer is above it
    client.post("/client/phone/rename-texts", data={"csrf": csrf, "action": "update"})
    assert "data-rename-stale" not in client.get("/client/phone").text


def test_no_stale_line_when_only_other_texts_keep_the_old_name(tmp_path, monkeypatch):
    client, telecom, clock, path, csrf = signed_in(tmp_path, monkeypatch)
    client.post("/client/messages", data={"csrf": csrf, "prompt_name": "Oak & Pine Tree Care needs your name."})
    page = client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak and Pine", "owner_mobile": OWNER}).text
    assert "data-rename-offer" in page and "data-rename-stale" not in page
    assert json.loads(path.read_text())["prompt_name"].startswith("Oak & Pine")


# --- Coming up: the next bookings on Home (and on Calendar while connected) ----------------------

from datetime import datetime, timedelta, timezone  # noqa: E402

from text_back import portal_calendar, portal_dates, portal_status  # noqa: E402
from test_client_portal import NOW  # noqa: E402


def book(state, n, start, *, end=None, name="", service="Tree trimming", location="412 Maple St, Charlotte"):
    caller = f"+1980555{n:04d}"
    state.store.save_appointment(conversation_id=caller, event_id=f"ev{n}", caller=caller, start=start.isoformat(),
                                 end=end.isoformat() if end else None, location=location, service=service)
    if name:
        state.store.set_conversation_field(caller, "name", name)
    return caller


def test_upcoming_lists_the_next_bookings_soonest_first_with_their_details(tmp_path, monkeypatch):
    client, *_ = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    state.timezone_name = "America/New_York"
    state.appointment_duration_minutes = 90
    later = book(state, 1, NOW + timedelta(days=3, hours=1), end=NOW + timedelta(days=3, hours=2), name="Dana Whitfield")
    soon = book(state, 2, NOW + timedelta(hours=2), service="Stump grinding", location="9 Oak Ln")  # no stored end, no name
    book(state, 3, NOW - timedelta(hours=1), name="Past")  # already started: left out
    state.preview_example_phones = (later,)
    rows = portal_status.upcoming(state, NOW)
    assert [r["phone"] for r in rows] == [soon, later]
    # NOW is 15:00 UTC on Mon Oct 19 2026 = 11:00 AM in New York; the length fills a missing end (90 min).
    assert rows[0]["label"] == "Mon, Oct 19 · 1:00–2:30 PM" and rows[0]["name"] == "…0002"
    assert (rows[0]["service"], rows[0]["location"], rows[0]["example"]) == ("Stump grinding", "9 Oak Ln", False)
    assert rows[1]["label"] == "Thu, Oct 22 · 12:00–1:00 PM" and rows[1]["name"] == "Dana Whitfield" and rows[1]["example"]
    for n in range(10, 20):
        book(state, n, NOW + timedelta(days=10, hours=n))
    assert len(portal_status.upcoming(state, NOW)) == 8 and len(portal_status.upcoming(state, NOW, limit=3)) == 3


def test_a_booking_span_reads_as_one_range():
    tz = "America/New_York"
    noon = datetime(2026, 10, 22, 15, 30, tzinfo=timezone.utc)  # 11:30 AM
    assert portal_dates.span(noon, noon + timedelta(hours=1), tz, NOW) == "Thu, Oct 22 · 11:30 AM–12:30 PM"
    next_year = datetime(2027, 1, 5, 15, 0, tzinfo=timezone.utc)
    assert portal_dates.span(next_year, next_year + timedelta(hours=1), tz, NOW) == "Tue, Jan 5, 2027 · 10:00–11:00 AM"
    late = datetime(2026, 10, 23, 3, 0, tzinfo=timezone.utc)  # 11:00 PM Thu
    assert portal_dates.span(late, late + timedelta(hours=2), tz, NOW) == "Thu, Oct 22, 11:00 PM – Fri, Oct 23, 1:00 AM"


def test_home_shows_coming_up_after_this_week_with_an_empty_state(tmp_path, monkeypatch):
    client, *_ = signed_in(tmp_path, monkeypatch)
    page = html.unescape(client.get("/client/home").text)
    assert "<h2>Coming up</h2>" in page and "No bookings coming up." in page
    assert page.index("<h2>This week</h2>") < page.index("<h2>Coming up</h2>") < page.index("<h2>This week's callers</h2>")
    state = client.app.state
    caller = book(state, 1, NOW + timedelta(days=1), name="Dana Whitfield")
    state.preview_example_phones = (caller,)
    page = client.get("/client/home").text
    rows = re.search(r"<ol class=upcoming data-upcoming>.*?</ol>", page, re.S).group(0)
    assert "<span class=booking__job>Tree trimming</span> · <span class=booking__name>Dana Whitfield</span> <span class=extag>Example</span>" in rows
    assert "<p class=booking__where>412 Maple St, Charlotte</p>" in rows and "<span class=nw>Tue, Oct 20</span>" in rows
    assert "No bookings coming up." not in page


def test_calendar_lists_the_bookings_only_while_connected(tmp_path, monkeypatch):
    client, *_ = signed_in(tmp_path, monkeypatch)
    book(client.app.state, 1, NOW + timedelta(days=1), name="Dana Whitfield")
    assert "Booked on this calendar" not in client.get("/client/calendar").text  # the stub is not a connection
    real = portal_calendar.page_context

    def connected(state, result=None):
        context = real(state, result)
        context["card"] = {**context["card"], "connected": True}
        return context
    monkeypatch.setattr(portal_calendar, "page_context", connected)
    page = html.unescape(client.get("/client/calendar").text)
    assert "<h2 tabindex=-1>Booked on this calendar</h2>" in page and "Dana Whitfield" in page
    assert page.index("id=connection") < page.index("id=booked") < page.index("id=availability")
