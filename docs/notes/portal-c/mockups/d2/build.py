#!/usr/bin/env python3
"""Render direction d2 ("Ledger") of the candidate C mockups.

Reads ../fixture.json, renders the plain Jinja2 templates in ./templates and writes
NN-<page>.html and NN-<page>--<state>.html beside this file. No content is typed into
templates: every visible string comes from the fixture. Run with the repo's .venv python.
"""
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, pass_context, select_autoescape
from markupsafe import Markup, escape

HERE = Path(__file__).resolve().parent
F = json.loads((HERE.parent / "fixture.json").read_text())

env = Environment(
    loader=FileSystemLoader(HERE / "templates"),
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


@pass_context
def fid(ctx, name):
    """The element a state is about carries id="focus" so the capture tool scrolls to it."""
    return Markup('id="%s"' % ("focus" if ctx.get("focus") == name else name))


env.globals["fid"] = fid

# The one check vocabulary (research SUMMARY.md, "Shared vocabulary"): word -> glyph kind.
STATE_KIND = {
    "Done": "done",
    "Needs you": "needs",
    "Waiting on phone companies": "waiting",
    "Not yet": "notyet",
    "You checked this": "checked",
    "Connected": "done",
    "Not connected": "needs",
    "Reconnect needed": "needs",
    "Couldn't be read": "needs",
}
env.globals["kind"] = lambda word: STATE_KIND.get(word, "notyet")

# Calendar speaks the shared vocabulary too: its own state words map onto the Home / checklist words.
VOCAB_WORD = {
    "Not connected": F["home"]["setup"][0]["state"],          # "Needs you"
    "Reconnect needed": F["home"]["setup"][0]["state"],
    "Couldn't be read": F["home"]["setup"][0]["state"],
    "Connected": F["phone"]["checks"]["state_words"][0],       # "Done"
}
env.globals["vocab"] = lambda word: VOCAB_WORD.get(word, word)

# The only words on screen that are not in fixture.json / copy-deck.md. Reported to the lead as deck additions.
GLUE = {"was": "Was:"}
env.globals["GLUE"] = GLUE

# Every "Saved." toast names the change, using the messages toast's own sentence as the pattern:
# 'Saved. You changed \u201cQuestion 2: the address\u201d.' with the title swapped out.
_T_MSG = F["shared"]["toasts"]["messages"]
_T_PAT = _T_MSG.replace(F["messages"]["cards"]["prompt_location"]["title"], "\x00")


def changed_toast(label, tail=None):
    text = _T_PAT.replace("\x00", label)
    return text + (" " + tail if tail else "")


def after_saved(text):
    """The part of a fixture toast after its leading 'Saved.'"""
    return text.split("Saved.", 1)[1].strip()


def reset_label(label):
    """'Reset Appointment length' pattern from schedule.reset_accessible."""
    pat = F["schedule"]["reset_accessible"]
    return pat.replace(F["schedule"]["appointments"]["duration"]["label"], label)


env.globals["reset_label"] = reset_label

# Text cost, computed the way the carrier bills it (GSM-7 160/153, otherwise UCS-2 70/67).
_GSM = set("@\u00a3$\u00a5\u00e8\u00e9\u00f9\u00ec\u00f2\u00c7\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà^{}\\[~]|€")


def cost_of(text):
    gsm = all(ch in _GSM for ch in text)
    single, multi = (160, 153) if gsm else (70, 67)
    n = 1 if len(text) <= single else -(-len(text) // multi)
    return n, len(text)


def cost_line(n, chars):
    """Reuse the fixture's own receipt wording ('1 text · 31 characters' / '3 texts · 147 characters')."""
    cards = F["messages"]["cards"].values()
    one = next(c["cost"]["line"] for c in cards if c["cost"]["texts"] == 1)
    many = next(c["cost"]["line"] for c in cards if c["cost"]["texts"] > 1)
    import re
    tpl = one if n == 1 else many
    nums = re.findall(r"\d+", tpl)
    out = tpl.replace(nums[0], "\x01", 1).replace(nums[1], "\x02", 1)
    return out.replace("\x01", str(n)).replace("\x02", str(chars))


def fill(parts):
    """Wording parts -> (textarea value with [markers], customer-facing filled text)."""
    raw, filled = "", ""
    for p in parts:
        if "text" in p:
            raw += p["text"]; filled += p["text"]
        else:
            raw += "[%s]" % p["insert"]
            filled += F["meta"]["business_name"] if p["insert"] == "Business name" else "[%s]" % p["insert"]
    return raw, filled


def toast_markup(text):
    for lead in ("Saved.", "Kept"):
        if text.startswith(lead) and lead == "Saved.":
            return Markup("<strong>Saved.</strong>%s" % escape(text[len("Saved."):]))
    return Markup("<strong>%s</strong>" % escape(text))


# Structure only: which texts are branches of which question, and which are branches at all.
PARENT = {
    "preferred_time_reprompt": "prompt_preferred_time",
    "phone_reprompt": "prompt_phone",
    "email_reprompt": "prompt_email",
}
BRANCH = set(PARENT) | {"slot_unavailable", "booking_error"}


def ordered(keys):
    out = [k for k in keys if k not in PARENT]
    for branch, parent in PARENT.items():
        if branch in keys and parent in out:
            out.insert(out.index(parent) + 1, branch)
    return out


def card_view(key, unsaved=(), open_key=None):
    m = F["messages"]
    c = dict(m["cards"][key])
    c["raw"], _ = fill(c["wording"])
    c["draft"] = None
    if key in unsaved:
        # The unsaved draft in this state is "Reset to the standard wording, not saved yet".
        raw, filled = fill(c["default_wording"])
        if c.get("optout_added"):
            filled = filled + " " + m["cards"]["opt_out_suffix"]["preview"]
        n, chars = cost_of(filled)
        amber = None
        if n > 1:
            amber = next((x["cost"]["amber"] for x in m["cards"].values()
                          if x["cost"]["amber"] and x["cost"]["texts"] == n and "\u2014" in x["cost"]["amber"]), None)
        c["raw"] = raw
        c["draft"] = {"text": filled, "cost": cost_line(n, chars), "warn": n > 1, "amber": amber, "was": c["preview"]}
    suffix = m["cards"]["opt_out_suffix"]["preview"]
    preview = c["preview"]
    c["preview_main"], c["preview_suffix"] = preview, None
    if c.get("optout_added") and preview.endswith(" " + suffix):
        c["preview_main"], c["preview_suffix"] = preview[: -len(suffix) - 1], suffix
    c["branch"] = key in BRANCH
    c["open"] = key == open_key
    sw = c.get("switch") or (m["cards"].get(PARENT.get(key, ""), {}).get("switch"))
    c["off"] = bool(sw and sw.get("state") != "on")
    c["steps_back"] = c.get("step") == "steps_back"
    if c["draft"] and c["draft"]["text"].endswith(" " + m["cards"]["opt_out_suffix"]["preview"]):
        sfx = m["cards"]["opt_out_suffix"]["preview"]
        c["draft"]["main"], c["draft"]["suffix"] = c["draft"]["text"][: -len(sfx) - 1], sfx
    elif c["draft"]:
        c["draft"]["main"], c["draft"]["suffix"] = c["draft"]["text"], None
    if key in unsaved:
        c["badge"] = m["editor"]["badge_states"]["unsaved"]
        c["badge_cls"] = "unsaved"
    else:
        c["badge_cls"] = "custom" if c["state"] == "customized" else "std"
    return c


def messages_view(unsaved=(), open_key=None):
    m = F["messages"]
    steps = []
    for s in m["steps"]:
        optional = set(s.get("optional_keys", []))
        is_opt = lambda k: k in optional or PARENT.get(k) in optional  # noqa: E731
        main = ordered([k for k in s["keys"] if not is_opt(k)])
        opt = ordered([k for k in s["keys"] if is_opt(k)])
        steps.append(
            {
                **s,
                "cards": [card_view(k, unsaved, open_key) for k in main],
                "optional_cards": [card_view(k, unsaved, open_key) for k in opt],
            }
        )
    pills = m["example"]["pills"]
    bubbles = []
    for b in m["example"]["bubbles"]:
        b = dict(b)
        if b["side"] == "event":
            b["pill"] = "missed" if b["text"] == pills["missed_call"] else (
                "booked" if b["text"] in (pills["booked_connected"], pills["booked_test"]) else "plain"
            )
        bubbles.append(b)
    # Five chips at most: "Missed call" sits right under the chips and START/HELP/STOP is a collapsed
    # footer, so the five are Questions, Booking, No reply, Steps back and the example conversation.
    drop = {"missed_call", "any_time"}
    jump = [j for j in m["jump_chips"] if j["anchor"] not in drop][:5]
    changed = [{"key": k, "title": m["cards"][k]["title"]} for k in unsaved]
    return {"steps": steps, "bubbles": bubbles, "jump": jump, "changed": changed,
            "jump_label": m["jump_label"].rstrip(":")}


def calendar_view(state):
    cal = dict(F["calendar"])
    view = dict(cal[state])
    if state == "connected":
        # The picker below is the one control that changes the calendar, so only Reconnect stays as a button.
        view["buttons"] = [b for b in view["buttons"] if b != view["picker"]["button"] and not b.startswith("Use a different")]
    if "availability" not in view:
        # Both not-connected states show the same test calendar (deck avail_title "Test calendar, not yours").
        view["availability"] = cal["not_connected_with_connect"]["availability"]
    cal["view"] = view
    cal["state"] = state
    return cal


def render(out, template, **ctx):
    ctx.setdefault("f", F)
    ctx.setdefault("signed_in", True)
    ctx.setdefault("focus", None)
    if ctx.get("toast"):
        ctx["toast_html"] = toast_markup(ctx["toast"])
        if ctx.get("focus") is None:
            ctx["focus"] = "status"
    html = env.get_template(template).render(**ctx)
    (HERE / f"{out}.html").write_text(html)
    return out


T = F["shared"]["toasts"]
P = F["phone"]
S = F["schedule"]
MS = F["messages"]
K = P["checks"]
SB = MS["save_bar"]


def savebar(count, links, form):
    return {"count": count, "links": links, "form": form, "discard": SB["discard"], "save": SB["save"]}


MSG = dict(page_id="messages", title=MS["title"], nav="Messages", wide=True)
SCH = dict(page_id="schedule", title=S["title"], nav="Schedule")
PH = dict(page_id="phone", title=P["title"], nav="Phone")
CAL = dict(page_id="calendar", title=F["calendar"]["title"], nav="Calendar")
UNSAVED = ("intro", "prompt_location")
msg_unsaved = messages_view(unsaved=UNSAVED)

PAGES = [
    ("01-sign-in", "sign_in.html", dict(signed_in=False, page_id="sign-in", title=F["sign_in"]["title"])),
    ("01-sign-in--error", "sign_in.html", dict(signed_in=False, page_id="sign-in", title=F["sign_in"]["title"], error=True,
                                               typed=P["numbers"]["owner_mobile"]["invalid_entry"], focus="errors")),
    ("02-enter-code", "enter_code.html", dict(signed_in=False, page_id="enter-code", title=F["enter_code"]["title"])),
    ("02-enter-code--error", "enter_code.html", dict(signed_in=False, page_id="enter-code", title=F["enter_code"]["title"], error=True, focus="errors")),
    ("03-home", "home.html", dict(page_id="home", title=F["home"]["title"], nav="Home")),
    ("03-home--account-menu", "home.html", dict(page_id="home", title=F["home"]["title"], nav="Home", menu_open=True, focus="menu")),
    ("04-messages", "messages.html", dict(MSG, m=messages_view())),
    ("04-messages--edit-open", "messages.html", dict(MSG, m=messages_view(open_key=MS["editor"]["open_on"]), focus="m-prompt_location")),
    ("04-messages--unsaved-bar", "messages.html", dict(MSG, m=msg_unsaved, focus="m-intro",
        savebar=savebar(SB["changed"], [{"href": "#m-" + c["key"], "label": c["title"]} for c in msg_unsaved["changed"]], "messages-form"))),
    ("04-messages--saved-toast", "messages.html", dict(MSG, m=messages_view(), toast=T["messages"])),
    ("04-messages--example-booked", "messages.html", dict(MSG, m=messages_view(), focus="example")),
    ("05-schedule", "schedule.html", dict(SCH)),
    ("05-schedule--hours-grid", "schedule.html", dict(SCH, focus="hours")),
    ("05-schedule--any-time-warning", "schedule.html", dict(SCH, any_time=True, focus="hours")),
    ("05-schedule--custom-length", "schedule.html", dict(SCH, custom=True, focus="length")),
    ("05-schedule--unsaved-bar", "schedule.html", dict(SCH, custom=True, focus="length",
        savebar=savebar(S["unsaved_bar"], [{"href": "#length", "label": S["appointments"]["duration"]["label"]}], "schedule-form"))),
    ("05-schedule--saved-toast", "schedule.html", dict(SCH, toast=changed_toast(S["hours"]["title"], after_saved(T["schedule"])))),
    ("06-calendar", "calendar.html", dict(CAL, cal=calendar_view("not_connected_with_connect"))),
    ("06-calendar--connected", "calendar.html", dict(CAL, cal=calendar_view("connected"), focus="cal-state")),
    ("06-calendar--not-connected-no-connect", "calendar.html", dict(CAL, cal=calendar_view("not_connected_without_connect"), focus="cal-state")),
    ("06-calendar--picked-toast", "calendar.html", dict(CAL, cal=calendar_view("connected"), toast=T["calendar_picked"])),
    ("07-phone", "phone.html", dict(PH)),
    ("07-phone--carrier-verizon", "phone.html", dict(PH, focus="codes")),
    ("07-phone--invalid-mobile", "phone.html", dict(PH, invalid_mobile=True, focus="errors")),
    ("07-phone--unsaved-bar", "phone.html", dict(PH, mobile_changed=True, focus="owner-mobile-row",
        savebar=savebar(P["unsaved_bar"], [{"href": "#owner-mobile", "label": P["numbers"]["owner_mobile"]["label"]}], "phone-form"))),
    ("07-phone--saved-toast", "phone.html", dict(PH, toast=changed_toast(P["numbers"]["help_number"]["label"]))),
    ("07-phone--rename-offer", "phone.html", dict(PH, rename=True, focus="rename", toast=changed_toast(P["business"]["name"]["label"]))),
    ("07-phone--confirm-mobile", "confirm_mobile.html", dict(PH, title=P["confirm_mobile"]["title"], focus="confirm")),
    ("07-phone--keep-mobile-toast", "phone.html", dict(PH, toast=T["keep_mobile"])),
    ("07-phone--checks-toast", "phone.html", dict(PH, checked3=True, toast=changed_toast(K["items"][2]["step"]))),
    ("08-account", "account.html", dict(page_id="account", title=F["account"]["title"], nav=None)),
    ("08-account--sign-out", "account.html", dict(page_id="account", title=F["account"]["title"], nav=None, dialog=True, focus="confirm")),
]

if __name__ == "__main__":
    for out, template, ctx in PAGES:
        render(out, template, **ctx)
    print(f"rendered {len(PAGES)} files into {HERE}")
