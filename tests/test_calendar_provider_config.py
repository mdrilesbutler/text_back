from fastapi.testclient import TestClient
import pytest

from text_back.app import create_app
from text_back.calendar_stub import CalendarStub


def test_default_provider_is_stub_and_health_reports_it():
    app = create_app()
    assert app.state.calendar.provider_name == "stub"
    health = TestClient(app).get("/health").json()
    assert health["calendar"] == "stub"


def test_unknown_provider_fails_closed_at_create_app(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "calcom")

    with pytest.raises(ValueError, match="TEXT_BACK_CALENDAR_PROVIDER"):
        create_app()


def test_google_mode_refuses_startup_without_credentials(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "google")

    with pytest.raises(ValueError) as excinfo:
        create_app()
    assert "TEXT_BACK_GOOGLE_CALENDAR_ID" in str(excinfo.value)
    assert "TEXT_BACK_GOOGLE_TOKEN_FILE" in str(excinfo.value)


def test_google_mode_refuses_missing_token_file(monkeypatch, tmp_path):
    missing = tmp_path / "does-not-exist.token"
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "google")
    monkeypatch.setenv("TEXT_BACK_GOOGLE_CALENDAR_ID", "mike@example.test")
    monkeypatch.setenv("TEXT_BACK_GOOGLE_TOKEN_FILE", str(missing))

    with pytest.raises(ValueError) as excinfo:
        create_app()
    assert "TEXT_BACK_GOOGLE_TOKEN_FILE" in str(excinfo.value)
    # Never leak filesystem detail beyond the env var name.
    assert str(tmp_path) not in str(excinfo.value)


def test_microsoft_mode_refuses_without_credentials(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "microsoft")

    with pytest.raises(ValueError) as excinfo:
        create_app()
    assert "TEXT_BACK_MS_USER" in str(excinfo.value)
    assert "TEXT_BACK_MS_TOKEN_FILE" in str(excinfo.value)


def test_icloud_mode_refuses_without_credentials(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "icloud")

    with pytest.raises(ValueError) as excinfo:
        create_app()
    message = str(excinfo.value)
    assert "TEXT_BACK_ICLOUD_USERNAME" in message
    assert "TEXT_BACK_ICLOUD_APP_PASSWORD_FILE" in message
    assert "TEXT_BACK_ICLOUD_CALENDAR_URL" in message


def test_icloud_mode_refuses_non_https_calendar_url(monkeypatch, tmp_path):
    password_file = tmp_path / "app-password"
    password_file.write_text("fixture-password\n")
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "icloud")
    monkeypatch.setenv("TEXT_BACK_ICLOUD_USERNAME", "mike@example.test")
    monkeypatch.setenv("TEXT_BACK_ICLOUD_APP_PASSWORD_FILE", str(password_file))
    monkeypatch.setenv(
        "TEXT_BACK_ICLOUD_CALENDAR_URL",
        "http://caldav.icloud.com/123/calendars/home/",
    )

    with pytest.raises(ValueError, match="HTTPS"):
        create_app()


@pytest.mark.parametrize(
    "url",
    [
        # Credentials are Basic-auth'd to whatever host this names, so only
        # Apple's own hosts are acceptable for the 'icloud' provider.
        "https://caldav.example.test/123/calendars/home/",
        "https://icloud.com.evil.test/123/calendars/home/",
        "https://user:pass@caldav.icloud.com/123/calendars/home/",
    ],
)
def test_icloud_mode_refuses_non_icloud_hosts_and_embedded_userinfo(
    monkeypatch, tmp_path, url
):
    password_file = tmp_path / "app-password"
    password_file.write_text("fixture-password\n")
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "icloud")
    monkeypatch.setenv("TEXT_BACK_ICLOUD_USERNAME", "mike@example.test")
    monkeypatch.setenv("TEXT_BACK_ICLOUD_APP_PASSWORD_FILE", str(password_file))
    monkeypatch.setenv("TEXT_BACK_ICLOUD_CALENDAR_URL", url)

    with pytest.raises(ValueError, match="icloud.com"):
        create_app()


def test_injected_calendar_still_bypasses_provider_config(monkeypatch):
    # Mirrors telecom= injection semantics: explicit injection skips env
    # validation so tests can build apps without provider credentials.
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "google")

    calendar = CalendarStub()
    app = create_app(calendar=calendar)

    assert app.state.calendar is calendar


def test_google_mode_with_valid_config_constructs_google_provider(
    monkeypatch, tmp_path
):
    token_file = tmp_path / "google.token"
    token_file.write_text("tok-test\n")
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "google")
    monkeypatch.setenv("TEXT_BACK_GOOGLE_CALENDAR_ID", "mike@example.test")
    monkeypatch.setenv("TEXT_BACK_GOOGLE_TOKEN_FILE", str(token_file))

    app = create_app()

    assert app.state.calendar.provider_name == "google"
    health = TestClient(app).get("/health").json()
    assert health["calendar"] == "google"
    assert "tok-test" not in str(health)


def test_microsoft_mode_with_valid_config_constructs_microsoft_provider(
    monkeypatch, tmp_path
):
    token_file = tmp_path / "ms.token"
    token_file.write_text("tok-test\n")
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "microsoft")
    monkeypatch.setenv("TEXT_BACK_MS_USER", "mike@example.test")
    monkeypatch.setenv("TEXT_BACK_MS_TOKEN_FILE", str(token_file))

    app = create_app()

    assert app.state.calendar.provider_name == "microsoft"
    health = TestClient(app).get("/health").json()
    assert health["calendar"] == "microsoft"
    assert "tok-test" not in str(health)


def test_icloud_mode_with_valid_config_constructs_icloud_provider(
    monkeypatch, tmp_path
):
    password_file = tmp_path / "app-password"
    password_file.write_text("fixture-password\n")
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "icloud")
    monkeypatch.setenv("TEXT_BACK_ICLOUD_USERNAME", "mike@example.test")
    monkeypatch.setenv("TEXT_BACK_ICLOUD_APP_PASSWORD_FILE", str(password_file))
    monkeypatch.setenv(
        "TEXT_BACK_ICLOUD_CALENDAR_URL",
        "https://caldav.icloud.com/123/calendars/home/",
    )

    app = create_app()

    assert app.state.calendar.provider_name == "icloud"
    health = TestClient(app).get("/health").json()
    assert health["calendar"] == "icloud"
    assert "fixture-password" not in str(health)
