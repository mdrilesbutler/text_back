"""Sign-in hardening: codes are bound to a purpose and to the owner's number; abuse caps.

B1 (review 2026-10-26): a code texted to a NEW owner mobile let that number sign in as the owner,
even after "Keep my current mobile". Codes now carry a purpose, /client/verify only accepts the
owner's number, and keeping the current mobile deletes the pending number's code.
"""
import html
import re
import sqlite3
from datetime import timedelta

from test_client_portal import NOW, OWNER, csrf_of, make, sign_in

from text_back import portal_phone
from text_back.client_portal import CODE_FAILURE, RATE_LIMITED, check_code, send_code
from text_back.store import Store

NEW = "+19805550199"


def codes_to(telecom, to):
    return [re.search(r"\b(\d{6})\b", m.body).group(1) for m in telecom.outbound if m.kind == "login_code" and m.to == to]


def signed_in_sessions(app):
    return app.state.store.conn.execute("SELECT phone FROM client_sessions WHERE pending=0").fetchall()


def test_p1_a_kept_new_mobile_code_never_signs_that_number_in(tmp_path, monkeypatch):
    owner, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(owner, telecom)
    app = owner.app
    csrf = csrf_of(owner.get("/client/phone").text)
    saved = owner.post("/client/phone", data={"csrf": csrf, "business_name": "Oak", "owner_mobile": "980 555 0199",
                                              "business_line": "", "business_contact": "", "carrier": ""})
    assert saved.status_code == 200 and codes_to(telecom, NEW)
    owner.post("/client/phone/keep", data={"csrf": csrf})
    assert portal_phone.pending_mobile(app.state) is None

    from fastapi.testclient import TestClient
    stranger = TestClient(app, base_url=str(owner.base_url))
    stranger.post("/client/login", data={"mobile": "980 555 0199"}, follow_redirects=False)
    assert len(codes_to(telecom, NEW)) == 1, "a number that is not on file never gets a sign-in code"
    page = stranger.post("/client/verify", data={"code": codes_to(telecom, NEW)[-1]}, follow_redirects=False)
    assert page.status_code == 200 and CODE_FAILURE in html.unescape(page.text)
    assert stranger.get("/client/home", follow_redirects=False).status_code == 303
    assert [row[0] for row in signed_in_sessions(app)] == [OWNER]


