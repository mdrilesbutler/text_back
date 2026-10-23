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
