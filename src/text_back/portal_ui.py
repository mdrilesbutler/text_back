"""Shared rendering layer for the owner portal (/client).

Owns the Jinja2 environment, the response headers every portal page carries,
the static mount for portal.css / portal.js, and the component styleguide.
Route modules call ``render(...)``; they never build HTML strings.

Design notes
- No inline styles or scripts anywhere: the CSP is ``style-src 'self'`` and
  ``script-src 'self'`` with no nonces, so two error responses stay
  byte-identical (tests/test_client_portal.py relies on that).
- ``asset_v`` is a content hash of portal.css + portal.js computed once at
  import, used as ``?v=`` for cache busting; the files themselves are served
  by StaticFiles with normal caching.
- Builders may add helpers and filters here, but should not restructure it.
"""
from __future__ import annotations

import hashlib
import inspect
import re
from pathlib import Path
from typing import Any, Callable

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"
STATIC_URL = "/client/static"

# Response headers for every portal page. CSP has no nonces on purpose.
# form-action allows accounts.google.com so the Connect Google Calendar
# POST -> 303 -> consent chain is not blocked by Chrome (IA E.2a).
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; "
        "form-action 'self' https://accounts.google.com; base-uri 'none'; frame-ancestors 'none'"
    ),
}

# (key, label, href, icon name). Order is the nav order on every device.
NAV_ITEMS: tuple[tuple[str, str, str, str], ...] = (
    ("home", "Home", "/client", "home"),
    ("messages", "Messages", "/client/messages", "message"),
    ("scheduling", "Scheduling", "/client/scheduling", "clock"),
    ("calendar", "Calendar", "/client/calendar", "calendar"),
    ("phone", "Phone", "/client/phone", "phone"),
)


def _asset_version() -> str:
    digest = hashlib.sha256()
    for name in ("portal.css", "portal.js"):
        path = STATIC_DIR / name
        if path.exists():
            digest.update(path.read_bytes())
    return digest.hexdigest()[:10]


def format_phone_display(e164: str | None) -> str:
    """'+17045550123' -> '(704) 555-0123'. Other shapes are returned as typed."""
    raw = str(e164 or "").strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return raw


def _nl2br(value: str):
    from markupsafe import Markup, escape

    return Markup("<br>".join(escape(part) for part in str(value or "").split("\n")))


asset_v = _asset_version()
nav_items = list(NAV_ITEMS)

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "htm", "xml"], default=True),
    trim_blocks=True,
    lstrip_blocks=True,
)
env.globals.update(asset_v=asset_v, nav_items=nav_items, static_url=STATIC_URL)
env.filters["phone"] = format_phone_display
env.filters["nl2br"] = _nl2br


def render(template: str | Request, *args: Any, status: int = 200, **ctx: Any) -> HTMLResponse:
    """Render ``template`` with ``ctx`` and the portal security headers.

    ``render("pages/home.html", title="Home", ...)`` is the normal call. For
    compatibility with the request-first convention a Request may be passed as
    the first argument followed by the template name; it is exposed as
    ``request`` in the context.
    """
    if not isinstance(template, str):
        ctx.setdefault("request", template)
        if not args:
            raise TypeError("render(request, template, ...) needs a template name")
        template, args = args[0], args[1:]
    if args:
        raise TypeError("render() takes the template name and keyword context only")
    body = env.get_template(template).render(**ctx)
    return HTMLResponse(body, status_code=status, headers=dict(SECURITY_HEADERS))


def flash_html(error: str = "", notice: str = "") -> str:
    """The flash macro rendered to a string, for pages still built from strings."""
    return str(env.get_template("components/display.html").module.flash(error, notice))


def install_static(app) -> None:
    """Serve portal.css / portal.js at /client/static (name 'portal_static')."""
    if any(getattr(route, "name", None) == "portal_static" for route in app.routes):
        return
    app.mount(STATIC_URL, StaticFiles(directory=str(STATIC_DIR)), name="portal_static")


