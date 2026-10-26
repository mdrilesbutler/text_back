"""Candidate C: page walk, state captures and audit at desktop (1280x900) and phone (390x844@2, mobile UA).

usage: python walk_c.py <base_url> <out_dir> [--private URL] [--connected URL]

  <base_url>   the preview to walk. Read-only: the only POSTs are the two sign-in forms, once per width
               (the shared C preview allows 3 codes per number per 15 minutes).
  --private    a PRIVATE localhost copy (preview.py on a fresh data dir) for the states that POST:
               sign-in error, enter-code error, invalid mobile, confirm-new-mobile, rename offer and the
               test-calendar free-times check.
  --connected  a PRIVATE localhost copy whose app.state.calendar reports a connected Google calendar
               (picker + free times). Never contacts Google.

Writes, in the bake-off naming that tools/build_packs.py reads:
  NN-<page>-<desktop|phone>-MM.png   scroll captures      NN-<page>-<view>.txt  visible text
  state-<page>-<state>-<view>.png    states               report.json           audit per page and state
Audit per page and state: scrollWidth vs innerWidth, tap targets under 44 px (inline links inside a
sentence excluded; a hidden radio/checkbox is measured by its label), console errors, failed requests.
"""
import argparse, json, re
from pathlib import Path
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("base"); ap.add_argument("out")
ap.add_argument("--private"); ap.add_argument("--connected")
args = ap.parse_args()
BASE, OUT = args.base.rstrip("/"), Path(args.out)
OUT.mkdir(parents=True, exist_ok=True)
OWNER = "980 555 0123"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
VIEWS = {"desktop": dict(viewport={"width": 1280, "height": 900}, device_scale_factor=1),
         "phone": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                       is_mobile=True, has_touch=True, user_agent=UA)}
PAGES = [("/client/home", "03-home"), ("/client/messages", "04-messages"), ("/client/schedule", "05-schedule"),
         ("/client/calendar", "06-calendar"), ("/client/phone", "07-phone"), ("/client/account", "08-account")]
NEW_MOBILE = {"desktop": "980 555 0166", "phone": "980 555 0155"}
NEW_NAME = {"desktop": "Oak & Pine Tree Service", "phone": "Oak & Pine Arborists"}

AUDIT_JS = r"""() => {
  const de = document.documentElement;
  const shown = e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return r.width > 2 && r.height > 2 && cs.visibility !== 'hidden' && cs.display !== 'none' && !e.closest('[hidden]'); };
  const blockOf = e => { let p = e.parentElement; while (p && getComputedStyle(p).display.startsWith('inline')) p = p.parentElement; return p; };
  const inlineTextLink = e => {
    if (e.tagName !== 'A' || getComputedStyle(e).display !== 'inline') return false;
    const b = blockOf(e); return !!b && b.innerText.trim().length > e.innerText.trim().length + 3; };
  const desc = (e, r) => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') +
    (typeof e.className === 'string' && e.className ? '.' + e.className.trim().split(/\s+/).join('.') : '') +
    ' "' + (e.innerText || e.value || e.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 40) + '" ' +
    Math.round(r.width) + 'x' + Math.round(r.height);
  const small = [];
  const sel = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=switch],label';
  for (const e of document.querySelectorAll(sel)) {
    if (e.tagName === 'LABEL') {          // a label counts only as the target of a visually hidden radio/checkbox
      const c = e.control; if (!c || !['radio', 'checkbox'].includes(c.type) || shown(c)) continue;
    }
    if (!shown(e) || inlineTextLink(e)) continue;
    let r = e.getBoundingClientRect(), w = r.width, h = r.height;
    if (e.tagName === 'INPUT' && ['radio', 'checkbox'].includes(e.type)) {
      for (const l of e.labels || []) { const lr = l.getBoundingClientRect(); w = Math.max(w, lr.width); h = Math.max(h, lr.height); }
    }
    if (e.tagName !== 'LABEL' && e.closest('label') && ['radio', 'checkbox'].includes(e.type)) {
      const lr = e.closest('label').getBoundingClientRect(); w = Math.max(w, lr.width); h = Math.max(h, lr.height); }
    if (w < 44 || h < 44) small.push(desc(e, {width: w, height: h}));
  }
  const over = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect();
    return r.width > 0 && r.right > innerWidth + 1 && !e.closest('.vh') && getComputedStyle(e).position !== 'fixed'; })
    .slice(0, 8).map(e => desc(e, e.getBoundingClientRect()));
  return {title: document.title, h1: [...document.querySelectorAll('h1')].map(e => e.innerText.trim()),
          scrollWidth: de.scrollWidth, innerWidth, horizontalOverflow: de.scrollWidth > innerWidth,
          overflowing: over, brokenImages: [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.src),
          smallTapTargets: small.length, smallTapTargetList: [...new Set(small)].slice(0, 30),
          links: [...new Set([...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')))],
          text: document.body.innerText};
}"""


