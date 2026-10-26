"""Candidate C shell: landing on Home, the five-tab nav, headers and CSP, CSRF on every POST form,
the in-flow notice slot, the header name, sign-in words, Account (remember, sign out everywhere)."""
import html
import re
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from text_back.portal_dates import when
from text_back.portal_render import CSP, ENV
from test_client_portal import BASE, OWNER, code_from, csrf_of, make, sign_in
from test_portal_c_words import visible

NAV = ("/client/home", "/client/messages", "/client/schedule", "/client/calendar", "/client/phone")
PAGES = NAV + ("/client/account",)


def assert_portal_page(response, status=200):
    assert response.status_code == status
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"] == CSP
    text = response.text
    assert "style=" not in text and "<style" not in text
    assert not re.search(r"""(?:src|href)=["']?http""", text)
    for script in re.findall(r"<script[^>]*>", text):
        assert script.startswith('<script type=module src="/client/static/portal.js?v=') or \
            script == "<script type=application/json id=tb-data>", script
    assert text.count("<link rel=stylesheet") == 1
    return text


def test_dates_format_from_datetimes():
    friday = datetime(2026, 10, 23, 18, 40, tzinfo=timezone.utc)
    assert when(friday, "America/New_York") == "Fri, Oct 23, 2:40 PM"
    assert when(friday, "America/New_York", now=friday + timedelta(hours=1)) == "Today, 2:40 PM"
    assert when(friday, "America/New_York", now=datetime(2027, 1, 4, tzinfo=timezone.utc)) == "Fri, Oct 23, 2026, 2:40 PM"
    # The templates' only date formatter is the registered filter.
    assert ENV.from_string("{{ d|when('America/New_York') }}").render(d=friday) == "Fri, Oct 23, 2:40 PM"
    assert ENV.from_string("{{ d|day('America/New_York') }}").render(d=friday) == "Fri, Oct 23"


