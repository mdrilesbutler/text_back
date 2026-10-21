"""Phone page: the typed numbers, the texting-number check, Verify, the owner-mobile change,
the carrier codes and the five-step forwarding checklist."""
from html import unescape
import json
import re
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from text_back import portal_data
from text_back.app import create_app
from text_back.telecom import FakeTelecom, OutboundSms

from test_client_portal import BASE, OWNER, code_from, csrf_of, sign_in
from test_portal_shell import CALLER_C, make, seed_event, seed_inbound, seed_sms

NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)
TEXTING = "+19805550177"
HANDLERS = {"voice_url": BASE + "/webhooks/voice", "sms_url": BASE + "/webhooks/sms"}
FORM = {"business_name": "Oak & Pine Tree Care", "business_line": "", "text_back_number": "", "owner_mobile": OWNER,
        "business_contact": "", "carrier": ""}


def open_phone(client):
    page = client.get("/client/phone")
    assert page.status_code == 200
    return unescape(page.text), csrf_of(unescape(page.text))


def test_page_shows_the_three_numbers_typed_and_never_offers_to_get_one(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    html, csrf = open_phone(client)
    assert "<h1>Phone</h1>" in html and html.count("<h1") == 1
    assert 'value="Oak & Pine Tree Care"' in html
    for label in ("Your business number", "Texting number", "Your mobile", "Number shown in HELP replies", "Business name", "Your carrier"):
        assert label in html, label
    for field in ("business_line", "text_back_number", "owner_mobile"):
        assert f'name="verify" value="{field}"' in html and 'formaction="/client/phone/verify"' in html
    assert 'aria-label="Verify Texting number"' in html
    assert "<select" not in html  # numbers are typed, never picked from a list
    assert not re.search(r"\b(buy|purchase|port|porting|provision|get a number|search for a number)\b", html, re.I)
    assert "business line" not in html.lower() and not re.search(r"\bAI\b", html)
    assert "Pick your carrier to see the codes." in html
    assert client.get("/client/business", follow_redirects=False).status_code == 301
    assert client.get("/client/business", follow_redirects=False).headers["location"] == "/client/phone"
    assert client.get("/client/business/keep", follow_redirects=False).headers["location"] == "/client/phone"
    assert client.post("/client/phone", data={"csrf": "forged", **FORM}).status_code == 400


def test_save_persists_name_line_contact_and_carrier_and_survives_restart(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    html, csrf = open_phone(client)
    saved = client.post("/client/phone", data={"csrf": csrf, **FORM, "business_name": "  Oak &  Pine  ", "business_line": "704 555 0100",
                                               "business_contact": "980-555-0100", "carrier": "verizon"})
    assert "Saved." in unescape(saved.text) and 'value="Oak & Pine"' in unescape(saved.text)
    state = client.app.state
    assert state.business_name == "Oak & Pine" and state.business_contact == "(980) 555-0100"
    assert state.store.setting("business_line") == "+17045550100" and state.store.setting("carrier") == "verizon"
    assert 'value="verizon" form="phone-form" checked' in unescape(saved.text) and "*73" in unescape(saved.text)
    again = create_app(db_path=str(tmp_path / "portal.db"), telecom=FakeTelecom(), public_base_url=BASE,
                       business_name="Oak & Pine Tree Care", now_provider=lambda: clock[0])
    assert again.state.business_name == "Oak & Pine" and again.state.business_contact == "(980) 555-0100"
    # Bad input is refused with the exact reason and nothing changes.
    bad = client.post("/client/phone", data={"csrf": csrf, **FORM, "business_name": ""})
    assert "Enter a business name of 1 to 60 characters." in unescape(bad.text) and "Not saved" in unescape(bad.text) and state.business_name == "Oak & Pine"
    assert 'aria-invalid="true"' in unescape(bad.text) and 'id="business_name-error"' in unescape(bad.text)
    bad = client.post("/client/phone", data={"csrf": csrf, **FORM, "business_contact": "call me"})
    assert "customer phone number" in unescape(bad.text) and state.business_contact == "(980) 555-0100"
    bad = client.post("/client/phone", data={"csrf": csrf, **FORM, "business_line": "nope"})
    assert "Enter your business number as digits" in unescape(bad.text)
    bad = client.post("/client/phone", data={"csrf": csrf, **FORM, "carrier": "sprint"})
    assert "Pick a carrier from the list." in unescape(bad.text)
    bad = client.post("/client/phone", data={"csrf": csrf, **FORM, "owner_mobile": ""})
    assert "Enter your mobile as digits" in unescape(bad.text)


def test_texting_number_is_saved_only_when_owned_and_pointed_at_text_back(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    state = client.app.state
    telecom.allowed_from_number = "+10000000000"
    html, csrf = open_phone(client)
    # Not owned: nothing changes.
    refused = client.post("/client/phone", data={"csrf": csrf, **FORM, "text_back_number": "980 555 0177"})
    assert "(980) 555-0177 is not a number this account owns." in unescape(refused.text) and "Not saved" in unescape(refused.text)
    assert state.store.setting("text_back_number") is None and telecom.lookups == [TEXTING]
    assert telecom.allowed_from_number == "+10000000000"
    # The Forwarding card never builds dial codes from a refused number: no copyable code carries it.
    refused_codes = unescape(refused.text).split('id="forwarding"')[1]
    assert "9805550177" not in refused_codes and "data-copy" not in refused_codes
    assert "Enter your texting number above to fill in the codes." in refused_codes
    # Owned but the handlers point elsewhere.
    telecom.owned_numbers[TEXTING] = {"voice_url": "https://elsewhere.example/voice", "sms_url": HANDLERS["sms_url"]}
    refused = client.post("/client/phone", data={"csrf": csrf, **FORM, "text_back_number": "980 555 0177"})
    assert "its voice/SMS handlers do not point at text_back" in unescape(refused.text) and state.store.setting("text_back_number") is None
    assert "9805550177" not in unescape(refused.text).split('id="forwarding"')[1]
    # Owned and pointed at text_back: saved and applied to the running app and the sender guard.
    telecom.owned_numbers[TEXTING] = dict(HANDLERS)
    saved = client.post("/client/phone", data={"csrf": csrf, **FORM, "text_back_number": "980 555 0177"})
    assert "Saved." in unescape(saved.text) and state.store.setting("text_back_number") == TEXTING
    assert state.business_number == TEXTING and telecom.allowed_from_number == TEXTING
    assert 'value="(980) 555-0177"' in unescape(saved.text)
    # Saving the same number again does not call the provider again.
    calls = len(telecom.lookups)
    client.post("/client/phone", data={"csrf": csrf, **FORM, "text_back_number": "(980) 555-0177"})
    assert len(telecom.lookups) == calls
    # A form without the texting-number field leaves it alone (a blank field would clear it).
    without = {k: v for k, v in FORM.items() if k != "text_back_number"}
    assert "Saved." in unescape(client.post("/client/phone", data={"csrf": csrf, **without}).text)
    assert state.store.setting("text_back_number") == TEXTING and state.business_number == TEXTING
    # The business number may not be the texting number.
    same = client.post("/client/phone", data={"csrf": csrf, **FORM, "text_back_number": "980 555 0177", "business_line": "980 555 0177"})
    assert "Your business number and texting number can't be the same." in unescape(same.text)
    # A fresh process applies the saved sender at boot.
    fresh = FakeTelecom()
    fresh.allowed_from_number = "+10000000000"
    again = create_app(db_path=str(tmp_path / "portal.db"), telecom=fresh, public_base_url=BASE,
                       business_name="Oak & Pine Tree Care", now_provider=lambda: clock[0])
    assert again.state.business_number == TEXTING and fresh.allowed_from_number == TEXTING
    # Blank puts the env default back.
    cleared = client.post("/client/phone", data={"csrf": csrf, **FORM, "text_back_number": ""})
    assert "Saved." in unescape(cleared.text) and state.store.setting("text_back_number") is None
    assert state.business_number == state.defaults["text_back_number"]


def test_telecom_without_lookup_means_checking_is_not_set_up(tmp_path, monkeypatch):
    class BareTelecom:
        provider_name = "stub"

        def __init__(self):
            self.outbound = []

        def send_sms(self, *, to, body, from_number, kind):
            self.outbound.append(OutboundSms(to=to, body=body, from_number=from_number, kind=kind))
            return f"SM-{len(self.outbound)}"

    monkeypatch.setenv("TEXT_BACK_OWNER_MOBILE", OWNER)
    monkeypatch.setenv("TEXT_BACK_REGISTRATION_DIR", str(tmp_path / "none"))
    telecom = BareTelecom()
    app = create_app(db_path=str(tmp_path / "bare.db"), telecom=telecom, public_base_url=BASE,
                     business_name="Oak & Pine Tree Care", now_provider=lambda: NOW)
    client = TestClient(app, base_url=BASE)
    sign_in(client, telecom)
    html, csrf = open_phone(client)
    refused = client.post("/client/phone", data={"csrf": csrf, **FORM, "text_back_number": "980 555 0177"})
    assert "not set up" in unescape(refused.text) and app.state.store.setting("text_back_number") is None


def test_verify_checks_one_field_and_saves_nothing(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    state = client.app.state
    html, csrf = open_phone(client)
    telecom.owned_numbers[TEXTING] = dict(HANDLERS)
    typed = {"csrf": csrf, **FORM, "business_name": "Changed", "business_line": "704 555 0100", "text_back_number": "980 555 0177",
             "owner_mobile": "980 555 0199", "business_contact": "980 555 0100", "carrier": "tmobile"}
    out = client.post("/client/phone/verify", data={**typed, "verify": "text_back_number"})
    assert out.status_code == 200 and "Owned by this account and pointed at text_back." in unescape(out.text)
    assert 'id="text_back_number-status" role="status"' in unescape(out.text)
    assert 'value="Changed"' in unescape(out.text) and 'value="(704) 555-0100"' in unescape(out.text)  # typed values travel
    out = client.post("/client/phone/verify", data={**typed, "verify": "business_line"})
    assert "Looks good: (704) 555-0100." in unescape(out.text)
    out = client.post("/client/phone/verify", data={**typed, "verify": "owner_mobile"})
    assert "Save to text a code to (980) 555-0199." in unescape(out.text)
    out = client.post("/client/phone/verify", data={**typed, "verify": "owner_mobile", "owner_mobile": OWNER})
    assert "This is the number that signs you in." in unescape(out.text)
    out = client.post("/client/phone/verify", data={**typed, "verify": "business_line", "business_line": "x"})
    assert "Enter your business number as digits" in unescape(out.text) and 'role="alert"' in unescape(out.text)
    del telecom.owned_numbers[TEXTING]
    out = client.post("/client/phone/verify", data={**typed, "verify": "text_back_number"})
    assert "is not a number this account owns." in unescape(out.text) and 'role="alert"' in unescape(out.text)
    # Nothing was written or texted by any of that.
    assert state.business_name == "Oak & Pine Tree Care" and state.store.setting("business_line") is None
    assert state.store.setting("text_back_number") is None and state.store.setting("carrier") is None
    assert state.store.setting("owner_mobile_pending") is None
    assert not [m for m in telecom.outbound if "new mobile" in m.body]


def test_changing_the_owner_mobile_requires_a_code_texted_to_the_new_number(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    html, csrf = open_phone(client)
    page = client.post("/client/phone", data={"csrf": csrf, **FORM, "owner_mobile": "980 555 0199"})
    assert "Confirm your new mobile" in unescape(page.text) and "(980) 555-0199" in unescape(page.text)
    assert "Saved. Now confirm your new mobile." in unescape(page.text)
    assert "Pick your carrier to see the codes." not in unescape(page.text)  # the pills are hidden while a change is pending
    code, text = code_from(telecom)
    assert text.to == "+19805550199" and "new mobile code" in text.body
    assert client.app.state.owner_mobile == OWNER  # nothing changed yet
    reload = unescape(client.get("/client/phone").text)
    assert "/client/phone/confirm" in reload and 'name="cancel" value="1"' in reload and 'id="phone-form"' not in reload
    wrong = client.post("/client/phone/confirm", data={"csrf": csrf, "code": "000000"})
    assert "not right or has expired" in unescape(wrong.text) and client.app.state.owner_mobile == OWNER
    done = client.post("/client/phone/confirm", data={"csrf": csrf, "code": code})
    assert "Sign-in codes now go to (980) 555-0199" in unescape(done.text)
    assert client.app.state.owner_mobile == "+19805550199"
    client.cookies.clear()
    before = len([m for m in telecom.outbound if m.kind == "login_code"])
    client.post("/client/login", data={"mobile": OWNER}, follow_redirects=False)
    assert len([m for m in telecom.outbound if m.kind == "login_code"]) == before
    sign_in(client, telecom, mobile="980 555 0199")


def test_keeping_the_current_mobile_cancels_the_pending_change_by_post(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    html, csrf = open_phone(client)
    client.post("/client/phone", data={"csrf": csrf, **FORM, "owner_mobile": "980 555 0199"})
    kept = client.post("/client/phone/confirm", data={"csrf": csrf, "cancel": "1"})
    assert "Kept your current mobile" in unescape(kept.text)
    assert "Confirm your new mobile" not in unescape(client.get("/client/phone").text)
    assert client.app.state.owner_mobile == OWNER


def test_forwarding_codes_follow_the_carrier_and_the_texting_number(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    html, csrf = open_phone(client)
    assert "Enter your texting number above to fill in the codes." in html and "data-copy" not in html
    telecom.owned_numbers[TEXTING] = dict(HANDLERS)
    saved = unescape(client.post("/client/phone", data={"csrf": csrf, **FORM, "text_back_number": "980 555 0177", "carrier": "verizon"}).text)
    verizon = saved.split('data-codes="verizon"')[1].split('data-codes="tmobile"')[0]
    assert "<code>*719805550177</code>" in verizon and "<code>*73</code>" in verizon
    assert 'data-copy="*719805550177" aria-label="Copy activation code for Verizon"' in verizon
    assert 'data-copy="*73" aria-label="Copy deactivation code for Verizon"' in verizon
    assert "Save carrier" not in saved  # one Save per page; a pill switches the codes at once
    assert "Only forward busy and unanswered calls." in saved
    assert 'data-codes="tmobile" hidden' in saved and 'data-codes="verizon">' in saved
    assert "Turn-off code: <code>*73</code>" in saved  # step 5 shows the carrier's turn-off code
    tmobile = unescape(client.post("/client/phone", data={"csrf": csrf, **FORM, "text_back_number": "980 555 0177", "carrier": "tmobile"}).text)
    block = tmobile.split('data-codes="tmobile"')[1].split('data-codes="att"')[0]
    for code in ("**61*19805550177#", "**67*19805550177#", "**62*19805550177#", "**61*19805550177**20#", "##61#", "##67#", "##62#", "##004#"):
        assert f"<code>{code}</code>" in block, code
    att = unescape(client.post("/client/phone", data={"csrf": csrf, **FORM, "text_back_number": "980 555 0177", "carrier": "att"}).text)
    block = att.split('data-codes="att"')[1].split('data-codes="cricket"')[0]
    assert "unverified on AT&T" in block and "(980) 555-0177" in block and "skip the Settings toggle" in block
    other = unescape(client.post("/client/phone", data={"csrf": csrf, **FORM, "text_back_number": "980 555 0177", "carrier": "other"}).text)
    assert "Ask your carrier to turn on conditional call forwarding" in other and "Never forward all calls." in other


def test_checklist_ticks_from_evidence_and_manual_steps_persist_to_home(tmp_path, monkeypatch):
    client, telecom, clock, _ = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    state, store = client.app.state, client.app.state.store
    html, csrf = open_phone(client)
    assert "0 of 5 done." in html and html.count("Not yet") == 5 and 'name="check_answered_no_text"' in html
    assert 'id="check-3"' in html and 'id="check-5"' in html and "Steps 1, 2 and 4 are ticked from real calls" in html

    sid = "CAtest9"
    when = NOW - timedelta(hours=2)
    seed_inbound(store, f"voice:{sid}", "voice", CALLER_C, {"call_sid": sid, "call_status": "no-answer", "from_number": CALLER_C, "to_number": TEXTING}, when)
    seed_event(store, CALLER_C, "call.missed", when, evidence=sid, key=f"call:{sid}:missed")
    seed_sms(store, f"{sid}:intro", CALLER_C, "Hey", "missed_call_intro", when)
    seed_event(store, CALLER_C, "sms.initial_sent", when + timedelta(seconds=3), evidence="SM1", key=f"call:{sid}:initial_sms")
    html = unescape(client.get("/client/phone").text)
    assert "2 of 5 done." in html and "from (•••) •••-0177" in html and CALLER_C not in html
    assert "Enter your business number first." in html  # step 4 needs the business number

    client.post("/client/phone", data={"csrf": csrf, **FORM, "business_line": "704 569 5600"})
    html = unescape(client.get("/client/phone").text)
    assert "3 of 5 done." in html and "not your business number" in html

    ticked = client.post("/client/phone/checklist", data={"csrf": csrf, "check_answered_no_text": "1", "check_deactivation_saved": "1"})
    assert "Checks saved." in unescape(ticked.text) and "5 of 5 done" in unescape(ticked.text) and "forwarding verified" in unescape(ticked.text)
    manual = json.loads(store.setting("forwarding_checklist"))
    assert manual["answered_no_text"] == NOW.isoformat() and manual["deactivation_saved"] == NOW.isoformat()
    assert 'name="check_answered_no_text" value="1" checked' in unescape(ticked.text)
    home = unescape(client.get("/client").text)
    assert "Forwarding verified" in home and "All five checks done." in home and 'href="/client/phone#forwarding"' in home
    # Unticking one drops it; re-ticking keeps the first timestamp.
    clock[0] = NOW + timedelta(hours=1)
    client.post("/client/phone/checklist", data={"csrf": csrf, "check_answered_no_text": "1"})
    manual = json.loads(store.setting("forwarding_checklist"))
    assert manual["deactivation_saved"] is None and manual["answered_no_text"] == NOW.isoformat()
    assert "4 of 5 done." in unescape(client.get("/client/phone").text)
    assert portal_data.forwarding_checklist(state)["done_count"] == 4
