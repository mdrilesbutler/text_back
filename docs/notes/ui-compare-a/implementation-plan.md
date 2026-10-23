# /client redesign, variant A: implementation plan

Date 2026-10-22. Branch `ui/compare-a`. Audience: the frontend developer who builds it.

Sources, earlier wins on conflict: `decisions.md` → explorer contract
(`/tmp/claude-1001/-home-ubuntu-projects-text-back-ui-a/59990a85-5a0d-48bb-adf1-5fa3b95b8a00/scratchpad/explorer-report.md`)
→ `design-spec.md` → `direction.md`. Visual values (sizes, colours, paddings) are not repeated here; they are cited as
"spec §x". Section H lists every place this plan had to choose between sources.

## 0. Ground rules

- Frozen: route paths and methods, form field names, status codes, cookie names and attributes, every notice and error
  string, `send_code`, `check_code`, `normalize_mobile`, `_session`, `_mac`, the code and session lifetimes and the rate limit.
- Every portal HTML response keeps `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`
  and adds the CSP from decisions.md.
- Validation stays in `messages.py` and `client_settings.py`. JS never validates copy; it only routes focus to server errors.
- Templates contain no `style=` attribute, no `<style>` element and no inline executable script. The one allowed
  `<script>` without `src` is `type=application/json`. JS may write `el.style.prop = …` (CSSOM is not blocked by CSP) and
  must never call `setAttribute('style', …)` (blocked).
- Every URL is root-relative. No external host at runtime.
- Attribute quoting rule (keeps the substring tests and `csrf_of()` working): single-token values from a closed set are
  written unquoted (`id=m_{{ c.key }}`, `name=ask_phone value=1 checked`, `autocomplete=one-time-code`,
  `inputmode=numeric`, `aria-invalid=true`, `type=radio`, `data-reset hidden`). Any value that can contain a space or
  comes from owner, Google or sample data is double-quoted (`class="…"`, `aria-label="…"`, `value="{{ name }}"`,
  `data-default="…"`, `value="{{ choice.id }}"`). CSRF is always the literal `name=csrf value='{{ csrf }}'`.

---

## A. File tree

Create:

| Path | One line |
|---|---|
| `src/text_back/portal_render.py` | Jinja environment, `render()`, page headers + CSP, `ASSET_VERSION`, `PortalStatic`, `mount_static()` |
| `src/text_back/portal_styleguide.py` | `styleguide_context()`: tokens parsed from portal.css, WCAG ratios, sprite ids, specimen view models |
| `src/text_back/static/portal.css` | The one stylesheet: `@layer tokens, reset, base, layout, components, pages, utilities, motion` |
| `src/text_back/static/portal.js` | The one ES module, ~575 lines, enhancement only |
| `src/text_back/templates/client/_document.html.j2` | `<html>`, `<head>`, sprite, skip link, toast region, announcer; blocks `body`, `data` |
| `src/text_back/templates/client/base.html.j2` | Signed-in shell: topbar, account menu, nav, `main`, toast notice, `#tb-data` |
| `src/text_back/templates/client/auth.html.j2` | Signed-out layout: brand-only topbar, `.auth` column, footer caption |
| `src/text_back/templates/client/_macros.html.j2` | Primitives: icon, csrf_input, button, pill, notice, toast, field_error, otp, switch, status_block, stepper, thread_item, page_head |
| `src/text_back/templates/client/_message_card.html.j2` | Macros message_card, moment, anytime, savebar, error_summary |
| `src/text_back/templates/client/_rail.html.j2` | Macro rail |
| `src/text_back/templates/client/login.html.j2` | Sign in |
| `src/text_back/templates/client/verify.html.j2` | Enter code (byte-identical, no digits of any number) |
| `src/text_back/templates/client/messages.html.j2` | Page head, error summary, `form#messages` (spine + any time + save bar), `aside.rail` |
| `src/text_back/templates/client/business.html.j2` | Business form with live name preview |
| `src/text_back/templates/client/confirm_mobile.html.j2` | Stepper, OTP, keep form, resend form |
| `src/text_back/templates/client/calendar.html.j2` | Status block, picker or empty state, connect card |
| `src/text_back/templates/client/expired.html.j2` | HTML 400 "This page expired" |
| `src/text_back/templates/client/styleguide.html.j2` | `GET /client/styleguide` |
| `tests/test_portal_frontend.py` | New invariants (§B.10) |

Modify:

| Path | One line |
|---|---|
| `src/text_back/client_portal.py` | Drop string-built HTML; add view dataclasses, LAYOUT/ANYTIME/TRIGGERS/SCENARIOS/CHIP_NAMES/CARD_SCENARIO, FormExpired, styleguide route, `fill()` fix, save normalisation |
| `src/text_back/client_settings.py` | Builders render templates; error→field map; `StatusView`/`Choice`/`status_view()`; picker only when ready |
| `tests/test_client_portal_ui.py` | Re-point markup assertions at the new hooks (table in §B.11) |
| `docs/notes/ui-compare-a/screenshots.py` | New selectors (§F), plus styleguide, dark and expired shots |
| `docs/notes/ui-compare-a/README.md` | Rewrite last, for the new build |
| `pyproject.toml` | Already declares `jinja2>=3.1` (uncommitted); commit it with this change so `scripts/deploy.sh` installs it |

Unchanged: `templates/client/_icons.svg.j2`, `static/fonts/*`, `static/ICONS-LICENSE.txt`, `app.py`, `scripts/deploy.sh`,
`messages.py`, `reconnect.py`.

Removed from `client_portal.py`: `STYLE`, `TABS`, `nav_html`, `_page`, `_flash`, `_message_card`, `MESSAGES_SCRIPT`,
and the `html` and `json` imports. Grep result (2026-10-22): `nav_html`, `_page` and `_flash` are imported only by
`client_settings.py`, which this change rewrites. Tests import only `DEFAULT_TEMPLATES, FIELD_KEYS, GROUPS,
OPTIONAL_QUESTIONS, blame, preview_text, sms_parts` from client_portal and `remember_calendars` from client_settings
(also used by screenshots.py). Those keep their names and behaviour, as do `MESSAGES`, `FIELDS`, `fill`,
`preview_values`, `_count_label`, `CODE_FAILURE`, `send_code`, `check_code`, `normalize_mobile`, `_session`, `_now`,
`calendar_status`, `calendar_choices`, `use_calendar`, `apply_settings`.

---

## B. Python changes

### B.1 `portal_render.py` (new)

```python
TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
THEME_COOKIE = "tb_theme"
CSP = "default-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
PAGE_HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
                "Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff"}

ENV = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR), autoescape=True,
                         undefined=jinja2.StrictUndefined, trim_blocks=True, lstrip_blocks=True)
```

- `autoescape=True`, not `select_autoescape()`: the names end in `.j2`, which `select_autoescape` does not treat as HTML,
  so it would silently turn escaping off.
- `StrictUndefined`: a missing context key fails the test instead of rendering blank. Builders pass every key below.
- Jinja escapes `'` as `&#39;` (the old code produced `&#x27;`).

`ASSET_VERSION`, computed once at import:

```python
def _asset_version() -> str:
    data = (STATIC_DIR / "portal.css").read_bytes() + (STATIC_DIR / "portal.js").read_bytes()
    return hashlib.sha256(data).hexdigest()[:8].translate(str.maketrans("0123456789", "ghijklmnop"))
```

Letters only, so `?v=` can never put `0123` or any digit run into the verify page (a hex prefix contains `0123` about
once in 13,000 builds).

`render(request, name, *, status_code=200, headers=None, **context) -> HTMLResponse`:
1. `theme = request.cookies.get(THEME_COOKIE)`; keep it only if it is `"light"` or `"dark"`, else `None`.
2. `body = ENV.get_template(name).render(asset_v=ASSET_VERSION, theme=theme, **context)`.
3. `return HTMLResponse(body, status_code=status_code, headers={**PAGE_HEADERS, **(headers or {})})`.

No nonce, timestamp or other per-request value. The verify page must be byte-identical across requests with the same cookies.

`PortalStatic(StaticFiles)` overrides `file_response(self, full_path, stat_result, scope, status_code=200)`: call super,
then set `X-Content-Type-Options: nosniff` and `Cache-Control` to `public, max-age=31536000, immutable` when
`b"v=" in scope["query_string"]`, else `no-cache` (the fonts, which CSS references without `?v`, revalidate by ETag).

`mount_static(app)`: `app.mount("/client/static", PortalStatic(directory=STATIC_DIR), name="client-static")`.

MIME types checked on this host (Python 3.12.3): `.css` text/css, `.js` text/javascript (required for a module
script), `.woff2` font/woff2. Starlette 1.9.0, FastAPI 0.156.2, Jinja2 3.1.6.

### B.2 `client_portal.py`: view models

Frozen dataclasses (`@dataclass(frozen=True, slots=True)`), not dicts. Jinja resolves `x.items`, `x.values` and
`x.keys` on a dict to the dict methods, which breaks any field with those names.

```python
@dataclass(frozen=True, slots=True)
class Item:                 # one row of a thread, in a card well or in the rail
    kind: str               # "customer" | "textback" | "missed" | "neutral" | "booked" | "handoff"
    text: str               # sample, pill or divider text; the rendered preview for "textback"
    key: str = ""           # template key, "textback" only (becomes data-preview)
    icon: str = ""          # sprite id without "i-", pills only
    ask: str = ""           # "phone" | "email": the row exists only when that question is asked

@dataclass(frozen=True, slots=True)
class Card:
    key: str
    label: str              # MESSAGES[key][0]
    when: str               # MESSAGES[key][1]
    rule: str               # MESSAGES[key][2], "" when none
    default: str            # DEFAULT_TEMPLATES[key]               -> data-default
    saved: str              # wording in force in the FILE         -> data-saved
    value: str              # textarea content: submitted or custom text, else the default; never ""
    length: int             # len(value)
    custom: bool            # values[key] != "" (after normalisation, §B.4)
    preview: str            # preview_text(key, templates, sample)
    count: str              # _count_label(preview)
    segments: int           # sms_parts(preview)[1]
    optout_required: bool   # key in OPT_OUT_REQUIRED
    optout_added: bool      # optout_required and not re.search(r"\bstop\b", templates[key], re.I)
    optional: str           # "phone" | "email" | ""
    switch_label: str       # OPTIONAL_QUESTIONS[key][1] or ""
    asked: bool             # switch state to render (as submitted, on a rejected save)
    asked_saved: bool       # switch state in the file                -> data-saved-checked
    branch: bool
    chips: tuple[tuple[str, str], ...]   # (("{business_name}", "Business name"), ...), sorted by token
    before: tuple[Item, ...]             # TRIGGERS[key][0]
    after: tuple[Item, ...]              # TRIGGERS[key][1]
    scenario: str           # CARD_SCENARIO[key]                     -> data-scenario
    sync: str               # bubble to ring in the rail: key, or "intro" for opt_out_suffix -> data-sync
    error: str              # blame() reason when this card is the offender, else ""
    dirty: bool = False     # styleguide specimen only

@dataclass(frozen=True, slots=True)
class QSet:     eyebrow: str; parent: Card; branches: tuple[Card, ...]
@dataclass(frozen=True, slots=True)
class Moment:   id: str; heading: str; blurb: str; icon: str; sets: tuple[QSet, ...]
@dataclass(frozen=True, slots=True)
class Scenario: id: str; label: str; thread: tuple[Item, ...]
@dataclass(frozen=True, slots=True)
class Rail:     business_name: str; initials: str; scenarios: tuple[Scenario, ...]
```

### B.3 `client_portal.py`: shared structures

Placed under `MESSAGES`/`GROUPS`. `GROUPS` is not edited (test_client_portal_ui asserts its headings, including "You step in").

