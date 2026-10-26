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


def toast_markup(text):
    if text.startswith("Saved."):
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
    suffix = m["cards"]["opt_out_suffix"]["preview"]
    preview = c["preview"]
    c["preview_main"], c["preview_suffix"] = preview, None
    if c.get("optout_added") and preview.endswith(" " + suffix):
        c["preview_main"], c["preview_suffix"] = preview[: -len(suffix) - 1], suffix
    c["branch"] = key in BRANCH
    c["open"] = key == open_key
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
    return {"steps": steps, "bubbles": bubbles, "jump": m["jump_chips"][:5]}


def calendar_view(state):
    cal = dict(F["calendar"])
    view = dict(cal[state])
    if state == "connected":
        # Research ruling 4: "Connected as [account]" is not stored, so the body is only the
        # deck's "Bookings go here: [calendar name]." part of the fixture string.
        view["body"] = view["body"].split(" Connected as ")[0]
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
        ctx.setdefault("focus", "status")
        if ctx["focus"] is None:
            ctx["focus"] = "status"
    html = env.get_template(template).render(**ctx)
    (HERE / f"{out}.html").write_text(html)
    return out


T = F["shared"]["toasts"]
P = F["phone"]

PAGES = [
    ("01-sign-in", "sign_in.html", dict(signed_in=False, page_id="sign-in", title=F["sign_in"]["title"])),
    ("01-sign-in--error", "sign_in.html", dict(signed_in=False, page_id="sign-in", title=F["sign_in"]["title"], error=True, focus="mobile")),
    ("02-enter-code", "enter_code.html", dict(signed_in=False, page_id="enter-code", title=F["enter_code"]["title"])),
    ("02-enter-code--error", "enter_code.html", dict(signed_in=False, page_id="enter-code", title=F["enter_code"]["title"], error=True, focus="code")),
    ("03-home", "home.html", dict(page_id="home", title=F["home"]["title"], nav="Home")),
    ("03-home--account-menu", "home.html", dict(page_id="home", title=F["home"]["title"], nav="Home", menu_open=True, focus="menu")),
    ("04-messages", "messages.html", dict(page_id="messages", title=F["messages"]["title"], nav="Messages", wide=True, m=messages_view())),
    ("04-messages--edit-open", "messages.html", dict(page_id="messages", title=F["messages"]["title"], nav="Messages", wide=True,
                                                     m=messages_view(open_key=F["messages"]["editor"]["open_on"]), focus="m-prompt_location")),
    ("04-messages--unsaved-bar", "messages.html", dict(page_id="messages", title=F["messages"]["title"], nav="Messages", wide=True,
                                                       m=messages_view(unsaved=("intro", "prompt_location")), savebar=True, focus="m-prompt_location")),
    ("04-messages--saved-toast", "messages.html", dict(page_id="messages", title=F["messages"]["title"], nav="Messages", wide=True, m=messages_view(), toast=T["messages"])),
    ("04-messages--example-booked", "messages.html", dict(page_id="messages", title=F["messages"]["title"], nav="Messages", wide=True, m=messages_view(), focus="example")),
    ("05-schedule", "schedule.html", dict(page_id="schedule", title=F["schedule"]["title"], nav="Schedule")),
    ("05-schedule--hours-grid", "schedule.html", dict(page_id="schedule", title=F["schedule"]["title"], nav="Schedule", focus="hours")),
    ("05-schedule--any-time-warning", "schedule.html", dict(page_id="schedule", title=F["schedule"]["title"], nav="Schedule", any_time=True, focus="hours-warning")),
    ("05-schedule--custom-length", "schedule.html", dict(page_id="schedule", title=F["schedule"]["title"], nav="Schedule", custom=True, focus="length")),
    ("05-schedule--saved-toast", "schedule.html", dict(page_id="schedule", title=F["schedule"]["title"], nav="Schedule", toast=T["schedule"])),
    ("06-calendar", "calendar.html", dict(page_id="calendar", title=F["calendar"]["title"], nav="Calendar", cal=calendar_view("not_connected_with_connect"))),
    ("06-calendar--connected", "calendar.html", dict(page_id="calendar", title=F["calendar"]["title"], nav="Calendar", cal=calendar_view("connected"), focus="cal-state")),
    ("06-calendar--not-connected-no-connect", "calendar.html", dict(page_id="calendar", title=F["calendar"]["title"], nav="Calendar",
                                                                    cal=calendar_view("not_connected_without_connect"), focus="cal-state")),
    ("06-calendar--picked-toast", "calendar.html", dict(page_id="calendar", title=F["calendar"]["title"], nav="Calendar", cal=calendar_view("connected"), toast=T["calendar_picked"])),
    ("07-phone", "phone.html", dict(page_id="phone", title=P["title"], nav="Phone")),
    ("07-phone--carrier-verizon", "phone.html", dict(page_id="phone", title=P["title"], nav="Phone", focus="codes")),
    ("07-phone--invalid-mobile", "phone.html", dict(page_id="phone", title=P["title"], nav="Phone", invalid_mobile=True, focus="owner-mobile")),
    ("07-phone--saved-toast", "phone.html", dict(page_id="phone", title=P["title"], nav="Phone", toast=T["phone"])),
    ("07-phone--confirm-mobile", "confirm_mobile.html", dict(page_id="phone", title=P["confirm_mobile"]["title"], nav="Phone", focus="confirm")),
    ("07-phone--keep-mobile-toast", "phone.html", dict(page_id="phone", title=P["title"], nav="Phone", toast=T["keep_mobile"])),
    ("07-phone--checks-toast", "phone.html", dict(page_id="phone", title=P["title"], nav="Phone", toast=T["checks"])),
    ("08-account", "account.html", dict(page_id="account", title=F["account"]["title"], nav=None)),
    ("08-account--sign-out", "account.html", dict(page_id="account", title=F["account"]["title"], nav=None, dialog=True, focus="confirm")),
]

if __name__ == "__main__":
    for out, template, ctx in PAGES:
        render(out, template, **ctx)
    print(f"rendered {len(PAGES)} files into {HERE}")
