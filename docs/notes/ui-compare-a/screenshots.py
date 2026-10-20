"""Screenshot every /client screen at 375px and 1024px with stub telecom and a sample messages file."""
import json, os, re, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

sys.path.insert(0, "tests")
from text_back.app import create_app
from text_back.telecom import FakeTelecom
from test_client_settings import google_fixture  # noqa: E402

OUT = Path("docs/notes/ui-compare-a"); OUT.mkdir(parents=True, exist_ok=True)
TMP = Path(sys.argv[1]); TMP.mkdir(parents=True, exist_ok=True)
NOW = datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc)
OWNER = "+19805550123"


def serve(app, port):
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server


# App 1: stub calendar (test mode), editable messages, one customized message + email question on.
os.environ["TEXT_BACK_OWNER_MOBILE"] = OWNER
messages = TMP / "messages.json"
messages.write_text(json.dumps({"intro": "Hey, this is Oak & Pine Tree Care. Sorry we missed your call! What do you need done?",
                                "fields": "service, location, preferred_time, name, email"}))
os.environ["TEXT_BACK_MESSAGES_FILE"] = str(messages)
telecom = FakeTelecom()
app = create_app(db_path=str(TMP / "a.db"), telecom=telecom, public_base_url="http://127.0.0.1:8765",
                 business_name="Oak & Pine Tree Care", now_provider=lambda: NOW)
app.state.business_number = "+17045550100"
serve(app, 8765)

# App 2: Google calendar in the three real states.
class MP:  # the test fixture wants a monkeypatch; the env is already set
    def setenv(self, k, v): os.environ[k] = v
    def delenv(self, k, raising=True): os.environ.pop(k, None)
(TMP / "g").mkdir(exist_ok=True)
gclient, gtelecom, credentials, transport = google_fixture(TMP / "g", MP())
gapp = gclient.app
gapp.state.public_base_url = "http://127.0.0.1:8766"
serve(gapp, 8766)


def code(tel):
    return re.search(r"\b(\d{6})\b", [m for m in tel.outbound if m.kind == "login_code"][-1].body).group(1)


def shoot(page, name):
    for width in (375, 1024):
        page.set_viewport_size({"width": width, "height": 812 if width == 375 else 900})
        page.wait_for_timeout(100)
        page.screenshot(path=str(OUT / f"{name}-{width}.png"), full_page=True)
    print("shot", name)


def sign_in(page, base, tel):
    page.goto(base + "/client/login")
    page.fill("#mobile", "980 555 0123")
    page.click("button[type=submit]")
    page.fill("#code", code(tel))
    page.click("button[type=submit]")
    page.wait_for_url(base + "/client/messages")


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 375, "height": 812}, device_scale_factor=2)
    page = ctx.new_page()
    base = "http://127.0.0.1:8765"
    page.goto(base + "/client/login"); shoot(page, "01-signin")
    page.fill("#mobile", "980 555 0123"); page.click("button[type=submit]")
    page.wait_for_url(base + "/client/verify"); shoot(page, "02-enter-code")
    page.fill("#code", code(telecom)); page.click("button[type=submit]")
    page.wait_for_url(base + "/client/messages"); shoot(page, "03-messages")
    # Live preview after typing, before saving (JS on): unsaved badge + customized state.
    page.fill("#f_prompt_name", "And who should we put the appointment under?")
    page.click("#m_prompt_name .chip")
    page.wait_for_timeout(100); shoot(page, "04-messages-editing-unsaved")
    # A rejected save: the reason lands on the card.
    page.fill("#f_prompt_name", "")
    page.fill("#f_handoff_ack", "Paused. Call our business line.")
    page.once("dialog", lambda d: d.accept())
    page.click(".savebar button[type=submit]")
    page.wait_for_selector(".msg.bad"); shoot(page, "05-messages-rejected-save")
    page.fill("#f_handoff_ack", "")
    page.click(".savebar button[type=submit]"); page.wait_for_selector(".flash.ok"); shoot(page, "06-messages-saved")
    page.goto(base + "/client/business"); shoot(page, "07-business")
    page.fill("#owner_mobile", "980 555 0199"); page.click("button.primary")
    page.wait_for_selector(".step.now"); shoot(page, "08-business-confirm-new-mobile")
    page.goto(base + "/client/business/keep")
    page.goto(base + "/client/calendar"); shoot(page, "09-calendar-test-mode")

    # JS off: the same Messages page must still work.
    nojs = browser.new_context(viewport={"width": 375, "height": 812}, device_scale_factor=2, java_script_enabled=False)
    npage = nojs.new_page(); sign_in(npage, base, telecom); shoot(npage, "10-messages-javascript-off")

    gbase = "http://127.0.0.1:8766"
    gpage = ctx.new_page(); sign_in(gpage, gbase, gtelecom)
    gpage.goto(gbase + "/client/calendar"); shoot(gpage, "11-calendar-reconnect-needed")
    from text_back.calendars.protocol import CalendarProviderError
    real_status = credentials.status
    credentials.status = lambda: (_ for _ in ()).throw(CalendarProviderError("x"))
    gpage.goto(gbase + "/client/calendar"); shoot(gpage, "12-calendar-could-not-be-read")
    credentials.status = lambda: "ready"
    from text_back.client_settings import remember_calendars
    remember_calendars(gapp.state, [{"id": "owner@example.test", "summary": "Personal", "primary": True},
                                    {"id": "jobs@group.calendar.google.com", "summary": "Tree jobs"}], NOW)
    gpage.goto(gbase + "/client/calendar"); shoot(gpage, "13-calendar-connected")
    credentials.status = real_status
    browser.close()