class Tab:
    """One browser context + page at one width, with console and network watchers."""

    def __init__(self, browser, view, base):
        self.view, self.base = view, base
        self.ctx = browser.new_context(reduced_motion="reduce", color_scheme="light", **VIEWS[view])
        self.page = self.ctx.new_page()
        self.errors, self.failed = [], []
        p = self.page
        p.on("dialog", lambda d: d.accept())          # beforeunload after unsaved edits: leave
        p.on("console", lambda m: m.type in ("error", "warning") and self.errors.append(f"{m.type}: {m.text}"))
        p.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"))
        p.on("requestfailed", lambda r: self.failed.append(f"{r.method} {r.url} {r.failure}"))
        p.on("response", lambda r: r.status >= 400 and self.failed.append(f"{r.status} {r.request.method} {r.url}"))

    def go(self, path):
        self.errors.clear(); self.failed.clear()
        resp = self.page.goto(self.base + path); self.page.wait_for_load_state("networkidle")
        return resp

    def settle(self):
        self.page.wait_for_load_state("networkidle"); self.page.wait_for_timeout(300)

    def audit(self):
        a = self.page.evaluate(AUDIT_JS)
        a["console"] = list(self.errors); a["failed_requests"] = list(self.failed)
        return a

    def shoot_scroll(self, name):
        p, vh = self.page, VIEWS[self.view]["viewport"]["height"]
        p.wait_for_timeout(400)
        h = p.evaluate("document.documentElement.scrollHeight")
        parts, y, i = [], 0, 1
        while True:
            p.evaluate(f"window.scrollTo(0, {y})"); p.wait_for_timeout(150)
            f = OUT / f"{name}-{self.view}-{i:02d}.png"; p.screenshot(path=str(f)); parts.append(f.name)
            if y + vh >= h: break
            y = min(y + vh - 120, h - vh); i += 1
        p.evaluate("window.scrollTo(0, 0)")
        return h, parts

    def page_record(self, name, resp=None):
        h, parts = self.shoot_scroll(name)
        a = self.audit()
        (OUT / f"{name}-{self.view}.txt").write_text(a.pop("text"))
        return {"final_url": self.page.url, "status": resp.status if resp else None, "height": h, "shots": parts, **a}

    def view_at(self, selector, frac=0.18):
        """Scroll so the element's top sits at `frac` of the viewport (under the sticky header)."""
        self.page.evaluate("""([s, f]) => { const e = document.querySelector(s); if (!e) return;
            const y = e.getBoundingClientRect().top + scrollY - innerHeight * f; scrollTo(0, Math.max(0, y)); }""",
                           [selector, frac])
        self.page.wait_for_timeout(250)

    def state(self, report, page_name, state_name, selector=None, frac=0.18, top=False):
        if top: self.page.evaluate("scrollTo(0, 0)"); self.page.wait_for_timeout(200)
        elif selector: self.view_at(selector, frac)
        f = OUT / f"state-{page_name}-{state_name}-{self.view}.png"
        self.page.screenshot(path=str(f))
        a = self.audit(); a.pop("text"); a.pop("links")
        report.setdefault("states", {}).setdefault(self.view, {})[f"{page_name}-{state_name}"] = {"file": f.name, "url": self.page.url, **a}
        print("  state", f.name, "overflow" if a["horizontalOverflow"] else "", len(a["console"]) or "", len(a["failed_requests"]) or "")

    def code(self):
        body = self.ctx.request.get(self.base + "/preview/code").text()
        found = re.search(r"<h1>(\d{3}) (\d{3})</h1>", body)
        assert found, f"no code on {self.base}/preview/code"
        return found.group(1) + found.group(2)

    def save(self, form_id):
        """Click the visible Save for a form: the in-flow/sticky bar, else the header save bar (phone)."""
        for sel in (f"[data-savebar] button[data-rest-save][form={form_id}]", f"button[data-rest-save][form={form_id}]",
                    f".topsave button[type=submit][form={form_id}]:not([name=discard])", ".topsave .btn--primary"):
            loc = self.page.locator(sel)
            for i in range(loc.count()):
                if loc.nth(i).is_visible():
                    loc.nth(i).click(); self.settle(); return
        raise AssertionError(f"no visible Save for {form_id}")


