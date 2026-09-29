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
    monkeypatch.setenv("TEXT_BACK_BUSINESS_NAME", "Oak & Pine Tree Care")
    monkeypatch.setenv("TEXT_BACK_TIMEZONE", "America/New_York")
    monkeypatch.setenv("TEXT_BACK_APPOINTMENT_DURATION_MINUTES", "90")
    monkeypatch.setenv("TEXT_BACK_HANDOFF_DESTINATION", "operator-queue")

    app = create_app()
    health = TestClient(app).get("/health").json()

    assert app.state.webhook_secret == "environment-secret"
    assert app.state.public_base_url == "https://calls.example.test"
    assert app.state.db_path == str(db_path)
    assert app.state.wiring_mode == "managed"
    assert app.state.business_name == "Oak & Pine Tree Care"
    assert app.state.timezone_name == "America/New_York"
    assert app.state.appointment_duration_minutes == 90
    assert app.state.handoff_destination == "operator-queue"
    assert db_path.exists()
    assert health["public_base_url"] == "https://calls.example.test"
    assert health["wiring_mode"] == "managed"
    assert health["timezone"] == "America/New_York"
    assert health["appointment_duration_minutes"] == 90
    assert health["handoff_notifier"] == "stub"
    assert health["handoff_destination_configured"] is True
    assert "operator-queue" not in str(health)
    assert "webhook_secret" not in health


def test_explicit_app_config_overrides_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("TEXT_BACK_WEBHOOK_SECRET", "environment-secret")
    monkeypatch.setenv("TEXT_BACK_PUBLIC_BASE_URL", "https://environment.example.test")
    monkeypatch.setenv("TEXT_BACK_DB_PATH", str(tmp_path / "environment.sqlite3"))
    monkeypatch.setenv("TEXT_BACK_WIRING_MODE", "managed")
    monkeypatch.setenv("TEXT_BACK_BUSINESS_NAME", "Environment Business")
    monkeypatch.setenv("TEXT_BACK_TIMEZONE", "America/Chicago")
    monkeypatch.setenv("TEXT_BACK_APPOINTMENT_DURATION_MINUTES", "120")
    monkeypatch.setenv("TEXT_BACK_HANDOFF_DESTINATION", "environment-queue")

    app = create_app(
        webhook_secret="explicit-secret",
        public_base_url="https://explicit.example.test/",
        db_path=":memory:",
        wiring_mode="forwarded",
        business_name="Explicit Business",
        timezone_name="America/New_York",
        appointment_duration_minutes=45,
        handoff_destination="explicit-queue",
    )

    assert app.state.webhook_secret == "explicit-secret"
    assert app.state.public_base_url == "https://explicit.example.test"
    assert app.state.db_path == ":memory:"
    assert app.state.wiring_mode == "forwarded"
    assert app.state.business_name == "Explicit Business"
    assert app.state.timezone_name == "America/New_York"
    assert app.state.appointment_duration_minutes == 45
    assert app.state.handoff_destination == "explicit-queue"


def test_create_app_builds_signalwire_telecom_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("TEXT_BACK_TELECOM_MODE", "signalwire")
    monkeypatch.setenv("TEXT_BACK_WEBHOOK_SECRET", "signalwire-signing-key")
    monkeypatch.setenv("TEXT_BACK_PUBLIC_BASE_URL", "https://calls.example.test")
    monkeypatch.setenv("TEXT_BACK_BUSINESS_NAME", "Pilot Business")
    monkeypatch.setenv(
        "TEXT_BACK_SIGNALWIRE_SPACE_URL", "https://pilot.signalwire.com/"
    )
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_PROJECT_ID", "project-id")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_API_TOKEN", "secret-token")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_FROM_NUMBER", "+15551234567")
    monkeypatch.setenv("TEXT_BACK_DB_PATH", str(tmp_path / "runtime.db"))
    # SignalWire mode refuses the stub calendar, so wire a real provider too.
    token_file = tmp_path / "google.token"
    token_file.write_text("tok-test\n")
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "google")
    monkeypatch.setenv("TEXT_BACK_GOOGLE_CALENDAR_ID", "mike@example.test")
    monkeypatch.setenv("TEXT_BACK_GOOGLE_TOKEN_FILE", str(token_file))

    app = create_app()
    health = TestClient(app).get("/health").json()

    assert isinstance(app.state.telecom, SignalWireTelecom)
    assert health["telecom"] == "signalwire"
    assert health["calendar"] == "google"
    assert "secret-token" not in str(health)
    assert "signalwire_api_token" not in health


