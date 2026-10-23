"""Screenshot every /client screen and state for review.

Run from the worktree root:
    .venv/bin/python docs/notes/ui-compare-a/screenshots.py <empty temp dir>

Each state is captured at 375px and 1024px wide, full page, device scale 2,
in light and dark (prefers-color-scheme emulation), as
docs/notes/ui-compare-a/<state>-<width>-<theme>.png.

Two throwaway apps run on 127.0.0.1 with FakeTelecom, so no SMS is sent:
app 1 uses the stub calendar (test mode); app 2 is the Google fixture from
tests/test_client_settings.py, patched into reconnect needed, could not be
read, and connected. Timers are frozen with Playwright's clock so toasts stay
on screen; the viewport is stretched to the page height before each shot so
fixed bars (tab bar, save bar) sit at the bottom as they do on a phone.

The styleguide is too tall for one capture (Chromium leaves tiles blank past
about 16k device pixels), so it is shot as 14-styleguide-00-top-<width>-<theme>
plus one file per section, 14-styleguide-NN-<section>[-partK]-<width>.png, cut
into chunks of at most 3,600 CSS px. Every section already draws a light and a
dark panel side by side (stacked on a phone), so sections are shot once per width.
"""
import json, os, re, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

sys.path.insert(0, "tests")
from text_back.app import create_app  # noqa: E402
from text_back.telecom import FakeTelecom  # noqa: E402
from test_client_settings import google_fixture  # noqa: E402

OUT = Path("docs/notes/ui-compare-a"); OUT.mkdir(parents=True, exist_ok=True)
TMP = Path(sys.argv[1]); TMP.mkdir(parents=True, exist_ok=True)
NOW = datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc)
OWNER = "+19805550123"
PORT_A, PORT_G = 8781, 8782
WIDTHS = {375: 812, 1024: 900}
THEMES = ("light", "dark")
ONLY = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None  # optional: shoot only these states


def serve(app, port):
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    return server


# App 1: stub calendar (test mode), editable messages, one customized message, email question on.
os.environ["TEXT_BACK_OWNER_MOBILE"] = OWNER
messages = TMP / "messages.json"
messages.write_text(json.dumps({
    "intro": "Hey, this is Oak & Pine Tree Care. Sorry we missed your call. What do you need done?",
    "fields": "service, location, preferred_time, name, email",
}))
os.environ["TEXT_BACK_MESSAGES_FILE"] = str(messages)
telecom = FakeTelecom()
app = create_app(db_path=str(TMP / "a.db"), telecom=telecom, public_base_url=f"http://127.0.0.1:{PORT_A}",
                 business_name="Oak & Pine Tree Care", now_provider=lambda: NOW)
app.state.business_number = "+17045550100"
serve(app, PORT_A)


# App 2: Google calendar in its real states.
class MP:  # the test fixture wants a monkeypatch; the env is already set
    def setenv(self, k, v): os.environ[k] = v
    def delenv(self, k, raising=True): os.environ.pop(k, None)


(TMP / "g").mkdir(exist_ok=True)
gclient, gtelecom, credentials, transport = google_fixture(TMP / "g", MP())
gapp = gclient.app
gapp.state.public_base_url = f"http://127.0.0.1:{PORT_G}"
serve(gapp, PORT_G)


def code(tel):
    return re.search(r"\b(\d{6})\b", [m for m in tel.outbound if m.kind == "login_code"][-1].body).group(1)


def settle(page, ms=300):
    """Let JS timers (debounces, not toast lifetimes) and CSS transitions finish."""
    try:
        page.clock.run_for(ms)
    except Exception:
        pass
    page.wait_for_timeout(ms)


def shoot(page, name):
    if ONLY and name not in ONLY:
        return
    for theme in THEMES:
        page.emulate_media(color_scheme=theme)
        for width, height in WIDTHS.items():
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(150)
            full = page.evaluate("Math.ceil(document.documentElement.scrollHeight)")
            page.set_viewport_size({"width": width, "height": max(height, full)})
            page.wait_for_timeout(150)
            # A second pass: some layouts (100dvh sidebar) grow with the viewport.
            full2 = page.evaluate("Math.ceil(document.documentElement.scrollHeight)")
            if full2 > full:
                page.set_viewport_size({"width": width, "height": full2})
                page.wait_for_timeout(100)
            page.screenshot(path=str(OUT / f"{name}-{width}-{theme}.png"), full_page=True)
            page.set_viewport_size({"width": width, "height": height})
    page.emulate_media(color_scheme="light")
    print("shot", name, flush=True)