def sign_in(tab, log=None, shoot=False, error_states=None):
    """Sign in as the demo owner. shoot: record 01/02 pages. error_states: report dict for the code error."""
    p = tab.page
    resp = tab.go("/client/login")
    if shoot: log["01-sign-in"] = tab.page_record("01-sign-in", resp)
    p.fill("input[name=mobile]", OWNER)
    p.click("form[action^='/client/login'] button[type=submit]"); tab.settle()
    assert "/client/verify" in p.url, f"sign-in did not reach Enter code: {p.url} {p.inner_text('main')[:200]}"
    if shoot: log["02-enter-code"] = tab.page_record("02-enter-code")
    code = tab.code()
    if error_states is not None:
        wrong = f"{(int(code[0]) + 1) % 10}{code[1:]}"
        p.fill("input[name=code]", wrong)
        p.click("form[action^='/client/verify'] button[type=submit]"); tab.settle()
        tab.state(error_states, "enter-code", "error", top=True)
    p.fill("input[name=code]", code)
    p.click("form[action^='/client/verify'] button[type=submit]"); tab.settle()
    assert "/client/verify" not in p.url and "/client/login" not in p.url, f"sign-in failed: {p.url}"
    return p.url


def open_editor(tab, key):
    s = f"#card-{key} details.editor"
    if not tab.page.locator(s).evaluate("d => d.open"):
        tab.page.click(f"#card-{key} summary.editor__summary")
    tab.page.wait_for_timeout(150)


def shared_states(tab, report):
    p = tab.page
    tab.go("/client/home")
    p.click("summary.menu__trigger"); p.wait_for_timeout(250)
    tab.state(report, "home", "account-menu", top=True)

    tab.go("/client/messages")
    open_editor(tab, "prompt_location")
    tab.state(report, "messages", "edit-wording", "#card-prompt_location", 0.12)
    p.fill("#w-prompt_location", "What's the street address for the job, and is there a gate code?")
    open_editor(tab, "intro")
    p.fill("#w-intro", "Hi, it's Oak & Pine Tree Care. Sorry we missed your call! What can we help with?")
    p.wait_for_timeout(300)
    tab.state(report, "messages", "unsaved-top", top=True)
    tab.state(report, "messages", "unsaved", "#card-prompt_location", 0.12)
    tab.go("/client/messages")                            # leave without saving (dialog accepted)
    p.select_option("#scenario", "booked"); p.wait_for_timeout(200)
    tab.view_at("#example", 0.02 if tab.view == "desktop" else 0.0)
    p.evaluate("""() => { const t = document.querySelector('.thread[data-scenario="booked"]');
        const b = t && (t.querySelector('[data-preview="booking_confirmation"]') || t.querySelector('.tpill--booked'));
        const log = document.querySelector('[data-rail-log]');
        if (!b) return;
        const li = b.closest('li') || b;
        if (log && log.scrollHeight > log.clientHeight + 2) log.scrollTop = li.offsetTop - log.clientHeight / 3;
        const r = li.getBoundingClientRect();         // a phone grows the log instead: scroll the page to it
        if (r.top < 0 || r.bottom > innerHeight) scrollTo(0, Math.max(0, r.top + scrollY - innerHeight / 2)); }""")
    p.wait_for_timeout(250)
    tab.state(report, "messages", "example-booked")

    tab.go("/client/schedule")
    p.check("input[name=hours_mode][value=set]"); p.wait_for_timeout(200)
    tab.state(report, "schedule", "set-hours", "#hours", 0.1)
    p.check("input[name=hours_mode][value=any]"); p.wait_for_timeout(200)
    tab.state(report, "schedule", "any-time", "#hours", 0.1)
    tab.go("/client/schedule")
    p.click("label[for=dur-custom]"); p.fill("#appointment_duration_custom", "75"); p.wait_for_timeout(300)
    tab.state(report, "schedule", "custom-length", "#appointments", 0.1 if tab.view == "desktop" else 0.0)

    tab.go("/client/calendar")
    tab.state(report, "calendar", "not-connected", top=True)

    tab.go("/client/phone")
    p.click("label[for=carrier-verizon]"); p.wait_for_timeout(200)
    tab.state(report, "phone", "carrier-verizon", "#rule-carrier", 0.1)

    tab.go("/client/account")
    p.click("summary.confirm-inline__trigger"); p.wait_for_timeout(200)
    tab.state(report, "account", "signout-everywhere", "form[data-confirm-everywhere]", 0.3)


