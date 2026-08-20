from fastapi.testclient import TestClient

from text_back.app import create_app


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