def shoot_styleguide(page):
    if ONLY and "14-styleguide" not in ONLY:
        return
    for theme in THEMES:  # the top of the page in both themes
        page.emulate_media(color_scheme=theme)
        for width, height in WIDTHS.items():
            page.set_viewport_size({"width": width, "height": height})
            page.evaluate("window.scrollTo(0, 0)"); page.wait_for_timeout(150)
            page.screenshot(path=str(OUT / f"14-styleguide-00-top-{width}-{theme}.png"))
    page.emulate_media(color_scheme="light")
    chunk = 3600
    for width, height in WIDTHS.items():
        page.set_viewport_size({"width": width, "height": height}); page.wait_for_timeout(200)
        boxes = page.evaluate("""() => [...document.querySelectorAll('section.sg-section')].map(s => {
            const r = s.getBoundingClientRect();
            return [s.id.replace(/^sg-/, ''), r.top + window.scrollY, r.height]; })""")
        for n, (sid, top, h) in enumerate(boxes, start=1):
            parts = max(1, -(-int(h) // chunk))
            for k in range(parts):
                y = top + k * chunk
                clip = {"x": 0, "y": y, "width": width, "height": min(chunk, top + h - y)}
                suffix = f"-part{k + 1}" if parts > 1 else ""
                page.screenshot(path=str(OUT / f"14-styleguide-{n:02d}-{sid}{suffix}-{width}.png"),
                                clip=clip, full_page=True)
    print("shot 14-styleguide", flush=True)


def sign_in(page, base, tel):
    page.goto(base + "/client/login")
    page.fill("#mobile", "980 555 0123")
    page.click("form[action='/client/login'] button[type=submit]")
    page.wait_for_url(base + "/client/verify")
    page.fill("#code", code(tel))
    page.click("form[action='/client/verify'] button[type=submit]")
    page.wait_for_url(base + "/client/messages")


def open_editor(page, key):
    page.click(f"#m_{key} .editor__summary")
    page.wait_for_selector(f"#f_{key}", state="visible")


with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 375, "height": 812}, device_scale_factor=2)
    page = ctx.new_page()
    page.clock.install(time=NOW)
    page.on("dialog", lambda d: d.accept())
    base = f"http://127.0.0.1:{PORT_A}"

    page.goto(base + "/client/login"); settle(page); shoot(page, "01-signin")
    page.fill("#mobile", "980 555 0123")
    page.click("form[action='/client/login'] button[type=submit]")
    page.wait_for_url(base + "/client/verify"); settle(page); shoot(page, "02-enter-code")
    page.fill("#code", code(telecom))
    page.click("form[action='/client/verify'] button[type=submit]")
    page.wait_for_url(base + "/client/messages"); settle(page); shoot(page, "03-messages")

    # Editing with unsaved changes: two cards changed, a placeholder chip inserted at the cursor.
    open_editor(page, "prompt_name")
    page.fill("#f_prompt_name", "Last one: what name should ")
    page.click("#m_prompt_name [data-insert]")
    page.type("#f_prompt_name", " put the job under?")
    open_editor(page, "prompt_service")
    page.fill("#f_prompt_service", "What do you need done? Removal, trimming, or stump grinding?")
    settle(page); shoot(page, "04-messages-editing-unsaved")

    # A rejected save: the reason lands beside the message that caused it.
    page.click("[data-discard]") if page.locator("[data-discard]").is_visible() else None
    settle(page)
    open_editor(page, "handoff_ack")
    page.fill("#f_handoff_ack", "Paused. Call our business line.")
    page.click("[data-save]")
    page.wait_for_selector(".msg--invalid"); settle(page); shoot(page, "05-messages-rejected-save")

    # A good save: the toast confirms it.
    open_editor(page, "handoff_ack") if not page.locator("#f_handoff_ack").is_visible() else None
    page.fill("#f_handoff_ack", "Got it, automated scheduling is paused. The owner will follow up with you directly.")
    page.click("[data-save]")
    page.wait_for_selector("[data-toast]"); settle(page); shoot(page, "06-messages-saved")

    page.goto(base + "/client/business"); settle(page); shoot(page, "07-business")
    page.fill("#owner_mobile", "980 555 0199")
    page.click("form[action='/client/business'] button[type=submit]")
    page.wait_for_selector("[data-stepper] [aria-current=step]"); settle(page)
    shoot(page, "08-business-confirm-new-mobile")
    page.click("[data-cancel]"); page.wait_for_load_state()

    page.goto(base + "/client/calendar"); settle(page); shoot(page, "09-calendar-test-mode")

    page.goto(base + "/client/styleguide"); settle(page); shoot_styleguide(page)

    # The CSRF-expired page (a stale tab): submit the form with a forged token, skipping JS handlers.
    page.goto(base + "/client/messages"); settle(page)
    page.evaluate("""() => { const f = document.querySelector('form#messages');
                             f.querySelector('input[name=csrf]').value = 'x'; f.submit(); }""")
    page.wait_for_load_state(); settle(page); shoot(page, "15-page-expired")

    # JS off: the same Messages page must still work.
    nojs = browser.new_context(viewport={"width": 375, "height": 812}, device_scale_factor=2,
                               java_script_enabled=False)
    npage = nojs.new_page(); sign_in(npage, base, telecom); shoot(npage, "10-messages-javascript-off")

    # Google calendar states on app 2.
    gbase = f"http://127.0.0.1:{PORT_G}"
    gpage = ctx.new_page(); gpage.clock.install(time=NOW); sign_in(gpage, gbase, gtelecom)
    gpage.goto(gbase + "/client/calendar"); settle(gpage); shoot(gpage, "11-calendar-reconnect-needed")
    from text_back.calendars.protocol import CalendarProviderError
    real_status = credentials.status
    credentials.status = lambda: (_ for _ in ()).throw(CalendarProviderError("x"))
    gpage.goto(gbase + "/client/calendar"); settle(gpage); shoot(gpage, "12-calendar-could-not-be-read")
    credentials.status = lambda: "ready"
    from text_back.client_settings import remember_calendars
    remember_calendars(gapp.state, [{"id": "owner@example.test", "summary": "Personal", "primary": True},
                                    {"id": "jobs@group.calendar.google.com", "summary": "Tree jobs"}], NOW)
    gpage.goto(gbase + "/client/calendar"); settle(gpage); shoot(gpage, "13-calendar-connected")
    credentials.status = real_status
    browser.close()
