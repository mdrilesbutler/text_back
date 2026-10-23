"""Front-end invariants of the /client settings pages (implementation-plan §B.10):
static files, security headers and CSP, the byte-identical verify page, the Messages form
contract, CSRF on every form, standard-wording normalisation, error rendering, the calendar
picker, the styleguide, the theme cookie, the shared layout tables and the copy rules."""
import collections
import json
import re
from pathlib import Path

from text_back.calendars.protocol import CalendarProviderError
from text_back.client_portal import ANYTIME, CARD_SCENARIO, DEFAULT_TEMPLATES, FIELD_KEYS, LAYOUT, SCENARIOS, TRIGGERS
from text_back.client_settings import remember_calendars
from text_back.messages import FORBIDDEN_PHRASES
from text_back.portal_render import CSP, STATIC_DIR, TEMPLATE_DIR
from text_back.portal_styleguide import contrast_pairs, declarations, token_block
from test_client_portal import csrf_of, make, sign_in
from test_client_settings import NOW, google_fixture

SECTIONS = ("colour", "type", "space", "icons", "buttons", "fields", "choices", "status", "feedback",
            "conversation", "cards", "spine", "rail", "savebar", "shell")


def messages_form(page_html):
    return re.search(r"<form method=post action=/client/messages id=messages.*?</form>", page_html, re.S).group(0)


def card(page_html, key):
    return re.search(rf'<article class="msg[^"]*" id=m_{key} .*?</article>', page_html, re.S).group(0)


def assert_portal_page(response, status=200):
    assert response.status_code == status
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"] == CSP
    text = response.text
    assert "style=" not in text and "<style" not in text
    assert not re.search(r"""(?:src|href)=["']?http""", text)
    for script in re.findall(r"<script[^>]*>", text):
        assert script.startswith('<script type=module src="/client/static/portal.js?v=') or \
            script == "<script type=application/json id=tb-data>", script
    assert text.count("<link rel=stylesheet") == 1
    return text


# 1 -------------------------------------------------------------------------------

