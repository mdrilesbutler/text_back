from fastapi.testclient import TestClient
import pytest

from text_back.app import create_app
from text_back.telecom import FakeTelecom, SignalWireTelecom


def test_create_app_loads_text_back_environment(monkeypatch, tmp_path):
    db_path = tmp_path / "configured.sqlite3"
    monkeypatch.setenv("TEXT_BACK_WEBHOOK_SECRET", "environment-secret")
    monkeypatch.setenv("TEXT_BACK_PUBLIC_BASE_URL", "https://calls.example.test/")
    monkeypatch.setenv("TEXT_BACK_DB_PATH", str(db_path))
    monkeypatch.setenv("TEXT_BACK_WIRING_MODE", "managed")

    app = create_app()
    health = TestClient(app).get("/health").json()

    assert app.state.webhook_secret == "environment-secret"
    assert app.state.public_base_url == "https://calls.example.test"
    assert app.state.db_path == str(db_path)
    assert app.state.wiring_mode == "managed"
    assert db_path.exists()
    assert health["public_base_url"] == "https://calls.example.test"
    assert health["wiring_mode"] == "managed"
    assert "webhook_secret" not in health


def test_explicit_app_config_overrides_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("TEXT_BACK_WEBHOOK_SECRET", "environment-secret")
    monkeypatch.setenv("TEXT_BACK_PUBLIC_BASE_URL", "https://environment.example.test")
    monkeypatch.setenv("TEXT_BACK_DB_PATH", str(tmp_path / "environment.sqlite3"))
    monkeypatch.setenv("TEXT_BACK_WIRING_MODE", "managed")

    app = create_app(
        webhook_secret="explicit-secret",
        public_base_url="https://explicit.example.test/",
        db_path=":memory:",
        wiring_mode="forwarded",
    )

    assert app.state.webhook_secret == "explicit-secret"
    assert app.state.public_base_url == "https://explicit.example.test"
    assert app.state.db_path == ":memory:"
    assert app.state.wiring_mode == "forwarded"


def test_create_app_builds_signalwire_telecom_from_environment(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_TELECOM_MODE", "signalwire")
    monkeypatch.setenv(
        "TEXT_BACK_SIGNALWIRE_SPACE_URL", "https://pilot.signalwire.com/"
    )
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_PROJECT_ID", "project-id")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_API_TOKEN", "secret-token")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_FROM_NUMBER", "+15551234567")

    app = create_app()
    health = TestClient(app).get("/health").json()

    assert isinstance(app.state.telecom, SignalWireTelecom)
    assert health["telecom"] == "signalwire"
    assert "secret-token" not in str(health)
    assert "signalwire_api_token" not in health


def test_signalwire_mode_fails_closed_when_credentials_are_missing(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_TELECOM_MODE", "signalwire")

    with pytest.raises(ValueError, match="TEXT_BACK_SIGNALWIRE_SPACE_URL"):
        create_app()


def test_explicit_telecom_does_not_require_environment_credentials(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_TELECOM_MODE", "signalwire")
    telecom = FakeTelecom()

    app = create_app(telecom=telecom)

    assert app.state.telecom is telecom