def _resolve(session_resolver: Callable[..., Any], app, request: Request):
    """Accept both ``resolver(request)`` and ``resolver(state, request)``."""
    try:
        params = [p for p in inspect.signature(session_resolver).parameters.values()
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    except (TypeError, ValueError):
        params = []
    if len(params) >= 2:
        return session_resolver(app.state, request)
    return session_resolver(request)


def styleguide_context(business_name: str = "Oak & Pine Tree Care") -> dict[str, Any]:
    """Realistic sample data for every component. Shared with the tests."""
    customers = [
            {"id": "c1", "phone": "+17045550141", "name": "Dana Whitfield", "service": "Oak removal",
             "location": "Matthews", "when": "Thu, Oct 22 at 4:00 PM", "email": "dana@example.com",
             "status": ("ok", "Booked"), "last": "2 hours ago"},
            {"id": "c2", "phone": "+17045550168", "name": "Luis Ortega", "service": "Stump grinding",
             "location": "Mint Hill", "when": "Next Tuesday morning", "email": "",
             "status": ("info", "In progress"), "last": "Yesterday"},
            {"id": "c3", "phone": "+19805550177", "name": "", "service": "",
             "location": "", "when": "", "email": "",
             "status": ("neutral", "New"), "last": "Yesterday"},
            {"id": "c4", "phone": "+17045550192", "name": "Priya Nair", "service": "Crown thinning",
             "location": "Ballantyne", "when": "Any weekday", "email": "priya@example.com",
             "status": ("warn", "Handed off"), "last": "Mon"},
            {"id": "c5", "phone": "+17045550105", "name": "", "service": "",
             "location": "", "when": "", "email": "",
             "status": ("err", "Opted out"), "last": "Oct 12"},
    ]
    rows = [
        {"id": c["id"], "cells": {
            "phone": {"text": format_phone_display(c["phone"]), "sub": c["name"]},
            "service": {"text": c["service"] or "\u2014", "sub": c["location"]},
            "when": c["when"] or "\u2014", "status": c["status"], "last": c["last"]}}
        for c in customers
    ]
    return {
        "title": "Styleguide",
        "active": "home",
        "business_name": business_name,
        "csrf": "styleguide-csrf",
        "remember": False,
        "customers": customers,
        "customer_rows": rows,
        "bubbles": [
            {"dir": "out", "text": f"Hey, sorry we missed your call. This is {business_name}. "
                                   "What can we help with? Reply STOP to opt out.", "meta": "Delivered 2:14 PM"},
            {"dir": "in", "text": "Big oak over the driveway needs to come down", "meta": "2:16 PM"},
            {"dir": "out", "text": "Got it. Where is the job? A street address or neighborhood is fine.", "meta": "Delivered 2:16 PM"},
            {"dir": "in", "text": "412 Elmhurst Dr, Matthews", "meta": "2:17 PM"},
            {"dir": "out", "text": "What day and time work for you? For example, Wednesday at 2 or Friday morning.", "meta": "Delivered 2:17 PM"},
            {"dir": "in", "text": "Thursday at 4", "meta": "2:19 PM"},
        ],
        "steps": [
            {"label": "Brand", "state": "done"},
            {"label": "Campaign", "state": "current"},
            {"label": "Number assigned", "state": "todo"},
        ],
        "forwarding_checks": [
            {"text": "A test call from another phone reached the assistant", "done": True,
             "evidence": "Missed call from a number ending 0177 on Oct 19, 6:33 AM"},
            {"text": "Exactly one first text went out for that call", "done": True,
             "evidence": "One first text sent, delivered Oct 19, 6:33 AM"},
            {"text": "An answered call sent no text", "done": False, "evidence": ""},
            {"text": "Forwarding is on at the carrier", "done": True,
             "evidence": "Ticked by you on Oct 19"},
            {"text": "STOP from the test phone was honored", "done": False, "evidence": ""},
        ],
    }


def install_styleguide(app, session_resolver: Callable[..., Any]) -> None:
    """GET /client/styleguide renders every component with sample data.

    Gated by the owner session: anyone not signed in is sent to /client/login.
    """
    install_static(app)

    @app.get("/client/styleguide", include_in_schema=False)
    def styleguide(request: Request):
        session = _resolve(session_resolver, app, request)
        if not session:
            return RedirectResponse("/client/login", status_code=303)
        ctx = styleguide_context(getattr(app.state, "business_name", "") or "Oak & Pine Tree Care")
        ctx["csrf"] = session.get("csrf", "") if isinstance(session, dict) else ""
        ctx["remember"] = bool(session.get("remember")) if isinstance(session, dict) else False
        from text_back.client_portal import NAV  # the routes that exist in this build
        ctx["nav"] = list(NAV)
        return render("styleguide.html", request=request, **ctx)
