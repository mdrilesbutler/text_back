"""Portal shell: landing, nav, headers, remembered sessions, Account, Home data."""
import json
import re
from datetime import datetime, timedelta, timezone

from text_back import portal_data
from text_back.client_portal import NAV
from text_back.store import Store

from test_client_portal import OWNER, code_from, csrf_of, make as _make, sign_in

NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)  # a Monday
CSP_FORM = "form-action 'self' https://accounts.google.com"
CALLER_A, CALLER_B, CALLER_C = "+17045550141", "+17045550168", "+19805550177"


def make(tmp_path, monkeypatch, **kwargs):
    # Never read the real staged registration responses from a test.
    monkeypatch.setenv("TEXT_BACK_REGISTRATION_DIR", str(tmp_path / "no-such-dir"))
    return _make(tmp_path, monkeypatch, **kwargs)


def seed_sms(store, key, phone, body, kind, created_at, status="sent"):
    store.conn.execute(
        "INSERT INTO sms_outbox(key,phone,from_number,body,kind,completion_json,status,next_attempt_at,created_at) "
        "VALUES(?,?,?,?,?,'{}',?,?,?)", (key, phone, "+19805550100", body, kind, status, created_at.isoformat(), created_at.isoformat()))
    store.conn.commit()


def seed_inbound(store, key, kind, phone, params, received_at):
    store.conn.execute(
        "INSERT INTO inbound_jobs(key,kind,phone,params_json,received_at,status,next_attempt_at) VALUES(?,?,?,?,?,'done',?)",
        (key, kind, phone, json.dumps(params), received_at.isoformat(), received_at.isoformat()))
    store.conn.commit()


def seed_event(store, phone, event_type, when, evidence="ev", key=None):
    store.record_outcome(lead_id=phone, event_type=event_type, idempotency_key=key or f"{phone}:{event_type}:{when.isoformat()}",
                         evidence_id=evidence, occurred_at=when.isoformat())


# --- landing, nav, headers -------------------------------------------------------

