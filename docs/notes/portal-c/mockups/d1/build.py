#!/usr/bin/env python3
"""Render direction d1 ("Spine") of the TextBack /client portal mockups.

usage: .venv/bin/python docs/notes/portal-c/mockups/d1/build.py
Reads ../fixture.json, renders templates/*.html with Jinja2 into this folder as
NN-<page>.html and NN-<page>--<state>.html. No content is typed here: every
visible string comes from the fixture. The only logic is ordering (a branch text
follows its parent), digit grouping for dial codes, keeping phone numbers on one
line, and which state flags each file turns on.
"""
import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

HERE = Path(__file__).resolve().parent
FX = json.loads((HERE.parent / "fixture.json").read_text())

# The fixture must not contradict itself: a booked caller while no calendar is connected has to say
# the booking went on the test calendar (critique d1 #1).
if FX["calendar"]["state"] != "connected":
    for row in FX["home"]["callers"]:
        assert row["status"] != "Booked", f"{row['name']} is Booked while no calendar is connected"
# The example conversation asks only the questions that are switched on (critique d1 #2).
_asked = {k for k, c in FX["messages"]["cards"].items() if not ("switch" in c and c["switch"]["state"] == "off")}
for b in FX["messages"]["example"]["bubbles"]:
    assert b.get("key", "intro") in _asked, f"example asks {b['key']}, which is switched off"
# A confirmation never promises an email invite while the email question is off.
if FX["messages"]["cards"]["prompt_email"]["switch"]["state"] == "off":
    assert "invite is on its way" not in FX["messages"]["cards"]["booking_confirmation"]["preview"]


# Kept on one line wherever they appear in visible text: phone numbers, dates and clock times.
NUM = re.compile(
    r"\(\d{3}\) \d{3}-\d{4}"
    r"|\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:day|sday|nesday|rsday|urday)?, (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}\b"
    r"|\b\d{1,2}:\d{2}(?:\s?[AP]M)?(?: [A-Z]{3}\b)?")


def keep_numbers_whole(html):
    """Wrap every (704) 555-0123 in visible text in a no-wrap span; tags, titles, options and textareas stay as they are."""
    out, skip = [], 0
    for chunk in re.split(r"(<[^>]+>)", html):
        if chunk.startswith("<"):
            tag = re.match(r"</?([a-zA-Z0-9]+)", chunk)
            name = tag.group(1).lower() if tag else ""
            if name in ("title", "option", "textarea", "script", "style"):
                skip += -1 if chunk.startswith("</") else 1
            out.append(chunk)
        else:
            out.append(chunk if skip else NUM.sub(lambda m: f'<span class="nw">{m.group(0)}</span>', chunk))
    return "".join(out)


def dial(code):
    """Group the 10-digit number inside a dial code for reading: *717045550100 -> *71 704 555 0100."""
    m = re.fullmatch(r"([*#]+\d*?[*#]*)(\d{10})([#]?)", code)
    if not m:
        return code
    pre, num, post = m.groups()
    return f"{pre} {num[:3]} {num[3:6]} {num[6:]}{post}"

env = Environment(
    loader=FileSystemLoader(HERE / "templates"),
    undefined=StrictUndefined,
    autoescape=select_autoescape(["html"]),
    trim_blocks=True,
    lstrip_blocks=True,
)
env.filters["dial"] = dial

# Icon per nav item and per Messages step (glyph names in templates/_sprite.html).
NAV_ICONS = {"Home": "home", "Messages": "messages", "Schedule": "clock", "Calendar": "calendar", "Phone": "phone"}
STEP_ICONS = {"missed_call": "missed", "questions": "question", "booking": "calendar",
              "no_reply": "bell", "steps_back": "person", "any_time": "shield"}
# A re-prompt is a branch of the question it repeats; it renders right after its parent.
BRANCH_OF = {"preferred_time_reprompt": "prompt_preferred_time",
             "phone_reprompt": "prompt_phone", "email_reprompt": "prompt_email"}
BRANCH_KEYS = set(BRANCH_OF) | {"slot_unavailable", "booking_error"}
JUMP_FIVE = ["missed_call", "questions", "booking", "no_reply", "steps_back"]  # research SUMMARY decision 8