def private_auth_states(tab, report):
    p = tab.page
    tab.go("/client/login")
    p.fill("input[name=mobile]", "555 01")
    p.click("form[action^='/client/login'] button[type=submit]"); tab.settle()
    tab.state(report, "sign-in", "error", top=True)
    sign_in(tab, error_states=report)


def private_phone_states(tab, report):
    p = tab.page
    tab.go("/client/phone")
    p.fill("#owner_mobile", "555 12"); tab.save("phone-form")
    tab.state(report, "phone", "invalid-mobile", top=True)
    tab.state(report, "phone", "invalid-mobile-field", "#rule-owner_mobile", 0.25)
    tab.go("/client/phone")
    p.fill("#owner_mobile", NEW_MOBILE[tab.view]); tab.save("phone-form")
    assert "Confirm your new mobile" in p.inner_text("h1"), p.inner_text("main")[:300]
    tab.state(report, "phone", "confirm-new-mobile", top=True)
    p.click("[data-keep]"); tab.settle()
    tab.go("/client/calendar")
    p.click("form[action^='/client/calendar'] input[value=check] ~ button"); tab.settle()
    tab.state(report, "calendar", "not-connected-free-times", "#availability", 0.12)


def private_rename_state(tab, report):
    p = tab.page
    tab.go("/client/phone")
    p.fill("#business_name", NEW_NAME[tab.view]); tab.save("phone-form")
    assert p.locator("[data-rename-offer]").count(), "no rename offer after a new business name"
    tab.state(report, "phone", "rename-offer", top=True)
    p.click("form[action^='/client/phone/rename-texts'] button[value=update]"); tab.settle()


def connected_states(tab, report):
    p = tab.page
    tab.go("/client/calendar")
    tab.state(report, "calendar", "connected", top=True)
    p.click("summary.picker__summary"); p.wait_for_timeout(200)
    tab.state(report, "calendar", "connected-picker", "#connection", 0.08)
    p.click("form[action^='/client/calendar'] input[value=check] ~ button"); tab.settle()
    tab.state(report, "calendar", "connected-free-times", "#availability", 0.12)


def main():
    report = {"base": BASE, "private": args.private, "connected": args.connected}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for view in VIEWS:
            print("walk", view)
            tab = Tab(browser, view, BASE)
            log = report.setdefault(view, {})
            log["landing_after_sign_in"] = sign_in(tab, log, shoot=True)
            discovered = set()
            for path, name in PAGES:
                resp = tab.go(path)
                rec = tab.page_record(name, resp)
                discovered.update(l for l in rec["links"] if l.startswith("/client"))
                log[name] = rec
                print(f"  {name}: {rec['status']} sw={rec['scrollWidth']}/{rec['innerWidth']} small={rec['smallTapTargets']} "
                      f"console={len(rec['console'])} failed={len(rec['failed_requests'])}")
            log["link_status"] = {l: tab.ctx.request.get(BASE + l, max_redirects=0).status
                                  for l in sorted(discovered) if not l.startswith("/client/logout")}
            shared_states(tab, report)
            tab.ctx.close()
        if args.private:
            tabs = {v: Tab(browser, v, args.private.rstrip("/")) for v in VIEWS}
            for v, tab in tabs.items(): print("private auth", v); private_auth_states(tab, report)
            for v, tab in tabs.items(): print("private phone", v); private_phone_states(tab, report)
            for v, tab in tabs.items(): print("private rename", v); private_rename_state(tab, report)
            for tab in tabs.values(): tab.ctx.close()
        if args.connected:
            for v in VIEWS:
                print("connected", v)
                tab = Tab(browser, v, args.connected.rstrip("/"))
                sign_in(tab); connected_states(tab, report); tab.ctx.close()
        browser.close()
    (OUT / "report.json").write_text(json.dumps(report, indent=1))
    pages = ["01-sign-in", "02-enter-code"] + [n for _, n in PAGES]
    print(json.dumps({v: {n: [report[v][n].get("status"), f"{report[v][n]['scrollWidth']}/{report[v][n]['innerWidth']}",
                              report[v][n]["smallTapTargets"], len(report[v][n]["console"]), len(report[v][n]["failed_requests"])]
                          for n in pages} for v in VIEWS}, indent=1))
    print("links:", json.dumps({v: report[v]["link_status"] for v in VIEWS}))


main()
