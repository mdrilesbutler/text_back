"""Capture static HTML mockups the way walk.py captures a live portal.

usage: capture_static.py <mockup_dir> <out_dir>
Every <mockup_dir>/NN-<page>.html is shot at 1280x900 and 390x844@2 with overlapping scroll
positions, plus its visible text. Files named NN-<page>--<state>.html are shot as
state-<page>-<state>-<view>.png (one screen, scrolled to the element with id="focus" if present).
Audits sideways scroll and small tap targets exactly like walk.py.
"""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SRC, OUT = Path(sys.argv[1]).resolve(), Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
VIEWS = {"desktop": dict(viewport={"width": 1280, "height": 900}, device_scale_factor=1),
         "phone": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                       user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
                                  "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")}
AUDIT = """() => {
  const de = document.documentElement;
  const over = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > innerWidth + 1; })
    .slice(0, 5).map(e => e.tagName.toLowerCase() + (typeof e.className === 'string' && e.className ? '.' + e.className.split(' ')[0] : ''));
  const small = [...document.querySelectorAll('a,button,input,select,textarea,[role=switch],[role=tab]')].filter(e => {
    const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && (r.height < 44 || r.width < 44) && cs.visibility !== 'hidden' && e.type !== 'hidden' && e.type !== 'checkbox' && e.type !== 'radio'; })
    .slice(0, 12).map(e => (e.id ? '#' + e.id : e.tagName.toLowerCase() + (typeof e.className === 'string' && e.className ? '.' + e.className.split(' ')[0] : '')) + ' ' + Math.round(e.getBoundingClientRect().width) + 'x' + Math.round(e.getBoundingClientRect().height));
  const sticky = [...document.querySelectorAll('body *')].filter(e => { const p = getComputedStyle(e).position; return (p === 'sticky' || p === 'fixed') && e.getBoundingClientRect().height > 0; })
    .map(e => (e.id ? '#' + e.id : e.tagName.toLowerCase() + (typeof e.className === 'string' && e.className ? '.' + e.className.split(' ')[0] : '')) + ':' + Math.round(e.getBoundingClientRect().height));
  return {title: document.title, scrollWidth: de.scrollWidth, innerWidth, overflowing: over, smallTapTargets: small, sticky, text: document.body.innerText};
}"""

def shoot(page, name, view):
    page.wait_for_timeout(300)
    h = page.evaluate("document.documentElement.scrollHeight"); vh = VIEWS[view]["viewport"]["height"]
    parts, y, i = [], 0, 1
    while True:
        page.evaluate(f"window.scrollTo(0, {y})"); page.wait_for_timeout(120)
        f = OUT / f"{name}-{view}-{i:02d}.png"; page.screenshot(path=str(f)); parts.append(f.name)
        if y + vh >= h: break
        y = min(y + vh - 120, h - vh); i += 1
    page.evaluate("window.scrollTo(0, 0)")
    return h, parts

report = {}
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for view, opts in VIEWS.items():
        ctx = browser.new_context(reduced_motion="reduce", color_scheme="light", **opts); page = ctx.new_page()
        log = report.setdefault(view, {})
        for html in sorted(SRC.glob("*.html")):
            if html.name.startswith("_"): continue
            page.goto(html.as_uri()); page.wait_for_load_state("networkidle")
            if "--" in html.stem:
                base, state = html.stem.split("--", 1)
                name = f"state-{base.split('-', 1)[1] if '-' in base else base}-{state}"
                page.wait_for_timeout(300)
                if page.locator("#focus").count():
                    page.locator("#focus").first.scroll_into_view_if_needed(); page.wait_for_timeout(150)
                f = OUT / f"{name}-{view}.png"; page.screenshot(path=str(f)); parts, h = [f.name], None
            else:
                name = html.stem; h, parts = shoot(page, name, view)
            a = page.evaluate(AUDIT)
            (OUT / f"{name}-{view}.txt").write_text(a.pop("text"))
            log[html.name] = {"height": h, "shots": parts, **a}
        ctx.close()
    browser.close()
(OUT / "report.json").write_text(json.dumps(report, indent=1))
for view, pages in report.items():
    for n, d in pages.items():
        flags = []
        if d["scrollWidth"] > d["innerWidth"]: flags.append(f"SIDEWAYS {d['scrollWidth']}>{d['innerWidth']} {d['overflowing']}")
        if d["smallTapTargets"]: flags.append(f"SMALL {d['smallTapTargets']}")
        print(view, n, d["height"], "ok" if not flags else "; ".join(flags), "sticky=" + ",".join(d["sticky"]))