```python
_BLURB = {gid: blurb for gid, _, blurb, _ in GROUPS}

# (moment id, H2, node icon, ((parent key, (branch keys, ...)), ...))
LAYOUT = (
    ("missed", "Missed call", "phone-missed", (("intro", ()),)),
    ("questions", "The questions", "message-circle-question", (
        ("prompt_service", ()), ("prompt_location", ()),
        ("prompt_preferred_time", ("preferred_time_reprompt",)), ("prompt_name", ()),
        ("prompt_phone", ("phone_reprompt",)), ("prompt_email", ("email_reprompt",)))),
    ("booking", "Booking", "calendar-check", (("booking_confirmation", ("slot_unavailable", "booking_error")),)),
    ("noreply", "No reply", "clock", (("followup_1", ()), ("followup_2", ()))),
    ("owner", "Owner steps in", "hand", (("handoff_ack", ()), ("handoff_ack_safety", ()))),
)
ANYTIME = ("keywords", "START, HELP and STOP", "",
           (("opt_in", ()), ("help", ()), ("opt_out_ack", ()), ("opt_out_suffix", ())))

def _c(text, ask=""):        return ("customer", text, "", ask)
def _t(key, ask=""):         return ("textback", key, "", ask)
def _p(kind, text, icon=""): return (kind, text, icon, "")      # kind: missed | neutral | booked
def _h(text):                return ("handoff", text, "", "")

MISSED = _p("missed", "Missed call · just now")
BOOKED = _p("booked", "Booked · on your calendar", "check")

TRIGGERS = {   # key -> (rows before the TextBack bubble, rows after); keys not listed have none
    "intro": ((MISSED,), ()),
    "preferred_time_reprompt": ((_c("Sometime next week"),), ()),
    "phone_reprompt": ((_c("Use my work phone"),), ()),
    "email_reprompt": ((_c("alex at example"),), ()),
    "slot_unavailable": ((_c("Wednesday at 10"),), ()),
    "booking_confirmation": ((), (BOOKED,)),
    "followup_1": ((_p("neutral", "No reply", "clock"),), ()),
    "followup_2": ((_p("neutral", "Still no reply", "clock"),), (_p("neutral", "Texts stop here"),)),
    "handoff_ack": ((_c("Can I just talk to the owner about pricing?"),), ()),
    "handoff_ack_safety": ((_c("A big limb just came down on the power line by our house"),), ()),
    "opt_in": ((_c("START"),), ()),
    "help": ((_c("HELP"),), ()),
    "opt_out_ack": ((_c("STOP"),), ()),
}

SCENARIOS = (   # radio order = spec §3.17 markup
    ("booked", "Books a job", (
        MISSED, _t("intro"), _c("Yes, I need some tree work."), _t("prompt_service"),
        _c("Tree removal. An oak is leaning toward the house."), _t("prompt_location"), _c("12 Elm St"),
        _t("prompt_preferred_time"), _c("Thursday at 4"), _t("prompt_name"), _c("Alex Rivera"),
        _t("prompt_phone", "phone"), _c("YES", "phone"), _t("prompt_email", "email"), _c("alex@example.com", "email"),
        _t("booking_confirmation"), BOOKED)),
    ("retry", "Second try", (
        _p("neutral", "After the job and address"), _t("prompt_preferred_time"), _c("Sometime next week"),
        _t("preferred_time_reprompt"), _c("Wednesday at 10"), _t("prompt_name"), _c("Alex Rivera"),
        _t("prompt_phone", "phone"), _c("Use my work phone", "phone"), _t("phone_reprompt", "phone"), _c("YES", "phone"),
        _t("prompt_email", "email"), _c("alex at example", "email"), _t("email_reprompt", "email"),
        _c("alex@example.com", "email"), _t("slot_unavailable"), _c("Thursday at 4"), _t("booking_confirmation"), BOOKED)),
    ("noreply", "No reply", (
        MISSED, _t("intro"), _p("neutral", "No reply", "clock"), _t("followup_1"),
        _p("neutral", "Still no reply", "clock"), _t("followup_2"), _p("neutral", "Texts stop here"))),
    ("failed", "Calendar error", (
        _p("neutral", "After all the questions"), _t("prompt_name"), _c("Alex Rivera"), _t("booking_error"),
        _p("neutral", "No booking was made"))),
    ("needsyou", "Needs you", (
        _t("prompt_preferred_time"), _c("Can I just talk to the owner about pricing?"), _t("handoff_ack"),
        _h("You take it from here"), _p("neutral", "You get a lead with this conversation", "bell"))),
    ("safety", "Safety", (
        _t("prompt_location"), _c("A big limb just came down on the power line by our house"), _t("handoff_ack_safety"),
        _h("You take it from here"), _p("neutral", "You get an urgent lead", "bell"))),
    ("keywords", "Keywords", (_c("START"), _t("opt_in"), _c("HELP"), _t("help"), _c("STOP"), _t("opt_out_ack"))),
)

CHIP_NAMES = {
    "business_name": "Business name", "service": "Job", "when": "Day and time", "location": "Address",
    "calendar_links": "Add-to-calendar links", "links_page": "Links page", "google_link": "Google Calendar link",
    "outlook_link": "Outlook link", "ical_link": "iCal link", "invite_line": "Invite sentence",
    "invited_email": "Customer email", "event_id": "Calendar event ID", "contact_line": "Contact number sentence",
}

# First scenario whose thread holds the key's bubble. The opt-out line is shown inside the intro bubble.
CARD_SCENARIO = {
    key: next(sid for sid, _, rows in SCENARIOS if any(r[0] == "textback" and r[1] == key for r in rows))
    for key in FIELD_KEYS if key != "opt_out_suffix"
} | {"opt_out_suffix": "booked"}
```

