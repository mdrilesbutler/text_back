"""The owner-only styleguide (GET /client/styleguide): every token and component of the
settings pages, in every state, in a light and a dark panel side by side.

Token values are parsed from the marker blocks in static/portal.css, so the page shows what
the stylesheet ships. Contrast ratios are computed from those values (WCAG 2.x relative
luminance) for the text and UI pairs of design-spec §1.3. Specimens are built with the same
view models and macros as the real pages. Nothing on the page posts.
"""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass

from text_back.client_portal import (
    ANYTIME,
    CHIP_NAMES,
    CODE_FAILURE,
    DEFAULT_TEMPLATES,
    FIELD_KEYS,
    GROUPS,
    LAYOUT,
    Card,
    Moment,
    QSet,
    _shell,
    bill_label,
    blame,
    card_view,
    count_label,
    friendly_reason,
    preview_text,
    preview_values,
    rail_view,
    sms_parts,
)
from text_back.client_settings import CONTACT_ERROR, MOBILE_ERROR, NAME_ERROR, SETUP_NOTE, status_view
from text_back.messages import MAX_TEMPLATE_CHARS, MessageTemplateError, validate_templates
from text_back.portal_render import STATIC_DIR, TEMPLATE_DIR

CSS_FILE = STATIC_DIR / "portal.css"
SPRITE_FILE = TEMPLATE_DIR / "client" / "_icons.svg.j2"

# --- tokens, parsed from the stylesheet ------------------------------------------

_DECL = re.compile(r"--([a-z0-9-]+):\s*([^;]+);")


def token_block(css: str, name: str) -> str:
    """The declarations between ``/* @tokens:<name> */ selector {`` and ``} /* @end */``."""
    match = re.search(rf"/\* @tokens:{re.escape(name)} \*/.*?\{{(.*?)\}}\s*/\* @end \*/", css, re.S)
    if not match:
        raise ValueError(f"portal.css has no @tokens:{name} block")
    return match.group(1)


def declarations(block: str) -> dict[str, str]:
    """Custom properties of a token block, in source order: {name without --: value}."""
    return {name: " ".join(value.split()) for name, value in _DECL.findall(block)}


