"""Rendering for the /client settings pages: Jinja templates, page headers and static files.

Every portal page goes through ``render()``, which adds the security headers and
the Content-Security-Policy. Templates carry no inline style and no inline
executable script; the one stylesheet and the one ES module are served from
``/client/static`` with a content-hash version in the query string.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import jinja2
from markupsafe import Markup, escape
from fastapi import Request
from fastapi.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
THEME_COOKIE = "tb_theme"
THEMES = ("light", "dark")
CSP = "default-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
PAGE_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
}

# autoescape=True, not select_autoescape(): the template names end in .j2, which
# select_autoescape does not treat as HTML, so it would silently turn escaping off.
ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
    autoescape=True,
    undefined=jinja2.StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)

_URL = re.compile(r"(https?://\S+)")


def url_runs(text: str) -> Markup:
    """Escape ``text`` and wrap each URL in span.sms__link, so a long link can break anywhere
    while the rest of the bubble wraps between words (portal.js bubble() does the same)."""
    return Markup("").join(Markup("<span class=sms__link>{}</span>").format(part) if index % 2 else escape(part)
                           for index, part in enumerate(_URL.split(text)) if part)


ENV.filters["url_runs"] = url_runs

# The add-to-calendar links in a TextBack bubble: a short label on screen, the full link in title.
LINK_LABELS = {"g": "Add to Google Calendar ›", "o": "Add to Outlook ›", "i": "Add to iCal ›", "": "Calendar links page ›"}
_CAL_LINK = re.compile(r"(?:\b(?:Google|Outlook|iCal) )?(https?://\S+?/a/[\w-]+?(?:/([goi]))?)(?=[\s.,;!?]*(?:\s|$))")


def sms_links(text: str) -> Markup:
    """Escape ``text``; each /a/<ref>/g|o|i link becomes its label (the provider word before it is
    folded into the label), every other URL is wrapped like ``url_runs``."""
    out, last = [], 0
    for match in _CAL_LINK.finditer(text):
        out.append(url_runs(text[last:match.start()]))
        url = match.group(1)
        out.append(Markup('<span class=sms__link title="{}">{}</span>').format(url, LINK_LABELS[match.group(2) or ""]))
        last = match.end()
    out.append(url_runs(text[last:]))
    return Markup("").join(out)


ENV.filters["sms_links"] = sms_links


def _when(value, tz_name: str, now=None) -> str:
    from text_back.portal_dates import when
    return when(value, tz_name, now)


def _day(value, tz_name: str) -> str:
    from text_back.portal_dates import day
    return day(value, tz_name)


# Every date a template shows goes through portal_dates (never strftime in a template).
ENV.filters["when"] = _when
ENV.filters["day"] = _day


def _asset_version() -> str:
    """First 8 hex characters of the CSS + JS hash, with digits mapped to letters,
    so the ?v= value can never put a digit run (like 0123) into any page."""
    data = (STATIC_DIR / "portal.css").read_bytes() + (STATIC_DIR / "portal.js").read_bytes()
    return hashlib.sha256(data).hexdigest()[:8].translate(str.maketrans("0123456789", "ghijklmnop"))


ASSET_VERSION = _asset_version()


def render(request: Request, name: str, *, status_code: int = 200, headers: dict | None = None, **context) -> HTMLResponse:
    """Render a portal template with the page headers. No nonce, clock or other
    per-request value is added, so a page is byte-identical for identical input."""
    theme = request.cookies.get(THEME_COOKIE)
    body = ENV.get_template(name).render(asset_v=ASSET_VERSION, theme=theme if theme in THEMES else None, **context)
    return HTMLResponse(body, status_code=status_code, headers={**PAGE_HEADERS, **(headers or {})})


_VERSIONED = re.compile(rb"(?:^|&)v=")


class PortalStatic(StaticFiles):
    """Static files with nosniff; versioned URLs are immutable, the rest revalidate by ETag."""

    def file_response(self, full_path, stat_result, scope, status_code: int = 200):
        response = super().file_response(full_path, stat_result, scope, status_code)
        response.headers["X-Content-Type-Options"] = "nosniff"
        versioned = _VERSIONED.search(scope.get("query_string", b"") or b"")
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable" if versioned else "no-cache"
        return response


def mount_static(app) -> None:
    app.mount("/client/static", PortalStatic(directory=STATIC_DIR), name="client-static")
