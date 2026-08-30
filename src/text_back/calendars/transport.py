from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from text_back.calendars.protocol import CalendarProviderError

REQUEST_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class HttpRequest:
    method: str  # "GET" | "POST" | "PUT" | "REPORT"
    url: str
    headers: tuple[tuple[str, str], ...]
    body: bytes | None = None


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: tuple[tuple[str, str], ...]
    body: bytes


HttpTransport = Callable[[HttpRequest], HttpResponse]
TokenProvider = Callable[[], str]  # returns a current bearer token / secret


class RedirectRefusingHandler(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect. stdlib urllib would otherwise replay the
    original headers — Authorization included — to whatever host a 3xx
    Location names (requests strips auth cross-host; urllib does not).
    Raising here surfaces the 3xx as an HttpResponse below, so adapters
    fail closed via their existing status checks."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)


_OPENER = urllib.request.build_opener(RedirectRefusingHandler)


def urllib_transport(request: HttpRequest) -> HttpResponse:
    """Production transport. HTTP error statuses (redirects included — see
    RedirectRefusingHandler) come back AS HttpResponse so adapters own
    3xx/4xx/5xx policy; network-level failures raise a redacted
    CalendarProviderError (no URL, no credentials in the message)."""
    req = urllib.request.Request(
        request.url,
        data=request.body,
        headers=dict(request.headers),
        method=request.method,
    )
    try:
        with _OPENER.open(req, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return HttpResponse(
                status=response.status,
                headers=tuple((k, v) for k, v in response.headers.items()),
                body=response.read(),
            )
    except urllib.error.HTTPError as exc:
        body = exc.read()
        return HttpResponse(
            status=exc.code,
            headers=tuple((k, v) for k, v in (exc.headers or {}).items()),
            body=body,
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise CalendarProviderError(
            f"calendar HTTP transport failure ({type(exc).__name__})"
        ) from None


def file_token_provider(path: str) -> TokenProvider:
    """Returns a closure that reads the credential file fresh on EVERY call —
    an external refresher may rotate it at any time."""

    def read_token() -> str:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                token = handle.read().strip()
        except OSError:
            raise CalendarProviderError(
                "calendar credential file unreadable or empty"
            ) from None
        if not token:
            raise CalendarProviderError("calendar credential file unreadable or empty")
        return token

    return read_token


def rfc3339_utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ics_utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@dataclass
class FakeHttpTransport:
    """Test transport: records every HttpRequest and pops canned responses."""

    responses: list[HttpResponse] = field(default_factory=list)
    requests: list[HttpRequest] = field(default_factory=list)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError(
                "FakeHttpTransport received a request with no canned responses left"
            )
        return self.responses.pop(0)