def test_signalwire_mode_refuses_default_stub_calendar(monkeypatch):
    # A fully production-wired app must not silently boot against the
    # in-memory stub calendar: bookings would be "confirmed" with fabricated
    # event ids while no real calendar records the appointment.
    monkeypatch.setenv("TEXT_BACK_TELECOM_MODE", "signalwire")
    monkeypatch.setenv("TEXT_BACK_WEBHOOK_SECRET", "signalwire-signing-key")
    monkeypatch.setenv("TEXT_BACK_PUBLIC_BASE_URL", "https://calls.example.test")
    monkeypatch.setenv(
        "TEXT_BACK_SIGNALWIRE_SPACE_URL", "https://pilot.signalwire.com/"
    )
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_PROJECT_ID", "project-id")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_API_TOKEN", "secret-token")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_FROM_NUMBER", "+15551234567")
    monkeypatch.delenv("TEXT_BACK_CALENDAR_PROVIDER", raising=False)

    with pytest.raises(ValueError, match="TEXT_BACK_CALENDAR_PROVIDER"):
        create_app()

    # An explicit 'stub' value fails closed the same way.
    monkeypatch.setenv("TEXT_BACK_CALENDAR_PROVIDER", "stub")
    with pytest.raises(ValueError, match="TEXT_BACK_CALENDAR_PROVIDER"):
        create_app()


def test_signalwire_mode_fails_closed_when_credentials_are_missing(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_TELECOM_MODE", "signalwire")

    with pytest.raises(ValueError, match="TEXT_BACK_SIGNALWIRE_SPACE_URL"):
        create_app()


def test_signalwire_mode_rejects_default_webhook_secret(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_TELECOM_MODE", "signalwire")
    monkeypatch.setenv("TEXT_BACK_PUBLIC_BASE_URL", "https://calls.example.test")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_SPACE_URL", "https://pilot.signalwire.com")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_PROJECT_ID", "project-id")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_API_TOKEN", "secret-token")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_FROM_NUMBER", "+15551234567")

    with pytest.raises(ValueError, match="TEXT_BACK_WEBHOOK_SECRET"):
        create_app()


def test_signalwire_mode_requires_https_public_url(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_TELECOM_MODE", "signalwire")
    monkeypatch.setenv("TEXT_BACK_WEBHOOK_SECRET", "signalwire-signing-key")
    monkeypatch.setenv("TEXT_BACK_PUBLIC_BASE_URL", "http://calls.example.test")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_SPACE_URL", "https://pilot.signalwire.com")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_PROJECT_ID", "project-id")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_API_TOKEN", "secret-token")
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_FROM_NUMBER", "+15551234567")

    with pytest.raises(ValueError, match="HTTPS"):
        create_app()


def test_explicit_telecom_does_not_require_environment_credentials(monkeypatch):
    monkeypatch.setenv("TEXT_BACK_TELECOM_MODE", "signalwire")
    telecom = FakeTelecom()

    app = create_app(telecom=telecom)

    assert app.state.telecom is telecom


def test_invalid_booking_configuration_fails_at_startup():
    with pytest.raises(ValueError, match="IANA timezone"):
        create_app(timezone_name="Not/A_Timezone")

    with pytest.raises(ValueError, match="must be positive"):
        create_app(appointment_duration_minutes=0)


def test_signalwire_runtime_requires_persistent_database(monkeypatch, tmp_path):
    monkeypatch.setenv('TEXT_BACK_TELECOM_MODE','signalwire')
    monkeypatch.setenv('TEXT_BACK_WEBHOOK_SECRET','test-signing-key')
    monkeypatch.setenv('TEXT_BACK_PUBLIC_BASE_URL','https://example.test')
    monkeypatch.setenv('TEXT_BACK_SIGNALWIRE_SPACE_URL','https://example.signalwire.com')
    monkeypatch.setenv('TEXT_BACK_SIGNALWIRE_PROJECT_ID','test-project')
    monkeypatch.setenv('TEXT_BACK_SIGNALWIRE_API_TOKEN','test-token')
    monkeypatch.setenv('TEXT_BACK_SIGNALWIRE_FROM_NUMBER','+15553334444')
    monkeypatch.setenv('TEXT_BACK_CALENDAR_PROVIDER','google')
    path=tmp_path/'token';path.write_text('test-token')
    monkeypatch.setenv('TEXT_BACK_GOOGLE_TOKEN_FILE',str(path))
    monkeypatch.setenv('TEXT_BACK_GOOGLE_CALENDAR_ID','primary')
    with pytest.raises(ValueError,match='persistent'):
        create_app(db_path=':memory:')
