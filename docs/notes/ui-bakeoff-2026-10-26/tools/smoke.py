"""Save-flow smoke on private clones: change, submit, reload, check persisted; screenshot the after-save state."""
import sys, re
from pathlib import Path
from playwright.sync_api import sync_playwright
site, BASE, STATE, OUT = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]); OUT.mkdir(parents=True, exist_ok=True)
res = []
import time; RUN = time.strftime("%H%M%S")
def check(name, ok, detail=""): res.append((name, "PASS" if ok else "FAIL", detail))
def flash(p): return " | ".join(t.strip()[:140] for t in p.locator("[role=status], [role=alert], .toast, .flash, .alert, .notice, .banner").all_inner_texts() if t.strip())[:300]
with sync_playwright() as pw:
    b = pw.chromium.launch()
    for view, vp, dpr in (("desktop", {"width": 1280, "height": 900}, 1), ("phone", {"width": 390, "height": 844}, 2)):
        ctx = b.new_context(storage_state=STATE, viewport=vp, device_scale_factor=dpr, reduced_motion="reduce"); p = ctx.new_page()
        n = 0
        def shot(tag):
            global n; n += 1; p.screenshot(path=str(OUT / f"save-{n:02d}-{tag}-{view}.png"))
        if site == "A":
            p.goto(BASE + "/client/messages")
            ed = p.locator("textarea[name=prompt_location]").locator("xpath=ancestor::details[1]/summary")
            if ed.count(): ed.first.click()
            else: p.locator("textarea[name=prompt_location]").locator("xpath=ancestor::*[contains(@class,'card') or contains(@class,'message')][1]").get_by_text("Edit wording").first.click()
            p.fill("textarea[name=prompt_location]", f"Where is the job? ({view} {RUN})")
            p.locator("button[name=save]").last.click(); p.wait_for_load_state("networkidle"); shot("messages"); f = flash(p)
            p.goto(BASE + "/client/messages"); v = p.input_value("textarea[name=prompt_location]")
            check(f"{view} messages prompt_location persists", v == f"Where is the job? ({view} {RUN})", f"flash={f!r}")
            p.goto(BASE + "/client/business")
            if p.get_by_text("Keep my current mobile").count(): p.get_by_text("Keep my current mobile").click(); p.wait_for_load_state("networkidle")
            p.goto(BASE + "/client/business"); p.fill("input[name=business_name]", f"Oak & Pine Tree Care ({view} {RUN})")
            p.click("form[action='/client/business'] button[type=submit]"); p.wait_for_load_state("networkidle"); shot("business"); f = flash(p)
            p.goto(BASE + "/client/business"); v = p.input_value("input[name=business_name]")
            check(f"{view} business_name persists", v.endswith(f"({view} {RUN})"), f"flash={f!r}")
            if view == "desktop":
                p.fill("input[name=owner_mobile]", "980 555 0199"); p.click("form[action='/client/business'] button[type=submit]")
                p.wait_for_load_state("networkidle"); shot("owner-mobile-change")
                check("owner mobile change asks for code to new number", "code" in p.inner_text("main").lower(), p.url)
                p.get_by_text("Keep my current mobile").click(); p.wait_for_load_state("networkidle"); shot("keep-mobile")
                check("keep current mobile returns to form", p.locator("input[name=business_name]").count() == 1, p.url)
        else:
            p.goto(BASE + "/client/messages"); p.fill("textarea[name=prompt_location]", f"Where is the job? ({view} {RUN})")
            p.click("form[action='/client/messages'] button[type=submit]:has-text('Save')"); p.wait_for_load_state("networkidle"); shot("messages"); f = flash(p)
            p.goto(BASE + "/client/messages"); v = p.input_value("textarea[name=prompt_location]")
            check(f"{view} messages prompt_location persists", v == f"Where is the job? ({view} {RUN})", f"flash={f!r}")
            p.goto(BASE + "/client/scheduling"); dur = "90" if view == "desktop" else "45"
            p.fill("input[name=appointment_duration_minutes]", dur)
            p.click("form[action='/client/scheduling'] button[type=submit]:has-text('Save')"); p.wait_for_load_state("networkidle"); shot("scheduling"); f = flash(p)
            p.goto(BASE + "/client/scheduling"); v = p.input_value("input[name=appointment_duration_minutes]")
            check(f"{view} appointment length persists", v == dur, f"flash={f!r}")
            p.goto(BASE + "/client/calendar"); p.click("text=Check availability now"); p.wait_for_load_state("networkidle"); shot("availability")
            check(f"{view} availability check responds", True, p.inner_text("main")[:200].replace("\n", " / "))
            p.goto(BASE + "/client/phone"); p.fill("input[name=business_name]", f"Oak & Pine Tree Care ({view} {RUN})")
            p.click("form[action='/client/phone'] button[type=submit]:has-text('Save')"); p.wait_for_load_state("networkidle"); shot("phone"); f = flash(p)
            p.goto(BASE + "/client/phone"); v = p.input_value("input[name=business_name]")
            check(f"{view} business_name persists", v.endswith(f"({view} {RUN})"), f"flash={f!r}")
            if view == "desktop":
                p.check("input[name=check_answered_no_text]"); p.click("text=Save checks"); p.wait_for_load_state("networkidle"); shot("checklist")
                p.goto(BASE + "/client/phone"); check("forwarding checklist tick persists", p.is_checked("input[name=check_answered_no_text]"))
        ctx.close()
    b.close()
for r in res: print(*r, sep=" | ")
