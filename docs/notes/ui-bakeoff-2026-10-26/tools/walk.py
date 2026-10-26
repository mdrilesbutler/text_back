"""Walk every /client page of one portal preview at desktop and phone width.

usage: python walk.py <base_url> <out_dir> <page paths comma-separated>
Signs in as the demo owner (980 555 0123) by reading /preview/code, so no SMS is sent.
Read-only on the preview: only the sign-in form is submitted.
"""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE, OUT = sys.argv[1].rstrip("/"), Path(sys.argv[2])
PAGES = [p.split("=") for p in sys.argv[3].split(",") if p]
OUT.mkdir(parents=True, exist_ok=True)
VIEWS = {"desktop": dict(viewport={"width": 1280, "height": 900}, device_scale_factor=1),
         "phone": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                       is_mobile=True, has_touch=True,
                       user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
                                  "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")}
CHUNK = {"desktop": 1800, "phone": 1400}


def slug(path):
    s = path.strip("/").replace("client", "", 1).strip("/").replace("/", "-")
    return s or "home"


def shoot(page, name, view):
    page.wait_for_timeout(400)
    h = page.evaluate("document.documentElement.scrollHeight")
    vh = VIEWS[view]["viewport"]["height"]
    parts, y, i = [], 0, 1
    while True:
        page.evaluate(f"window.scrollTo(0, {y})"); page.wait_for_timeout(150)
        f = OUT / f"{name}-{view}-{i:02d}.png"
        page.screenshot(path=str(f)); parts.append(f.name)
        if y + vh >= h: break
        y = min(y + vh - 120, h - vh); i += 1
    page.evaluate("window.scrollTo(0, 0)")
    return h, parts


def audit(page, ctx):
    return page.evaluate("""() => {
      const de = document.documentElement;
      const over = [...document.querySelectorAll('body *')].filter(e => {
        const r = e.getBoundingClientRect(); return r.width > 0 && r.right > innerWidth + 1;
      }).slice(0, 5).map(e => e.tagName.toLowerCase() + (e.className && typeof e.className === 'string' ? '.' + e.className.split(' ')[0] : ''));
      const imgs = [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.src);
      const links = [...new Set([...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href')))];
      const h1 = [...document.querySelectorAll('h1')].map(e => e.innerText.trim());
      const small = [...document.querySelectorAll('a,button,input,select,textarea,[role=switch]')].filter(e => {
        const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.height < 32 || r.width < 32) && getComputedStyle(e).visibility !== 'hidden';
      }).length;
      return {title: document.title, h1, scrollWidth: de.scrollWidth, innerWidth, overflowing: over,
              brokenImages: imgs, links, smallTapTargets: small, text: document.body.innerText};
    }""")


def sign_in(page, view, log):
    page.goto(BASE + "/client/login"); page.wait_for_load_state("networkidle")
    h, parts = shoot(page, "01-sign-in", view); log["login"] = {"height": h, "shots": parts}
    page.fill("input[name=mobile]", "980 555 0123")
    page.click("form[action='/client/login'] button[type=submit]")
    page.wait_for_load_state("networkidle")
    h, parts = shoot(page, "02-enter-code", view); log["verify"] = {"url": page.url, "height": h, "shots": parts}
    verify_url = page.url
    page.goto(BASE + "/preview/code")
    code = re.sub(r"\D", "", page.inner_text("h1"))
    assert len(code) == 6, f"no code on /preview/code: {page.inner_text('body')[:300]}"
    page.goto(verify_url)
    page.fill("input[name=code]", code)
    page.click("form[action='/client/verify'] button[type=submit]")
    page.wait_for_load_state("networkidle")
    log["landing_after_sign_in"] = page.url


def main():
    report = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for view, opts in VIEWS.items():
            ctx = browser.new_context(reduced_motion="reduce", color_scheme="light", **opts)
            page = ctx.new_page()
            errors, failed = [], []
            page.on("console", lambda m: m.type in ("error", "warning") and errors.append(f"{m.type}: {m.text}"))
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
            page.on("requestfailed", lambda r: failed.append(f"{r.method} {r.url} {r.failure}"))
            page.on("response", lambda r: r.status >= 400 and failed.append(f"{r.status} {r.request.method} {r.url}"))
            log = report.setdefault(view, {})
            sign_in(page, view, log)
            discovered = set()
            for path, name in PAGES:
                errors.clear(); failed.clear()
                resp = page.goto(BASE + path); page.wait_for_load_state("networkidle")
                h, parts = shoot(page, name, view)
                a = audit(page, ctx)
                discovered.update(l for l in a["links"] if l.startswith("/client"))
                (OUT / f"{name}-{view}.txt").write_text(a.pop("text"))
                log[path] = {"final_url": page.url, "status": resp.status if resp else None, "height": h,
                             "shots": parts, "console": list(errors), "failed_requests": list(failed), **a}
            # link check: every same-origin /client link seen anywhere, GET only
            checks = {}
            for l in sorted(discovered):
                if l.startswith("/client/logout"):
                    continue
                r = ctx.request.get(BASE + l, max_redirects=0)
                checks[l] = r.status
            log["link_status"] = checks
            ctx.close()
        browser.close()
    (OUT / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({v: {p: (d.get("status"), d.get("final_url"), d.get("scrollWidth"), len(d.get("console", [])), len(d.get("failed_requests", [])))
                          for p, d in r.items() if isinstance(d, dict) and "status" in d} for v, r in report.items()}, indent=1))
    print("links:", json.dumps({v: r["link_status"] for v, r in report.items()}))
    print("landing:", {v: r["landing_after_sign_in"] for v, r in report.items()})


main()
