from __future__ import annotations

import os
import urllib.parse

from text_back.calendar_stub import CalendarStub
from text_back.calendars.google import GoogleCalendarProvider
from text_back.calendars.icloud import ICloudCalDAVProvider
from text_back.calendars.microsoft import MicrosoftGraphProvider
from text_back.calendars.protocol import CalendarProvider
from text_back.calendars.transport import file_token_provider, urllib_transport

_KNOWN_PROVIDERS = {"stub", "google", "microsoft", "icloud"}


def calendar_from_config(config, *, timezone_name: str) -> CalendarProvider:
    """Build the configured calendar provider, failing closed at startup on
    unknown provider values, missing credentials, or absent credential files —
    the same pattern as _telecom_from_config / transport_from_config."""
    provider = config.calendar_provider
    if provider == "stub":
        return CalendarStub(timezone_name=timezone_name)
    if provider not in _KNOWN_PROVIDERS:
        raise ValueError(
            "invalid TEXT_BACK_CALENDAR_PROVIDER; must be one of "
            "'stub', 'google', 'microsoft', 'icloud'"
        )

    if provider == "google":
        _require(
            "google",
            {
                "TEXT_BACK_GOOGLE_CALENDAR_ID": config.google_calendar_id,
                "TEXT_BACK_GOOGLE_TOKEN_FILE": config.google_token_file,
            },
        )
        _require_credential_file("TEXT_BACK_GOOGLE_TOKEN_FILE", config.google_token_file)
        return GoogleCalendarProvider(
            calendar_id=config.google_calendar_id,
            token_provider=file_token_provider(config.google_token_file),
            transport=urllib_transport,
        )

    if provider == "microsoft":
        _require(
            "microsoft",
            {
                "TEXT_BACK_MS_USER": config.ms_user,
                "TEXT_BACK_MS_TOKEN_FILE": config.ms_token_file,
            },
        )
        _require_credential_file("TEXT_BACK_MS_TOKEN_FILE", config.ms_token_file)
        return MicrosoftGraphProvider(
            user=config.ms_user,
            token_provider=file_token_provider(config.ms_token_file),
            transport=urllib_transport,
        )

    # icloud
    _require(
        "icloud",
        {
            "TEXT_BACK_ICLOUD_USERNAME": config.icloud_username,
            "TEXT_BACK_ICLOUD_APP_PASSWORD_FILE": config.icloud_app_password_file,
            "TEXT_BACK_ICLOUD_CALENDAR_URL": config.icloud_calendar_url,
        },
    )
    _require_icloud_calendar_url(config.icloud_calendar_url)
    _require_credential_file(
        "TEXT_BACK_ICLOUD_APP_PASSWORD_FILE", config.icloud_app_password_file
    )
    return ICloudCalDAVProvider(
        username=config.icloud_username,
        password_provider=file_token_provider(config.icloud_app_password_file),
        transport=urllib_transport,
        calendar_url=config.icloud_calendar_url,
    )


def _require_icloud_calendar_url(url: str) -> None:
    """The provider is named 'icloud', so restrict the CalDAV endpoint to
    Apple's own hosts — the Apple ID and app-specific password are sent as
    Basic auth to whatever host this URL names. Reject embedded userinfo too.
    Self-hosted CalDAV, if ever wanted, gets its own provider value instead
    of loosening this check."""
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or not (host == "icloud.com" or host.endswith(".icloud.com"))
    ):
        raise ValueError(
            "TEXT_BACK_ICLOUD_CALENDAR_URL must be an HTTPS *.icloud.com URL "
            "without embedded credentials"
        )


def _require(mode: str, required: dict[str, str]) -> None:
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(
            f"{mode} calendar mode is missing required configuration: "
            + ", ".join(missing)
        )


def _require_credential_file(env_name: str, path: str) -> None:
    # Name only the env var — never echo the path or its contents.
    if not os.path.isfile(path):
        raise ValueError(f"{env_name} credential file is missing")
