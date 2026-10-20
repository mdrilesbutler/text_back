"""Client settings pages: the business owner signs in and edits message copy.
Business details and the calendar connection live in client_settings.py and
share the sign-in, page frame and code helpers defined here.

Sign-in is passwordless. The owner enters the business mobile that is on
file (TEXT_BACK_OWNER_MOBILE); if it matches, a six-digit code is texted to
that number and nothing else. The code lives ten minutes, allows five
guesses, and a browser session lasts twelve hours. Everything is
server-rendered HTML with no external assets: one inline stylesheet, and a
small script that only adds live previews, counters and placeholder chips on
top of pages that work without it.

The Messages page is one long page in conversation order (missed call, the
questions, booking, no reply, you step in, START/HELP/STOP). Every message is
a card with a phone-bubble preview of what the customer will receive, the
editor, a character and text-segment count, the allowed placeholders, and a
Standard/Customized state with a one-tap reset.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import math
import re
import secrets
from datetime import datetime, timedelta, timezone
from string import Formatter

from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from text_back.messages import (
    DEFAULT_TEMPLATES,
    MAX_TEMPLATE_CHARS,
    OPT_OUT_REQUIRED,
    PLACEHOLDERS,
    MessageTemplateError,
    write_message_file,
)
from text_back.policy import format_contact_number
from text_back.sms import enqueue_sms, run_due_sms

CODE_TTL = timedelta(minutes=10)
CODE_ATTEMPTS = 5
CODES_PER_WINDOW = 3
CODE_WINDOW = timedelta(minutes=15)
SESSION_TTL = timedelta(hours=12)
SESSION_COOKIE = "text_back_client"
PENDING_COOKIE = "text_back_client_login"
CODE_FAILURE = "That code is not right or has expired. Check the text or send a new code."

# --- the Messages page: every text, in the order the customer meets it --------

# key -> (label, when it is sent, the rule the owner should know before saving)
MESSAGES: dict[str, tuple[str, str, str]] = {
    "intro": ("First text after a missed call", "Sent the moment a call goes unanswered.",
              "Carriers require an opt-out line: if your wording leaves out the word STOP, the opt-out line (last card) is added."),
    "prompt_service": ("Question 1: the job", "Asked as soon as the customer replies.", ""),
    "prompt_location": ("Question 2: the location", "Asked once the job is known.", ""),
    "prompt_preferred_time": ("Question 3: day and time", "Asked once the location is known. Spoken examples help: Wednesday at 2, tomorrow at 10am.", ""),
    "preferred_time_reprompt": ("If the time could not be understood", "Sent instead of moving on when the reply is not a day and time.", ""),
    "prompt_name": ("Question 4: the name", "Asked once the time is known.", ""),
    "prompt_phone": ("Optional question: best phone number", "Asked only when switched on. YES keeps the number they are texting from.", ""),
    "phone_reprompt": ("If the phone number could not be read", "Sent when the reply is not a phone number or YES.", ""),
    "prompt_email": ("Optional question: email address", "Asked only when switched on. SKIP is allowed.", ""),
    "email_reprompt": ("If the email could not be read", "Sent when the reply is not an email address or SKIP.", ""),
    "slot_unavailable": ("When the time is already taken", "Sent when the calendar shows that slot busy.", ""),
    "booking_confirmation": ("Booking confirmation", "Sent only after the appointment exists on your calendar.", ""),
    "booking_error": ("When the calendar failed", "Sent if the appointment could not be created.",
                      "Must say \"no booking was made\" and must not use the word \"call\": the customer stays in the text thread."),
    "followup_1": ("First reminder", "Sent after the first follow-up delay with no reply.",
                   "Carriers require an opt-out line: if your wording leaves out STOP, the opt-out line is added."),
    "followup_2": ("Last reminder", "Sent after the second delay. After this the assistant stops texting.",
                   "Carriers require an opt-out line: if your wording leaves out STOP, the opt-out line is added."),
    "handoff_ack": ("When you need to step in", "Sent when the customer asks for a person or the assistant cannot help; you get a lead.",
                    "Must promise a follow-up. Never promise a person or send them to your business line."),
    "handoff_ack_safety": ("Safety hand-off", "Sent when a text mentions danger; you get an urgent lead.",
                           "Must mention 911 and promise a follow-up."),
    "opt_in": ("Reply to START", "Sent when a customer texts START.",
               "Carriers require an opt-out line: if your wording leaves out STOP, the opt-out line is added."),
    "help": ("Reply to HELP", "Sent when a customer texts HELP.",
             "Carriers require an opt-out line: if your wording leaves out STOP, the opt-out line is added."),
    "opt_out_ack": ("Reply to STOP", "Sent once when a customer texts STOP; nothing follows it.", ""),
    "opt_out_suffix": ("Opt-out line", "Added to the first text, reminders, START and HELP replies when they leave out the word STOP.",
                       "Must contain the word STOP; carriers check for it."),
}

# (group id, heading, what happens at this moment, message keys in order)
GROUPS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("missed", "Missed call", "A call goes unanswered. Within seconds the caller gets this text.", ("intro",)),
    ("questions", "The questions", "Asked one at a time, in this order. The assistant only moves on once it has an answer.",
     ("prompt_service", "prompt_location", "prompt_preferred_time", "preferred_time_reprompt", "prompt_name",
      "prompt_phone", "phone_reprompt", "prompt_email", "email_reprompt")),
    ("booking", "Booking", "With the answers in hand the assistant checks your calendar and books a free slot.",
     ("slot_unavailable", "booking_confirmation", "booking_error")),
    ("noreply", "No reply", "If the customer goes quiet, two reminders. Then it stops.", ("followup_1", "followup_2")),
    ("owner", "You step in", "When a text needs you, automated scheduling pauses and you get a lead.",
     ("handoff_ack", "handoff_ack_safety")),
    ("keywords", "START, HELP and STOP", "Replies carriers require to the three keywords, and the opt-out line itself.",
     ("opt_in", "help", "opt_out_ack", "opt_out_suffix")),
)

# Optional questions: the on/off switch lives on the question's own card.
OPTIONAL_QUESTIONS = {"prompt_phone": ("phone", "Also ask for the best phone number"), "prompt_email": ("email", "Also ask for an email address")}

FIELD_KEYS: tuple[str, ...] = tuple(key for _, _, _, keys in GROUPS for key in keys)
# Kept for callers that only need (key, label, hint).
FIELDS = tuple((key, MESSAGES[key][0], MESSAGES[key][1]) for key in FIELD_KEYS)

# Example values so the preview reads like a real text.
SAMPLE_SERVICE, SAMPLE_WHEN, SAMPLE_LOCATION, SAMPLE_EMAIL = "tree removal", "Thursday, Oct 22 at 4:00 PM", "12 Elm St", "alex@example.com"

# GSM-7 alphabet: texts made only of these fit 160 characters per segment;
# anything else (em dash, curly quotes, emoji) drops the limit to 70.
GSM_BASIC = "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
GSM_EXTENDED = "^{}\\[~]|€"


def sms_parts(text: str) -> tuple[int, int, bool]:
    """(characters, text segments, fits the plain GSM alphabet) for a rendered text."""
    if all(ch in GSM_BASIC or ch in GSM_EXTENDED for ch in text):
        units = sum(2 if ch in GSM_EXTENDED else 1 for ch in text)
        return len(text), (1 if units <= 160 else math.ceil(units / 153)), True
    return len(text), (1 if len(text) <= 70 else math.ceil(len(text) / 67)), False


class _Keep(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def fill(template: str, values: dict[str, str]) -> str:
    try:
        return template.format_map(_Keep(values))
    except (ValueError, IndexError, KeyError):
        return template


def preview_values(state) -> dict[str, str]:
    base = str(state.public_base_url).rstrip("/")
    contact = (getattr(state, "business_contact", "") or "").strip() or format_contact_number(getattr(state, "business_number", "") or "")
    links = {name: f"{base}/a/k7q2-ref{suffix}" for name, suffix in
             (("links_page", ""), ("google_link", "/g"), ("outlook_link", "/o"), ("ical_link", "/i"))}
    return {
        "business_name": state.business_name, "service": SAMPLE_SERVICE, "when": SAMPLE_WHEN, "location": SAMPLE_LOCATION,
        "event_id": "", "invited_email": SAMPLE_EMAIL, "invite_line": f"A calendar invite is on its way to {SAMPLE_EMAIL}.",
        "calendar_links": f"Add to calendar: Google {links['google_link']} Outlook {links['outlook_link']} iCal {links['ical_link']}",
        "contact_line": f" Contact: {contact}." if contact else "", **links,
    }


def preview_text(key: str, templates: dict[str, str], values: dict[str, str]) -> str:
    """What the customer receives for ``key``: placeholders filled and, where
    carriers require it, the opt-out line appended (same rule as MessageSet.render)."""
    text = fill(templates[key], values)
    if key in OPT_OUT_REQUIRED and not re.search(r"\bstop\b", templates[key], re.IGNORECASE):
        text = f"{text} {fill(templates['opt_out_suffix'], values)}"
    return " ".join(text.split())


def blame(error: str, templates: dict[str, str]) -> tuple[str | None, str]:
    """Which message a MessageTemplateError is about, and the reason without the key."""
    match = re.match(r"^(\w+) (.+)$", error)
    if match and match.group(1) in DEFAULT_TEMPLATES:
        return match.group(1), match.group(2)
    if error.startswith("handoff acknowledgements"):
        for key in ("handoff_ack", "handoff_ack_safety"):
            if "follow up" not in templates[key].lower():
                return key, "must promise a follow-up"
    if "unbalanced" in error or "placeholders must look like" in error:
        for key in FIELD_KEYS:
            try:
                for _, name, _, _ in Formatter().parse(templates[key]):
                    if name is not None and (name == "" or not name.isidentifier()):
                        return key, error
            except ValueError:
                return key, error
    return None, error


# --- page frame ----------------------------------------------------------------

STYLE = (
    ":root{--bg:#faf8f3;--card:#fff;--ink:#171a1f;--muted:#596270;--line:#d9d4c8;--soft:#f1eee6;--accent:#F0B429;--accent-ink:#1c1300;"
    "--ok:#1d6b3a;--ok-bg:#e6f4ea;--err:#b3261e;--err-bg:#fdecea;--warn:#8a5a00;--warn-bg:#fff4d6;--bubble:#e9e7e0;--radius:12px}"
    "*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}"
    "body{margin:0;font:17px/1.5 'Atkinson Hyperlegible','IBM Plex Sans','Segoe UI',system-ui,sans-serif;color:var(--ink);background:var(--bg)}"
    "main{max-width:44rem;margin:0 auto;padding:0 16px 32px}@media(min-width:700px){main{padding:0 24px 48px}}"
    "h1{font-size:1.65rem;line-height:1.2;margin:1.2rem 0 .4rem;letter-spacing:-.01em}h2{font-size:1.25rem;margin:0 0 .25rem}h3{font-size:1.05rem;margin:0}"
    "p{margin:.5rem 0}a{color:#1b5e9e}.muted{color:var(--muted)}.lead{margin:0 0 1rem}"
    ".top{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 0 8px;border-bottom:1px solid var(--line)}"
    ".brand{display:flex;flex-direction:column;min-width:0}.brand .eyebrow{font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}"
    ".brand strong{font-size:1.05rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.top form{margin:0}"
    ".tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:12px 0 4px;padding:4px;background:var(--soft);border-radius:var(--radius)}"
    ".tabs a{display:flex;align-items:center;justify-content:center;min-height:48px;border-radius:9px;font-weight:700;color:var(--ink);text-decoration:none}"
    ".tabs a.on{background:var(--card);box-shadow:inset 0 -3px 0 var(--accent),0 1px 2px rgba(0,0,0,.08)}"
    "label{display:block;font-weight:700;margin-top:1.1rem}label.edit{font-size:.95rem;color:var(--muted);margin-top:.9rem}.help{display:block;color:var(--muted);font-size:.95rem;font-weight:400;margin:.15rem 0 .4rem}"
    "input:not([type=checkbox]):not([type=radio]),textarea{width:100%;font:inherit;font-size:1.05rem;padding:12px 14px;border:1.5px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);margin-top:4px}"
    "input:focus,textarea:focus,button:focus-visible,a:focus-visible{outline:3px solid var(--accent);outline-offset:2px}"
    "textarea{min-height:6rem;resize:vertical;line-height:1.45}input[type=checkbox],input[type=radio]{width:24px;height:24px;margin:0 10px 0 0;accent-color:#1c1300;flex:none}"
    "button{font:inherit;font-weight:700;min-height:48px;padding:10px 20px;border:0;border-radius:10px;cursor:pointer;background:var(--accent);color:var(--accent-ink)}"
    "button.ghost{background:transparent;border:1.5px solid var(--line);color:var(--ink);min-height:40px;padding:6px 14px}"
    "button.text{background:none;color:#1b5e9e;padding:6px 0;min-height:40px;text-decoration:underline}button:disabled{opacity:.5;cursor:default}"
    ".primary{width:100%;font-size:1.1rem}@media(min-width:700px){.primary{width:auto;min-width:16rem}}"
    ".flash{padding:12px 14px;border-radius:10px;margin:.8rem 0;border:1px solid}.err{background:var(--err-bg);border-color:#f0b4ae;color:#5a1510}.ok{background:var(--ok-bg);border-color:#a9d8b4;color:#123d21}"
    ".flash a{color:inherit;font-weight:700}"
    ".card{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:16px;margin:.9rem 0}"
    ".group{margin-top:2rem}.group header{display:flex;gap:12px;align-items:flex-start}.num{flex:none;width:34px;height:34px;border-radius:50%;background:var(--accent);color:var(--accent-ink);font-weight:800;display:flex;align-items:center;justify-content:center}"
    ".group header p{margin:0;color:var(--muted)}"
    ".msg{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:14px 16px 16px;margin:.9rem 0;scroll-margin-top:12px}.msg.bad{border-color:var(--err);box-shadow:0 0 0 2px var(--err-bg)}"
    ".msghead{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap}.when{margin:.15rem 0 .7rem;color:var(--muted);font-size:.95rem}"
    ".state{font-size:.8rem;font-weight:700;padding:3px 9px;border-radius:999px;background:var(--soft);color:var(--muted);white-space:nowrap}.state.custom{background:var(--warn-bg);color:var(--warn)}"
    ".phone{background:var(--soft);border-radius:var(--radius);padding:12px 12px 8px}.phone .from{font-size:.78rem;color:var(--muted);text-align:center;margin:0 0 8px}"
    ".bubble{position:relative;background:var(--bubble);border-radius:18px;border-bottom-left-radius:4px;padding:10px 14px;max-width:88%;overflow-wrap:anywhere;font-size:1rem;line-height:1.4}"
    ".meta{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;font-size:.85rem;color:var(--muted);margin:8px 2px 0}"
    ".vh{position:absolute!important;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}"
    ".chips{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:.6rem 0 0;font-size:.9rem;color:var(--muted)}"
    ".chip{min-height:36px;padding:4px 12px;font-size:.9rem;font-weight:600;background:var(--soft);color:var(--ink);border:1px solid var(--line);font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace}"
    ".rule{margin:.6rem 0 0;font-size:.9rem;color:var(--muted);padding-left:1.4rem;position:relative}.rule:before{content:'';position:absolute;left:4px;top:.45em;width:8px;height:8px;border-radius:50%;background:var(--accent)}"
    ".fielderr{margin:.6rem 0 0;color:var(--err);font-weight:700}.ask{display:flex;align-items:center;gap:0;margin:.6rem 0 .8rem;padding:10px 12px;border:1.5px solid var(--line);border-radius:10px;font-weight:700}"
    ".actions{display:flex;justify-content:flex-end;margin-top:.4rem}"
    ".savebar{position:sticky;bottom:0;background:var(--card);border-top:1px solid var(--line);margin:1.5rem -16px 0;padding:12px 16px calc(12px + env(safe-area-inset-bottom));display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}"
    "@media(min-width:700px){.savebar{margin:1.5rem -24px 0;padding:12px 24px}}.dirty{font-weight:700;color:var(--warn)}"
    "details{margin:.8rem 0}summary{cursor:pointer;font-weight:700;padding:10px 0}details ul{margin:.3rem 0 .6rem;padding-left:1.3rem}details li{margin:.25rem 0}"
    ".status{display:flex;gap:14px;align-items:flex-start;padding:16px;border-radius:var(--radius);border:1px solid var(--line);background:var(--card);margin:.9rem 0}"
    ".status svg{flex:none;width:28px;height:28px}.status.ok{background:var(--ok-bg);border-color:#a9d8b4}.status.warn{background:var(--warn-bg);border-color:#ebcf85}.status.err{background:var(--err-bg);border-color:#f0b4ae}"
    ".status>div>strong{display:block;font-size:1.1rem}.status p{margin:.3rem 0 0}"
    ".choice{display:flex;align-items:center;min-height:52px;padding:8px 12px;margin:6px 0;border:1.5px solid var(--line);border-radius:10px;font-weight:600;cursor:pointer}.choice:has(:checked){border-color:var(--accent);background:#fff8e3}"
    "fieldset.plain{border:0;padding:0;margin:0;min-width:0}.steps{display:flex;gap:10px;margin:1rem 0 .4rem}.step{flex:1;padding:10px 12px;border-radius:10px;border:1.5px solid var(--line);font-weight:700;font-size:.95rem;color:var(--muted)}"
    ".step.done{background:var(--ok-bg);border-color:#a9d8b4;color:var(--ok)}.step.now{background:#fff8e3;border-color:var(--accent);color:var(--ink)}"
    ".code{font-size:1.6rem;letter-spacing:.35em;text-align:center;font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace}"
    ".signin h1{font-size:1.9rem;margin-top:2.5rem}.signin .eyebrow{font-size:.85rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-top:2.5rem}.signin .eyebrow+h1{margin-top:.2rem}"
)

TABS = (("messages", "Messages", "/client/messages"), ("business", "Business", "/client/business"), ("calendar", "Calendar", "/client/calendar"))


def nav_html(state, session, title: str, active: str) -> str:
    """Business header with sign-out, the three settings tabs, and the page title."""
    tabs = "".join(
        f"<a href={href}{' class=on aria-current=page' if key == active else ''}>{label}</a>" for key, label, href in TABS
    )
    return (
        f"<header class=top><div class=brand><span class=eyebrow>Assistant settings</span>"
        f"<strong>{html.escape(state.business_name)}</strong></div><form method=post action=/client/logout>"
        f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'><button type=submit class=ghost>Sign&nbsp;out</button></form></header>"
        f"<nav class=tabs aria-label=Settings>{tabs}</nav><h1>{html.escape(title)}</h1>"
    )


def _page(title: str, body: str, *, script: str = "", main_class: str = "") -> HTMLResponse:
    doc = (
        "<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<meta name=color-scheme content=light><title>{html.escape(title)}</title><style>{STYLE}</style></head><body>"
        f"<main{' class=' + main_class if main_class else ''}>{body}</main>"
        + (f"<script>{script}</script>" if script else "")
        + "</body></html>"
    )
    return HTMLResponse(doc, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY"})


def _now(state):
    return state.now_provider() if state.now_provider else datetime.now(timezone.utc)


def _mac(state, value: str) -> str:
    return hmac.new(state.webhook_secret.encode(), ("client-portal:" + value).encode(), hashlib.sha256).hexdigest()


def normalize_mobile(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        digits = "1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if 8 <= len(digits) <= 15 and raw.strip().startswith("+"):
        return "+" + digits
    return None


def _secure(state) -> bool:
    return str(state.public_base_url).lower().startswith("https://")


def _session(state, request: Request):
    token = request.cookies.get(SESSION_COOKIE, "")
    if not token:
        return None
    now = _now(state)
    with state.store.lock:
        # pending=0: a "code requested" row must never pass as a signed-in session.
        row = state.store.conn.execute(
            "SELECT * FROM client_sessions WHERE token_hash=? AND pending=0 AND expires_at>?", (_mac(state, token), now.isoformat())
        ).fetchone()
    return dict(row) if row else None


def _flash(error: str = "", notice: str = "") -> str:
    if error:
        return f"<p class='flash err' role=alert>{html.escape(error)}</p>"
    return f"<p class='flash ok' role=status>{html.escape(notice)}</p>" if notice else ""


# --- sign in -------------------------------------------------------------------

def _login_form(state, error: str = "", notice: str = "") -> HTMLResponse:
    return _page(
        "Sign in",
        f"<p class=eyebrow>Scheduling assistant settings</p><h1>{html.escape(state.business_name)}</h1>"
        "<p class=lead>Enter the business mobile on file and we'll text you a sign-in code. No password to remember.</p>"
        + _flash(error, notice)
        + "<form method=post action=/client/login><label for=mobile>Business mobile</label>"
        "<input id=mobile name=mobile type=tel autocomplete=tel inputmode=tel required maxlength=24 placeholder='704 555 0123'>"
        "<p><button type=submit class=primary>Text me a code</button></p></form>",
        main_class="signin",
    )


def _verify_form(state, error: str = "") -> HTMLResponse:
    return _page(
        "Enter code",
        f"<p class=eyebrow>{html.escape(state.business_name)}</p><h1>Check your phone</h1>"
        "<p class=lead>Enter the 6-digit code we just texted. It expires in ten minutes.</p>"
        + _flash(error)
        + "<form method=post action=/client/verify><label for=code>Sign-in code</label>"
        "<input id=code name=code class=code inputmode=numeric autocomplete=one-time-code pattern='[0-9]{6}' required maxlength=6 autofocus>"
        "<p><button type=submit class=primary>Sign in</button></p></form>"
        "<p><a href=/client/login>Didn't get it? Send a new code</a></p>",
        main_class="signin",
    )


# --- the Messages page ----------------------------------------------------------

def _count_label(text: str) -> str:
    chars, parts, plain = sms_parts(text)
    label = f"{chars} characters · {parts} text{'s' if parts != 1 else ''}"
    return label if plain or parts == 1 else label + " (symbols like — shorten each text)"


def _message_card(key: str, custom: str, templates: dict[str, str], values: dict[str, str], *, asked: set[str],
                  editable: bool, field_error: str = "") -> str:
    label, when, rule = MESSAGES[key]
    default = DEFAULT_TEMPLATES[key]
    preview = preview_text(key, templates, values)
    is_custom = bool(custom)
    chips = "".join(
        f"<button type=button class=chip data-insert='{{{name}}}'>{{{name}}}</button>" for name in sorted(PLACEHOLDERS[key])
    )
    disabled = "" if editable else " disabled"
    ask = ""
    if key in OPTIONAL_QUESTIONS:
        field, ask_label = OPTIONAL_QUESTIONS[key]
        ask = (f"<label class=ask><input type=checkbox name=ask_{field} value=1{' checked' if field in asked else ''}{disabled}>"
               f"{ask_label}</label>")
    return (
        f"<section class='msg{' bad' if field_error else ''}' id=m_{key} data-key={key} data-default='{html.escape(default, quote=True)}'"
        f" data-optout='{1 if key in OPT_OUT_REQUIRED else 0}'>"
        f"<div class=msghead><h3>{html.escape(label)}</h3>"
        f"<span class='state{' custom' if is_custom else ''}' data-state>{'Customized' if is_custom else 'Standard wording'}</span></div>"
        f"<p class=when>{html.escape(when)}</p>{ask}"
        f"<div class=phone><p class=from>What the customer sees</p><div class=bubble data-preview>{html.escape(preview)}</div>"
        f"<div class=meta><span data-count>{html.escape(_count_label(preview))}</span></div></div>"
        + (f"<p class=fielderr id=e_{key}>Not saved: {html.escape(field_error)}</p>" if field_error else "")
        + f"<label for=f_{key} class=edit>Edit the wording</label>"
        f"<textarea id=f_{key} name={key} maxlength={MAX_TEMPLATE_CHARS} placeholder=\"{html.escape(default, quote=True)}\"{disabled}"
        + (f" aria-describedby=e_{key} aria-invalid=true" if field_error else "")
        + f">{html.escape(custom)}</textarea>"
        + (f"<div class=chips><span>Insert:</span>{chips}</div>" if chips else "")
        + (f"<p class=rule>{html.escape(rule)}</p>" if rule else "")
        + (f"<div class=actions><button type=submit class=text name=reset value={key} data-reset{'' if is_custom else ' hidden'}>"
           f"Use standard wording</button></div>" if editable else "")
        + "</section>"
    )


def _messages_form(state, session, *, error: str = "", notice: str = "", values: dict[str, str] | None = None,
                   asked: set[str] | None = None) -> HTMLResponse:
    """The Messages page. ``values`` are the owner's custom texts ("" = standard); when a
    save is rejected they are the texts as typed, so nothing is lost."""
    source = state.messages
    current = source.current()
    editable = source.path is not None
    if values is None:
        values = {key: (current.templates[key] if current.templates[key] != DEFAULT_TEMPLATES[key] else "") for key in FIELD_KEYS}
    if asked is None:
        asked = set(current.fields)
    templates = {key: values.get(key) or DEFAULT_TEMPLATES[key] for key in FIELD_KEYS}
    sample = preview_values(state)
    bad_key, reason = blame(error, templates) if error else (None, "")
    flash = ""
    if error:
        if bad_key:
            flash = (f"<p class='flash err' role=alert>Not saved. Fix <a href=#m_{bad_key}>{html.escape(MESSAGES[bad_key][0])}</a>: "
                     f"{html.escape(reason)}</p>")
        else:
            flash = _flash(error=f"Not saved: {error}")
    elif notice:
        flash = _flash(notice=notice)
    if not editable:
        flash += _flash(error="Message editing is not set up for this account yet. Ask your operator to enable it.")
    groups = []
    for number, (gid, heading, blurb, keys) in enumerate(GROUPS, start=1):
        cards = "".join(
            _message_card(key, values.get(key, ""), templates, sample, asked=asked, editable=editable,
                          field_error=reason if key == bad_key else "")
            for key in keys
        )
        groups.append(
            f"<section class=group id=g_{gid} aria-labelledby=h_{gid}><header><span class=num aria-hidden=true>{number}</span>"
            f"<div><h2 id=h_{gid}>{html.escape(heading)}</h2><p>{html.escape(blurb)}</p></div></header>{cards}</section>"
        )
    rules = (
        "<details><summary>The rules every message follows</summary><ul>"
        "<li>Texts that start or restart a conversation carry an opt-out line with the word STOP. If yours leaves it out, the opt-out line is added.</li>"
        "<li>Never promise a person or send customers to your business line. The assistant is the only one texting.</li>"
        "<li>The safety hand-off mentions 911. When the calendar fails, the text says no booking was made.</li>"
        f"<li>Up to {MAX_TEMPLATE_CHARS} characters each. Words in curly brackets, like {{business_name}}, are filled in for you; only the ones listed under each message work.</li>"
        "<li>Leave a message blank to use the standard wording. Changes apply to new conversations once you save.</li></ul></details>"
    )
    body = (
        nav_html(state, session, "Your messages", "messages")
        + f"<p class=lead>Every text <strong>{html.escape(state.business_name)}</strong>'s scheduling assistant sends, in the order a customer meets them. "
        "Each card shows the text as the customer will see it; edit the wording underneath.</p>"
        + rules + flash
        + "<form method=post action=/client/messages id=messages>"
        + f"<input type=hidden name=csrf value='{html.escape(session['csrf'])}'>"
        + ("<button type=submit class=vh tabindex=-1 aria-hidden=true name=save value=1></button>" if editable else "")
        + "".join(groups)
        + ("<div class=savebar><span class=dirty data-dirty hidden>Unsaved changes</span>"
           "<button type=submit class=primary name=save value=1>Save messages</button></div>" if editable else "")
        + "</form>"
    )
    script = MESSAGES_SCRIPT.replace("__SAMPLE__", json.dumps(sample)).replace("__GSM__", json.dumps(GSM_BASIC + GSM_EXTENDED)) if editable else ""
    return _page("Your messages", body, script=script)


# Progressive enhancement only: live preview and counts, placeholder chips that
# insert at the cursor, reset without a round trip, unsaved-changes awareness.
MESSAGES_SCRIPT = (
    "(function(){var S=__SAMPLE__,G=__GSM__,F=document.getElementById('messages');if(!F)return;"
    "function fill(t){return t.replace(/\\{(\\w+)\\}/g,function(m,k){return k in S?S[k]:m;});}"
    "function parts(t){var g=true,u=0;for(var i=0;i<t.length;i++){var c=t[i];if(G.indexOf(c)<0){g=false;break;}u+='^{}\\\\[~]|€'.indexOf(c)>=0?2:1;}"
    "var n=t.length,p=g?(u<=160?1:Math.ceil(u/153)):(n<=70?1:Math.ceil(n/67));"
    "return n+' characters \\u00b7 '+p+' text'+(p!==1?'s':'')+(!g&&p>1?' (symbols like \\u2014 shorten each text)':'');}"
    "var cards=[].slice.call(F.querySelectorAll('.msg')),suffix=F.querySelector('#f_opt_out_suffix');"
    "function tpl(c){var t=c.querySelector('textarea');return t.value.trim()||c.dataset.default;}"
    "function render(c){var t=tpl(c),x=fill(t);"
    "if(c.dataset.optout==='1'&&!/\\bstop\\b/i.test(t)){var sc=suffix?suffix.closest('.msg'):null;x+=' '+fill(sc?tpl(sc):'');}"
    "x=x.replace(/\\s+/g,' ').trim();c.querySelector('[data-preview]').textContent=x;c.querySelector('[data-count]').textContent=parts(x);"
    "var cu=!!c.querySelector('textarea').value.trim(),st=c.querySelector('[data-state]');st.textContent=cu?'Customized':'Standard wording';st.className='state'+(cu?' custom':'');"
    "var r=c.querySelector('[data-reset]');if(r)r.hidden=!cu;}"
    "var dirty=false,badge=F.querySelector('[data-dirty]');function mark(){dirty=true;if(badge)badge.hidden=false;}"
    "cards.forEach(function(c){var t=c.querySelector('textarea');t.addEventListener('input',function(){render(c);if(c.dataset.key==='opt_out_suffix')cards.forEach(render);mark();});"
    "c.querySelectorAll('.chip').forEach(function(b){b.addEventListener('click',function(){var s=t.selectionStart||0,e=t.selectionEnd||0,v=t.value||'';"
    "t.value=v.slice(0,s)+b.dataset.insert+v.slice(e);t.selectionStart=t.selectionEnd=s+b.dataset.insert.length;t.focus();t.dispatchEvent(new Event('input'));});});"
    "var r=c.querySelector('[data-reset]');if(r)r.addEventListener('click',function(ev){ev.preventDefault();t.value='';t.dispatchEvent(new Event('input'));});render(c);});"
    "F.addEventListener('change',function(e){if(e.target.type==='checkbox')mark();});"
    "F.addEventListener('submit',function(){dirty=false;});"
    "window.addEventListener('beforeunload',function(e){if(dirty){e.preventDefault();e.returnValue='';}});})();"
)


# --- codes ---------------------------------------------------------------------

def send_code(state, mobile: str, now: datetime, *, purpose: str = "sign-in") -> None:
    """Text a fresh six-digit code to ``mobile`` (rate limited per number)."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    key = f"login:{mobile}:{secrets.token_hex(8)}"
    with state.store.transaction():
        # The outbox is the durable record of codes actually texted.
        recent = state.store.conn.execute(
            "SELECT count(*) FROM sms_outbox WHERE kind='login_code' AND phone=? AND created_at>?",
            (mobile, (now - CODE_WINDOW).isoformat()),
        ).fetchone()[0]
        if recent >= CODES_PER_WINDOW:
            return
        state.store.conn.execute("DELETE FROM client_login_codes WHERE phone=?", (mobile,))
        state.store.conn.execute(
            "INSERT INTO client_login_codes(phone,code_hash,expires_at,attempts,created_at) VALUES(?,?,?,0,?)",
            (mobile, _mac(state, code), (now + CODE_TTL).isoformat(), now.isoformat()),
        )
        enqueue_sms(
            store=state.store, key=key, to=mobile, from_number=state.business_number, now=now,
            kind="login_code", body=f"{state.business_name} settings {purpose} code: {code}. It expires in 10 minutes.",
        )
    run_due_sms(store=state.store, telecom=state.telecom, now=now, policy=state.followup_policy,
                keys=[key], callback_base_url=state.public_base_url, immediate=True)
    with state.store.transaction():
        # Once handed to the carrier the code has no business sitting in the outbox.
        state.store.conn.execute(
            "UPDATE sms_outbox SET body='[sign-in code]' WHERE key=? AND status IN ('sent','unknown','dead_letter')", (key,)
        )