@functools.cache
def _tokens() -> dict[str, dict[str, str]]:
    css = CSS_FILE.read_text(encoding="utf-8")
    return {name: declarations(token_block(css, name)) for name in ("light", "dark-media", "dark", "static")}


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    digits = color.lstrip("#")
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    r, g, b = (_channel(int(digits[i:i + 2], 16)) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG 2.x contrast ratio of two #rrggbb colours, rounded to two places."""
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return round((high + 0.05) / (low + 0.05), 2)


# design-spec §1.3: (kind, foreground token, background token, where the pair is used).
# Text pairs need 4.5:1, UI pairs (borders, rings, dots) need 3:1.
CONTRAST_PAIRS: tuple[tuple[str, str, str, str], ...] = (
    ("Text", "text-ink", "bg", ""), ("Text", "text-ink", "surface", ""), ("Text", "text-ink", "sunken", ""),
    ("Text", "text-ink", "card", "cards, status blocks"),
    ("Text", "text-muted", "bg", ""), ("Text", "text-muted", "surface", ""), ("Text", "text-muted", "sunken", ""),
    ("Text", "text-muted", "card", "when-lines, rules, help"),
    ("Text", "text-subtle", "bg", ""), ("Text", "text-subtle", "surface", ""), ("Text", "text-subtle", "sunken", ""),
    ("Text", "text-subtle", "card", "Standard wording caption"), ("Text", "text-subtle", "well", "receipt line"),
    ("Text", "accent", "bg", "links, TextBack badge"), ("Text", "accent", "surface", ""), ("Text", "accent", "card", "Edit wording, Reset"),
    ("Text", "accent", "accent-tint", "current nav item, success and booked pills"),
    ("Text", "accent", "accent-tint-hover", ""),
    ("Text", "text-ink", "accent-tint", "checked radio row"),
    ("Text", "on-accent", "accent-fill", "primary button"), ("Text", "on-accent", "accent-fill-hover", ""),
    ("Text", "on-accent", "accent-fill-pressed", ""),
    ("Text", "bubble-customer-fg", "bubble-customer-bg", ""), ("Text", "bubble-textback-fg", "bubble-textback-bg", ""),
    ("Text", "bubble-you-fg", "bubble-you-bg", ""),
    ("Text", "warning-fg", "warning-bg", ""), ("Text", "warning-fg", "bg", ""), ("Text", "warning-fg", "well", "receipt from 2 texts"),
    ("Text", "text-ink", "warning-bg", ""), ("Text", "text-muted", "warning-bg", ""),
    ("Text", "danger-fg", "danger-bg", ""), ("Text", "danger-fg", "bg", ""),
    ("Text", "text-ink", "danger-bg", ""), ("Text", "text-muted", "danger-bg", ""),
    ("Text", "info-fg", "info-bg", ""),
    ("UI", "line-input", "bg", "field, radio and switch borders"), ("UI", "line-input", "surface", "switch row"),
    ("UI", "focus", "bg", "focus ring"), ("UI", "focus", "surface", ""),
    ("UI", "accent-fill", "bg", "switch on, radio dot"),
    ("UI", "missed", "bg", "missed-call dot"), ("UI", "missed", "surface", ""),
    ("UI", "text-muted", "bg", "segment pips"),
)
NEED = {"Text": "4.5", "UI": "3"}


@dataclass(frozen=True, slots=True)
class Shade:
    fg: str
    bg: str
    ratio: float
    ok: bool


@dataclass(frozen=True, slots=True)
class Pair:
    kind: str                 # Text | UI
    fg: str
    bg: str
    use: str
    need: str
    shades: dict[str, Shade]  # light | dark


@dataclass(frozen=True, slots=True)
class Swatch:
    token: str
    hex: dict[str, str]       # light | dark
    note: dict[str, str]      # light | dark: the stylesheet comment; notes about the light values stay in the light panel
    pairs: tuple[Pair, ...]   # the §1.3 pairs this token is the foreground of


@dataclass(frozen=True, slots=True)
class SwatchGroup:
    name: str
    note: str
    swatches: tuple[Swatch, ...]


def contrast_pairs() -> tuple[Pair, ...]:
    tokens = _tokens()
    light = tokens["light"]
    dark = {**light, **tokens["dark"]}
    pairs = []
    for kind, fg, bg, use in CONTRAST_PAIRS:
        shades = {}
        for theme, values in (("light", light), ("dark", dark)):
            ratio = contrast(values[fg], values[bg])
            shades[theme] = Shade(values[fg], values[bg], ratio, ratio >= float(NEED[kind]))
        pairs.append(Pair(kind, fg, bg, use, NEED[kind], shades))
    return tuple(pairs)


def colour_groups(pairs: tuple[Pair, ...]) -> tuple[SwatchGroup, ...]:
    """Every colour token of the light block, grouped under the block's own comment headings,
    with the trailing comment as the note and its dark value (the light one if not redefined)."""
    css = CSS_FILE.read_text(encoding="utf-8")
    dark = _tokens()["dark"]
    groups: list[tuple[str, list[Swatch]]] = []
    for line in token_block(css, "light").splitlines():
        text = line.strip()
        found = _DECL.findall(text)
        if not found:
            heading = re.fullmatch(r"/\*\s*(.+?)\s*\*/", text)
            if heading:
                groups.append((heading.group(1), []))
            continue
        note = re.search(r"/\*\s*(.+?)\s*\*/\s*$", text)
        for index, (token, value) in enumerate(found):
            value = value.strip()
            if not value.startswith("#") or not groups:
                continue
            text = note.group(1) if note and index == len(found) - 1 else ""
            groups[-1][1].append(Swatch(
                token, {"light": value, "dark": dark.get(token, value)},
                {"light": text, "dark": "" if "white" in text else text},
                tuple(p for p in pairs if p.fg == token),
            ))
    out = []
    for heading, swatches in groups:
        if swatches:  # the Elevation heading holds shadows only; they have their own section
            name, _, note = heading.partition(" (")
            out.append(SwatchGroup(name, note.rstrip(")"), tuple(swatches)))
    return tuple(out)


def _px(value: str) -> str:
    """'1.75rem' -> '28', '6px' -> '6'; anything else as written."""
    match = re.fullmatch(r"([\d.]+)(rem|px)", value)
    if not match:
        return value
    number = float(match.group(1)) * (16 if match.group(2) == "rem" else 1)
    return f"{number:g}"


@dataclass(frozen=True, slots=True)
class TypeRole:
    name: str
    cls: str
    sample: str
    spec: str
    use: str


# design-spec §1.2: (role, sg-type modifier, family, weight, size token, line-height token or literal, use)
TYPE_ROLES = (
    ("Display", "display", "Archivo", 600, "fs-display", "lh-display", "H1, one per page (32/40 at 1024 and up)"),
    ("Title", "title", "Archivo", 600, "fs-title", "lh-title", "Moment headings, status block titles"),
    ("Heading", "heading", "Archivo", 600, "fs-heading", "lh-heading", "Card labels, card headings, rail title"),
    ("Lead", "lead", "Source Sans 3", 400, "fs-lead", "lh-lead", "Page lead, muted"),
    ("Body", "body", "Source Sans 3", 400, "fs-body", "lh-body", "Paragraphs, inputs, textareas"),
    ("Label", "label", "Source Sans 3", 600, "fs-label", "lh-label", "Form labels, button text"),
    ("Small", "small", "Source Sans 3", 400, "fs-small", "lh-small", "When-lines, rules, help, inline errors"),
    ("Caption", "caption", "Source Sans 3", 500, "fs-caption", "lh-caption", "Receipt lines, pills, tab-bar labels; the floor"),
    ("Eyebrow", "eyebrow", "Source Sans 3", 500, "fs-eyebrow", "lh-eyebrow", "Any time, Optional questions, Appearance"),
    ("Role badge", "badge", "Source Sans 3", 600, "fs-caption", "1rem", "Customer, TextBack, You"),
    ("Bubble", "bubble", "Source Sans 3", 400, "fs-bubble", "lh-bubble", "Texts in the cards"),
    ("Bubble, rail", "bubble-rail", "Source Sans 3", 400, "fs-bubble-rail", "lh-bubble-rail", "Texts in the phone rail"),
)


def type_roles(static: dict[str, str]) -> tuple[TypeRole, ...]:
    roles = []
    for name, cls, family, weight, size, line, use in TYPE_ROLES:
        spec = f"{family} {weight} · {_px(static[size])}/{_px(static.get(line, line))}"
        roles.append(TypeRole(name, cls, "Oak & Pine Tree Care", spec, use))
    roles.append(TypeRole("Code", "otp", "481 920", "Monospace 600 · up to 30, fits a 320 screen", "Sign-in code only"))
    return tuple(roles)


def _scale(static: dict[str, str], prefix: str) -> tuple[tuple[str, str, str], ...]:
    """(token, value, px) for every static token starting with ``prefix``."""
    return tuple((name, value, _px(value)) for name, value in static.items() if name.startswith(prefix))


# --- specimens --------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CardSpecimen:
    name: str
    note: str
    card: Card
    branches: tuple[Card, ...]
    editable: bool


CUSTOM_INTRO = "Hi, this is {business_name}. Sorry we missed your call. What do you need done?"
CUSTOM_LOCATION = "Where is the job? A street address is best."
REJECTED_HANDOFF = "Got it. Automated scheduling is paused."


def _card_specimens(state, current, sample) -> tuple[tuple[CardSpecimen, ...], tuple[Moment, ...], Moment]:
    def make(key: str, *, value: str = "", saved: str | None = None, branch: bool = False, error: str = "",
             asked: frozenset[str] = frozenset(), asked_saved: frozenset[str] | None = None) -> Card:
        values = {name: "" for name in FIELD_KEYS} | ({key: value} if value else {})
        templates = {name: values[name] or DEFAULT_TEMPLATES[name] for name in FIELD_KEYS}
        return card_view(key, values=values, templates=templates, current=current, sample=sample, asked=set(asked),
                         asked_saved=set(asked if asked_saved is None else asked_saved), branch=branch, error=error,
                         saved=DEFAULT_TEMPLATES[key] if saved is None else saved)

    # The rejected card shows the validator's reason in the owner's words, exactly as a failed save would.
    templates = dict(DEFAULT_TEMPLATES, handoff_ack=REJECTED_HANDOFF)
    try:
        validate_templates({"handoff_ack": REJECTED_HANDOFF})
        reason = ""
    except MessageTemplateError as exc:
        key, raw = blame(str(exc), templates)
        reason = friendly_reason(raw, key)

    cards = (
        CardSpecimen("Standard", "Saved wording is the standard: a quiet caption, no pill, no Reset.",
                     make("prompt_service"), (), True),
        CardSpecimen("Customized", "The saved wording differs from the standard: the pill, and Reset in the footer. "
                     "It leaves out STOP, so the opt-out line is added and drawn dotted.",
                     make("intro", value=CUSTOM_INTRO, saved=CUSTOM_INTRO), (), True),
        CardSpecimen("Unsaved", "The box differs from the saved wording; JavaScript keeps this pill and the save bar count current.",
                     make("prompt_location", value=CUSTOM_LOCATION), (), True),
        CardSpecimen("Not saved", "A rejected save: the danger pill replaces the others, the editor opens on the reason.",
                     make("handoff_ack", value=REJECTED_HANDOFF, error=reason), (), True),
        CardSpecimen("Billed as more than one text", "From 2 texts the receipt turns amber and says why; links break anywhere.",
                     make("booking_confirmation"), (), True),
        CardSpecimen("Optional, switched off", "Title, switch and one line; the re-prompt hides. Every field still posts.",
                     make("prompt_phone"), (make("phone_reprompt", branch=True),), True),
        CardSpecimen("Optional, switched on, with its branch", "A parent and the card sent instead of it share one frame.",
                     make("prompt_email", asked=frozenset({"email"})), (make("email_reprompt", branch=True, asked=frozenset({"email"})),), True),
        CardSpecimen("Read only", "Message editing not set up: no editor, and a pill in place of the switch.",
                     make("prompt_email", asked=frozenset({"email"})), (), False),
    )
    blurbs = {gid: blurb for gid, _, blurb, _ in GROUPS}
    (m_id, m_heading, m_icon, _), (q_id, q_heading, q_icon, _) = LAYOUT[0], LAYOUT[1]
    spine = (
        Moment(m_id, m_heading, blurbs[m_id], m_icon, (QSet("", make("intro"), ()),)),
        Moment(q_id, q_heading, blurbs[q_id], q_icon,
               (QSet("", make("prompt_preferred_time"), (make("preferred_time_reprompt", branch=True),)),)),
    )
    a_id, a_heading, a_icon, _ = ANYTIME
    return cards, spine, Moment(a_id, a_heading, blurbs[a_id], a_icon, ())


def styleguide_context(state, session) -> dict:
    """Context for templates/client/styleguide.html.j2."""
    tokens = _tokens()
    static = tokens["static"]
    light, dark = tokens["light"], {**tokens["light"], **tokens["dark"]}
    pairs = contrast_pairs()
    current = state.messages.current()
    sample = preview_values(state)
    defaults = {key: DEFAULT_TEMPLATES[key] for key in FIELD_KEYS}
    cards, spine, anytime = _card_specimens(state, current, sample)
    intro = preview_text("intro", defaults, sample)
    meters = tuple((caption, count_label(text), bill_label(text), sms_parts(text)[1]) for caption, text in (
        ("120 plain characters", "a" * 120), ("200 plain characters", "a" * 200), ("400 plain characters", "a" * 400),
        ("The standard first text: its dash is not in the plain alphabet", intro)))
    statuses = tuple(status_view({"provider": provider, "status": status}, "Personal") for provider, status in (
        ("google", "ready"), ("google", "reauth_required"), ("google", "unavailable"), ("stub", "none"),
        ("microsoft", "managed"), ("icloud", "managed")))
    return {
        **_shell(state, session, title="Styleguide", nav=None),
        "colour_groups": colour_groups(pairs),
        "shadows": tuple((name, light[name], dark[name]) for name in light if name.startswith("shadow-")),
        "type_roles": type_roles(static),
        "spaces": _scale(static, "space-"),
        "radii": _scale(static, "radius-"),
        "sizes": tuple(row for row in _scale(static, "") if row[0] in ("tap", "tap-lg", "tap-fine", "field-h", "otp-h")),
        "motion": tuple((name, value) for name, value in static.items() if name.startswith(("dur-", "ease-"))),
        "layers": tuple((name, value) for name, value in static.items() if name.startswith("z-")),
        "icons": tuple(re.findall(r'id="i-([a-z0-9-]+)"', SPRITE_FILE.read_text(encoding="utf-8"))),
        "chips": tuple(("{%s}" % name, label) for name, label in CHIP_NAMES.items()),
        "setup_note": SETUP_NOTE,
        "rejected_reason": friendly_reason("must promise a follow-up", "handoff_ack"),
        "saved_detail": "Changed: Question 1, Question 4.",
        "meters": meters,
        "statuses": statuses,
        "cards": cards,
        "spine": spine,
        "anytime": anytime,
        "rail": rail_view(state, defaults, sample),
        "max_chars": MAX_TEMPLATE_CHARS,
        "errors": {"name": NAME_ERROR, "contact": CONTACT_ERROR, "mobile": MOBILE_ERROR, "code": CODE_FAILURE},
        "long_text": DEFAULT_TEMPLATES["help"],
        "short_text": DEFAULT_TEMPLATES["prompt_name"],
        "rejected_text": REJECTED_HANDOFF,
        "texts": {"customer": "Tree removal. An oak is leaning toward the house.",
                  "textback": preview_text("prompt_location", defaults, sample),
                  "you": "Thanks, Alex. See you Thursday at 4."},
    }
