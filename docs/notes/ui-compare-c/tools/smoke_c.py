"""Candidate C save checks on PRIVATE localhost copies: change, Save, screenshot the notice, reload, check it stuck.

usage: python smoke_c.py <desktop_base> <phone_base> <out_dir>
Give each width its own fresh copy (preview.py on an empty data dir, 127.0.0.1, port 8799+), so both start
from the same saved state; the same URL twice also works. Never point this at the shared preview: it saves.
Writes save-NN-<what>-<desktop|phone>.png (right after each save) and smoke.json; prints PASS/FAIL per check.
"""
import json, re, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASES = {"desktop": sys.argv[1].rstrip("/"), "phone": sys.argv[2].rstrip("/")}
OUT = Path(sys.argv[3]); OUT.mkdir(parents=True, exist_ok=True)
for b in BASES.values():
    assert re.match(r"http://(127\.0\.0\.1|localhost):(\d+)", b) and int(b.rsplit(":", 1)[1]) not in (8000, 8443, 8765, 8003, 8766), b
OWNER = "980 555 0123"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
VIEWS = {"desktop": dict(viewport={"width": 1280, "height": 900}, device_scale_factor=1),
         "phone": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, user_agent=UA)}
RUN = time.strftime("%H%M%S")
NEW = {"desktop": dict(name="Oak & Pine Tree Service", help="(704) 555-0188", mobile="980 555 0166"),
       "phone": dict(name="Oak & Pine Arborists", help="(704) 555-0187", mobile="980 555 0155")}
results = []
digits = lambda s: re.sub(r"\D", "", s or "")[-10:]


def check(view, name, ok, detail=""):
    results.append({"view": view, "check": name, "result": "PASS" if ok else "FAIL", "detail": detail})


class Tab:
    def __init__(self, browser, view):
        self.view, self.base, self.n = view, BASES[view], 0
        self.ctx = browser.new_context(reduced_motion="reduce", color_scheme="light", **VIEWS[view])
        self.p = self.ctx.new_page()
        self.errors = []
        self.p.on("dialog", lambda d: d.accept())
        self.p.on("pageerror", lambda e: self.errors.append(str(e)))
        self.p.on("console", lambda m: m.type == "error" and self.errors.append(m.text))

    def go(self, path):
        self.p.goto(self.base + path); self.p.wait_for_load_state("networkidle")

    def settle(self):
        self.p.wait_for_load_state("networkidle"); self.p.wait_for_timeout(250)

    def shot(self, what):
        self.n += 1
        self.p.evaluate("scrollTo(0, 0)"); self.p.wait_for_timeout(150)
        f = OUT / f"save-{self.n:02d}-{what}-{self.view}.png"; self.p.screenshot(path=str(f)); return f.name

    def notice(self):
        return " ".join(self.p.locator("#notice").inner_text().split())[:300]

    def save(self, form_id):
        """The visible Save for this form: the in-flow/sticky save bar, else the header save bar (phone)."""
        for sel in (f"[data-savebar] button[data-rest-save][form={form_id}]", f"button[data-rest-save][form={form_id}]",
                    f".topsave button[type=submit][form={form_id}]:not([name=discard])", ".topsave .btn--primary"):
            loc = self.p.locator(sel)
            for i in range(loc.count()):
                if loc.nth(i).is_visible():
                    loc.nth(i).click(); self.settle(); return sel
        raise AssertionError(f"no visible Save for {form_id}")

    def sign_in(self):
        self.go("/client/login")
        self.p.fill("input[name=mobile]", OWNER)
        self.p.click("form[action='/client/login'] button[type=submit]"); self.settle()
        body = self.ctx.request.get(self.base + "/preview/code").text()
        code = "".join(re.search(r"<h1>(\d{3}) (\d{3})</h1>", body).groups())
        self.p.fill("input[name=code]", code)
        self.p.click("form[action='/client/verify'] button[type=submit]"); self.settle()
        assert "/client/home" in self.p.url, self.p.url