def test_keep_current_mobile_deletes_the_pending_numbers_code(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    store = client.app.state.store
    csrf = csrf_of(client.get("/client/phone").text)
    client.post("/client/phone", data={"csrf": csrf, "business_name": "Oak", "owner_mobile": "980 555 0199"})
    assert store.conn.execute("SELECT count(*) FROM client_login_codes WHERE phone=?", (NEW,)).fetchone()[0] == 1
    client.post("/client/phone/keep", data={"csrf": csrf})
    assert store.conn.execute("SELECT count(*) FROM client_login_codes WHERE phone=?", (NEW,)).fetchone()[0] == 0


def test_verify_refuses_a_pending_number_that_is_not_the_owner_even_with_a_live_sign_in_code(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    state = client.app.state
    client.post("/client/login", data={"mobile": "980 555 0199"}, follow_redirects=False)
    send_code(state, NEW, NOW)  # a live sign-in code for a number that is not on file
    page = client.post("/client/verify", data={"code": codes_to(telecom, NEW)[-1]}, follow_redirects=False)
    assert page.status_code == 200 and CODE_FAILURE in html.unescape(page.text)
    assert signed_in_sessions(client.app) == []


def test_a_sign_in_code_cannot_confirm_a_mobile_change(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    state = client.app.state
    state.store.set_setting(portal_phone.PENDING_MOBILE_KEY, NEW)
    send_code(state, NEW, NOW)  # purpose "sign-in"
    assert portal_phone.confirm_new_mobile(state, codes_to(telecom, NEW)[-1], NOW) is None
    assert state.owner_mobile == OWNER and portal_phone.pending_mobile(state) == NEW
    send_code(state, NEW, NOW, purpose=portal_phone.CODE_PURPOSE)
    assert portal_phone.confirm_new_mobile(state, codes_to(telecom, NEW)[-1], NOW) == NEW


def test_a_new_mobile_code_cannot_sign_in_even_for_the_owners_number(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    state = client.app.state
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    send_code(state, OWNER, NOW, purpose=portal_phone.CODE_PURPOSE)  # replaces the sign-in code
    page = client.post("/client/verify", data={"code": codes_to(telecom, OWNER)[-1]}, follow_redirects=False)
    assert page.status_code == 200 and CODE_FAILURE in html.unescape(page.text)
    assert signed_in_sessions(client.app) == []


def test_check_code_requires_the_purpose(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    state = client.app.state
    send_code(state, OWNER, NOW, purpose="new mobile")
    code = codes_to(telecom, OWNER)[-1]
    assert check_code(state, OWNER, code, NOW, purpose="sign-in") is False
    assert check_code(state, OWNER, code, NOW, purpose="new mobile") is True


def test_an_old_database_gains_the_purpose_column(tmp_path):
    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE client_login_codes (
        phone TEXT PRIMARY KEY, code_hash TEXT NOT NULL, expires_at TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)""")
    conn.execute("INSERT INTO client_login_codes VALUES('+19805550123','h','2099-01-01T00:00:00+00:00',0,'2026-10-26T00:00:00+00:00')")
    conn.commit(); conn.close()
    store = Store(path)
    columns = {row[1] for row in store.conn.execute("PRAGMA table_info(client_login_codes)")}
    assert "purpose" in columns
    assert store.conn.execute("SELECT purpose FROM client_login_codes").fetchone()[0] == "sign-in"
    Store(path)  # a second open is a no-op


# --- Note 1: abuse caps -----------------------------------------------------------

def test_ten_code_texts_per_number_per_rolling_day(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    for i in range(10):
        response = client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
        assert response.status_code == 303, i
        clock[0] += timedelta(minutes=16)
    assert len(codes_to(telecom, OWNER)) == 10
    capped = client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    assert capped.status_code == 200 and RATE_LIMITED in html.unescape(capped.text)
    assert len(codes_to(telecom, OWNER)) == 10
    clock[0] = NOW + timedelta(hours=24, minutes=1)  # the first request has rolled out of the day
    assert client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False).status_code == 303
    assert len(codes_to(telecom, OWNER)) == 11


def test_the_daily_cap_reads_the_same_for_a_number_not_on_file(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    for _ in range(10):
        assert client.post("/client/login", data={"mobile": "980 555 9999"}, follow_redirects=False).status_code == 303
        clock[0] += timedelta(minutes=16)
    capped = client.post("/client/login", data={"mobile": "980 555 9999"}, follow_redirects=False)
    assert capped.status_code == 200 and RATE_LIMITED in html.unescape(capped.text)


def test_send_code_itself_stops_at_ten_a_day(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    state = client.app.state
    for i in range(12):
        send_code(state, NEW, NOW + timedelta(minutes=16 * i), purpose=portal_phone.CODE_PURPOSE)
    assert len(codes_to(telecom, NEW)) == 10


def test_login_purges_pending_sessions_older_than_a_day(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    store = client.app.state.store
    client.post("/client/login", data={"mobile": "980 555 9999"}, follow_redirects=False)
    clock[0] += timedelta(hours=23)
    client.post("/client/login", data={"mobile": "980 555 9998"}, follow_redirects=False)
    assert store.conn.execute("SELECT count(*) FROM client_sessions WHERE pending=1").fetchone()[0] == 2
    clock[0] += timedelta(hours=2)
    client.post("/client/login", data={"mobile": "980 555 9997"}, follow_redirects=False)
    phones = [r[0] for r in store.conn.execute("SELECT phone FROM client_sessions WHERE pending=1 ORDER BY created_at")]
    assert phones == ["+19805559998", "+19805559997"]