def test_sign_in_label_is_your_mobile_number_with_a_neutral_placeholder_and_no_prefill(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    page = assert_portal_page(client.get("/client/login"))
    assert "<label class=field__label for=mobile>Your mobile number</label>" in page
    field = re.search(r"<input id=mobile [^>]*>", page).group(0)
    assert 'placeholder="10 digits"' in field and "value=" not in field
    shown = visible(page)
    assert "0123" not in shown and "555" not in shown  # no real or sample number anywhere on the public page
    assert "<h1>Oak &amp; Pine Tree Care</h1>" in page and "Sign in to TextBack" in page and "Owner settings" not in page
    bad = html.unescape(client.post("/client/login", data={"mobile": "12"}).text)
    assert "Enter your mobile as 10 digits, area code first." in bad


def test_landing_is_home_and_every_nav_item_resolves(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    anonymous = TestClient(client.app, base_url=BASE)
    for url in PAGES:
        response = anonymous.get(url, follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == "/client/login", url
    sign_in(client, telecom)  # asserts the verify redirect lands on /client/home
    assert client.get("/client", follow_redirects=False).headers["location"] == "/client/home"
    assert client.get("/client/login", follow_redirects=False).headers["location"] == "/client/home"
    home = client.get("/client/home").text
    nav = re.search(r"<nav class=nav aria-label=Pages>.*?</nav>", home, re.S).group(0)
    tabs = re.findall(r'<a class=nav__item href=(/client/\w+)( aria-current=page)?>', nav)
    assert [href for href, _ in tabs] == list(NAV)
    assert [label for label in re.findall(r"</span><span>([^<]+)</span></a>", nav)][:5] == [
        "Home", "Messages", "Schedule", "Calendar", "Phone"]
    for url in PAGES:
        page = client.get(url)
        assert page.status_code == 200, url
        current = re.findall(r"href=(/client/\w+) aria-current=page", page.text)
        # On Account both the sidebar link and the menu's Account item are marked (mockup d1).
        assert current == ([url] if url in NAV else ["/client/account", "/client/account"]), url
    # The old Business tab lands on Phone; its state-changing GET is gone.
    assert client.get("/client/business", follow_redirects=False).headers["location"] == "/client/phone"
    assert client.get("/client/business/keep").status_code in (404, 405)
    assert client.get("/client/logout").status_code == 405


def test_every_page_sends_headers_csp_and_own_assets_only(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    assert_portal_page(client.get("/client/login"))
    client.post("/client/login", data={"mobile": "980 555 0123"}, follow_redirects=False)
    assert_portal_page(client.get("/client/verify"))
    sign_in(client, telecom)
    for url in PAGES:
        assert_portal_page(client.get(url))
    csrf = csrf_of(client.get("/client/home").text)
    assert_portal_page(client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak", "owner_mobile": "980 555 0199"}))
    for url in ("/client/messages", "/client/schedule", "/client/calendar", "/client/phone", "/client/phone/checks",
                "/client/phone/keep", "/client/phone/confirm", "/client/phone/rename-texts", "/client/account/remember",
                "/client/account/signout-everywhere"):
        response = client.post(url, data={"csrf": "forged", "business_name": "Evil", "owner_mobile": "980 555 0100"})
        assert "This page expired" in assert_portal_page(response, status=400), url
    assert client.app.state.business_name == "Oak"


def test_every_post_form_carries_the_csrf_token(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    pages = [client.get(url).text for url in PAGES]
    csrf = csrf_of(pages[0])
    pages.append(client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak", "owner_mobile": "980 555 0199"}).text)
    pages.append(client.post("/client/account/signout-everywhere", data={"csrf": csrf}).text)
    actions = set()
    for page in pages:
        forms = re.findall(r"<form method=post .*?</form>", page, re.S)
        assert forms
        for form in forms:
            assert f"name=csrf value='{csrf}'" in form, form[:160]
            actions.add(re.search(r"action=(\S+?)[\s>]", form).group(1))
        # The only GET form picks which example conversation is drawn; it changes nothing.
        assert re.findall(r"<form method=get action=(\S+)", page) in ([], ["/client/messages#example"])
        assert not re.search(r"<form(?! method=(?:post|get) )", page)
    assert {"/client/logout", "/client/messages", "/client/schedule", "/client/calendar", "/client/phone",
            "/client/phone/confirm", "/client/phone/keep", "/client/account/remember",
            "/client/account/signout-everywhere"} <= actions


def test_header_business_name_wraps_and_is_the_account_menu(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/home").text)
    client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak & Pine's Tree Care of the Carolinas, Inc.",
                                       "owner_mobile": OWNER})
    page = client.get("/client/home").text
    header = re.search(r"<header class=topbar data-topbar>.*?</header>", page, re.S).group(0)
    trigger = re.search(r"<summary class=\"menu__trigger\">.*?</summary>", header, re.S).group(0)
    assert "<span class=menu__biz>Oak &amp; Pine&#39;s Tree Care of the Carolinas, Inc.</span>" in trigger
    assert "<span class=vh>Account</span>" in trigger
    assert "ellipsis" not in header and "truncate" not in header and "text-overflow" not in header
    assert "Signed in as <span class=nw>(980) 555-0123</span>" in header and "href=/client/account>" in header


def test_notice_slot_sits_between_the_header_and_the_h1_on_every_page(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    for url in PAGES:
        page = client.get(url).text
        slot = page.index("<div class=status-slot id=notice role=status>")
        assert page.index("</header>") < slot < page.index("<h1"), url
        assert "data-toast" not in page.split("<main", 1)[1].split("</main>", 1)[0], url  # no floating toast in the page
    csrf = csrf_of(page)
    saved = client.post("/client/account/remember", data={"csrf": csrf, "remember": "1"}).text
    assert re.search(r"<div class=status-slot id=notice role=status><div class=\"notice notice--success toast\" data-notice>"
                     r".*?<p class=notice__text>Saved\.</p>", saved, re.S)


def test_account_page_has_sign_out_everywhere_and_remember(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = html.unescape(client.get("/client/account").text)
    shown = re.sub(r"<[^>]+>", "", page)  # dates and times sit in no-wrap spans
    assert "<h1>Account</h1>" in page and "Signed in as" in page and "(980) 555-0123" in page
    assert "Remember this device for 30 days" in page and "Off. This device signs out after 12 hours." in page
    assert "Only this device is signed in." in page and "Sign out everywhere" in page
    assert "This device · signed in Mon, Oct 19, 3:00 PM · stays signed in until Tue, Oct 20, 3:00 AM" in shown


def test_remember_toggles_expiry(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/account").text)
    on = client.post("/client/account/remember", data={"csrf": csrf, "remember": "1"})
    assert "On. This device stays signed in for 30 days." in html.unescape(on.text)
    assert "max-age=2592000" in on.headers["set-cookie"].lower()
    row = client.app.state.store.conn.execute("SELECT remember, expires_at FROM client_sessions WHERE pending=0").fetchone()
    assert row["remember"] == 1 and datetime.fromisoformat(row["expires_at"]) == clock[0] + timedelta(days=30)
    clock[0] += timedelta(hours=13)
    assert client.get("/client/home").status_code == 200  # past the 12-hour session, still signed in
    off = client.post("/client/account/remember", data={"csrf": csrf})
    assert "Off. This device signs out after 12 hours." in html.unescape(off.text)
    clock[0] += timedelta(hours=13)
    assert client.get("/client/home", follow_redirects=False).headers["location"].startswith("/client/login")


def test_remember_at_sign_in_keeps_the_phone_for_30_days(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    verify = client.get("/client/verify").text
    assert "Remember this device for 30 days" in verify and "name=remember value=1" in verify
    code, _ = code_from(telecom)
    response = client.post("/client/verify", data={"code": code, "remember": "1"}, follow_redirects=False)
    assert response.headers["location"] == "/client/home" and "max-age=2592000" in response.headers["set-cookie"].lower()
    clock[0] += timedelta(days=29)
    assert client.get("/client/home").status_code == 200


def test_signout_everywhere_kills_other_sessions_after_an_inline_confirm(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    other = TestClient(client.app, base_url=BASE)
    sign_in(client, telecom)
    sign_in(other, telecom)
    page = html.unescape(client.get("/client/account").text)
    assert "Another device · last used Mon, Oct 19, 3:00 PM" in re.sub(r"<[^>]+>", "", page) and "Only this device is signed in." not in page
    csrf = csrf_of(page)
    ask = html.unescape(client.post("/client/account/signout-everywhere", data={"csrf": csrf}).text)
    assert "Sign out of every device? You'll need a new code on each one." in ask and "Stay signed in" in ask
    assert "<dialog" not in ask and "name=confirm value=1" in ask
    assert other.get("/client/home").status_code == 200  # nothing changed at step one
    done = client.post("/client/account/signout-everywhere", data={"csrf": csrf, "confirm": "1"}, follow_redirects=False)
    assert done.status_code == 303 and done.headers["location"] == "/client/login?notice=everywhere"
    assert "Signed out everywhere." in client.get(done.headers["location"]).text
    for browser in (client, other):
        assert browser.get("/client/home", follow_redirects=False).headers["location"].startswith("/client/login")
    ended = other.get("/client/home")  # the other device lands on sign-in with the signed-out notice
    assert "You were signed out. Sign in again to continue." in ended.text


def test_sign_in_requests_are_limited_and_the_notice_is_the_same_for_unknown_numbers(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    pages = {}
    for mobile in (OWNER, "+19805559999"):
        for _ in range(3):
            assert client.post("/client/login", data={"mobile": mobile}, follow_redirects=False).status_code == 303
        fourth = client.post("/client/login", data={"mobile": mobile}, follow_redirects=False)
        assert fourth.status_code == 200
        pages[mobile] = fourth.content
    assert pages[OWNER] == pages["+19805559999"]
    assert b"We&#39;ve sent three codes in the last 15 minutes. Wait a few minutes, then try again." in pages[OWNER]
    assert len([m for m in telecom.outbound if m.kind == "login_code"]) == 3
    clock[0] += timedelta(minutes=16)
    assert client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False).status_code == 303


def test_every_visible_form_control_has_a_name_and_lives_in_a_form(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    pages = [client.get("/client/login").text]
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    pages.append(client.get("/client/verify").text)
    sign_in(client, telecom)
    pages += [client.get(url).text for url in PAGES]
    csrf = csrf_of(pages[-1])
    pages.append(client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak", "owner_mobile": "980 555 0199"}).text)
    for page in pages:
        body = re.split(r"<body[^>]*>", page, maxsplit=1)[1]
        depth, pos = 0, 0
        for match in re.finditer(r"<(/?)(form|input|select|textarea|button)\b([^>]*)>", body):
            closing, tag, attrs = match.groups()
            if tag == "form":
                depth += -1 if closing else 1
                continue
            if closing:
                continue
            js_only = tag == "button" and "type=button" in attrs and re.search(r"\shidden\b", attrs)
            if js_only:
                continue  # progressive enhancement: hidden until portal.js wires it up
            owner = re.search(r"\sform=(\S+?)[\s>]", attrs + ">")
            if tag == "button" and owner:
                assert f"id={owner.group(1)}" in body, attrs  # posts the form it names (the header save bar)
                continue
            assert depth == 1, (tag, attrs[:120])
            if tag != "button" or "name=" in attrs:
                assert "name=" in attrs, (tag, attrs[:120])


def test_cookies_follow_the_public_url_unless_a_harness_overrides(tmp_path):
    from types import SimpleNamespace
    from text_back.client_portal import _secure
    assert _secure(SimpleNamespace(public_base_url="https://x.example")) is True
    assert _secure(SimpleNamespace(public_base_url="http://x.example")) is False
    assert _secure(SimpleNamespace(public_base_url="https://x.example", cookie_secure=False)) is False