def run(tab):
    p, v, new = tab.p, tab.view, NEW[tab.view]

    # 1. Messages: prompt_location wording
    tab.go("/client/messages")
    p.click("#card-prompt_location summary.editor__summary")
    text = f"What's the street address for the job? ({v} {RUN})"
    p.fill("#w-prompt_location", text)
    used = tab.save("messages-form"); f = tab.shot("messages-wording"); note = tab.notice()
    tab.go("/client/messages")
    got = p.input_value("#w-prompt_location")
    check(v, "messages prompt_location persists", got == text, f"save={used!r} notice={note!r} shot={f}")

    # 2. Schedule: appointment length 90
    tab.go("/client/schedule")
    before = p.input_value("#appointment_duration_custom")
    p.click("label[for=dur-90]")
    used = tab.save("schedule-form"); f = tab.shot("schedule-length-90"); note = tab.notice()
    tab.go("/client/schedule")
    got = p.input_value("#appointment_duration_custom")
    check(v, "appointment length 90 persists", got == "90" and p.is_checked("#dur-90"),
          f"before={before} after={got} notice={note!r} shot={f}")

    # 3. Phone: business name -> rename offer -> Update them -> texts updated
    tab.go("/client/phone")
    old_name = p.input_value("#business_name")
    p.fill("#business_name", new["name"])
    tab.save("phone-form"); f = tab.shot("business-name-rename-offer"); note = tab.notice()
    offer = p.locator("[data-rename-offer]")
    offered = offer.count() == 1
    check(v, "business name save shows the rename offer", offered, f"notice={note!r} shot={f}")
    if offered:
        p.click("form[action='/client/phone/rename-texts'] button[value=update]"); tab.settle()
        f = tab.shot("rename-texts-updated"); note = tab.notice()
        tab.go("/client/messages")
        intro = p.input_value("#w-intro")
        check(v, "Update them rewrites the texts", new["name"] in intro and old_name not in intro,
              f"notice={note!r} intro={intro!r} shot={f}")
    tab.go("/client/phone")
    check(v, "business name persists", p.input_value("#business_name") == new["name"], p.input_value("#business_name"))

    # 4. Phone: HELP number
    p.fill("#business_contact", new["help"])
    tab.save("phone-form"); f = tab.shot("help-number"); note = tab.notice()
    tab.go("/client/phone")
    got = p.input_value("#business_contact")
    check(v, "HELP number persists", digits(got) == digits(new["help"]), f"got={got!r} notice={note!r} shot={f}")

    # 5. Phone: a manual forwarding tick
    boxes = p.locator(".check input.checkbox")
    target = next((boxes.nth(i).get_attribute("id") for i in range(boxes.count()) if not boxes.nth(i).is_checked()), None)
    if target is None:
        check(v, "forwarding manual tick persists", False, "no unticked manual check to tick")
    else:
        p.check(f"#{target}")
        tab.save("phone-form"); f = tab.shot("forwarding-tick"); note = tab.notice()
        tab.go("/client/phone")
        check(v, "forwarding manual tick persists", p.is_checked(f"#{target}"), f"{target} notice={note!r} shot={f}")

    # 6. Phone: owner mobile -> confirm step -> Keep my current mobile
    saved_mobile = p.input_value("#owner_mobile")
    p.fill("#owner_mobile", new["mobile"])
    tab.save("phone-form"); f = tab.shot("owner-mobile-confirm-step")
    h1 = p.inner_text("h1")
    check(v, "owner-mobile change opens the confirm step", "Confirm your new mobile" in h1, f"h1={h1!r} shot={f}")
    if p.locator("[data-keep]").count():
        p.click("[data-keep]"); tab.settle(); f = tab.shot("keep-current-mobile"); note = tab.notice()
        tab.go("/client/phone")
        ok = p.locator("#owner_mobile").count() == 1 and digits(p.input_value("#owner_mobile")) == digits(saved_mobile)
        check(v, "Keep my current mobile keeps it", ok, f"mobile={p.input_value('#owner_mobile') if ok else p.url!r} notice={note!r} shot={f}")

    # 7. Account: remember toggle
    tab.go("/client/account")
    was = p.is_checked("#remember")
    p.click("label[for=remember]")
    used = tab.save("account-form"); f = tab.shot("account-remember"); note = tab.notice()
    tab.go("/client/account")
    now = p.is_checked("#remember")
    check(v, "remember toggle persists", now == (not was), f"was={was} now={now} notice={note!r} shot={f}")
    check(v, "no console errors during the checks", not tab.errors, "; ".join(tab.errors)[:300])


with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for view in VIEWS:
        tab = Tab(browser, view)
        tab.sign_in()
        try:
            run(tab)
        except Exception as exc:  # a broken step is a FAIL, not a crash; keep the other width
            tab.shot("error")
            check(view, "smoke run completed", False, f"{type(exc).__name__}: {exc}"[:300])
        tab.ctx.close()
    browser.close()
(OUT / "smoke.json").write_text(json.dumps(results, indent=1))
for r in results:
    print(r["result"], "|", r["view"], "|", r["check"], "|", r["detail"])
print(f"{sum(r['result'] == 'PASS' for r in results)}/{len(results)} PASS")
