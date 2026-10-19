"""Client settings page: passwordless sign-in and message editing."""
import json
import re
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from text_back.app import create_app
from text_back.messages import MessageSource
from text_back.telecom import FakeTelecom

NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
OWNER = "+19805550123"
BASE = "https://example.test"


def make(tmp_path, monkeypatch, *, owner=OWNER, messages_file=True):
    monkeypatch.setenv("TEXT_BACK_OWNER_MOBILE", owner)
    path = tmp_path / "messages.json"
    if messages_file:
        monkeypatch.setenv("TEXT_BACK_MESSAGES_FILE", str(path))
    else:
        monkeypatch.delenv("TEXT_BACK_MESSAGES_FILE", raising=False)
    clock = [NOW]
    telecom = FakeTelecom()
    app = create_app(db_path=str(tmp_path / "portal.db"), telecom=telecom, public_base_url=BASE,
                     business_name="Oak & Pine Tree Care", now_provider=lambda: clock[0])
    return TestClient(app, base_url=BASE), telecom, clock, path


def code_from(telecom):
    login = [m for m in telecom.outbound if m.kind == "login_code"]
    assert login, "no sign-in text was sent"
    return re.search(r"\b(\d{6})\b", login[-1].body).group(1), login[-1]


def sign_in(client, telecom, mobile="(980) 555-0123"):
    assert client.post("/client/login", data={"mobile": mobile}, follow_redirects=False).status_code == 303
    code, _ = code_from(telecom)
    response = client.post("/client/verify", data={"code": code}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/client/messages"


def csrf_of(page_html):
    return re.search(r"name=csrf value='([^']+)'", page_html).group(1)


def test_login_texts_a_code_only_to_the_number_on_file(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    assert client.get("/client/messages", follow_redirects=False).headers["location"] == "/client/login"
    other = client.post("/client/login", data={"mobile": "980 555 9999"}, follow_redirects=False)
    assert other.status_code == 303 and other.headers["location"] == "/client/verify"  # same answer, no leak
    assert not [m for m in telecom.outbound if m.kind == "login_code"]
    assert client.post("/client/verify", data={"code": "123456"}).status_code == 200  # expired/absent code page

    client.post("/client/login", data={"mobile": "980-555-0123"}, follow_redirects=False)
    code, text = code_from(telecom)
    assert text.to == OWNER
    assert "Oak & Pine Tree Care" in text.body and "10 minutes" in text.body
    assert "characters" not in text.body


def test_wrong_code_five_times_then_locked_and_expiry(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    code, _ = code_from(telecom)
    for _ in range(5):
        page = client.post("/client/verify", data={"code": "000000"})
        assert "not right" in page.text
    assert "expired" in client.post("/client/verify", data={"code": code}).text  # locked after 5 guesses
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    code, _ = code_from(telecom)
    clock[0] += timedelta(minutes=11)
    late = client.post("/client/verify", data={"code": code}, follow_redirects=False)
    assert late.status_code == 303 and late.headers["location"] == "/client/login"  # pending sign-in expired too


def test_code_requests_are_rate_limited_per_number(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    for _ in range(5):
        client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    assert len([m for m in telecom.outbound if m.kind == "login_code"]) == 3
    clock[0] += timedelta(minutes=16)
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    assert len([m for m in telecom.outbound if m.kind == "login_code"]) == 4


def test_signed_in_owner_edits_copy_and_the_app_uses_it(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/messages")
    assert page.status_code == 200 and "Your messages" in page.text
    assert "Hey, sorry we missed your call" in page.text  # default shown as placeholder
    csrf = csrf_of(page.text)
    saved = client.post("/client/messages", data={"csrf": csrf, "intro": "Oak & Pine here, sorry we missed you! What do you need?",
                                                  "prompt_name": "And your name?"})
    assert "Saved" in saved.text
    assert json.loads(path.read_text()) == {"intro": "Oak & Pine here, sorry we missed you! What do you need?",
                                            "prompt_name": "And your name?"}
    live = client.app.state.messages.current()
    assert live.render("intro", business_name="x") == "Oak & Pine here, sorry we missed you! What do you need? Reply STOP to opt out."
    # Clearing a field returns it to the default.
    client.post("/client/messages", data={"csrf": csrf, "intro": ""})
    assert json.loads(path.read_text()) == {}


def test_bad_copy_is_rejected_with_a_reason_and_nothing_is_written(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/messages").text)
    page = client.post("/client/messages", data={"csrf": csrf, "intro": "Call our business line any time"})
    assert "Not saved" in page.text and "business line" in page.text
    assert not path.exists()
    page = client.post("/client/messages", data={"csrf": csrf, "opt_out_suffix": "Reply END to end"})
    assert "Not saved" in page.text and "STOP" in page.text
    assert client.post("/client/messages", data={"csrf": "forged", "intro": "x"}).status_code == 400


def test_logout_ends_the_session_and_sessions_expire(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    csrf = csrf_of(client.get("/client/messages").text)
    assert client.post("/client/logout", data={"csrf": csrf}, follow_redirects=False).headers["location"] == "/client/login"
    assert client.get("/client/messages", follow_redirects=False).headers["location"] == "/client/login"
    sign_in(client, telecom)
    clock[0] += timedelta(hours=13)
    assert client.get("/client/messages", follow_redirects=False).headers["location"] == "/client/login"


def test_without_a_messages_file_the_page_explains_and_cannot_save(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch, messages_file=False)
    sign_in(client, telecom)
    page = client.get("/client/messages")
    assert "not set up" in page.text and "Save messages" not in page.text


def test_login_code_ignores_quiet_hours(tmp_path, monkeypatch):
    monkeypatch.setenv("TEXT_BACK_QUIET_HOURS_START", "00:00")
    monkeypatch.setenv("TEXT_BACK_QUIET_HOURS_END", "23:59")
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    code_from(telecom)