def test_static_files_are_served_with_their_types_and_nosniff(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    for url, kind in (("/client/static/portal.css", "text/css"), ("/client/static/portal.js", "text/javascript"),
                      ("/client/static/fonts/archivo-600-latin.woff2", "font/woff2")):
        response = client.get(url)
        assert response.status_code == 200 and response.headers["content-type"].startswith(kind), url
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["cache-control"] == "no-cache"  # unversioned: revalidate by ETag
    versioned = client.get("/client/static/portal.css?v=abcdefgh")
    assert "immutable" in versioned.headers["cache-control"] and "max-age=31536000" in versioned.headers["cache-control"]


# 2 -------------------------------------------------------------------------------

def test_every_portal_page_sends_the_headers_and_the_csp_and_loads_only_its_own_assets(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    assert_portal_page(client.get("/client/login"))
    client.post("/client/login", data={"mobile": "980 555 0123"}, follow_redirects=False)
    assert_portal_page(client.get("/client/verify"))
    sign_in(client, telecom)
    messages = assert_portal_page(client.get("/client/messages"))
    assert re.search(r"<script type=application/json id=tb-data>\{", messages)
    assert_portal_page(client.get("/client/business"))
    assert_portal_page(client.get("/client/calendar"))
    assert_portal_page(client.get("/client/styleguide"))
    csrf = csrf_of(messages)
    assert_portal_page(client.post("/client/business", data={
        "csrf": csrf, "business_name": "Oak", "business_contact": "", "owner_mobile": "980 555 0199"}))
    assert_portal_page(client.post("/client/messages", data={"csrf": "forged"}), status=400)


def test_the_calendar_page_sends_the_headers_in_every_google_state(tmp_path, monkeypatch):
    client, telecom, credentials, transport = google_fixture(tmp_path, monkeypatch)
    sign_in(client, telecom)
    assert "data-status=reauth_required" in assert_portal_page(client.get("/client/calendar"))
    monkeypatch.setattr(credentials, "status", lambda: (_ for _ in ()).throw(CalendarProviderError("boom")))
    assert "data-status=unavailable" in assert_portal_page(client.get("/client/calendar"))
    monkeypatch.setattr(credentials, "status", lambda: "ready")
    assert "data-status=ready" in assert_portal_page(client.get("/client/calendar"))


# 3 -------------------------------------------------------------------------------

def test_the_verify_page_is_identical_for_an_unknown_number_and_a_wrong_code_and_shows_no_digits(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    client.post("/client/login", data={"mobile": "980 555 9999"}, follow_redirects=False)  # not on file
    blank = client.get("/client/verify").content
    unknown = client.post("/client/verify", data={"code": "000000"}).content
    client.post("/client/login", data={"mobile": "980 555 0123"}, follow_redirects=False)  # on file
    assert client.get("/client/verify").content == blank
    wrong = client.post("/client/verify", data={"code": "000000"}).content
    assert unknown == wrong
    business = re.sub(r"\D", "", client.app.state.business_number or "")
    for page in (blank, wrong):
        text = page.decode()
        for digits in ("0123", "5550123", "9805550123", "9999") + ((business, business[-4:]) if business else ()):
            assert digits not in text, digits


# 4 -------------------------------------------------------------------------------

def test_the_messages_form_always_posts_all_21_texts_and_enter_saves(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    form = messages_form(client.get("/client/messages").text)
    assert form.count("<textarea") == len(FIELD_KEYS) == 21
    assert set(re.findall(r"<textarea [^>]*\bname=(\w+)", form)) == set(FIELD_KEYS)
    assert not re.search(r"\sdisabled[\s>=]", form)  # a disabled field would silently not post
    first_submit = re.search(r"<button type=submit[^>]*>", form).group(0)
    assert "name=save value=1" in first_submit and "class=vh" in first_submit and "aria-hidden=true" in first_submit
    assert "name=ask_phone value=1" in form and "name=ask_email value=1" in form


# 5 -------------------------------------------------------------------------------

def test_every_post_form_on_a_signed_in_page_carries_the_csrf_token(tmp_path, monkeypatch):
    client, telecom, credentials, transport = google_fixture(tmp_path, monkeypatch)
    sign_in(client, telecom)
    monkeypatch.setattr(credentials, "status", lambda: "ready")
    remember_calendars(client.app.state, [{"id": "a@x", "summary": "Personal", "primary": True},
                                          {"id": "b@x", "summary": "Tree jobs"}], NOW)
    pages = [client.get(url).text for url in ("/client/messages", "/client/business", "/client/calendar", "/client/styleguide")]
    csrf = csrf_of(pages[0])
    pages.append(client.post("/client/business", data={
        "csrf": csrf, "business_name": "Oak", "business_contact": "", "owner_mobile": "980 555 0199"}).text)
    pages.append(client.post("/client/calendar", data={"csrf": "forged"}).text)
    seen = collections.Counter()
    for page in pages:
        forms = re.findall(r"<form method=post .*?</form>", page, re.S)
        assert forms
        for form in forms:
            assert f"name=csrf value='{csrf}'" in form, form[:120]
            seen[re.search(r"action=(\S+?)[\s>]", form).group(1)] += 1
    assert seen["/client/logout"] == len(pages)
    assert {"/client/business", "/client/business/confirm", "/client/calendar"} <= set(seen)


# 6 -------------------------------------------------------------------------------

def test_the_standard_wording_posted_back_is_stored_as_standard(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/messages").text)
    # The editors are pre-filled, so an untouched save posts every default; one with doubled spaces.
    data = {"csrf": csrf, **{key: DEFAULT_TEMPLATES[key] for key in FIELD_KEYS}}
    data["intro"] = DEFAULT_TEMPLATES["intro"].replace(" ", "  ")
    page = client.post("/client/messages", data=data).text
    assert json.loads(path.read_text()) == {}
    assert "Standard wording</span>" in card(page, "intro") and "Customized</span>" not in page


# 7, 8 ----------------------------------------------------------------------------

def test_a_rejected_save_opens_the_editor_on_the_reason(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/messages").text)
    page = client.post("/client/messages", data={"csrf": csrf, "intro": "Ask for a representative"}).text
    intro = card(page, "intro")
    assert "<details class=editor open>" in intro and "aria-invalid=true" in intro
    describedby = re.search(r'<textarea [^>]*aria-describedby="([^"]+)"', intro).group(1).split()
    assert "e_intro" in describedby and "id=e_intro" in intro
    assert "data-initial=error" in page and 'id=error-summary role=alert' in page
    assert "<details class=editor open>" not in card(page, "prompt_name")


def test_a_rejected_save_with_a_dotted_placeholder_keeps_the_typed_text(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/messages").text)
    response = client.post("/client/messages", data={"csrf": csrf, "intro": "Hi {a.b}"})
    assert response.status_code == 200 and "Not saved" in response.text
    assert ">Hi {a.b}</textarea>" in card(response.text, "intro")
    assert not path.exists()


# 9 -------------------------------------------------------------------------------

def test_the_calendar_picker_appears_only_while_connected(tmp_path, monkeypatch):
    client, telecom, credentials, transport = google_fixture(tmp_path, monkeypatch)
    sign_in(client, telecom)
    remember_calendars(client.app.state, [{"id": "a@x", "summary": "Personal", "primary": True},
                                          {"id": "b@x", "summary": "Tree jobs"}], NOW)
    page = client.get("/client/calendar").text
    assert "data-status=reauth_required" in page and "name=calendar_id" not in page
    monkeypatch.setattr(credentials, "status", lambda: "ready")
    page = client.get("/client/calendar").text
    assert page.count("name=calendar_id") == 2 and "Use this calendar" in page


# 10 ------------------------------------------------------------------------------

def test_the_styleguide_is_owner_only_unindexed_and_draws_every_section_in_both_themes(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    response = client.get("/client/styleguide", follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/client/login"
    sign_in(client, telecom)
    response = client.get("/client/styleguide")
    assert response.status_code == 200 and response.headers["x-robots-tag"] == "noindex"
    page = response.text
    for section in SECTIONS:
        block = re.search(rf"<section class=sg-section id=sg-{section} .*?</section>\s*(?=<section class=sg-section|</main>)",
                          page, re.S)
        assert block, section
        assert "<div class=sg-panel data-theme=light" in block.group(0) and "<div class=sg-panel data-theme=dark" in block.group(0)
    assert "data-demo-toast" in page and "data-demo-motion" in page
    ids = re.findall(r'\sid="?([^\s">]+)', page)
    assert [i for i, n in collections.Counter(ids).items() if n > 1] == []
    # Nothing on the page posts except Sign out; static specimens stay out of portal.js's reach.
    assert re.findall(r"<form method=post action=(\S+?)>", page) == ["/client/logout"]
    assert "data-toast " not in page and "data-rail" not in page and "id=error-summary" not in page
    # Every colour token of the stylesheet is shown, and every §1.3 pair passes in both themes.
    for token in declarations(token_block((STATIC_DIR / "portal.css").read_text(), "light")):
        assert f"--{token}</code>" in page or token.startswith("shadow-"), token
    for pair in contrast_pairs():
        for theme, shade in pair.shades.items():
            assert shade.ok, (pair.fg, pair.bg, theme, shade.ratio)


# 11 ------------------------------------------------------------------------------

def test_a_forged_csrf_token_answers_with_the_page_expired_html(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    for url in ("/client/messages", "/client/business", "/client/business/confirm", "/client/calendar"):
        response = client.post(url, data={"csrf": "forged", "business_name": "Evil", "owner_mobile": "980 555 0199"})
        assert response.status_code == 400 and response.headers["content-type"].startswith("text/html"), url
        assert "This page expired" in response.text
    assert client.app.state.business_name == "Oak & Pine Tree Care"


# 12 ------------------------------------------------------------------------------

def test_the_theme_cookie_sets_data_theme_and_anything_else_is_ignored(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    client.cookies.set("tb_theme", "dark")
    assert "<html lang=en class=no-js data-theme=dark>" in client.get("/client/login").text
    client.cookies.set("tb_theme", "blue")
    assert "<html lang=en class=no-js>" in client.get("/client/login").text


# 13 ------------------------------------------------------------------------------

def test_the_layout_tables_cover_every_message_exactly_once():
    keys = [key for *_, sets in (*LAYOUT, ANYTIME) for parent, branches in sets for key in (parent, *branches)]
    assert sorted(keys) == sorted(FIELD_KEYS) and len(keys) == len(set(keys))
    assert set(TRIGGERS) <= set(FIELD_KEYS)
    scenario_ids = {sid for sid, _, _ in SCENARIOS}
    for _, _, rows in SCENARIOS:
        assert {text for kind, text, _, _ in rows if kind == "textback"} <= set(FIELD_KEYS)
    assert set(CARD_SCENARIO) == set(FIELD_KEYS) and set(CARD_SCENARIO.values()) <= scenario_ids


# 14 ------------------------------------------------------------------------------

def test_the_two_dark_token_blocks_are_identical():
    css = (STATIC_DIR / "portal.css").read_text()
    media, forced = declarations(token_block(css, "dark-media")), declarations(token_block(css, "dark"))
    assert list(media.items()) == list(forced.items()) and len(media) > 40


# 15 ------------------------------------------------------------------------------

def test_no_template_says_ai_or_promises_a_person():
    templates = sorted(Path(TEMPLATE_DIR, "client").glob("*.j2"))
    assert len(templates) >= 14
    for template in templates:
        text = template.read_text(encoding="utf-8")
        assert not re.search(r"\bAI\b", text), template.name
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in text.lower(), (template.name, phrase)