def ordered(step):
    """Main keys with their branches, then optional keys with theirs."""
    keys, optional = list(step["keys"]), step.get("optional_keys", [])
    def with_branches(parent):
        return [parent] + [b for b, p in BRANCH_OF.items() if p == parent and b in keys]
    main = [k for k in keys if k not in BRANCH_OF and k not in optional]
    return ([k for p in main for k in with_branches(p)],
            [k for p in optional for k in with_branches(p)])


def base_ctx():
    return {
        "fx": FX, "meta": FX["meta"], "shell": FX["shell"], "nav_icons": NAV_ICONS,
        "step_icons": STEP_ICONS, "branch_keys": BRANCH_KEYS, "branch_of": BRANCH_OF, "jump_five": JUMP_FIVE,
        "ordered": ordered,
        # state flags, all off by default
        "menu_open": False, "banner": None, "dirty": False, "edit_open": None, "focus": None,
        "error": False, "any_time": False, "custom": False, "cal_state": FX["calendar"]["state"],
        "invalid_mobile": False, "dialog": False, "rename_offer": False, "saved": False, "hours_edit": False, "dirty_form": None,
    }


M, S, P, H = FX["messages"], FX["schedule"], FX["phone"], FX["shared"]
PAGES = [
    ("01-sign-in", "sign_in.html", {}),
    ("01-sign-in--error", "sign_in.html", {"error": True}),
    ("02-enter-code", "enter_code.html", {}),
    ("02-enter-code--error", "enter_code.html", {"error": True}),
    ("03-home", "home.html", {}),
    ("03-home--account-menu", "home.html", {"menu_open": True, "focus": "menu"}),
    ("04-messages", "messages.html", {}),
    ("04-messages--edit-open", "messages.html", {"edit_open": M["editor"]["open_on"], "focus": "editor"}),
    ("04-messages--unsaved-bar", "messages.html", {"dirty": True, "focus": "dirty"}),
    ("04-messages--saved-toast", "messages.html", {"banner": M["toasts"]["saved"], "focus": "banner"}),
    ("04-messages--example-booked", "messages.html", {"focus": "example"}),
    ("05-schedule", "schedule.html", {}),
    ("05-schedule--hours-grid", "schedule.html", {"focus": "hours", "dirty": True, "hours_edit": True}),
    ("05-schedule--any-time-warning", "schedule.html", {"any_time": True, "focus": "hours"}),
    ("05-schedule--custom-length", "schedule.html", {"custom": True, "focus": "duration", "dirty": True}),
    ("05-schedule--saved-toast", "schedule.html", {"banner": S["toast"], "focus": "banner", "saved": True}),
    ("05-schedule--unsaved-bar", "schedule.html", {"dirty": True, "focus": "duration"}),
    ("06-calendar", "calendar.html", {"cal_state": "not_connected_with_connect"}),
    ("06-calendar--connected", "calendar.html", {"cal_state": "connected", "focus": "connection"}),
    ("06-calendar--not-connected-no-connect", "calendar.html", {"cal_state": "not_connected_without_connect", "focus": "connection"}),
    ("07-phone", "phone.html", {}),
    ("07-phone--carrier-verizon", "phone.html", {"focus": "codes"}),
    ("07-phone--invalid-mobile", "phone.html", {"invalid_mobile": True, "focus": "mobile", "dirty": True, "dirty_form": "phone"}),
    ("07-phone--saved-toast", "phone.html", {"banner": P["toast"], "focus": "banner"}),
    ("07-phone--unsaved-bar", "phone.html", {"dirty": True, "dirty_form": "business", "focus": "business"}),
    ("07-phone--rename-offer", "phone.html", {"rename_offer": True, "focus": "banner"}),
    ("07-phone--confirm-mobile", "confirm_mobile.html", {}),
    ("07-phone--keep-mobile-toast", "phone.html", {"banner": P["confirm_mobile"]["toast_kept"], "focus": "banner"}),
    ("08-account", "account.html", {}),
    ("08-account--sign-out", "account.html", {"dialog": True, "focus": "dialog"}),
]

for name, template, flags in PAGES:
    ctx = base_ctx(); ctx.update(flags)
    html = keep_numbers_whole(env.get_template(template).render(**ctx))
    (HERE / f"{name}.html").write_text(html)
    print("wrote", name + ".html")