`CARD_SCENARIO` reproduces the spec §3.17 card-to-scenario table exactly. Pills with no icon in the spec ("Texts stop
here", "After the job and address", "After all the questions", "No booking was made") get none.

Builders:

| Function | Returns | Notes |
|---|---|---|
| `initials(name: str) -> str` | "OP" | First letter of the first two `[A-Za-z0-9]+` words, upper-cased; "TB" if none |
| `_item(row, templates, sample) -> Item` | Item | `textback` rows: `Item("textback", preview_text(key, templates, sample), key=key, ask=ask)` |
| `card_view(key, *, values, templates, current, sample, asked, asked_saved, branch, error, dirty=False) -> Card` | Card | `value = values.get(key) or DEFAULT_TEMPLATES[key]`; `saved = current.templates[key]`; `chips = tuple(("{%s}" % n, CHIP_NAMES[n]) for n in sorted(PLACEHOLDERS[key]))` |
| `rail_view(state, templates, sample) -> Rail` | Rail | One `Scenario` per SCENARIOS row |
| `messages_view(state, *, values=None, asked=None, error="") -> dict` | context part | Steps below |

`messages_view` steps:
1. `current = state.messages.current()`; `editable = state.messages.path is not None`.
2. `values` defaults to `{k: current.templates[k] if current.templates[k] != DEFAULT_TEMPLATES[k] else "" for k in FIELD_KEYS}`.
3. `asked_saved = set(current.fields) & {"phone", "email"}`; `asked` defaults to `asked_saved`.
4. `templates = {k: values.get(k) or DEFAULT_TEMPLATES[k] for k in FIELD_KEYS}`; `sample = preview_values(state)`.
5. `bad_key, reason = blame(error, templates) if error else (None, "")`.
6. Moments from LAYOUT (blurb `_BLURB[id]`); `anytime` from ANYTIME. `QSet.eyebrow = "Optional questions"` on the first
   set whose parent is in OPTIONAL_QUESTIONS, else "".

### B.4 Fixes in existing helpers

1. **`fill()` crash (pre-existing bug).** It catches `(ValueError, IndexError, KeyError)`. Verified on this branch:
   posting `intro="Hi {a.b}"` is rejected by validation ("placeholders must look like {business_name}"), then the
   rejected-save re-render calls `preview_text`, and `format_map` raises `AttributeError`. The owner gets a 500 and loses
   everything typed. `{business_name[x]}` raises `TypeError` the same way. Catch
   `(ValueError, IndexError, KeyError, AttributeError, TypeError)`. Covered by test §B.10 #8.
2. **Default normalisation in `save_messages`,** right after `submitted` is built and before `reset` is applied:
   ```python
   def _norm(text: str) -> str:
       return " ".join(text.split())
   for key, value in submitted.items():
       if _norm(value) == _norm(DEFAULT_TEMPLATES[key]):
           submitted[key] = ""
   ```
   `write_message_file` already drops default-equal values from the file. This step is what makes a rejected-save
   re-render show "Standard wording" for untouched pre-filled editors, and keeps `values` and `blame()` consistent.

### B.5 Handlers in `client_portal.install_routes`

Shell context, built by `_shell(state, session, *, title, nav, notice="", page_error="", tb_data=None) -> dict`:

| Key | Type | Value |
|---|---|---|
| `title` | str | Page name; `_document` appends " · TextBack" |
| `business_name` | str | `state.business_name` |
| `nav_active` | str \| None | "messages", "business", "calendar" or None |
| `csrf` | str | `session["csrf"]` |
| `signed_in_with` | str | `format_contact_number(session["phone"])` |
| `notice` | str | Success text (becomes the toast); "" if none |
| `page_error` | str | Danger notice text; "" if none |
| `tb_data` | dict \| None | JSON for portal.js; only Messages sets it |

`render()` adds `asset_v: str` and `theme: str | None`.

Auth context (login, verify): `title: str`, `business_name: str`, `error: str`. Nothing else: no csrf, no `tb_data`,
no phone number of any kind.

Builders take `request` first (render needs the theme cookie); their names stay:

| Route | Builder | Template | Title |
|---|---|---|---|
| (install start) | `mount_static(app)`, then register the `FormExpired` handler | — | — |
| GET/POST `/client/login` | `_login_form(request, state, *, error="")` | login.html.j2 | Sign in |
| GET/POST `/client/verify` | `_verify_form(request, state, *, error="")` | verify.html.j2 | Enter code |
| GET/POST `/client/messages` | `_messages_form(request, state, session, *, error="", notice="", page_error="", values=None, asked=None)` | messages.html.j2 | Messages |
| POST `/client/logout` | unchanged | — | — |
| GET `/client/styleguide` (new) | `styleguide_context(state, session)` | styleguide.html.j2 | Styleguide |

Messages context (added to the shell; nav "messages"):

| Key | Type | Value |
|---|---|---|
| `editable` | bool | `state.messages.path is not None` |
| `max_chars` | int | `MAX_TEMPLATE_CHARS` (480) |
| `moments` | tuple[Moment, ...] | 5, from LAYOUT |
| `anytime` | Moment | keywords |
| `error_summary` | dict \| None | `{"key": bad_key or "", "label": MESSAGES[bad_key][0] if bad_key else "", "reason": reason if bad_key else error}` |
| `savebar_initial` | str | "error" if `error_summary`, "saved" if `notice`, else "clean" |
| `asked` | tuple[str, ...] | Asked questions, used to hide rail rows when read-only |
| `rail` | Rail | `rail_view(state, templates, sample)` |
| `tb_data` | dict \| None | editable: `{"sample": preview_values(state), "gsm": GSM_BASIC, "ext": GSM_EXTENDED}`; else None |

`save_messages` changes (everything else stays):
1. CSRF mismatch: `raise FormExpired("/client/messages")` instead of `HTTPException(400, …)`.
2. No messages file: pass `page_error="Message editing is not set up for this account yet."` (it was `error=`, which
   would now go through `blame()` into the error summary).
3. Default normalisation (§B.4.2).

CSRF-expired page:

```python
class FormExpired(Exception):
    def __init__(self, reload_url: str):
        self.reload_url = reload_url

@app.exception_handler(FormExpired)
async def _form_expired(request: Request, exc: FormExpired):
    session = _session(state, request)
    if not session:
        return RedirectResponse("/client/login", status_code=303)
    nav = exc.reload_url.rsplit("/", 1)[-1]          # messages | business | calendar
    return render(request, "client/expired.html.j2", status_code=400,
                  **_shell(state, session, title="This page expired", nav=nav), reload_url=exc.reload_url)
```

Styleguide route:

```python
@app.get("/client/styleguide", include_in_schema=False)
def styleguide_page(request: Request):
    session = _session(state, request)
    if not session:
        return RedirectResponse("/client/login", status_code=303)
    from text_back.portal_styleguide import styleguide_context   # imports client_settings; avoid a cycle
    return render(request, "client/styleguide.html.j2", headers={"X-Robots-Tag": "noindex"},
                  **styleguide_context(state, session))
```

Static mount and route order: `mount_static(app)` is the first statement of `client_portal.install_routes`, which
`create_app` already calls at app.py:342-343 after reconnect's routes. `app.py` does not change. No route matches
`/client/static/*`; `/client` and `/client/` are exact routes.

Theme cookie: the server only reads it, in `render()`. JS writes it. Name `tb_theme`, path `/client`, values
`light|dark`, absent means System.

Byte-identical verify page: `verify.html.j2` extends `auth.html.j2`, which renders no csrf, no number, no `tb_data`
and no time. Its inputs are `business_name`, `error`, `asset_v` and `theme`. Keep it that way.

### B.6 `client_settings.py`

Constants, used by both the validators and the map so they cannot drift:

```python
NAME_ERROR = f"Enter a business name of 1 to {NAME_MAX} characters."
CONTACT_ERROR = "Enter the customer phone number as digits, like 704 555 0123, or leave it blank."
MOBILE_ERROR = "Enter your mobile as digits, like 704 555 0123."
ERROR_FIELD = {NAME_ERROR: "business_name", CONTACT_ERROR: "business_contact", MOBILE_ERROR: "owner_mobile"}
```

`_checked_form(request, session, reload_url)` raises `FormExpired(reload_url)`. Callers pass `"/client/business"`
(business and confirm) or `"/client/calendar"`. Import `FormExpired` from client_portal; drop the imports of `_flash`,
`_page` and `nav_html`, the `html` import, `_ICONS` and `_status_block`.

`_business_form(request, state, session, *, error="", notice="", values=None)`, template business.html.j2, title
"Business", nav "business":

| Key | Type | Value |
|---|---|---|
| `values` | dict[str, str] | `business_name`, `business_contact`, `owner_mobile`: submitted, else saved (mobile formatted) |
| `name_max` | int | `NAME_MAX` |
| `sender` | str | Formatted `business_number`, or "the number the texts come from" |
| `error` | dict \| None | `{"field": ERROR_FIELD.get(error), "message": error}` |
| `name_preview` | dict[str, str] | `text`, `template`, `suffix`, `saved_name` (below) |

`name_preview`: `templates = state.messages.current().templates`; `shown = values["business_name"].strip() or
state.business_name`; `text = preview_text("intro", templates, {**preview_values(state), "business_name": shown})`;
`template = templates["intro"]`; `suffix = fill(templates["opt_out_suffix"], {})` when the intro template has no
`\bstop\b`, else ""; `saved_name = state.business_name`.

`_confirm_form(request, state, session, pending, *, error="")`, template confirm_mobile.html.j2, title "Confirm your
new mobile", nav "business":

| Key | Type | Value |
|---|---|---|
| `pending_display` | str | `format_contact_number(pending)` |
| `error` | str | `CODE_FAILURE` or "" |
| `resend` | dict[str, str] | `{"business_name": state.business_name, "business_contact": state.business_contact or "", "owner_mobile": pending_display}` |

The resend form re-posts these to POST /client/business, which re-sends through `send_code` and its 3-per-15-minutes
limit (decision 9). The keep form posts `cancel=1` to /client/business/confirm. GET /client/business/keep stays; nothing links to it.

Calendar view models:

```python
@dataclass(frozen=True, slots=True)
class StatusView:
    kind: str            # ready | reauth_required | unavailable | none | managed  -> data-status
    pill_variant: str    # success | warning | danger | info
    pill_icon: str
    pill_word: str
    title: str
    detail: Markup
    meta: tuple[tuple[str, str], ...]

@dataclass(frozen=True, slots=True)
class Choice:
    id: str; name: str; main: bool; in_use: bool
```

`status_view(view: dict, label: str) -> StatusView`. Kind: `none` for stub; `managed` for microsoft/icloud;
`ready` or `reauth_required` as returned by Google; any other Google status, or a `CalendarProviderError`, is
`unavailable`. Copy is the spec §3.9 table (preserved strings). The ready detail is
`Markup("Google Calendar is connected. Appointments are checked against and booked on <strong>{}</strong>.").format(label)`;
markupsafe escapes the label, and test_client_settings expects exactly `<strong>Personal</strong>`. Managed: title
`f"{provider.title()} calendar connected"`, detail `Markup("Your {} calendar is connected and managed by your operator.").format(provider)`.

`_calendar_page(request, state, session, *, error="", notice="", picker_error="")`, template calendar.html.j2, title
"Calendar", nav "calendar":

| Key | Type | Value |
|---|---|---|
| `status` | StatusView | |
| `connect` | dict \| None | Google and `can_connect`: `{"verb": "Reconnect" if kind == "ready" else "Connect", "primary": kind != "ready", "after_picker": kind == "ready"}` |
| `cannot_connect` | bool | Google and not `can_connect` |
| `picker` | tuple[Choice, ...] \| None | Only when `kind == "ready"` and more than one choice (decision 2) |
| `only_calendar` | str | `kind == "ready"` with exactly one choice: its name; else "" |
| `picker_error` | str | Shown above the radios when `picker` is not None |
| `page_error` | str | `error`, or `picker_error` when `picker` is None |

`calendar_action`: "Pick one of the calendars listed." goes to `picker_error=`. "Connecting a calendar is not set up for
this account yet." stays `error=`. GET `?error=` stays `error=error[:200]`.

### B.7 `portal_styleguide.py` (new)

`styleguide_context(state, session) -> dict` = `_shell(state, session, title="Styleguide", nav=None)` plus:

| Key | Type | Source |
|---|---|---|
| `colors` | tuple[tuple[str, str, str], ...] | (token, light, dark) parsed from the portal.css marker blocks (§D.3) |
| `contrast` | tuple[tuple[str, str, float, float, float], ...] | (fg, bg, light ratio, dark ratio, need) for `CONTRAST_PAIRS`, the token pairs of spec §1.3 |
| `icons` | tuple[str, ...] | `re.findall(r'id="i-([a-z0-9-]+)"', sprite)`: 55 today |
| `chips` | tuple[tuple[str, str], ...] | Every CHIP_NAMES entry as ("{token}", name) |
| `meters` | tuple[tuple[str, int], ...] | `_count_label` and segments for 120, 200 and 400 plain characters, plus the default intro preview (non-GSM) |
| `cards` | dict[str, Card] | standard, customized, dirty, invalid, optional_off, branch, read_only, built with `card_view` and synthetic values |
| `statuses` | tuple[StatusView, ...] | All five kinds |
| `rail` | Rail | `rail_view` with DEFAULT_TEMPLATES and the live business name |

WCAG ratio: per channel `c/12.92` if `c <= 0.03928` else `((c + 0.055) / 1.055) ** 2.4`; `L = 0.2126R + 0.7152G + 0.0722B`;
ratio `(L1 + 0.05) / (L2 + 0.05)`, rounded to two places.

### B.8 Deploy

`scripts/deploy.sh` is unchanged. It runs `pip install -e '.[dev]'` (or `uv pip install`), which installs jinja2 from
pyproject. The install is editable, so templates and static files are read from the checkout. Hatchling's wheel target
`src/text_back` would also ship them, since neither directory is git-ignored.

### B.9 Security properties, mapped

| Property | Where it holds |
|---|---|
| Cookies (names, httponly, samesite, secure, path, max-age) | Handlers untouched |
| CSRF per session, `compare_digest` | Handlers untouched; markup `name=csrf value='…'` via `csrf_input` |
| Rate limits, code TTL and attempts | `send_code` and `check_code` untouched |
| Byte-identical verify page with no digits | §B.5 plus letters-only `ASSET_VERSION` |
| Escaping | `autoescape=True`; `Markup.format` for the one `<strong>` |
| Three headers + CSP | `PAGE_HEADERS` in `render()` |
| No live human, never "AI", STOP stays in the suffix | Copy only from MESSAGES and spec §6; validators untouched |

### B.10 New tests: `tests/test_portal_frontend.py`

Use the existing `make`, `sign_in`, `csrf_of` and `google_fixture` helpers.

1. Static: `portal.css` 200 text/css, `portal.js` text/javascript, a font font/woff2, all with nosniff; a `?v=` request is `immutable`.
2. Login, verify, messages, business, confirm, calendar (three states), styleguide and the expired 400 page all send the
   three old headers and the exact CSP string. Bodies have no `style=`, no `<style`, no `src=` or `href=` starting with
   `http`. Every `<script` is either `<script type=module src="/client/static/portal.js?v=` or
   `<script type=application/json id=tb-data>`. Exactly one `<link rel=stylesheet`.
3. Verify page: identical bytes for an unknown number and a wrong code (exists today), and none of `0123`, `5550123`,
   `9805550123` or the business number's digits.
4. `form#messages`: exactly 21 `<textarea`, names equal `set(FIELD_KEYS)`, no `disabled` between `<form` and `</form>`,
   and the first `type=submit` is the hidden `name=save` button.
5. Every `<form method=post` on a signed-in page contains `name=csrf value='`.
6. Posting the default intro verbatim, with doubled spaces, writes `{}` and renders "Standard wording".
7. A rejected save renders `<details class=editor open>`, `aria-invalid=true`, `e_intro` inside `aria-describedby`, and `data-initial=error`.
8. A rejected save with `intro="Hi {a.b}"` returns 200 with "Not saved" and keeps the typed text.
9. The picker is absent for `reauth_required` with two cached choices and present for `ready`.
10. `/client/styleguide` returns 303 without a session, and 200 with `X-Robots-Tag: noindex` with one.
11. A forged CSRF on /client/messages, /client/business, /client/business/confirm and /client/calendar returns 400, text/html, "This page expired".
12. Cookie `tb_theme=dark` gives `<html lang=en class=no-js data-theme=dark>`; `tb_theme=blue` gives no `data-theme`.
13. LAYOUT plus ANYTIME keys equal FIELD_KEYS, each once; TRIGGERS and SCENARIOS keys are a subset; CARD_SCENARIO covers FIELD_KEYS.
14. In portal.css the `@tokens:dark-media` and `@tokens:dark` declaration lists are identical.
15. No template file contains `\bAI\b` or any `messages.FORBIDDEN_PHRASES` entry. Scan the template files only: the
    owner-facing MESSAGES rules mention "business line" on purpose.

### B.11 Existing tests

Stay green with no edit (checked against this plan): all of test_client_portal.py, test_client_settings.py,
test_contact_fields.py, test_messages.py and test_no_live_human_copy.py. They depend on:
- `name=csrf value='…'`;
- `value="Oak &amp; Pine Tree Care"` (double-quoted value);
- "Save messages" absent when read-only;
- `name=ask_email value=1 checked`, in exactly that attribute order;
- `<strong>Personal</strong>`;
- "Connect Google Calendar" absent when `can_connect` is false, so no hidden copy and no JS string;
- "Confirm your new mobile" absent on the business page;
- `/client/business/confirm` present while a change is pending.

test_client_portal_ui.py, re-point (these are allowed to go red):

| Test | Old assertion | New assertion |
|---|---|---|
| helper `card()` | `<section class='msg[^']*' id=m_{key} .*?</section>` | `<article class="msg[^"]*" id=m_{key} .*?</article>` |
| renders_groups | "Save messages" | "Save changes" and `data-savebar` |
| shows_rendered_preview | `Tree Care&#x27;s` | `Tree Care&#39;s` |
| rejected_save | `Not saved. Fix <a href=#m_intro>` and `class='msg bad'` | `Not saved. Fix <a href=#f_intro data-error-link>` and `msg--invalid` |
| self_contained | `<link` absent, one `<style>` | Delete; replaced by test_portal_frontend #2 |
| business step | `class='step done'>1. Details saved` | `stepper__step--done` holding "Details saved"; `aria-current=step` on "Confirm the new number" |
| calendar states | `class='status none\|warn\|err\|ok'` | `data-status=none\|reauth_required\|unavailable\|ready` |
| calendar radios | `count("<input type=radio") == 2` | Stays green (calendar radios start `<input type=radio class=radio`, theme radios start `<input class=vh-input type=radio`); better to count `name=calendar_id` |

Green as they stand: `Standard wording</span>` count == 21, `data-reset hidden`, `data-reset>`, `Customized</span>`,
`data-count>…<`, `>{typed}</textarea>`, `aria-invalid=true`, `id=g_{gid}` order, `id=m_{key}`,
`<h1>Oak &amp; Pine Tree Care</h1>`, `autocomplete=tel`, `autocomplete=one-time-code`, `inputmode=numeric`, `class=choice`.

---

## C. Templates

### C.1 Inheritance

```
_document.html.j2            blocks: body, data
├── base.html.j2             signed in. Fills body; blocks: page_class, content
│   └── messages, business, confirm_mobile, calendar, expired, styleguide
└── auth.html.j2             signed out. Fills body; block: content
    └── login, verify
```

`_document.html.j2`:

```jinja
<!doctype html>
<html lang=en class=no-js{% if theme %} data-theme={{ theme }}{% endif %}>
<head>
<meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name=color-scheme content="light dark">
<meta name=theme-color media="(prefers-color-scheme: light)" content="#ffffff">
<meta name=theme-color media="(prefers-color-scheme: dark)" content="#0c0a09">
<meta name=robots content=noindex>
<meta name=format-detection content="telephone=no">
<title>{{ title }} · TextBack</title>
<link rel=preload href=/client/static/fonts/source-sans-3-var-latin.woff2 as=font type=font/woff2 crossorigin>
<link rel=preload href=/client/static/fonts/archivo-600-latin.woff2 as=font type=font/woff2 crossorigin>
<link rel=stylesheet href="/client/static/portal.css?v={{ asset_v }}">
<script type=module src="/client/static/portal.js?v={{ asset_v }}"></script>
</head>
<body>
{% include "client/_icons.svg.j2" %}
<a class=skip href=#main>Skip to content</a>
{% block body %}{% endblock %}
<div class=toast-region data-toast-region></div>
<div class=vh id=announcer aria-live=polite></div>
{% block data %}{% endblock %}
</body>
</html>
```

- Preload hrefs carry no `?v`. They must equal the `@font-face` `url()` byte for byte, or each font downloads twice.
- Module scripts are deferred by default: no `defer` attribute.
- `.toast-region` is not a live region. `#announcer` is the only one, so a toast is read once.

`base.html.j2`:

```jinja
{% extends "client/_document.html.j2" %}
{% from "client/_macros.html.j2" import icon, csrf_input, toast %}
{% block body %}
<div class=shell>
  <header class=topbar>
    <a class=brand href=/client/messages>{{ icon("message-square-text", "brand__icon") }}<span>TextBack</span></a>
    <span class=topbar__sep aria-hidden=true></span>
    <span class=topbar__biz>{{ business_name }}</span>
    {# account menu, §C.4 #}
  </header>
  <nav class=nav aria-label=Settings>
  {% for id, label, ic in (("messages", "Messages", "message-square-text"), ("business", "Business", "store"), ("calendar", "Calendar", "calendar-days")) %}
    <a class=nav__item href=/client/{{ id }}{% if nav_active == id %} aria-current=page{% endif %}><span class=nav__icon>{{ icon(ic) }}</span><span class=nav__label>{{ label }}</span></a>
  {% endfor %}
  </nav>
  <main id=main class="page page--{% block page_class %}{% endblock %}" tabindex=-1>
    {% if notice %}{{ toast(notice) }}{% endif %}
    {% block content %}{% endblock %}
  </main>
</div>
{% endblock %}
{% block data %}{% if tb_data %}<script type=application/json id=tb-data>{{ tb_data|tojson }}</script>{% endif %}{% endblock %}
```

`tojson` escapes `<`, `>`, `&` and `'`, which makes the JSON safe in a data block. A data block does not execute, so the
CSP does not block it. Each page renders `page_error` itself, after its page head (spec §4.5 order).

`auth.html.j2`: `<header class="topbar topbar--auth">` holding the brand link to `/client/login` only, then
`<main id=main class="page auth" tabindex=-1>{% block content %}{% endblock %}<p class=auth__foot>TextBack by FluxWorks</p></main>`.

### C.2 Macros

Imported macros do not see the page context. Pass every value as an argument and never use `with context`. Every macro
that emits an id takes `idp=""` (id prefix), so the styleguide can render a component in both the light and the dark
panel without duplicate ids. Pages always pass "".

`_macros.html.j2`:

| Signature | Output |
|---|---|
| `icon(name, cls="")` | `<svg class="icon{{ ' ' ~ cls if cls }}" aria-hidden=true focusable=false><use href="#i-{{ name }}"/></svg>` |
| `csrf_input(token)` | `<input type=hidden name=csrf value='{{ token }}'>` |
| `button(label, variant="primary", type="submit", size="", block="", icon_name="", name="", value="", loading="", hook="", hidden=False)` | `<button type=… class="btn btn--{variant}[ btn--{size}][ btn--{block}]"[ name=… value=…][ data-loading="…"][ {hook}][ hidden]>[icon]{label}</button>`. `block` is "" / "block" / "block-phone". `hook` is a bare attribute from a closed set: data-save, data-discard, data-show-error, data-connect, data-resend, data-cancel, data-demo-toast, data-demo-motion |
| `pill(variant, icon_name, word, hook="", hidden=False)` | `<span class="pill pill--{variant}"[ {hook}][ hidden]>{icon}{word}</span>`: the word is last, so `…Standard wording</span>` holds |
| `notice(kind, text, title="")` | `.notice.notice--{kind}`, `role=alert` for danger else `role=status`, icon per spec §3.11 |
| `toast(text, kind="success")` | §C.4 |
| `field_error(id, text)` | `<p class=field-error id={id}>{icon circle-alert}<span>{text}</span></p>` |
| `otp(id="code", error="", help_id="", value="", autofocus=True, idp="")` | §C.4 |
| `switch(field, label, on, saved_on, idp="")` | §C.4 |
| `status_block(s, idp="")` | §C.4 |
| `stepper()` | §C.4 |
| `thread_item(it, tag="div", hide=False)` | §C.4; `tag="li"` in the rail |
| `page_head(title, lead, meta="", jump=False)` | `.page-head`: h1, `p.lead`, optional `p.page-head__meta` with `i-info`, optional `a.page-head__jump href=#conversation` |

`_message_card.html.j2`: `message_card(c, editable, max_chars, idp="")`, `moment(m, editable, max_chars, idp="")`,
`anytime(m, editable, max_chars, idp="")`, `savebar(initial)`, `error_summary(es)`.
`_rail.html.j2`: `rail(r, editable=True, asked=())`.

Imports: `_message_card.html.j2` starts with `{% from "client/_macros.html.j2" import icon, pill, switch, field_error, thread_item %}`; `_rail.html.j2` with `{% from "client/_macros.html.j2" import icon, thread_item %}`; pages import what they call.

### C.3 Pages

| Template | Order of contents |
|---|---|
| login | `p.eyebrow.eyebrow--accent` "Scheduling assistant settings"; bare `<h1>{{ business_name }}</h1>`; `p.lead`; `form method=post action=/client/login` with `.field` (label for=mobile; `<input id=mobile name=mobile class="input input--tel tnum" type=tel autocomplete=tel inputmode=tel required maxlength=24 placeholder="704 555 0123">`, plus ` aria-invalid=true aria-describedby=mobile-error autofocus` and `field_error("mobile-error", error)` on error); button "Text me a code", `block="block"`, size lg, loading "Sending code…" |
| verify | Eyebrow `{{ business_name }}`; h1 "Check your phone"; `p.lead id=code-help`; form `action=/client/verify` with `<label for=code>Sign-in code</label>` and `otp(help_id="code-help", error=error)`; button "Sign in", loading "Signing in…"; `a.auth__link href=/client/login` "Didn't get it? Send a new code". No placeholder |
| messages | `page_head(..., jump=True)`; `error_summary` if set; `notice("danger", page_error)` if set; `notice("info", "Message editing is not set up for this account yet. Ask your operator to enable it.")` if not editable; `<div class=msg-layout>`; editable: `<form method=post action=/client/messages id=messages class=msg-list>` with `csrf_input`, then exactly `<button type=submit class=vh tabindex=-1 aria-hidden=true name=save value=1></button>`, `<ol class=moments aria-label="The conversation, in order">` of `moment()`, `anytime()`, `savebar(savebar_initial)`, `</form>`. Read-only: `<div class=msg-list>` with the same lists and no csrf, hidden button or save bar. Then `rail(rail, editable, asked)`; `</div>` |
| business | `page_head`; business error summary when `error` (`<strong>Not saved.</strong> <a href=#{{ error.field }} data-error-link>{{ error.message }}</a>`, plain text when field is None); `page_error`; `form method=post action=/client/business class=page__body`: csrf, `.card` with three `.field`s (`value="{{ values.x }}"` double-quoted; the field named by `error.field` gets `aria-invalid=true` and `field_error("{field}-error", …)`), the name field followed by `.well.field-preview` (eyebrow "In the first text" and `<p class=sms__bubble data-name-preview data-template="…" data-suffix="…" data-saved-name="…">`), then button "Save business details", `block="block-phone"`, loading "Saving…" |
| confirm_mobile | h1 "Confirm your new mobile"; `stepper()`; lead with `<strong class=tnum>{{ pending_display }}</strong>`; confirm form (csrf, `.card` with label "Code from the text" and `otp(error=error)`, button "Confirm new mobile", loading "Confirming…"); keep form (csrf, `<button type=submit class="btn btn--secondary btn--block-phone" name=cancel value=1 data-cancel>Keep my current mobile</button>`); resend form `action=/client/business` (csrf, three `<input type=hidden … value="…">` from `resend`, "Didn't get it?" plus a ghost button "Send the code again", hook data-resend, loading "Sending…") |
| calendar | `page_head`; `page_error`; `status_block(status)`; connect card if `connect and not connect.after_picker`; picker card if `picker` (form with csrf, `<fieldset aria-describedby=picker-error?>`, legend, help, `field_error("picker-error", picker_error)` above the list, then one `<label class=choice><input type=radio class=radio name=calendar_id value="{{ ch.id }}"{% if ch.in_use %} checked{% endif %}>…</label>` per choice with " (main calendar)" meta and an "In use" pill, button "Use this calendar", loading "Saving…"); `.empty` if `only_calendar`; connect card if `connect and connect.after_picker`; `notice("info", …)` with `data-connect-note` if `cannot_connect`. Connect card: h2 "What Google will ask", the four-item `ul` (spec §6.5), `form data-connect` with csrf and `<input type=hidden name=action value=connect>`, button "{verb} Google Calendar", primary or secondary per `connect.primary`, loading "Opening Google…" |
| expired | `page_head("This page expired", "Reload the page and try again. Your changes were not saved.")`; `<a class="btn btn--primary" href="{{ reload_url }}">Reload</a>` |
| styleguide | Anchor list, then the 15 sections of spec §4.6, each `<section class=sg-section id=sg-{name}>` with an h2 and a `.sg-pair` holding `<div class=sg-panel data-theme=light>` and `<div class=sg-panel data-theme=dark>`, which call the same macros with `idp="l-"` and `idp="d-"`. The page has no `<form>`, so submit buttons inside specimens do nothing. OTP specimens pass `autofocus=False` and never contain `0123`. The real `disabled` attribute may appear only here |

### C.4 Markup skeletons

Message card:

```jinja
{% macro message_card(c, editable, max_chars, idp="") -%}
<article class="msg{% if c.branch %} msg--branch{% endif %}{% if c.optional %} msg--optional{% endif %}{% if c.error %} msg--invalid{% endif %}" id={{ idp }}m_{{ c.key }} data-card={{ c.key }} data-scenario={{ c.scenario }} data-sync={{ c.sync }} data-optout={{ 1 if c.optout_required else 0 }} data-default="{{ c.default }}" data-saved="{{ c.saved }}"{% if c.dirty %} data-dirty{% endif %} aria-labelledby={{ idp }}l_{{ c.key }}>
  <header class=msg__head>
    <h3 class=msg__label id={{ idp }}l_{{ c.key }}>{{ c.label }}</h3>
    <p class=msg__when id={{ idp }}w_{{ c.key }}>{{ c.when }}</p>
  </header>
  <div class=msg__status>
    {% if c.custom %}{{ pill("success", "pencil", "Customized", hook="data-state-pill") }}{% else %}{{ pill("neutral", "check", "Standard wording", hook="data-state-pill") }}{% endif %}
    {{ pill("warning", "circle-alert", "Unsaved", hook="data-dirty-pill", hidden=not c.dirty) }}
    {% if editable %}<button type=submit name=reset value={{ c.key }} class="btn btn--ghost" data-reset{% if not c.custom %} hidden{% endif %}>{{ icon("rotate-ccw") }}Use standard wording<span class=vh> for {{ c.label }}</span></button>{% endif %}
  </div>
  {% if c.optional %}{% if editable %}{{ switch(c.optional, c.switch_label, c.asked, c.asked_saved, idp) }}{% elif c.asked %}{{ pill("success", "check", "Asked") }}{% else %}{{ pill("neutral", "x", "Not asked") }}{% endif %}{% endif %}
  {% if c.rule %}<p class=msg__rule id={{ idp }}r_{{ c.key }}>{{ icon("shield-check") }}<span>{{ c.rule }}</span></p>{% endif %}
  <div class="well msg__preview">
    {% for it in c.before %}{{ thread_item(it) }}{% endfor %}
    <div class="sms sms--textback"><span class=sms__badge>TextBack</span><p class=sms__bubble data-preview={{ c.key }}>{{ c.preview }}</p></div>
    {% for it in c.after %}{{ thread_item(it) }}{% endfor %}
  </div>
  {% if c.optional and editable %}<p class=msg__off>Not asked right now. Switch it on to add this question.</p>{% endif %}
  <div class="msg__meta{% if not c.optout_required %} msg__meta--end{% endif %}">
    {% if c.optout_required %}<a class=msg__optout href=#m_opt_out_suffix data-optout-note{% if not c.optout_added %} hidden{% endif %}>Opt-out line added</a>{% endif %}
    <span class=msg__countwrap><span class="count tnum" data-count>{{ c.count }}</span><span class=pips data-pips aria-hidden=true>{% for _ in range([c.segments, 5]|min) %}<i></i>{% endfor %}{% if c.segments > 5 %}<b>+</b>{% endif %}</span></span>
  </div>
  {% if editable %}
  <details class=editor{% if c.error %} open{% endif %}>
    <summary class=editor__summary>{{ icon("pencil") }}Edit wording<span class=vh>: {{ c.label }}</span>{{ icon("chevron-down", "editor__chev") }}</summary>
    <div class=editor__body>
      {% if c.error %}{{ field_error(idp ~ "e_" ~ c.key, "Not saved: " ~ c.error) }}{% endif %}
      <label class=vh for={{ idp }}f_{{ c.key }}>Wording for {{ c.label }}</label>
      <textarea class=textarea id={{ idp }}f_{{ c.key }} name={{ c.key }} maxlength={{ max_chars }} rows=4 spellcheck=true autocapitalize=sentences enterkeyhint=done aria-describedby="{{ idp }}x_{{ c.key }}{% if c.rule %} {{ idp }}r_{{ c.key }}{% endif %}{% if c.error %} {{ idp }}e_{{ c.key }}{% endif %}"{% if c.error %} aria-invalid=true{% endif %}>{{ c.value }}</textarea>
      <p class=field-help id={{ idp }}x_{{ c.key }}>Texts are sent as one paragraph. Leave it empty to use the standard wording.</p>
      {% if c.chips %}
      <div class=chips data-chips hidden><span class="eyebrow eyebrow--muted">Insert</span>{% for token, name in c.chips %}<button type=button class=chip data-insert="{{ token }}">{{ icon("plus") }}{{ name }}<span class=vh> placeholder</span></button>{% endfor %}</div>
      <p class=chips-fallback>Words in curly brackets are filled in for you. This message can use: {% for token, name in c.chips %}{{ token }} ({{ name }}){% if not loop.last %}, {% endif %}{% endfor %}.</p>
      {% endif %}
      <p class="limit tnum" data-limit{% if c.length < 420 %} hidden{% endif %}>{{ c.length }} of {{ max_chars }} characters</p>
    </div>
  </details>
  {% endif %}
</article>
{%- endmacro %}
```

No whitespace between `>` and `{{ c.value }}`: the HTML parser drops a leading newline in a textarea.

Moment and Any time:

```jinja
{% macro moment(m, editable, max_chars, idp="") -%}
<li class=moment id={{ idp }}g_{{ m.id }} aria-labelledby={{ idp }}h_{{ m.id }}>
  <span class="moment__node{% if m.id == 'missed' %} moment__node--missed{% endif %}" aria-hidden=true>{{ icon(m.icon) }}</span>
  <div class=moment__head><h2 id={{ idp }}h_{{ m.id }}>{{ m.heading }}</h2><p>{{ m.blurb }}</p></div>
  <div class=moment__cards>
  {% for s in m.sets %}
    {% if s.eyebrow %}<p class="eyebrow eyebrow--muted moment__eyebrow">{{ s.eyebrow }}</p>{% endif %}
    <div class=qset>{{ message_card(s.parent, editable, max_chars, idp) }}{% for b in s.branches %}{{ message_card(b, editable, max_chars, idp) }}{% endfor %}</div>
  {% endfor %}
  </div>
</li>
{%- endmacro %}
```

`anytime(m, …)` renders `<section class=anytime id=g_keywords aria-labelledby=h_keywords>`, then `p.eyebrow.eyebrow--accent`
"Any time", the h2, `p.anytime__blurb` and `.anytime__cards` holding the four QSets.

Rail:

```jinja
{% macro rail(r, editable=True, asked=()) -%}
<aside class=rail id=conversation aria-labelledby=rail-title data-rail data-active=booked>
  <h2 class=rail__title id=rail-title>Conversation preview</h2>
  <fieldset class=scenarios><legend class=vh>Show conversation</legend>
  {% for s in r.scenarios %}<input class=vh-input type=radio name=scenario id=sc-{{ s.id }} value={{ s.id }}{% if loop.first %} checked{% endif %}><label class=pill-radio for=sc-{{ s.id }}>{{ s.label }}</label>{% endfor %}
  </fieldset>
  <div class=phone role=group aria-label="Sample text conversation with {{ r.business_name }}">
    <div class=phone__screen>
      <div class=phone__head><span class=phone__avatar aria-hidden=true>{{ r.initials }}</span><div class=phone__who><p class=phone__name>{{ r.business_name }}</p><p class=phone__sub>Text message</p></div></div>
      <div class=phone__log tabindex=0 aria-label=Messages data-rail-log>
      {% for s in r.scenarios %}<ol class=thread data-scenario={{ s.id }} aria-label="{{ s.label }}">{% for it in s.thread %}{{ thread_item(it, "li", hide=(not editable and it.ask and it.ask not in asked)) }}{% endfor %}</ol>{% endfor %}
      </div>
    </div>
  </div>
  <div class=phone__foot><p>Sample conversation · nothing is sent · names invented</p></div>
</aside>
{%- endmacro %}
```

The aside sits outside `form#messages`, so the scenario radios are never posted. There is no Play button (cut, §E.6).

Thread item:

```jinja
{% macro thread_item(it, tag="div", hide=False) -%}
{%- if it.kind == "customer" -%}
<{{ tag }} class="sms sms--customer"{% if it.ask %} data-ask={{ it.ask }}{% endif %}{% if hide %} hidden{% endif %}><span class=sms__badge>Customer</span><p class=sms__bubble>{{ it.text }}</p></{{ tag }}>
{%- elif it.kind == "textback" -%}
<{{ tag }} class="sms sms--textback"{% if it.ask %} data-ask={{ it.ask }}{% endif %}{% if hide %} hidden{% endif %}><span class=sms__badge>TextBack</span><p class=sms__bubble data-preview={{ it.key }}>{{ it.text }}</p></{{ tag }}>
{%- elif it.kind == "handoff" -%}
<{{ tag }} class=handoff>{{ it.text }}</{{ tag }}>
{%- else -%}
<{{ tag }} class="tpill tpill--{{ it.kind }}">{% if it.icon %}{{ icon(it.icon) }}{% endif %}{{ it.text }}</{{ tag }}>
{%- endif -%}
{%- endmacro %}
```

Save bar:

```jinja
{% macro savebar(initial) -%}
<div class=savebar data-savebar data-state=nojs data-initial={{ initial }}>
  <p class="savebar__status tnum" data-savebar-status></p>
  <div class=savebar__actions>
    <button type=button class="btn btn--ghost" data-show-error hidden>Show</button>
    <button type=button class="btn btn--danger-ghost" data-discard hidden>Discard</button>
    <button type=submit class="btn btn--primary" name=save value=1 data-save data-loading="Saving…" aria-keyshortcuts="Control+S Meta+S">Save changes</button>
  </div>
</div>
{%- endmacro %}
```

JS fills the status as `<svg class=icon…><use href="#i-…"/></svg><span class=savebar__short aria-hidden=true>2 unsaved</span><span class=savebar__long>2 unsaved changes</span>`.
Below 640 the long span is visually hidden (not `display:none`), so assistive tech still has it.

OTP:

```jinja
{% macro otp(id="code", error="", help_id="", value="", autofocus=True, idp="") -%}
{% set describedby = [help_id, (idp ~ id ~ "-error") if error else ""]|select|join(" ") %}
<div class=otp data-otp data-filled={{ value|length }}>
  <input id={{ idp }}{{ id }} name=code class=otp__input inputmode=numeric autocomplete=one-time-code pattern="[0-9]{6}" maxlength=6 required{% if autofocus %} autofocus{% endif %} spellcheck=false autocapitalize=off autocorrect=off{% if value %} value="{{ value }}"{% endif %}{% if error %} aria-invalid=true{% endif %}{% if describedby %} aria-describedby="{{ describedby }}"{% endif %}>
  <span class=otp__cells aria-hidden=true><i></i><i></i><i></i><i></i><i></i><i></i></span>
</div>
{% if error %}{{ field_error(idp ~ id ~ "-error", error) }}{% endif %}
{%- endmacro %}
```

Switch:

```jinja
{% macro switch(field, label, on, saved_on, idp="") -%}
<label class=switch-row for={{ idp }}ask_{{ field }}><span class=switch-row__text>{{ label }}</span><input type=checkbox role=switch class=switch id={{ idp }}ask_{{ field }} name=ask_{{ field }} value=1{% if on %} checked{% endif %} data-saved-checked={{ 1 if saved_on else 0 }}></label>
{%- endmacro %}
```

Status block:

```jinja
{% macro status_block(s, idp="") -%}
<section class=status data-status={{ s.kind }} aria-labelledby={{ idp }}status-title>
  {{ pill(s.pill_variant, s.pill_icon, s.pill_word) }}
  <h2 class=status__title id={{ idp }}status-title>{{ s.title }}</h2>
  <p class=status__detail>{{ s.detail }}</p>
  {% if s.meta %}<dl class=status__meta>{% for term, value in s.meta %}<dt>{{ term }}</dt><dd class=tnum>{{ value }}</dd>{% endfor %}</dl>{% endif %}
</section>
{%- endmacro %}
```

The styleguide passes `idp="l-ready-"` and so on, because it renders five status blocks per panel.

Stepper (BEM modifiers, not spec's `is-done`/`is-current`, which would collide with the styleguide's forced-state `is-*` classes):

```jinja
{% macro stepper() -%}
<ol class=stepper aria-label="Change your mobile" data-stepper>
  <li class="stepper__step stepper__step--done"><span class=stepper__dot>{{ icon("check") }}</span><span class=stepper__label><span class=vh>Done: </span>Details saved</span></li>
  <li class="stepper__step stepper__step--current" aria-current=step><span class="stepper__dot tnum">2</span><span class=stepper__label>Confirm the new number</span></li>
</ol>
{%- endmacro %}
```

Account menu (inline in base.html.j2, inside `.topbar`):

```jinja
<details class=menu data-menu>
  <summary class="menu__trigger icon-btn">{{ icon("circle-user-round", "menu__avatar") }}<span class=vh>Account</span>{{ icon("chevron-down", "menu__chev") }}</summary>
  <div class=menu__panel>
    <div class=menu__who><p class=menu__biz>{{ business_name }}</p><p class="menu__meta tnum">Signed in with {{ signed_in_with }}</p></div>
    <fieldset class=menu__theme data-theme-picker hidden>
      <legend class="eyebrow eyebrow--muted">Appearance</legend>
      <div class=pill-radios>
      {% for value, label, ic in (("system", "System", ""), ("light", "Light", "sun"), ("dark", "Dark", "moon")) %}
        <input class=vh-input type=radio name=theme id=theme-{{ value }} value={{ value }}{% if (theme or "system") == value %} checked{% endif %}><label class=pill-radio for=theme-{{ value }}>{% if ic %}{{ icon(ic) }}{% endif %}{{ label }}</label>
      {% endfor %}
      </div>
    </fieldset>
    <form method=post action=/client/logout>{{ csrf_input(csrf) }}<button type=submit class=menu__item>{{ icon("log-out") }}Sign out</button></form>
  </div>
</details>
```

The theme radios are outside every POST form. `.pill-radio` is the one component behind both the scenario switcher
and the Appearance control; spec §3.17 calls it `.scenario`.

Toast:

```jinja
{% macro toast(text, kind="success") -%}
<div class="notice notice--{{ kind }} toast" role=status data-toast data-kind={{ kind }}>
  {{ icon("circle-check" if kind == "success" else "info", "notice__icon") }}
  <p class=notice__text>{{ text }}</p>
  <button type=button class="icon-btn toast__close" data-toast-close hidden>{{ icon("x") }}<span class=vh>Dismiss</span></button>
</div>
{%- endmacro %}
```

Error summary (Messages):

```jinja
{% macro error_summary(es) -%}
<div class="notice notice--danger error-summary" id=error-summary role=alert tabindex=-1>
  {{ icon("circle-alert", "notice__icon") }}
  <p class=notice__text>{% if es.key %}Not saved. Fix <a href=#f_{{ es.key }} data-error-link>{{ es.label }}</a>: {{ es.reason }}{% else %}Not saved: {{ es.reason }}{% endif %}</p>
</div>
{%- endmacro %}
```

### C.5 UI states by page

| State | How it is produced |
|---|---|
| Empty | Calendar ready with one choice: `.empty` (spec §3.25). Calendar ready with none: picker omitted. Messages read-only: info notice and no editors |
| Loading | Every submit button carries `data-loading`; JS swaps the label, adds a spinner and sets `aria-disabled` (§E.4). Save bar `saving` state |
| Skeleton | Styleguide only. Every page is server-rendered with its data, so no page has async content to wait for |
| Error | Page: `notice--danger`. Form: error summary plus `field-error`, `aria-invalid` and the open editor. Calendar picker: `field-error` above the radios. Session: HTML 400 page |
| Success | Toast (inline `notice--success` without JS); save bar `saved` for 4000 ms |
| Disabled | `aria-disabled=true` on Save in `clean` and `saved`; read-only Messages. The `disabled` attribute is never used outside the styleguide |
| Focus, hover, pressed | `:focus-visible` global ring; hover only under `(hover: hover)`; `:active`. Styleguide forces each with `.is-focus`, `.is-hover`, `.is-active` |

---

## D. CSS architecture (`static/portal.css`)

### D.1 Layers

```css
@layer tokens, reset, base, layout, components, pages, utilities, motion;
@font-face { … Archivo 600 … }          /* spec §1.1, verbatim */
@font-face { … Source Sans 3 400 600 … }
```

The two `@font-face` rules are the only unlayered rules. Unlayered author styles beat every layer, so nothing else may
sit outside a layer.

| Layer | Contents |
|---|---|
| tokens | Spec §1.1 verbatim, in four marker blocks (§D.3), then the 640/1024/1280 token overrides |
| reset | `*, ::before, ::after { box-sizing: border-box }`, margin resets, `button, input, textarea, select { font: inherit; color: inherit }`, `:where(ul, ol)[class] { list-style: none; padding: 0 }`, `[hidden] { display: none !important }` |
| base | `html`, `body` (spec §1.1 base rules), h1–h3 roles, `p`, `a`, `:focus-visible` and `.is-focus` ring, `svg.sprite { position: absolute; width: 0; height: 0; overflow: hidden }`, `.icon { width: 1em; height: 1em; flex: none }` |
| layout | `.shell`, `.topbar`, `.nav` container (tab bar and sidebar), `.page`, `.page__body`, `.auth`, `.page-head`, `.msg-layout`, rail placement, `.moments`/`.moment` grid and spine, `.anytime` |
| components | In spec §3 order: btn, field/input/tel, textarea, otp, switch, choice, pill and badge, status, stepper, notice and error summary, field-error, toast, chip, count and pips, sms/tpill/handoff, rail/phone/pill-radio/thread, savebar, menu, nav__item, msg/well/editor/limit, skeleton, empty, card, skip |
| pages | `.sg-*` styleguide-only rules; one-off page rules (business preview well, calendar card order) |
| utilities | `.vh`, `.vh-input`, `.tnum`, `.eyebrow` and its modifiers |
| motion | Only the reduced-motion overrides (§D.8) |

Within a layer, source order decides equal specificity: block, then elements, then modifiers, then states.

### D.2 Naming

- BEM: block `.msg`, element `.msg__label`, modifier `.msg--branch`. Component-private custom properties are `--_name`.
- JS and test hooks are `data-*` attributes and ids, never classes. Classes are for styling only.
- Styled state attributes (closed list): `data-state` (savebar), `data-dirty` (msg), `data-current` (bubble),
  `data-filled` (otp), `data-active` (rail), `data-busy` (form), `data-kind` (toast), `data-leaving` (toast),
  `data-warn` (limit), `data-run` (styleguide motion). Every other `data-*` is a hook and is never styled.
- `is-hover`, `is-active` and `is-focus` exist only for styleguide specimens.
- `html.no-js` and `html.js` are the only context classes.

### D.3 Token marker blocks (parsed by portal_styleguide and test #14)

```css
@layer tokens {
  /* @tokens:light */ :root, [data-theme="light"] { … } /* @end */
  @media (prefers-color-scheme: dark) {
    /* @tokens:dark-media */ :root:not([data-theme="light"]) { … } /* @end */
  }
  /* @tokens:dark */ :root[data-theme="dark"], [data-theme="dark"] { … } /* @end */
  /* @tokens:static */ :root { … } /* @end */
  @media (min-width: 640px) { :root { … } }   /* spec §1.1 overrides */
  @media (min-width: 1024px) { :root { … } }
  @media (min-width: 1280px) { :root { … } }
}
```

Parser: `re.search(r"/\* @tokens:(\w[\w-]*) \*/.*?\{(.*?)\}\s*/\* @end \*/", …, re.S)` per name, then
`re.findall(r"--([a-z0-9-]+):\s*([^;]+);", block)`. A styleguide panel `<div data-theme="dark">` receives the dark
tokens through `[data-theme="dark"]`. `.sg-panel` sets `background: var(--bg); color: var(--text-ink)` on itself,
because the tokens change on that element and `body`'s background does not follow.

### D.4 Breakpoints and media

| Query | Used for |
|---|---|
| `(min-width: 640px)` | Token overrides (spine, gutters, card padding); `.btn--block-phone` becomes auto width; long save-bar label |
| `(min-width: 1024px)` | Shell grid and sidebar nav; `.msg-layout` two columns; sticky rail; save bar `bottom`; toast region on the right; jump link hidden; styleguide panels side by side |
| `(min-width: 1280px)` | Rail 360px (token); column gap `--space-14` |
| `(hover: hover)` | Every `:hover` rule, without exception |
| `(hover: hover) and (pointer: fine)` | 36px chips, pill-radios and `.btn--sm` |
| `(prefers-color-scheme: dark)` | Tokens layer only |
| `(prefers-reduced-motion: reduce)` | Motion layer only |
| `@supports (field-sizing: content)` | `.textarea { field-sizing: content }` |

Mobile first: base rules are the phone layout; every query is `min-width`. 768–1023 keeps the bottom tab bar (spec §2.1).

### D.5 Variants and states: the slot pattern

Variants set private slots; state rules choose which slot is painted. States are written once per block, never once per variant.

```css
@layer components {
  .btn { --_bg: transparent; --_bg-hover: var(--_bg); --_bg-active: var(--_bg-hover);
         --_fg: var(--text-ink); --_line: transparent;
         background: var(--_bg); color: var(--_fg); border: 1px solid var(--_line); /* box per spec §3.1 */ }
  .btn--primary      { --_bg: var(--accent-fill); --_bg-hover: var(--accent-fill-hover); --_bg-active: var(--accent-fill-pressed); --_fg: var(--on-accent); }
  .btn--secondary    { --_bg: var(--bg); --_bg-hover: var(--sunken); --_bg-active: var(--line); --_line: var(--line-strong); }
  .btn--ghost        { --_fg: var(--accent); --_bg-hover: var(--accent-tint); --_bg-active: var(--accent-tint-hover); }
  .btn--danger-ghost { --_fg: var(--danger-fg); --_bg-hover: var(--danger-bg); --_bg-active: var(--danger-line); }
  @media (hover: hover) { .btn:hover { background: var(--_bg-hover); } }
  .btn.is-hover { background: var(--_bg-hover); }
  .btn:active, .btn.is-active { background: var(--_bg-active); }
  .btn[aria-disabled="true"] { --_fg: var(--text-subtle); --_bg-hover: var(--_bg); --_bg-active: var(--_bg); cursor: not-allowed; }
  :is(.btn--primary, .btn--secondary)[aria-disabled="true"] { --_bg: var(--sunken); --_line: var(--line); }
}
```

The same pattern applies to `.chip`, `.pill-radio`, `.nav__item`, `.choice`, `.icon-btn`, `.menu__item` and `.pill`
(variant colours as `--_fg`, `--_bg`, `--_line`). Status variants map to the semantic tokens (spec §3.8, §3.11).

How each kind of state is expressed:

| Kind | Mechanism | Examples |
|---|---|---|
| Static variant | `--modifier` class | `.btn--primary`, `.pill--warning`, `.msg--branch`, `.notice--danger` |
| Native state | Pseudo-class | `:hover` (in media), `:active`, `:focus-visible`, `:checked`, `[open]` |
| ARIA state | Attribute | `[aria-current="page"]`, `[aria-current="step"]`, `[aria-invalid="true"]`, `[aria-disabled="true"]` |
| Server state | Modifier class rendered by Jinja | `.msg--invalid`, `.stepper__step--done` |
| JS state | Styled data attribute (§D.2 list) | `.savebar[data-state="dirty"]`, `.msg[data-dirty]`, `.sms__bubble[data-current]` |
| Forced state (styleguide) | `.is-hover`, `.is-active`, `.is-focus` next to the pseudo-class | §D.5 code |

### D.6 Specificity rules

1. Ceiling (0,2,0): block + one class, attribute or pseudo-class. Exceptions are the `:has()` rules in §D.7, which may reach (0,6,0).
2. No id selectors. Ids are hooks for JS, tests and anchors. `:has()` rules use attribute selectors:
   `.vh-input[value="retry"]`, `.switch[name="ask_phone"]`.
3. No `!important` except `[hidden] { display: none !important }` in reset, which makes `hidden` beat any component
   `display`. (For important declarations an earlier layer wins, so this one cannot be overridden.)
4. Element selectors only in reset and base. When a component needs a context, wrap it in `:where()` so it adds nothing:
   `:where(.js) .chips-fallback { display: none }`.
5. Variants never restate box properties. They set `--_` slots (§D.5).
6. A rule that styles a block inside another block belongs to the outer block's section (`.msg .well` lives with `.msg`).
7. Later layers win by design: utilities over components (`.vh` on anything), motion over every transition.
8. Never set `outline: none` without a replacement. The phone log uses an inset ring (`outline-offset: -2px`); nav items use `-4px`.

### D.7 No-JS, JS and `:has()`

| Rule | Selector |
|---|---|
| JS-only blocks hidden without JS | Rendered with the `hidden` attribute; JS removes it (chips, theme picker, toast close, save-bar buttons) |
| No-JS fallback hidden with JS | `:where(.js) .chips-fallback { display: none }` |
| Textarea | `.textarea { resize: vertical }` (rows=4 without JS); `:where(.js) .textarea { resize: none }`; `@supports (field-sizing: content) { .textarea { field-sizing: content } }` |
| Save bar | `[data-state="nojs"]` sticky; `clean`/`saved` static and no shadow; `dirty`/`error`/`saving` sticky with `--shadow-bar` |
| Scenario default | `.thread { display: none } .thread[data-scenario="booked"] { display: flex }` |
| Scenario via `:has()` | `.rail:has(.vh-input:checked) .thread { display: none }`, then per id `.rail:has(.vh-input[value="retry"]:checked) .thread[data-scenario="retry"] { display: flex }` (7 rules) |
| Scenario via JS | `.rail[data-active] .thread { display: none }`, then per id `.rail[data-active="retry"] .thread[data-scenario="retry"] { display: flex }`. JS keeps `data-active` equal to the checked radio, so both mechanisms always agree |
| Optional question off | `.msg--optional:has(.switch:not(:checked)) :is(.msg__preview, .msg__meta) { display: none }`; `.msg__off { display: none }`, shown by `.msg--optional:has(.switch:not(:checked)) .msg__off` |
| Branch of an off question | `.qset:has(> .msg--optional .switch:not(:checked)) > .msg--branch { display: none }` |
| Rail rows of an off question | `.msg-layout:has(.switch[name="ask_phone"]:not(:checked)) [data-ask="phone"] { display: none }` and the email equivalent. Scoped to `.msg-layout` (spec wrote `body:has(#ask_phone…)`) so styleguide specimens are unaffected |

Keep every `:has()` rule in its own rule block. A selector list that contains `:has()` is dropped whole by a browser
without `:has()` support, which would take the fallback with it.

Because a module script runs after parsing, the first paint can show the `no-js` state. Keep JS-only differences inside
closed editors or below the fold. The visible exceptions are the server notice moving into the toast region and the save
bar going from sticky (`nojs`) to resting (`clean`); both are accepted.

### D.8 Reduced motion

Transitions and animations are declared in the component that owns them (durations and easings from spec §5.1). The
motion layer only removes them:

```css
@layer motion {
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      transition-duration: 0.01ms; transition-delay: 0s;
      animation-duration: 0.01ms; animation-iteration-count: 1;
      scroll-behavior: auto;
    }
    .spin { animation: none; }               /* spinner stands still; the label carries the state */
    .skeleton { background-image: none; }    /* static block */
  }
}
```

No `!important` is needed: the motion layer is last, so its longhands beat the `transition` shorthands in components.
JS reads the same query (§E.1) for `scrollTo` behaviour and toast removal timing.

### D.9 Budget

At most 35 KB unminified. Expect about 200 lines of tokens and 900 of rules.

---

## E. JavaScript (`static/portal.js`)

### E.1 Module shape

One ES module, no imports, no globals, no framework. It runs once, after parsing.

```js
const root = document.documentElement;
root.classList.replace('no-js', 'js');
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const DATA = JSON.parse($('#tb-data')?.textContent || '{}');
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)');
const WIDE = matchMedia('(min-width: 1024px)');
const COPY = { /* every JS-owned string from spec §6, in one place */ };

initTheme(); initMenu(); initToasts(); initForms(); initTel(); initOtp();
const form = $('#messages');
if (form) { const bar = initSavebar(form); initCards(form, bar); initRail(form); }
initErrorFocus(); initNamePreview(); initStyleguide();
```

Each `init*` returns early when its root element is absent. Shared helpers: `announce(text, {debounce, channel})`
writes to `#announcer` (150 ms default; the save bar uses an 800 ms debounce on its own channel); `icon(name, cls)`
builds `<svg><use href="#i-…">` with `createElementNS`; `norm(s) = s.split(/\s+/).filter(Boolean).join(' ')`,
the equivalent of Python's `" ".join(s.split())`.

### E.2 Data contract

| Source | Contents | Used by |
|---|---|---|
| `#tb-data` (Messages only) | `{sample: {business_name, service, when, location, event_id, invited_email, invite_line, calendar_links, contact_line, links_page, google_link, outlook_link, ical_link}, gsm: GSM_BASIC, ext: GSM_EXTENDED}` | fill, parts |
| `article.msg` | `data-card`, `data-default`, `data-saved`, `data-optout`, `data-scenario`, `data-sync` | cards, save bar, rail sync |
| `.switch` | `data-saved-checked` (`1`/`0`) | save bar |
| `[data-savebar]` | `data-initial` (`clean`/`saved`/`error`) | save bar |
| `[data-name-preview]` | `data-template`, `data-suffix`, `data-saved-name` | business preview |
| Submit buttons | `data-loading` | form guard |

### E.3 SMS engine (identical to the server)

```js
const GSM = new Set([...(DATA.gsm || ''), ...(DATA.ext || '')]);
const EXT = new Set([...(DATA.ext || '')]);
function parts(text) {                                  // = client_portal.sms_parts
  const ch = [...text];                                 // code points, like Python len()
  if (ch.every(c => GSM.has(c))) {
    const units = ch.reduce((n, c) => n + (EXT.has(c) ? 2 : 1), 0);
    return [ch.length, units <= 160 ? 1 : Math.ceil(units / 153), true];
  }
  return [ch.length, ch.length <= 70 ? 1 : Math.ceil(ch.length / 67), false];
}
function countLabel(text) {                             // = client_portal._count_label
  const [n, k, gsm] = parts(text);
  const label = `${n} characters · ${k} text${k !== 1 ? 's' : ''}`;
  return gsm || k === 1 ? label : `${label} (symbols like — shorten each text)`;
}
function fill(t) {                                      // = client_portal.fill
  let out = '';
  for (let i = 0; i < t.length;) {
    const c = t[i];
    if ((c === '{' || c === '}') && t[i + 1] === c) { out += c; i += 2; continue; }
    if (c === '}') return t;                            // Python raises ValueError -> template unchanged
    if (c !== '{') { out += c; i += 1; continue; }
    const end = t.indexOf('}', i);
    const name = end < 0 ? '' : t.slice(i + 1, end);
    if (!/^[A-Za-z_]\w*$/.test(name)) return t;         // unbalanced, {0}, {}, {a.b}, {x:spec} -> unchanged
    out += name in DATA.sample ? DATA.sample[name] : `{${name}}`;
    i = end + 1;
  }
  return out;
}
const tpl = card => { const v = $('textarea', card).value.trim(); return v || card.dataset.default; };
function preview(card) {                                // = client_portal.preview_text
  const t = tpl(card);
  let x = fill(t);
  if (card.dataset.optout === '1' && !/\bstop\b/i.test(t)) x += ' ' + fill(tpl(suffixCard));
  return norm(x);
}
```

Known differences, left alone (the server preview after save is authoritative): `{business_name!r}` and
`{business_name:>3}` pass validation and the server formats them while JS leaves the template unfilled; Python's `\b`
is Unicode-aware and JS's is ASCII. `maxlength` counts UTF-16 units and the limit line uses `value.length` to match
it; segment counts use code points to match `sms_parts`.

### E.4 Features, events and budget

| Feature | Function | Events | Behaviour | Lines |
|---|---|---|---|---|
| Boot and helpers | top of module | — | §E.1, `announce`, `icon`, `norm`, `COPY` | 35 |
| Appearance | `initTheme` | `change` on `input[name=theme]` | Unhide `[data-theme-picker]`. Light/Dark: `document.cookie = "tb_theme=<v>; Path=/client; Max-Age=31536000; SameSite=Lax"` (+ `; Secure` on https) and `root.dataset.theme = v`. System: same cookie with `Max-Age=0`, `delete root.dataset.theme` | 25 |
| Account menu | `initMenu` | `keydown` Escape, document `click`, `focusout` | Escape closes and focuses the summary. A click outside closes. `focusout` closes only when `relatedTarget` is outside the menu and not null (a null target is an outside click, which the click handler covers) | 25 |
| Toasts | `toast(text, {kind, action, ms})`, `initToasts` | timers, `mouseenter/leave`, `focusin/out`, `keydown` Escape, close `click` | Move each server `[data-toast]` into `[data-toast-region]`, add `toast--floating`, unhide close, `announce(text)` after 150 ms. 6000 ms (Undo 8000); pause on hover or focus, resume at 3000 ms; one toast at a time; exit by setting `data-leaving` and removing on `transitionend` (immediately under reduced motion) | 65 |
| Submit guard | `initForms` | document `submit` (capture), window `pageshow` | Block when `form.dataset.busy` is set or `e.submitter` has `aria-disabled=true`. Otherwise set `busy`; on the submitter lock the width (`b.style.width = b.getBoundingClientRect().width + 'px'`), set `aria-disabled=true`, replace the content with `icon('loader-circle', 'spin')` + `data-loading`. On `pageshow` with `persisted`, undo all of it (back/forward cache) | 35 |
| Tel format | `initTel` | `focusout` on `.input--tel` | Strip non-digits; 11 digits starting with 1 → drop the 1; exactly 10 → `(AAA) BBB-CCCC`; otherwise leave the value untouched | 12 |
| OTP | `initOtp` | `input`, `paste` on `.otp__input` | Paste: digits only, first 6, `preventDefault`. Input: strip non-digits. Set `data-filled` to the length. No auto-submit | 18 |
| SMS engine | `fill`, `parts`, `countLabel`, `preview` | — | §E.3 | 45 |
| Cards | `initCards(form, bar)` | delegated `input`, `click` ([data-reset], [data-insert], `.editor__summary`), `keydown` | `render(card)` (below). Reset: `preventDefault`, value = `data-default`, dispatch `input` (bubbles), announce "Standard wording restored for {label}.", focus the textarea if the editor is open, else its summary. Chip: focus the textarea, `execCommand('insertText', false, token)`, falling back to `setRangeText(token, start, end, 'end')`, then dispatch `input`. Summary click: on the next animation frame, if open, focus the textarea, put the caret at the end and grow it. Enter without `isComposing`: `preventDefault`. Unhide `[data-chips]` | 110 |
| Save bar | `initSavebar(form)` → `{update, setState}` | form `input`/`change`/`submit`, document `keydown` (Ctrl/Cmd+S), window `beforeunload`, `[data-discard]`/`[data-show-error]` `click` | §E.5 | 95 |
| Error focus | `initErrorFocus` | load, `click` on `[data-error-link]` | §E.7 | 20 |
| Rail | `initRail(form)` | `change` on `input[name=scenario]`, form `focusin`/`focusout` | `data-active` = the checked value on load and on change; `log.scrollTop = 0` on change. Sync: §E.6 | 45 |
| Business preview | `initNamePreview` | `input` on `#business_name` | `bubble.textContent = norm(template.replaceAll('{business_name}', value.trim() \|\| savedName) + (suffix ? ' ' + suffix : ''))`. The intro can only use `{business_name}` | 15 |
| Styleguide demos | `initStyleguide` | `click` on `[data-demo-toast]`, `[data-demo-motion]` | Live toast; toggle `data-run` on `.sg-motion` | 15 |
| main | — | — | Calls | 15 |
| **Total** | | | | **575** |

Card `render(card)`, run on every `input` in that card:
1. `text = preview(card)`; set `textContent` of every `[data-preview="<key>"]` in the document (the card and every rail
   occurrence). The key is an identifier, so no `CSS.escape` is needed.
2. Count, pips (`min(k, 5)` × `<i>`, plus `+` when k > 5), opt-out note `hidden = !(optout && !/\bstop\b/i.test(tpl(card)))`.
3. Customized = `norm(v) !== '' && norm(v) !== norm(default)`. Update the state pill in place (class, `use` href, last
   text node) and `[data-reset].hidden = !customized`.
4. Card dirty = text dirty (§E.5) or its switch dirty: toggle `data-dirty` and `[data-dirty-pill].hidden`.
5. Limit: show `${value.length} of 480 characters` when length ≥ 420; set `data-warn` at ≥ 460.
6. Grow the textarea when `field-sizing` is unsupported: `ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 2 + 'px'`.
7. If the key is `opt_out_suffix`, render every `[data-optout="1"]` card too.

### E.5 Dirty state and the save bar

```js
const textDirty   = c => (norm($('textarea', c).value) || norm(c.dataset.default)) !== norm(c.dataset.saved);
const switchDirty = s => s.checked !== (s.dataset.savedChecked === '1');
const count = () => cards.filter(textDirty).length + switches.filter(switchDirty).length;   // N, per spec §3.18
```

| State | Entered when | Status (phone / ≥640) | Buttons |
|---|---|---|---|
| `nojs` | Server default; JS replaces it at once | — | Save |
| `clean` | N = 0 | `i-circle-check` "All changes saved" | Save `aria-disabled` |
| `saved` | `data-initial=saved` on load; becomes `clean` after 4000 ms | `i-circle-check` (accent) "All changes saved" | Save `aria-disabled` |
| `dirty` | N > 0 | "N unsaved" / "N unsaved change(s)" | Discard, Save |
| `error` | `data-initial=error` on load; kept until the offending textarea (`.msg--invalid textarea`) changes, then recomputed | "Not saved" / "Not saved · 1 message needs a change" | Show, Save |
| `saving` | `submit` on `form#messages` | spinner, "Saving…" | Save loading; others hidden |

- `update(changedKey)` runs on form `input` and `change` after the card render. It recounts N, sets the state, writes
  the status synchronously, and passes the long text to `announce(…, {debounce: 800, channel: 'savebar'})`.
  `.savebar__status` itself is not a live region.
- Discard: snapshot every textarea value and switch state; restore `data-saved` and `data-saved-checked`; render every
  card; remove `msg--invalid`, `aria-invalid`, the inline errors and `#error-summary` (the offending text is gone);
  state `clean`; then `toast(COPY.discarded, {action: {label: 'Undo', run}, ms: 8000})` and focus Undo. Undo restores
  the snapshot, renders, runs `update()` and focuses Save.
- Ctrl/Cmd+S on the Messages page: always `preventDefault`; when N > 0, `form.requestSubmit($('[data-save]'))`.
  `requestSubmit` fires `submit` with the submitter, so the loading state applies.
- `beforeunload`: when N > 0 and the state is not `saving`, `preventDefault()` and `returnValue = ''`.
- A click on Save while it is `aria-disabled` is blocked by the submit guard.

### E.6 Rail updates and sync

- Text: `render(card)` already updates every `[data-preview]` copy (§E.4). Rows of optional questions show and hide
  through CSS `:has()` from the switch state; JS does nothing for them.
- Sync (only while `WIDE.matches`): on `focusin` inside `article.msg`, skip it if the card is optional and switched off.
  Otherwise `key = card.dataset.sync`. If the visible thread (`.thread[data-scenario=<data-active>]`) has no
  `[data-preview=key]`, check `#sc-<card.dataset.scenario>` and run the change logic. Then clear any `data-current`, set
  it on that thread's bubble, and centre it:
  `log.scrollTo({top: bubble.offsetTop - (log.clientHeight - bubble.offsetHeight) / 2, behavior: REDUCED.matches ? 'auto' : 'smooth'})`.
  `.phone__log` is `position: relative`, so `offsetTop` is relative to the log. Never `scrollIntoView`: it would scroll the page.
- On `focusout` where `relatedTarget` is outside the card, clear `data-current`.
- **Cut: Play.** The spec's Play replay (typing indicator, staged timing, Play/Playing/Play again) would add about 60
  lines and take the module over 600. It is demo polish, not an owner task: the static thread already shows the whole
  conversation, Play is hidden under reduced motion anyway, and it carries the most timing code to keep correct. The
  typing indicator stays as a static styleguide specimen. If the module still runs over budget, the next cut is the
  styleguide motion "Run" demo, replaced by a CSS-only `:hover` demo.

### E.7 Focus management

| Moment | Action |
|---|---|
| Load with `#error-summary` (Messages, Business) | `summary.focus({preventScroll: false})` |
| `[data-error-link]` click or Save-bar Show | `preventDefault`; target = `#f_<key>` or the business field; `target.closest('details')?.setAttribute('open', '')`; focus it; caret at the end for a textarea |
| Server-open editor (`.msg--invalid`) | Do not react to its initial `toggle` event; only summary clicks focus the textarea. Otherwise the parse-time toggle would steal focus from the error summary |
| Login and verify errors | Server `autofocus` on the field; JS does nothing |
| Reset | Textarea if the editor is open, else the summary (the reset button hides itself) |
| Discard and Undo | Undo button, then Save |
| Menu Escape | The summary |
| Toast | Never takes focus, except the Undo toast's action |

---

## F. Stable hooks

For `docs/notes/ui-compare-a/screenshots.py`, tests and JS. Classes are not hooks.

| Hook | Element | Page |
|---|---|---|
| `html.no-js` / `html.js`, `html[data-theme]` | root | all |
| `#main` | main | all |
| `[data-menu]`, `[data-theme-picker]`, `input[name=theme][value=system\|light\|dark]` | account menu | signed in |
| `nav.nav a[aria-current=page]` | current nav item | signed in |
| `form[action="/client/logout"]` | sign out | signed in |
| `[data-toast]` (`[data-kind]`), `[data-toast-region]`, `[data-toast-close]`, `#announcer` | feedback | all |
| `#tb-data` | JSON | Messages |
| `#mobile`, `#mobile-error` | sign-in field | Sign in |
| `#code`, `#code-error`, `#code-help`, `[data-otp][data-filled]` | OTP | Verify, Confirm |
| `button[data-loading]` | any submit with a loading label | all |
| `form#messages` | the form | Messages |
| `#g_missed`, `#g_questions`, `#g_booking`, `#g_noreply`, `#g_owner`, `#g_keywords` | moments | Messages |
| `#m_<key>`, `[data-card=<key>]`, `[data-dirty]`, `.msg--invalid` | card | Messages |
| `#l_<key>`, `#w_<key>`, `#r_<key>`, `#f_<key>`, `#x_<key>`, `#e_<key>` | label, when, rule, textarea, help, error | Messages |
| `[data-preview=<key>]` | bubble (cards and rail) | Messages |
| `[data-state-pill]`, `[data-dirty-pill]`, `[data-reset]`, `[data-chips]`, `[data-insert]`, `[data-count]`, `[data-pips]`, `[data-limit]`, `[data-optout-note]` | card parts | Messages |
| `#m_<key> .editor__summary` | open an editor (the only class used as a hook, because `<summary>` has no attribute to hang one on) | Messages |
| `#ask_phone`, `#ask_email` (`[data-saved-checked]`) | switches | Messages |
| `#error-summary`, `[data-error-link]` | error summary | Messages, Business |
| `[data-savebar][data-state]`, `[data-savebar-status]`, `[data-save]`, `[data-discard]`, `[data-show-error]` | save bar | Messages |
| `#conversation`, `[data-rail][data-active]`, `#sc-<id>` / `input[name=scenario]`, `.thread[data-scenario=<id>]`, `[data-rail-log]`, `[data-ask]`, `[data-current]` | rail | Messages |
| `#business_name`, `#business_contact`, `#owner_mobile`, `#<field>-error`, `[data-name-preview]` | business form | Business |
| `[data-stepper]`, `[aria-current=step]`, `[data-cancel]`, `[data-resend]` | confirm step | Confirm |
| `[data-status=<kind>]`, `#picker-error`, `input[name=calendar_id]`, `form[data-connect]`, `[data-connect-note]` | calendar | Calendar |
| `#sg-<section>`, `.sg-panel[data-theme]`, `[data-demo-toast]`, `[data-demo-motion]` | styleguide | Styleguide |

screenshots.py replacements:

| Old | New |
|---|---|
| `page.fill("#f_prompt_name", …)` on a closed editor | `page.click("#m_prompt_name .editor__summary")` first |
| `#m_prompt_name .chip` | `#m_prompt_name [data-insert]` |
| `.savebar button[type=submit]` | `[data-save]` |
| `.msg.bad` | `.msg--invalid` |
| `.flash.ok` | `[data-toast]` |
| `button.primary` (Business) | `form[action="/client/business"] button[type=submit]`: the menu also has a submit |
| `.step.now` | `[data-stepper] [aria-current=step]` |
| — | New: 14-styleguide (1024), 15-messages-dark (`page.emulate_media(color_scheme="dark")`), 16-page-expired (set `form#messages input[name=csrf]` to "x" and call `form.submit()`, which skips the submit handlers) |

---

## G. Build order

Each step ends in something visible in a browser (`.venv/bin/uvicorn` against a stub app, or `screenshots.py` app 1 and
app 2) and a test command.

1. **Render and static.** Add `portal_render.py`, empty `portal.css` and `portal.js`, `mount_static` at the start of
   `client_portal.install_routes`. Check: `curl -I /client/static/portal.css?v=x` shows text/css, nosniff, immutable.
2. **Tokens and auth pages.** `_document`, `auth`, `_macros` (icon, field_error, otp, button), login, verify. CSS
   tokens (with markers), reset, base, auth layout, field, button, otp, field-error. Switch `_login_form` and
   `_verify_form` to `render`. Check in a browser: both pages light and dark (devtools emulation), the OTP cells line up
   at 320/375 in Chrome and Firefox, no CSP console errors. Run `pytest tests/test_client_portal.py`: green.
3. **Shell.** `base.html.j2`: topbar, nav (tab bar under 1024, sidebar at 1024 and up), account menu without JS, sign
   out. Business page and confirm page (`stepper`, `.card`, `pill`). Check: sign out works with JS off; no horizontal
   scroll at 320. Run `pytest tests/test_client_settings.py tests/test_contact_fields.py`: green.
4. **Calendar.** `StatusView`, `status_view`, `Choice`, picker-only-when-ready, empty state, connect card order, info
   notice. Check all five states via the screenshots.py app 2 fixture. test_client_settings stays green.
5. **Expired page.** `FormExpired` and its handler; switch all three `_checked_form` callers and `save_messages`. Check:
   a curl POST with a wrong csrf returns 400 HTML in the shell.
6. **Messages, server side, JS off.** Dataclasses, LAYOUT/ANYTIME/TRIGGERS/SCENARIOS/CHIP_NAMES/CARD_SCENARIO,
   `card_view`, `messages_view`, the `fill()` fix, save normalisation. Templates: `_message_card` (card, moment,
   anytime, error_summary). CSS: page head, spine, moments, msg, well, sms, tpill, handoff, pill, editor, chips
   fallback, count and pips, switch. Check with JS disabled: reset posts, a rejected save opens the right editor,
   switching a question off collapses its card. Run test 4 from §B.10.
7. **Rail, no JS.** `_rail`, `.msg-layout`, phone frame, `.pill-radio`, the `:has()` scenario and `data-ask` rules,
   sticky rail at 1024 and up. Check: scenarios switch with JS off in Chrome and Safari.
8. **Save bar and notices, no JS.** `savebar` (`nojs` sticky above the tab bar), toast as an inline notice, error
   summary styling. Check the full JS-off flow: edit → save → toast; a bad edit → summary → anchor jump.
9. **JS platform.** Boot, `announce`, theme, menu, toasts, submit guard (+`pageshow`), tel, OTP. Check: Appearance
   persists across reloads and sign out; Escape and outside click close the menu; the toast pauses on hover; loading
   labels show; double clicks do not double-submit.
10. **JS Messages engine.** SMS engine and cards: live preview, pills, reset, chips at the cursor, editor focus,
    auto-grow, Enter blocked, limit line. Check: for 5 edited cards, the live count equals the server count after
    saving (including an em dash and a `€`).
11. **JS save bar.** Dirty count, the six states, Discard/Undo, Ctrl/Cmd+S, beforeunload, Show, error-summary focus
    and links. Check by keyboard only, then with VoiceOver or NVDA for the announcements.
12. **JS rail and business.** Scenario fallback (`data-active`), focus sync at 1024 and up, business name preview.
    Check: tabbing through cards rings the right bubble without scrolling the page.
13. **Styleguide.** `portal_styleguide.py`, the template, `.sg-*` CSS, demos. Check: every token shows a hex and a
    ratio matching spec §1.3; both panels render.
14. **Audit.** Widths 320, 375, 640, 1024 and 1280; dark mode; reduced motion; keyboard order per spec §4; 200%
    zoom; Safari iOS safe areas (tab bar, save bar, toasts). CSS ≤ 35 KB; JS ≤ ~600 lines.
15. **Tests.** Re-point test_client_portal_ui.py (§B.11); add tests/test_portal_frontend.py (§B.10). Run
    `.venv/bin/pytest tests/`: all green.
16. **Docs.** Update screenshots.py (§F), regenerate the screenshots, rewrite README.md for this build.

---

## H. Calls made where the sources disagree

| Topic | Sources | Call |
|---|---|---|
| File names, JS form | spec §7.1 `client.css`, `client.js` as an ES2019 IIFE with `defer` | decisions.md: `portal.css`, `portal.js` as an ES module |
| Moment heading | spec "You step in" | decisions.md "Owner steps in". `GROUPS` keeps "You step in" for its test |
| Calendar verbs, picker, HELP label, Appearance, sample date, resend, hand-off placement | spec §8 open | decisions.md 1–10, applied as written |
| CSRF failure | contract: JSON 400 | decisions.md: HTML 400 page, status unchanged |
| Font preload | spec §2.2 adds `?v=` to the preload href | No `?v=`: it must match the `@font-face` URL or the font downloads twice |
| Asset version | spec §7.1 "first 8 hex characters" | Same hash with digits mapped to letters, so the verify page can never contain `0123` |
| Toast region | spec: `aria-live` on the region plus `#announcer` | `#announcer` only; two live regions would read each toast twice |
| Save-bar status | spec: `aria-live` on the status, "debounced 800 ms" | Visual update synchronous, announcement debounced through `#announcer` |
| Scenario order | spec §6.3 lists Calendar error before No reply; §3.17 markup and the wireframe list No reply first | §3.17 markup order |
| Stepper classes | spec `is-done`, `is-current` | `stepper__step--done`, `--current`; `is-*` is reserved for styleguide forced states |
| `.scenario` class | spec uses it for the theme radios too | One component, `.pill-radio` |
| Optional rows `:has()` | spec `body:has(#ask_phone…)` | `.msg-layout:has(.switch[name="ask_phone"]…)`: no id selectors, styleguide-safe |
| Error-summary link | contract test expects `href=#m_<key>` | spec §4.3 `href=#f_<key>` (focuses the field); test re-pointed |
| Icon count | spec §4.6 "52 symbols" | The sprite has 55; the styleguide lists what it parses |
| JS scope | spec §5 includes Play | Cut (§E.6) to stay within ~600 lines |
| `fill()` | contract: preserve behaviour | Fixed: a rejected save with `{a.b}` or `{x[y]}` is a 500 today (§B.4) |