def test_landing_is_home_and_nav_links_only_to_routes_that_exist(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    assert client.get("/client", follow_redirects=False).headers["location"] == "/client/login"
    sign_in(client, telecom)  # asserts the 303 lands on /client
    home = client.get("/client")
    assert home.status_code == 200 and "<h1>Home</h1>" in home.text
    assert home.text.count("<h1") == 1
    for key, label, href, _ in NAV:
        assert f'href="{href}"' in home.text and f"<span>{label}</span>" in home.text
        assert client.get(href, follow_redirects=False).status_code == 200, href
    styleguide = client.get("/client/styleguide").text
    for missing in ("/client/customers", "/client/phone"):
        assert missing not in home.text and missing not in styleguide
    assert '<h2 class="sr-only" id="setup-heading">Setup</h2>' in home.text and 'class="hide-sm"' in home.text
    assert 'href="/client" aria-current="page"' in home.text
    assert client.get("/client/login", follow_redirects=False).headers["location"] == "/client"
    assert client.get("/client/verify", follow_redirects=False).headers["location"] == "/client"


def test_every_portal_page_carries_the_security_headers(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    pages = ["/client/login"]
    login = client.get("/client/login")
    assert login.status_code == 200
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    verify = client.get("/client/verify")
    assert verify.status_code == 200
    sign_in(client, telecom)
    responses = [login, verify] + [client.get(path) for path in ("/client", "/client/account", "/client/messages", "/client/scheduling", "/client/business", "/client/calendar", "/client/styleguide")]
    for response in responses:
        assert response.status_code == 200, response.url
        csp = response.headers["content-security-policy"]
        assert "script-src 'self'" in csp and "style-src 'self'" in csp and CSP_FORM in csp
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert "<script>" not in response.text and ' style="' not in response.text
        assert response.text.count("<h1") == 1, response.url
    css = client.get("/client/static/portal.css")
    assert css.status_code == 200 and css.headers["content-type"].startswith("text/css")


# --- sessions and remember ---------------------------------------------------------

def test_plain_session_dies_after_12_hours_and_remembered_one_lasts_30_days(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    clock[0] += timedelta(hours=13)
    assert client.get("/client", follow_redirects=False).headers["location"] == "/client/login"

    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    code, _ = code_from(telecom)
    response = client.post("/client/verify", data={"code": code, "remember": "1"}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/client"
    assert "Max-Age=2592000" in response.headers["set-cookie"]
    clock[0] += timedelta(hours=13)
    assert client.get("/client", follow_redirects=False).status_code == 200
    clock[0] += timedelta(days=29)  # 29d 13h in total: still inside 30 days
    assert client.get("/client", follow_redirects=False).status_code == 200
    clock[0] += timedelta(days=1, hours=12)  # past 31 days
    assert client.get("/client", follow_redirects=False).headers["location"] == "/client/login"


def test_account_toggle_flips_the_session_expiry_both_ways(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    page = client.get("/client/account")
    assert page.status_code == 200 and "Remember this phone for 30 days" in page.text
    assert "Signed in as (980) 555-0123" in page.text and 'name="remember" value="1"' in page.text
    assert "<h2>Signed in</h2>" in page.text and 'aria-describedby="remember-label"' in page.text
    csrf = csrf_of(page.text)
    assert client.post("/client/account", data={"csrf": "forged", "remember": "1"}).status_code == 400

    on = client.post("/client/account", data={"csrf": csrf, "remember": "1"})
    assert on.status_code == 200 and "This phone stays signed in for 30 days." in on.text
    assert "Max-Age=2592000" in on.headers["set-cookie"] and 'name="remember" value="0"' in on.text
    assert client.app.state.store.setting("remember_default") == "1"
    row = client.app.state.store.conn.execute("SELECT remember, expires_at FROM client_sessions WHERE pending=0").fetchone()
    assert row["remember"] == 1 and datetime.fromisoformat(row["expires_at"]) == clock[0] + timedelta(days=30)
    clock[0] += timedelta(hours=13)
    assert client.get("/client", follow_redirects=False).status_code == 200

    off = client.post("/client/account", data={"csrf": csrf, "remember": "0"})
    assert "This phone signs out after 12 hours." in off.text and "Max-Age=43200" in off.headers["set-cookie"]
    assert client.app.state.store.setting("remember_default") == "0"
    row = client.app.state.store.conn.execute("SELECT remember, expires_at FROM client_sessions WHERE pending=0").fetchone()
    assert row["remember"] == 0 and datetime.fromisoformat(row["expires_at"]) == clock[0] + timedelta(hours=12)
    clock[0] += timedelta(hours=13)
    assert client.get("/client", follow_redirects=False).headers["location"] == "/client/login"


def test_verify_page_checkbox_follows_the_saved_default_and_stays_request_independent(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    page = client.get("/client/verify").text
    assert "name=remember value=1" in page and "checked" not in page and "Remember this phone for 30 days" in page
    unknown = client.post("/client/verify", data={"code": "000000"}).text
    client.app.state.store.set_setting("remember_default", "1")
    client.post("/client/login", data={"mobile": "980 555 9999"}, follow_redirects=False)
    ticked = client.post("/client/verify", data={"code": "123456"}).text
    assert "name=remember value=1 checked" in ticked
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    wrong = client.post("/client/verify", data={"code": "000000"}).text
    assert ticked == wrong and unknown != ticked  # identical per request, varies only with the saved default


def test_old_databases_get_the_remember_column_and_indexes(tmp_path):
    path = str(tmp_path / "old.db")
    first = Store(path)
    first.conn.execute("DROP INDEX idx_sms_outbox_phone")
    first.conn.execute("ALTER TABLE client_sessions DROP COLUMN remember")
    first.conn.commit()
    first.conn.close()
    again = Store(path)
    columns = {row[1] for row in again.conn.execute("PRAGMA table_info(client_sessions)")}
    assert "remember" in columns
    indexes = {row[1] for row in again.conn.execute("PRAGMA index_list(sms_outbox)")}
    assert "idx_sms_outbox_phone" in indexes
    assert "idx_inbound_jobs_phone" in {row[1] for row in again.conn.execute("PRAGMA index_list(inbound_jobs)")}
    Store(path)  # idempotent


# --- Home data ----------------------------------------------------------------------

def test_week_counts_use_monday_in_the_business_timezone(tmp_path, monkeypatch):
    monkeypatch.setenv("TEXT_BACK_TIMEZONE", "America/New_York")
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    store = client.app.state.store
    monday_local = datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc)  # Mon 00:00 EDT
    seed_event(store, CALLER_A, "call.missed", monday_local + timedelta(hours=6), evidence="CA1")
    seed_event(store, CALLER_B, "call.missed", monday_local + timedelta(hours=7), evidence="CA2")
    seed_event(store, CALLER_C, "call.missed", monday_local - timedelta(hours=1), evidence="CA0")  # Sunday night local
    seed_event(store, CALLER_A, "calendar.event_created", monday_local + timedelta(hours=8))
    seed_event(store, CALLER_B, "lead.handoff_requested", monday_local + timedelta(hours=8))
    seed_event(store, CALLER_C, "lead.handoff_requested", monday_local - timedelta(days=3))
    seed_sms(store, "CA1:intro", CALLER_A, "Hey, sorry we missed your call.", "missed_call_intro", monday_local + timedelta(hours=6))
    seed_sms(store, "CA2:intro", CALLER_B, "Hey, sorry we missed your call.", "missed_call_intro", monday_local + timedelta(hours=7))
    seed_sms(store, "CA2:f1", CALLER_B, "Still there?", "followup", monday_local + timedelta(hours=9), status="pending")
    seed_sms(store, "login:x", OWNER, "[sign-in code]", "login_code", monday_local + timedelta(hours=9))
    seed_sms(store, "CA0:intro", CALLER_C, "old", "missed_call_intro", monday_local - timedelta(days=2))
    counts = portal_data.week_counts(store, "America/New_York", clock[0])
    assert counts == {"missed_calls": 2, "texts_sent": 2, "booked": 1, "handed_off": 1}
    sign_in(client, telecom)
    home = client.get("/client").text
    assert "Since Monday, Oct 19." in home
    tiles = re.findall(r'<div class="label">([^<]+)</div>\s*<div class="value">([^<]+)</div>', home)
    assert tiles == [("Missed calls", "2"), ("Texts sent", "2"), ("Booked", "1"), ("Handed off", "1")]


def test_last_conversations_are_ordered_latest_first_with_derived_status(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    store = client.app.state.store
    t0 = NOW - timedelta(hours=5)
    # A: missed call, replied, qualified, booked -> Booked; named Dana.
    seed_event(store, CALLER_A, "call.missed", t0, evidence="CA1")
    seed_sms(store, "CA1:intro", CALLER_A, "Hey, sorry we missed your call. This is Oak & Pine Tree Care.", "missed_call_intro", t0)
    seed_inbound(store, "sms:m1", "sms", CALLER_A, {"body": "Big oak over the driveway needs to come down before the storm season starts"}, t0 + timedelta(minutes=2))
    seed_event(store, CALLER_A, "sms.customer_replied", t0 + timedelta(minutes=2))
    seed_event(store, CALLER_A, "lead.qualified", t0 + timedelta(minutes=9))
    store.set_conversation_field(CALLER_A, "name", "Dana")
    store.save_appointment(conversation_id=CALLER_A, event_id="evt-1", caller=CALLER_A, start="2026-10-22T16:00:00-04:00", location="Matthews", service="oak")
    # B: replied only -> In progress; most recent activity.
    seed_event(store, CALLER_B, "call.missed", t0 + timedelta(hours=1), evidence="CA2")
    seed_inbound(store, "sms:m2", "sms", CALLER_B, {"body": "stump grinding"}, t0 + timedelta(hours=4))
    seed_event(store, CALLER_B, "sms.customer_replied", t0 + timedelta(hours=4))
    # C: opted out, oldest.
    seed_event(store, CALLER_C, "call.missed", t0 - timedelta(days=9), evidence="CA0")
    store.set_opted_out(CALLER_C, True)
    # Owner's sign-in code must not appear as a conversation; non-E.164 leads are skipped.
    seed_sms(store, "login:1", OWNER, "[sign-in code]", "login_code", NOW)
    seed_event(store, "calendar-owner", "handoff.alert_delivered", NOW)

    rows = portal_data.recent_conversations(store, limit=10, now=NOW)
    assert [r["phone"] for r in rows] == [CALLER_B, CALLER_A, CALLER_C]
    assert rows[0]["status"] == ("info", "In progress") and rows[0]["display"] == "(704) 555-0168"
    assert rows[1]["status"] == ("ok", "Booked") and rows[1]["display"] == "Dana"
    assert rows[1]["snippet"].endswith("…") and len(rows[1]["snippet"]) <= 60
    assert rows[2]["status"] == ("neutral", "Opted out") and rows[2]["last_label"] == "Oct 10"
    assert rows[0]["last_label"] == "Today 2:00 PM"
    assert portal_data.recent_conversations(store, limit=2, now=NOW)[-1]["phone"] == CALLER_A

    sign_in(client, telecom)
    home = client.get("/client").text
    assert home.index("(704) 555-0168") < home.index("Dana") < home.index("(980) 555-0177")
    assert "In progress" in home and "Booked" in home and "Opted out" in home
    assert "[sign-in code]" not in home


def test_status_derivation_order(tmp_path):
    store = Store(str(tmp_path / "s.db"))
    phone = CALLER_A
    assert portal_data.conversation_status(store, phone) == ("neutral", "New")
    seed_event(store, phone, "sms.customer_replied", NOW)
    assert portal_data.conversation_status(store, phone) == ("info", "In progress")
    seed_event(store, phone, "lead.qualified", NOW)
    assert portal_data.conversation_status(store, phone) == ("info", "Qualified")
    seed_event(store, phone, "lead.expired", NOW)
    assert portal_data.conversation_status(store, phone) == ("neutral", "Expired")
    store.save_appointment(conversation_id=phone, event_id="e", caller=phone, start="2026-10-22T16:00:00-04:00", location="x", service="y")
    assert portal_data.conversation_status(store, phone) == ("ok", "Booked")
    store.request_handoff(phone, "safety")
    assert portal_data.conversation_status(store, phone) == ("warn", "Handed off")
    store.set_opted_out(phone, True)
    assert portal_data.conversation_status(store, phone) == ("neutral", "Opted out")


def test_home_is_calm_when_empty(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    home = client.get("/client").text
    assert "No conversations yet. They appear here after the first missed call." in home
    assert "No calendar yet" in home and "Forwarding 0 of 5" in home and "Five checks left." in home and "Finish setup" in home
    assert "Messaging registration" not in home  # directory points nowhere -> card omitted


# --- registration card -------------------------------------------------------------

def test_registration_status_reads_staged_responses_read_only(tmp_path, monkeypatch):
    assert portal_data.registration_status(tmp_path / "missing") is None
    directory = tmp_path / "registration"
    directory.mkdir()
    assert portal_data.registration_status(directory)["headline"] == "Registration not started"
    (directory / "brand-request.json").write_text("{}")
    (directory / "brand-response.json").write_text(json.dumps({"id": "b1", "state": "VERIFIED"}))
    status = portal_data.registration_status(directory)
    assert status["headline"] == "Brand submitted" and status["state"] == "verified" and not status["complete"]
    (directory / "campaign-response.json").write_text(json.dumps({"id": "c1", "state": "IN_REVIEW"}))
    assert portal_data.registration_status(directory)["headline"] == "Campaign in review"
    (directory / "order-response.json").write_text(json.dumps({"id": "o1", "state": "pending"}))
    assert portal_data.registration_status(directory)["headline"] == "Number assigned"
    (directory / "order-response.json").write_text(json.dumps({"id": "o1", "state": "complete"}))
    done = portal_data.registration_status(directory)
    assert done["headline"] == "Registered" and done["complete"]
    (directory / "order-response.json").write_text("not json")
    assert portal_data.registration_status(directory)["headline"] == "Number assigned"

    monkeypatch.setenv("TEXT_BACK_REGISTRATION_DIR", str(directory))
    client, telecom, clock, _ = _make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    home = client.get("/client").text
    assert "Messaging registration" in home and "Number assigned" in home and "Free Trial" in home
    assert "Status: In review." in home and "in_review" not in home
    assert "Registration" not in home.split("Messaging registration")[0]  # no action button on this card
    assert not list(directory.glob("*response.json.bak")) and sorted(p.name for p in directory.iterdir()) == [
        "brand-request.json", "brand-response.json", "campaign-response.json", "order-response.json"]


# --- forwarding checklist ----------------------------------------------------------

def test_forwarding_checklist_ticks_steps_1_2_4_from_evidence_only(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    state = client.app.state
    store = state.store
    checklist = portal_data.forwarding_checklist(state)
    assert checklist["done_count"] == 0 and not checklist["verified"] and len(checklist["steps"]) == 5
    assert checklist["steps"][3]["evidence"] == "Enter your business number first."

    sid = "CAtest1"
    when = NOW - timedelta(hours=2)
    seed_inbound(store, f"voice:{sid}", "voice", CALLER_C, {"call_sid": sid, "call_status": "no-answer", "from_number": CALLER_C, "to_number": "+19805550100"}, when)
    seed_event(store, CALLER_C, "call.missed", when, evidence=sid, key=f"call:{sid}:missed")
    checklist = portal_data.forwarding_checklist(state)
    assert checklist["steps"][0]["done"] and checklist["steps"][0]["evidence"] == "Oct 19, 1:00 PM from (•••) •••-0177"
    assert CALLER_C not in json.dumps(checklist)  # never a full customer number
    assert not checklist["steps"][1]["done"]

    seed_sms(store, f"{sid}:intro", CALLER_C, "Hey", "missed_call_intro", when)
    seed_event(store, CALLER_C, "sms.initial_sent", when + timedelta(seconds=3), evidence="SM1", key=f"call:{sid}:initial_sms")
    checklist = portal_data.forwarding_checklist(state)
    assert checklist["steps"][1]["done"] and checklist["steps"][1]["evidence"] == "Sent Oct 19, 1:00 PM"
    assert not checklist["steps"][3]["done"]  # business number still unknown

    store.set_setting("business_line", "+17045695600")
    checklist = portal_data.forwarding_checklist(state)
    assert checklist["steps"][3]["done"] and "not your business number" in checklist["steps"][3]["evidence"]
    assert checklist["done_count"] == 3

    # A call from the business number itself is not a probe.
    store.set_setting("business_line", CALLER_C)
    assert portal_data.forwarding_checklist(state)["done_count"] == 0

    store.set_setting("business_line", "+17045695600")
    store.set_setting("forwarding_checklist", json.dumps({"answered_no_text": NOW.isoformat(), "deactivation_saved": NOW.isoformat()}))
    checklist = portal_data.forwarding_checklist(state)
    assert checklist["verified"] and checklist["done_count"] == 5 and checklist["steps"][2]["evidence"] == "Ticked Oct 19, 3:00 PM"
    sign_in(client, telecom)
    home = client.get("/client").text
    assert "Forwarding verified" in home and "All five checks done." in home and "Finish setup" not in home