def check_code(state, phone: str, code: str, now: datetime) -> bool:
    """True when ``code`` is the live code for ``phone``; the code is consumed on success.
    Every failure (no code, expired, too many guesses, wrong digits) looks the same."""
    code = re.sub(r"\D", "", code or "")
    with state.store.transaction():
        row = state.store.conn.execute(
            "SELECT * FROM client_login_codes WHERE phone=? AND expires_at>?", (phone, now.isoformat())
        ).fetchone()
        if row is None or row["attempts"] >= CODE_ATTEMPTS:
            return False
        state.store.conn.execute("UPDATE client_login_codes SET attempts=attempts+1 WHERE phone=?", (phone,))
        if len(code) != 6 or not hmac.compare_digest(row["code_hash"], _mac(state, code)):
            return False
        state.store.conn.execute("DELETE FROM client_login_codes WHERE phone=?", (phone,))
        return True


# --- routes --------------------------------------------------------------------

def install_routes(app):
    state = app.state

    @app.get("/client", include_in_schema=False)
    @app.get("/client/", include_in_schema=False)
    def client_root(request: Request):
        return RedirectResponse("/client/messages" if _session(state, request) else "/client/login", status_code=303)

    @app.get("/client/login", include_in_schema=False)
    def login_page(request: Request):
        if _session(state, request):
            return RedirectResponse("/client/messages", status_code=303)
        return _login_form(state)

    @app.post("/client/login", include_in_schema=False)
    async def login(request: Request):
        form = await request.form()
        mobile = normalize_mobile(str(form.get("mobile", "")))
        now = _now(state)
        if mobile is None:
            return _login_form(state, error="Enter the mobile number as digits, like 704 555 0123.")
        owner = getattr(state, "owner_mobile", "")
        if owner and hmac.compare_digest(mobile, owner):
            send_code(state, mobile, now)
        # Same answer either way so the page never confirms which number is on file.
        response = RedirectResponse("/client/verify", status_code=303)
        pending = secrets.token_urlsafe(24)
        with state.store.transaction():
            state.store.conn.execute(
                "INSERT INTO client_sessions(token_hash,csrf,phone,expires_at,created_at,pending) VALUES(?,?,?,?,?,1)",
                (_mac(state, pending), secrets.token_urlsafe(24), mobile, (now + CODE_TTL).isoformat(), now.isoformat()),
            )
        response.set_cookie(PENDING_COOKIE, pending, secure=_secure(state), httponly=True, samesite="lax",
                            max_age=int(CODE_TTL.total_seconds()), path="/client")
        return response

    def _pending(request: Request):
        token = request.cookies.get(PENDING_COOKIE, "")
        if not token:
            return None
        now = _now(state)
        with state.store.lock:
            row = state.store.conn.execute(
                "SELECT * FROM client_sessions WHERE token_hash=? AND pending=1 AND expires_at>?",
                (_mac(state, token), now.isoformat()),
            ).fetchone()
        return dict(row) if row else None

    @app.get("/client/verify", include_in_schema=False)
    def verify_page(request: Request):
        if _session(state, request):
            return RedirectResponse("/client/messages", status_code=303)
        if not _pending(request):
            return RedirectResponse("/client/login", status_code=303)
        return _verify_form(state)

    @app.post("/client/verify", include_in_schema=False)
    async def verify(request: Request):
        pending = _pending(request)
        if not pending:
            return RedirectResponse("/client/login", status_code=303)
        form = await request.form()
        now = _now(state)
        # One message for a wrong code, an expired code, too many guesses and a
        # number that is not on file, so the page never confirms which number is.
        if not check_code(state, pending["phone"], str(form.get("code", "")), now):
            return _verify_form(state, error=CODE_FAILURE)
        with state.store.transaction():
            state.store.conn.execute("DELETE FROM client_sessions WHERE token_hash=?", (pending["token_hash"],))
            token = secrets.token_urlsafe(32)
            state.store.conn.execute(
                "INSERT INTO client_sessions(token_hash,csrf,phone,expires_at,created_at,pending) VALUES(?,?,?,?,?,0)",
                (_mac(state, token), secrets.token_urlsafe(24), pending["phone"], (now + SESSION_TTL).isoformat(), now.isoformat()),
            )
        response = RedirectResponse("/client/messages", status_code=303)
        response.set_cookie(SESSION_COOKIE, token, secure=_secure(state), httponly=True, samesite="lax",
                            max_age=int(SESSION_TTL.total_seconds()), path="/client")
        response.delete_cookie(PENDING_COOKIE, path="/client")
        return response

    @app.get("/client/messages", include_in_schema=False)
    def messages_page(request: Request):
        session = _session(state, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        return _messages_form(state, session)

    @app.post("/client/messages", include_in_schema=False)
    async def save_messages(request: Request):
        session = _session(state, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        form = await request.form()
        if not hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
            raise HTTPException(400, "Form expired; reload the page and try again")
        if state.messages.path is None:
            return _messages_form(state, session, error="Message editing is not set up for this account yet.")
        submitted = {key: str(form.get(key, "")).strip() for key in FIELD_KEYS}
        reset = str(form.get("reset", ""))
        if reset in submitted:
            submitted[reset] = ""  # "Use standard wording" without JavaScript
        overrides = {key: value for key, value in submitted.items() if value}
        asked = {field for field in ("phone", "email") if form.get(f"ask_{field}")}
        if asked:
            overrides["fields"] = ", ".join(("service", "location", "preferred_time", "name", *[f for f in ("phone", "email") if f in asked]))
        try:
            write_message_file(state.messages.path, overrides)
        except MessageTemplateError as exc:
            return _messages_form(state, session, error=str(exc), values=submitted, asked=asked)
        state.messages.current()  # pick up the new file right away
        return _messages_form(state, session, notice="Saved. New conversations use these messages from now on.")

    @app.post("/client/logout", include_in_schema=False)
    async def logout(request: Request):
        session = _session(state, request)
        form = await request.form()
        if session and hmac.compare_digest(str(form.get("csrf", "")), session["csrf"]):
            with state.store.transaction():
                state.store.conn.execute("DELETE FROM client_sessions WHERE token_hash=?", (session["token_hash"],))
        response = RedirectResponse("/client/login", status_code=303)
        response.delete_cookie(SESSION_COOKIE, path="/client")
        return response
