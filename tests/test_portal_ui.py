"""Portal rendering layer: headers, static assets, styleguide gate, macros, copy rules."""
import re
from pathlib import Path

from text_back import client_portal, messages, portal_ui
from text_back.portal_ui import env, format_phone_display, install_static, install_styleguide, render

from test_client_portal import make, sign_in

ROOT = Path(portal_ui.__file__).resolve().parent
CSP = ("default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; "
       "form-action 'self' https://accounts.google.com; base-uri 'none'; frame-ancestors 'none'")


def _macro_module(name):
    return env.get_template(f"components/{name}.html").module


def test_render_sets_every_security_header_and_status():
    response = render("auth.html", title="Sign in", business_name="Oak & Pine", status=418)
    assert response.status_code == 418
    assert response.headers["content-security-policy"] == CSP
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    body = response.body.decode()
    assert "Oak &amp; Pine" in body and f"portal.css?v={portal_ui.asset_v}" in body
    assert "nonce" not in body and " style=" not in body and "onclick" not in body


def test_render_accepts_request_first_for_compatibility():
    class Req:  # anything that is not a template name is treated as the request
        cookies = {}
    assert render(Req(), "auth.html", title="x", business_name="y").status_code == 200


def test_static_mount_serves_css_and_js(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    install_static(client.app)
    install_static(client.app)  # idempotent
    css = client.get(f"/client/static/portal.css?v={portal_ui.asset_v}")
    assert css.status_code == 200 and css.headers["content-type"].startswith("text/css")
    assert "--accent" in css.text
    js = client.get("/client/static/portal.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert client.get("/client/static/../portal_ui.py").status_code in (404, 400)


def test_styleguide_needs_a_session(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    install_styleguide(client.app, client_portal._session)
    out = client.get("/client/styleguide", follow_redirects=False)
    assert out.status_code == 303 and out.headers["location"] == "/client/login"
    sign_in(client, telecom)
    page = client.get("/client/styleguide")
    assert page.status_code == 200 and page.headers["content-security-policy"] == CSP
    html = page.text
    assert "Oak &amp; Pine Tree Care" in html
    for _, label, href, _ in client_portal.NAV:
        assert f"<span>{label}</span>" in html and f'href="{href}"' in html  # bottom tabs, routes that exist
    assert "/client/scheduling" not in html and "/client/phone" not in html and "data-toast" not in html
    assert html.count("action=\"/client/logout\"") == 1
    assert re.search(r"name=csrf value='([^']+)'", html)  # csrf_of() keeps working
    assert "Remember this phone for 30 days" in html
    assert "(704) 555-0141" in html and "customers-d-c1" in html  # table + open drawer
    assert html.count('class="bubble') >= 6
    assert " style=" not in html and "<script>" not in html


def test_phone_filter():
    assert format_phone_display("+17045550123") == "(704) 555-0123"
    assert format_phone_display("7045550123") == "(704) 555-0123"
    assert format_phone_display("+442071234567") == "+442071234567"
    assert format_phone_display("") == "" and format_phone_display(None) == ""


def test_every_macro_renders():
    forms, display, data = _macro_module("forms"), _macro_module("display"), _macro_module("data")
    out = []
    out.append(forms.input("n", "Name", value="a<b", hint="h", error="e", required=True, default="d", reset_name="reset"))
    out.append(forms.phone_input("p", "Phone", value="+17045550123", verify_label="Verify", status="ok", status_kind="ok"))
    out.append(forms.textarea_counter("t", "Text", value="x", placeholder="p", default="p", reset_name="reset"))
    out.append(forms.select("s", "Pick", [("a", "A"), "b"], value="b"))
    out.append(forms.toggle("ask_email", "Email", on=True))
    out.append(forms.radio_pills("r", "Len", [("30", "30"), ("60", "60")], value="60"))
    out.append(forms.button("Go")); out.append(forms.button("Go", "secondary", href="/x", icon_name="external"))
    out.append(forms.chips(["business_name"], "t"))
    out.append(display.section_header("T", "s"))
    out.append(display.status_pill("ok", "Booked")); out.append(display.status_pill("neutral", "New"))
    out.append(display.status_card("Calendar", "warn", "detail", "Fix", "/client/calendar"))
    out.append(display.stat("Missed", "3", "hint"))
    out.append(display.flash(error="bad")); out.append(display.flash(notice="good")); out.append(display.flash())
    out.append(display.toast("Copied", "ok"))
    out.append(display.empty_state("message", "None", "body", "Go", "/client"))
    out.append(display.stepper([{"label": "A", "state": "done"}, {"label": "B", "state": "current"}, {"label": "C", "state": "todo"}]))
    out.append(display.checklist([{"text": "x", "done": True, "evidence": "ev"}, {"text": "y", "done": False, "evidence": ""}]))
    cols = [{"key": "a", "label": "A"}, {"key": "b", "label": "B", "num": True}]
    out.append(data.table(cols, [{"id": 1, "cells": {"a": ("ok", "Booked"), "b": {"text": "1", "sub": "s"}}}]))
    out.append(data.table(cols, []))
    out.append(data.phone_preview([{"dir": "out", "text": "hi", "meta": "m"}, {"dir": "in", "text": "yo", "meta": ""}]))
    html = "\n".join(str(x) for x in out)
    assert "a&lt;b" in html and "(704) 555-0123" in html and 'name="p_e164" value="+17045550123"' in html
    assert "name=ask_email value=1 checked" in html
    assert "Nothing here yet" in html and 'data-insert="{business_name}"' in html
    assert "<svg" in html and " style=" not in html


def test_card_with_body_and_table_with_drawer():
    tpl = env.from_string(
        '{% from "components/display.html" import card %}{% from "components/data.html" import table %}'
        '{% call card("T", subtitle="s", flush=true) %}body{% endcall %}'
        '{% call(row) table([{"key": "a", "label": "A"}], [{"id": "r1", "cells": {"a": "x"}}], id="t", open_id="t-d-r1") %}D:{{ row.cells.a }}{% endcall %}'
    )
    html = tpl.render()
    assert "<h2>T</h2>" in html and "body" in html and "flush" in html
    assert 'data-drawer="t-d-r1"' in html and 'aria-expanded="true"' in html and "D:x" in html
    assert ' hidden' not in html.split('id="t-d-r1"')[1].split(">")[0]


def test_toggle_off_never_says_the_word():
    forms = _macro_module("forms")
    off = str(forms.toggle("ask_email", "Also ask for an email address", on=False, hint="SKIP is allowed"))
    assert "checked" not in off
    assert "name=ask_email value=1" in off
    layout = env.get_template("layout.html").render(title="Messages", active="messages", business_name="B", csrf="c", remember=False)
    assert "checked" not in layout
    layout_on = env.get_template("layout.html").render(title="Messages", active="messages", business_name="B", csrf="c", remember=True)
    assert "checked" not in layout_on  # the account toggle uses aria-pressed, not a checkbox


def test_templates_and_static_obey_the_copy_rules():
    files = list((ROOT / "templates").rglob("*.html")) + list((ROOT / "static").glob("*.js")) + list((ROOT / "static").glob("*.css"))
    assert len(files) >= 7
    for path in files:
        text = path.read_text()
        lowered = text.lower()
        for phrase in messages.FORBIDDEN_PHRASES:
            assert phrase not in lowered, f"{phrase!r} in {path.name}"
        assert not re.search(r"\bAI\b", text), f"'AI' in {path.name}"
        assert "<script>" not in text and "onclick=" not in text and 'style="' not in text, path.name
