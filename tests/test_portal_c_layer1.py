"""Candidate C, layer 1: the d1 shell (header, five-tab nav, in-flow notice slot), sign-in words, Home's
spine (one glyph and one word per state, Example tags only from the preview harness, rows with full dates)
and Account (devices from the session table, last use recorded)."""
import html
import re
from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from markupsafe import escape

from text_back import portal_status
from test_client_portal import BASE, OWNER, csrf_of, make, sign_in
from test_portal_c_pages import missed
from test_portal_c_shell import NAV, PAGES

STATIC = Path(__file__).resolve().parents[1] / "src" / "text_back" / "static"
LABELS = ("Home", "Messages", "Schedule", "Calendar", "Phone")


def nav_of(page: str) -> str:
    return re.search(r"<nav class=nav aria-label=Pages>.*?</nav>", page, re.S).group(0)


def node_of(page: str, key: str) -> str:
    return re.search(rf"<li class=\"node node--\w+\" data-setup={key}>.*?</li>", page, re.S).group(0)


# --- the shell ------------------------------------------------------------------------------

def test_shell_has_five_nav_items_with_the_current_page_marked(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    for url in PAGES:
        page = client.get(url).text
        nav = nav_of(page)
        tabs = re.findall(r"<a class=nav__item href=(/client/\w+)( aria-current=page)?><span class=nav__icon>.*?"
                          r"</span><span>(\w+)</span></a>", nav, re.S)
        assert [(href, label) for href, _, label in tabs] == list(zip(NAV, LABELS)), url
        assert [href for href, current, _ in tabs if current] == ([url] if url in NAV else []), url
        # Account: in the desktop sidebar (hidden on a phone, where it sits behind the business name).
        wide = re.search(r'<a class="nav__item nav__item--wide" href=/client/account( aria-current=page)?>', nav)
        assert wide and bool(wide.group(1)) == (url == "/client/account"), url
        trigger = re.search(r"<summary class=\"?menu__trigger[^>]*>.*?</summary>", page, re.S).group(0)
        assert ("menu__trigger--current" in trigger) == (url == "/client/account"), url
        assert ("<span class=vh>Account, current page</span>" in trigger) == (url == "/client/account"), url


def test_business_name_is_the_menu_trigger_and_is_never_cut_short(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    long_name = "Oak & Pine's Tree Care and Stump Grinding of the Carolinas, Inc."
    client.app.state.business_name = long_name
    page = client.get("/client/home").text
    header = re.search(r"<header class=topbar data-topbar>.*?</header>", page, re.S).group(0)
    assert f"<span class=menu__biz>{escape(long_name)}</span>" in header
    for word in ("ellipsis", "truncate", "text-overflow", "nowrap", "line-clamp"):
        assert word not in header, word
    assert "Signed in as <span class=nw>(980) 555-0123</span>" in header
    css = (STATIC / "portal.css").read_text()
    rule = re.search(r"\.menu__biz \{[^}]*\}", css.split("@layer d1 {", 1)[1]).group(0)
    assert "overflow-wrap: anywhere" in rule and "ellipsis" not in rule and "nowrap" not in rule


def test_notice_slot_is_role_status_and_sits_between_the_header_and_the_h1(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    for url in PAGES:
        page = client.get(url).text
        slot = page.index("<div class=status-slot id=notice role=status>")
        assert page.index("<header class=topbar data-topbar>") < page.index("</header>") < slot < page.index("<h1"), url
        main = page.split("<main", 1)[1].split("</main>", 1)[0]
        assert "data-toast" not in main and "toast-region" not in page, url
    saved = client.post("/client/account/remember", data={"csrf": csrf_of(page), "remember": "1"}).text
    slot = re.search(r"<div class=status-slot id=notice role=status>(.*?)</div>\s*<div class=page-head>", saved, re.S).group(1)
    assert "<p class=notice__text>Saved.</p>" in slot and 'class="notice notice--success' in slot
    assert "role=" not in slot  # the slot is the live region; the notice inside carries no role of its own
    assert re.search(r"<button type=button class=\"icon-btn toast__action\" data-notice-dismiss hidden>", slot)


def test_page_frame_carries_the_skip_link_and_one_stylesheet_with_the_d1_layer_last(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/home").text
    assert page.index("<a class=skip href=#main>Skip to content</a>") < page.index("<header class=topbar data-topbar>")
    assert "<main class=page id=main tabindex=-1>" in page
    css = (STATIC / "portal.css").read_text()
    assert css.count("@layer d1;") == 1 and css.rindex("@layer d1 {") > css.rindex("@layer motion {")
    assert "scroll-padding-top" in css.split("@layer d1 {", 1)[1]


def test_portal_js_has_no_floating_toast_and_marks_the_jump_chip(tmp_path):
    js = (STATIC / "portal.js").read_text()
    for gone in ("toast-region", "floatToast", "toast--floating", "COPY.undo", "'Undo'"):
        assert gone not in js, gone
    assert "IntersectionObserver" in js and "'location'" in js  # the jump chip of the step on screen
    assert "data-notice-dismiss" in js and "#notice" in js          # notices stay in flow


# --- sign in ------------------------------------------------------------------------------------

def test_sign_in_names_the_business_and_never_shows_a_number(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    page = client.get("/client/login").text
    assert "<h1>Oak &amp; Pine Tree Care</h1>" in page and "<p class=auth__sub>Sign in to TextBack</p>" in page
    assert "Owner settings" not in page
    assert "<label class=field__label for=mobile>Your mobile number</label>" in page
    field = re.search(r"<input id=mobile [^>]*>", page).group(0)
    assert 'placeholder="10 digits"' in field and "value=" not in field and "autofocus" not in field
    stepper = re.search(r"<ol class=stepper>.*?</ol>", page, re.S).group(0)
    assert "aria-current=step" in stepper and "Sign in" in stepper and "Check your phone" in stepper
    raw = re.sub(r"(?s)<svg [^>]*class=\"sprite\".*?</svg>", "", page)  # icon path data is all digits
    for number in ("0123", "980", "555", "5550123"):
        assert number not in raw, number  # the raw page, not only the words on screen


def test_a_bad_number_gets_one_inline_error_with_focus_on_the_field(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    bad = client.post("/client/login", data={"mobile": "980 555 01"}).text
    text = html.unescape(bad)
    assert text.count("Enter your mobile as 10 digits, area code first.") == 1
    assert "error-summary" not in bad and "role=alert" not in bad
    field = re.search(r"<input id=mobile [^>]*>", bad).group(0)
    assert "aria-invalid=true" in field and "autofocus" in field and 'aria-describedby="mobile-help mobile-error"' in field
    assert 'value="980 555 01"' in field  # the field keeps what was typed, so it can be fixed (deck round 3)
    assert client.get("/client/login").text.count("980 555 01") == 0  # and only beside its own error


def test_verify_page_carries_step_two_and_no_number(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    page = client.get("/client/verify").text
    assert "<p class=eyebrow>Oak &amp; Pine Tree Care</p>" in page and "<h1>Check your phone</h1>" in page
    stepper = re.search(r"<ol class=stepper>.*?</ol>", page, re.S).group(0)
    assert "stepper__step--done" in stepper and stepper.count("aria-current=step") == 1
    raw = re.sub(r"(?s)<svg [^>]*class=\"sprite\".*?</svg>", "", page)
    assert "0123" not in raw and "980" not in raw


# --- Home ---------------------------------------------------------------------------------------

def _items(*words):
    keys = ("calendar", "forwarding", "approval")
    return [dict(key=k, title=k.title(), state_word=w, detail=f"{k} detail.", action_label=None, action_href=None)
            for k, w in zip(keys, words)]


def test_home_draws_one_glyph_and_one_word_for_each_state(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    cases = [
        (("Done", "Done", "Done"), "done", ["done", "done", "done"]),
        (("Needs you", "Done", "Waiting on phone companies"), "needs", ["needs", "done", "waiting"]),
        (("Done", "Done", "Waiting on phone companies"), "waiting", ["done", "done", "waiting"]),
        (("Done", "Done", "Couldn't check"), "waiting", ["done", "done", "waiting"]),
        (("Done", "Done", "Not started"), "waiting", ["done", "done", "waiting"]),
    ]
    for words, head_kind, kinds in cases:
        monkeypatch.setattr(portal_status, "setup_items", lambda state, now, w=words: _items(*w))
        page = client.get("/client/home").text
        head = re.search(r'<li class="node node--(\w+) node--status">', page)
        assert head and head.group(1) == head_kind, words
        for key, word, kind in zip(("calendar", "forwarding", "approval"), words, kinds):
            node = node_of(page, key)
            assert f'class="node node--{kind}" data-setup={key}' in node, (key, word)
            pill = re.search(r'<span class="pill state state--(\w+)( pill--\w+)?">([^<]+)</span>', node)
            assert pill and pill.group(1) == kind and html.unescape(pill.group(3)) == word, node
            assert node.count("<svg") <= 1 and "pill state" in node  # the dot draws the glyph; the pill has none
            glyph = re.search(r"<span class=node__dot aria-hidden=true>(.*?)</span>", node, re.S).group(1)
            assert {"done": "#i-check", "needs": "node__bang", "waiting": "#i-clock"}[kind] in glyph


def test_home_example_tags_appear_only_when_the_harness_flags_them(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    state = client.app.state
    missed(state, "CA-ex", "+19805550141", clock[0] - timedelta(hours=1))
    missed(state, "CA-real", "+19805550142", clock[0] - timedelta(minutes=30))
    plain = client.get("/client/home").text
    assert "extag" not in plain and "Example" not in plain
    state.preview_example_phones = {"+19805550141"}
    state.preview_example_setup = {"forwarding", "approval"}
    page = client.get("/client/home").text
    callers = re.findall(r"<li class=caller>.*?</li>", page, re.S)
    assert len(callers) == 2
    flagged = [c for c in callers if "<span class=extag>Example</span>" in c]
    assert len(flagged) == 1 and "(980) 555-0141" in flagged[0]
    assert re.search(r"<h2>This week</h2><span class=extag>Example numbers</span>", page)
    assert "extag" not in node_of(page, "calendar")
    for key in ("forwarding", "approval"):
        assert "<span class=extag>Example</span>" in node_of(page, key), key


def test_home_caller_rows_stack_with_labels_and_always_carry_a_full_date(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    missed(client.app.state, "CA-1", "+19805550141", clock[0] - timedelta(minutes=30))
    page = html.unescape(client.get("/client/home").text)
    row = re.search(r"<li class=caller>.*?</li>", page, re.S).group(0)
    assert "<p class=caller__who><span class=caller__name><span class=nw>(980) 555-0141</span></span>" in row
    assert "<p class=caller__status>Waiting for a reply</p>" in row
    assert ("<span class=caller__k>Last activity</span> <span class=tnum><span class=nw>Mon, Oct 19</span>, "
            "<span class=nw>2:30 PM</span></span>") in row
    assert "<span class=caller__k>Last text</span>" in row and "Today" not in page
    assert "<table" not in page


def test_home_test_calendar_wording_matches_calendar(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    node = html.unescape(node_of(client.get("/client/home").text, "calendar"))
    assert "No calendar of yours yet. Until you connect one, bookings go on a test calendar you can't see." in node
    assert re.search(r'<a class="btn btn--secondary setup__btn" href=/client/calendar>', node)


# --- Account ------------------------------------------------------------------------------------

def test_account_lists_this_phone_and_other_devices_with_their_last_use(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    other = TestClient(client.app, base_url=BASE)
    sign_in(other, telecom)
    clock[0] += timedelta(minutes=20)
    sign_in(client, telecom)
    page = html.unescape(client.get("/client/account").text)
    assert "<h2>Signed in as <span class=nw>(980) 555-0123</span></h2>" in page
    devices = re.search(r"<ul class=devices>.*?</ul>", page, re.S).group(0)
    assert "<li class=\"device device--current\" data-device=this>" in devices
    devices = re.sub(r"<[^>]+>", "", devices)
    # A 12-hour session ends within a day, so its end carries the time as well as the day.
    assert "This device · signed in Mon, Oct 19, 3:20 PM · stays signed in until Tue, Oct 20, 3:20 AM" in devices
    assert "Another device · last used Mon, Oct 19, 3:00 PM" in devices
    clock[0] += timedelta(hours=2)
    assert other.get("/client/home").status_code == 200  # the other device is used again
    devices = re.search(r"<ul class=devices>.*?</ul>", html.unescape(client.get("/client/account").text), re.S).group(0)
    devices = re.sub(r"<[^>]+>", "", devices)
    assert "Another device · last used Mon, Oct 19, 5:20 PM" in devices


def test_account_signout_everywhere_confirms_in_place(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/account").text
    assert "<details class=confirm-inline>" in page and "<dialog" not in page
    panel = re.search(r"<details class=confirm-inline>.*?</details>", page, re.S).group(0)
    assert "<summary class=\"btn btn--secondary confirm-inline__trigger\">Sign out everywhere</summary>" in panel
    assert "Sign out of every device? You'll need a new code on each one." in panel
    assert "name=confirm value=1" in panel and "Stay signed in" in panel
    asked = client.post("/client/account/signout-everywhere", data={"csrf": csrf_of(page)}).text
    assert "<details class=confirm-inline open>" in asked  # the no-JS first step opens it in place


def test_a_reply_stamped_with_its_question_is_the_last_text(tmp_path, monkeypatch):
    """The worker answers inside the same instant it received the customer's text; the reply is still the later one."""
    import json as _json
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    state = client.app.state
    at = clock[0] - timedelta(minutes=10)
    missed(state, "CA-1", "+19805550141", at - timedelta(minutes=5))
    with state.store.transaction():
        state.store.conn.execute(
            "INSERT INTO inbound_jobs(key,kind,phone,params_json,received_at,status,attempts,next_attempt_at) "
            "VALUES('SM-1','sms','+19805550141',?,?,'done',1,?)",
            (_json.dumps({"body": "Dana Whitfield"}), at.isoformat(), at.isoformat()))
        state.store.conn.execute("UPDATE sms_outbox SET created_at=?, body=? WHERE key='CA-1:intro'",
                                 (at.isoformat(), "Booked: Tree trimming on Thursday at 10:00 AM."))
    row = portal_status.this_week(state, clock[0])["rows"][0]
    assert row["snippet"] == "Booked: Tree trimming on Thursday at 10:00 AM."
    long = portal_status._snippet("word " * 60)
    assert long.endswith("word…") and len(long) <= portal_status.SNIPPET_MAX


def test_account_save_rests_until_something_changes(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/account").text
    form = re.search(r"<form method=post action=/client/account/remember class=card id=account-form .*?</form>", page, re.S).group(0)
    assert re.search(r'<button type=submit class="btn btn--primary" form=account-form aria-disabled=true[^>]*>Save</button>', form)
    assert "<span class=savebar__rest data-rest-status>No unsaved changes</span>" in form
    remembered = client.post("/client/account/remember", data={"csrf": csrf_of(page), "remember": "1"})
    assert "On. This device stays signed in for 30 days." in html.unescape(remembered.text)  # still posts without JS
    devices = re.sub(r"<[^>]+>", "", re.search(r"<ul class=devices>.*?</ul>", remembered.text, re.S).group(0))
    assert "stays signed in until Wed, Nov 18" in html.unescape(devices) and "Nov 18," not in html.unescape(devices)


# --- round 3: the phone header becomes the save bar ----------------------------------------------

def _shell_page(tmp_path, monkeypatch, **extra):
    """Render the signed-in shell (Account) with extra context, as a later page layer will."""
    from text_back import client_portal
    from text_back.portal_render import ENV, ASSET_VERSION
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    state = client.app.state
    with state.store.lock:
        session = dict(state.store.conn.execute("SELECT * FROM client_sessions WHERE pending=0").fetchone())
    context = {**client_portal.shell(state, session, title="Account", nav="account"),
               **client_portal.account_view(state, session), **extra}
    return ENV.get_template("client/account.html.j2").render(asset_v=ASSET_VERSION, theme=None, **context)


def test_header_is_plain_until_a_page_reports_unsaved_changes(tmp_path, monkeypatch):
    page = _shell_page(tmp_path, monkeypatch)
    assert "<header class=topbar data-topbar>" in page and "topsave" not in page


def test_a_page_with_unsaved_changes_turns_the_header_into_the_save_bar(tmp_path, monkeypatch):
    topsave = {"form": "schedule-form", "changed": "1 rule changed", "save": "Save",
               "names": [("#duration", "Appointment length")]}
    page = _shell_page(tmp_path, monkeypatch, topsave=topsave)
    header = re.search(r"<header class=\"topbar topbar--dirty\" data-topbar>.*?</header>", page, re.S).group(0)
    bar = re.search(r"<div class=topsave data-topsave-server>.*</div>", header, re.S).group(0)
    assert "<summary class=topsave__summary><span class=topsave__count>1 rule changed</span>" \
           "<span class=vh>. Show what changed</span>" in bar
    assert '<li><a href="#duration">Appointment length</a></li>' in bar
    assert ('<button type=submit class="btn btn--ghost" name=discard value=1 form=schedule-form formnovalidate '
            'data-topsave-discard>Discard</button>') in bar
    assert '<button type=submit class="btn btn--primary" form=schedule-form>Save</button>' in bar
    # The brand and the menu stay in the markup (CSS hides them below 1024 px); the bottom nav stays.
    assert "<a class=brand" in header and "<details class=menu" in header
    assert "<nav class=nav aria-label=Pages>" in page


def test_portal_js_tracks_changes_per_form_and_drives_the_header(tmp_path):
    js = (STATIC / "portal.js").read_text()
    for hook in ("data-track-changes", "data-topsave", "topbar--dirty", "topsave__changes", "data-rest-save",
                 "beforeunload", "COPY.discarded"):
        assert hook in js, hook
    css = (STATIC / "portal.css").read_text().split("@layer d1 {", 1)[1]
    assert ".topbar--dirty > .brand, .topbar--dirty > .menu { display: none; }" in css
    assert ".nw { white-space: nowrap; }" in css


# --- round 3: Example tag on seeded device rows ---------------------------------------------------

def test_other_device_rows_carry_the_example_tag_only_when_flagged(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    other = TestClient(client.app, base_url=BASE)
    sign_in(other, telecom)
    sign_in(client, telecom)
    page = client.get("/client/account").text
    assert "extag" not in page
    state = client.app.state
    with state.store.lock:
        hashes = [r[0] for r in state.store.conn.execute("SELECT token_hash FROM client_sessions WHERE pending=0")]
    state.preview_example_sessions = set(hashes)  # the harness flags its seeded rows; this phone is never tagged
    devices = re.search(r"<ul class=devices>.*?</ul>", client.get("/client/account").text, re.S).group(0)
    rows = re.findall(r"<li class=\"?device[^>]*>.*?</li>", devices, re.S)
    assert len(rows) == 2 and "extag" not in rows[0] and "<span class=extag>Example</span>" in rows[1]
