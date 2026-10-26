"""Phone page logic (candidate C): the business name, the typed numbers, the read-only texting
number, the two-step owner-mobile change, the rename offer, the carrier codes and the checklist
wrapper. No HTTP here; routes and templates are tested elsewhere."""
import json
import re
from datetime import datetime, timedelta, timezone

import pytest

from text_back import portal_phone
from text_back.app import create_app
from text_back.store import Store
from text_back.telecom import FakeTelecom

NOW = datetime(2026, 10, 26, 15, 0, tzinfo=timezone.utc)
BASE = "https://portal.example"
OWNER = "+19805550123"
TEXTING = "+19805550177"
NEW_MOBILE = "+19805550199"
FORM = {"business_name": "Oak & Pine Tree Care", "business_line": "", "owner_mobile": "980 555 0123",
        "business_contact": "", "carrier": ""}


def make_state(tmp_path, monkeypatch, *, texting=TEXTING):
    monkeypatch.setenv("TEXT_BACK_OWNER_MOBILE", OWNER)
    monkeypatch.setenv("TEXT_BACK_SIGNALWIRE_FROM_NUMBER", texting)
    monkeypatch.delenv("TEXT_BACK_MESSAGES_FILE", raising=False)
    clock = [NOW]
    telecom = FakeTelecom()
    app = create_app(db_path=str(tmp_path / "portal.db"), telecom=telecom, public_base_url=BASE,
                     business_name="Oak & Pine Tree Care", now_provider=lambda: clock[0])
    return app.state, telecom, clock


def code_texted_to(telecom, number):
    texts = [m for m in telecom.outbound if m.kind == "login_code" and m.to == number]
    assert texts, f"no code was texted to {number}"
    return re.search(r"\b(\d{6})\b", texts[-1].body).group(1)


# --- the texting number is read-only ---------------------------------------------------

def test_texting_number_is_read_only_and_a_posted_value_is_ignored(tmp_path, monkeypatch):
    state, telecom, clock = make_state(tmp_path, monkeypatch)
    assert "text_back_number" not in portal_phone.FIELD_ORDER
    assert "text_back_number" not in portal_phone.VERIFIABLE
    for gone in ("apply_texting_number", "check_texting_number", "texting_number_changed", "texting_number_problem"):
        assert not hasattr(portal_phone, gone), gone
    # Displayed from the running sender, with the locked sentence.
    assert portal_phone.current_values(state)["text_back_number"] == TEXTING
    assert portal_phone.TEXTING_READ_ONLY == "Set up by FluxWorks. It can't be changed here."
    # A form that posts a texting number: the value never reaches validate or save.
    submitted = portal_phone.read_form({**FORM, "text_back_number": "704 555 0100"})
    assert "text_back_number" not in submitted
    values, errors = portal_phone.validate(submitted, state)
    assert errors == {} and "text_back_number" not in values
    portal_phone.save(state, values, NOW)
    assert state.business_number == TEXTING
    assert state.store.setting("text_back_number") is None
    assert portal_phone.verify(state, "text_back_number", values) is None


def test_page_context_shows_the_texting_number_as_text_and_names_the_missing_case(tmp_path, monkeypatch):
    state, telecom, clock = make_state(tmp_path, monkeypatch)
    context = portal_phone.page_context(state, now=NOW)
    assert context["texting_number"] == "(980) 555-0177"
    assert context["texting_note"] == "Set up by FluxWorks. It can't be changed here."
    assert context["carrier"] == "" and context["codes"]["note"] == "Pick your carrier to see the codes."
    assert context["forward_all_warning"] == portal_phone.FORWARD_ALL_WARNING
    assert context["checklist"]["done_count"] == 0
    assert context["values"]["text_back_number"] == TEXTING
    assert context["rename"] is None
    (tmp_path / "none").mkdir()
    unassigned, _, _ = make_state(tmp_path / "none", monkeypatch, texting="")
    context = portal_phone.page_context(unassigned, now=NOW)
    assert context["texting_number"] == "" and context["texting_note"] == "Not assigned yet. FluxWorks sets this up for you."
    assert context["texting_note"] == portal_phone.TEXTING_NOT_ASSIGNED
    context = portal_phone.page_context(unassigned, {**FORM, "carrier": "verizon"}, now=NOW)
    assert context["codes"]["enable"] == [] and context["codes"]["note"] == portal_phone.CODES_NEED_NUMBER


# --- validation ------------------------------------------------------------------------

def test_validation_refuses_bad_input_with_the_exact_reason(tmp_path, monkeypatch):
    state, telecom, clock = make_state(tmp_path, monkeypatch)

    def errors_for(**changes):
        _, errors = portal_phone.validate(portal_phone.read_form({**FORM, **changes}), state)
        return errors

    assert errors_for(business_name="") == {"business_name": "Enter a business name of 1 to 60 characters."}
    assert errors_for(business_name="x" * 61) == {"business_name": portal_phone.ERR_NAME}
    assert errors_for(business_line="nope") == {
        "business_line": "Enter your business number as 10 digits, area code first, or leave it blank."}
    assert errors_for(business_line="(980) 555-0177") == {
        "business_line": "Your business number and the texting number can't be the same."}
    assert errors_for(owner_mobile="") == {"owner_mobile": "Enter your mobile as 10 digits, area code first."}
    assert errors_for(owner_mobile="call me") == {"owner_mobile": portal_phone.ERR_MOBILE}
    assert errors_for(business_contact="call me") == {
        "business_contact": "Enter the phone number as 10 digits, area code first, or leave it blank."}
    assert errors_for(carrier="sprint") == {"carrier": "Pick a carrier from the list."}
    # The first error follows the field order on the page.
    both = errors_for(business_name="", carrier="sprint")
    assert portal_phone.first_error(both) == portal_phone.ERR_NAME
    # Good input is normalised: collapsed name, E.164 numbers, formatted HELP number.
    values, errors = portal_phone.validate(portal_phone.read_form({
        **FORM, "business_name": "  Oak &  Pine  ", "business_line": "704 555 0100",
        "business_contact": "980-555-0100", "carrier": "verizon"}), state)
    assert errors == {}
    assert values == {"business_name": "Oak & Pine", "business_line": "+17045550100", "owner_mobile": OWNER,
                      "business_contact": "(980) 555-0100", "carrier": "verizon"}


# --- save and restart ------------------------------------------------------------------

def test_save_persists_and_survives_restart(tmp_path, monkeypatch):
    state, telecom, clock = make_state(tmp_path, monkeypatch)
    values, errors = portal_phone.validate(portal_phone.read_form({
        **FORM, "business_name": "Oak & Pine", "business_line": "704 555 0100",
        "business_contact": "980-555-0100", "carrier": "verizon"}), state)
    assert errors == {}
    assert portal_phone.save(state, values, NOW) is None  # the mobile did not change: no code
    assert state.business_name == "Oak & Pine" and state.business_contact == "(980) 555-0100"
    assert state.owner_mobile == OWNER
    assert not [m for m in telecom.outbound if m.kind == "login_code"]
    # Another process reading the same database sees every value.
    again = Store(str(tmp_path / "portal.db"))
    assert again.setting("business_name") == "Oak & Pine"
    assert again.setting("business_line") == "+17045550100"
    assert again.setting("business_contact") == "(980) 555-0100"
    assert again.setting("carrier") == "verizon"
    assert again.setting("owner_mobile_pending") is None
    # A fresh app on the same database boots with the saved details.
    fresh = create_app(db_path=str(tmp_path / "portal.db"), telecom=FakeTelecom(), public_base_url=BASE,
                       business_name="Oak & Pine Tree Care", now_provider=lambda: clock[0])
    assert fresh.state.business_name == "Oak & Pine" and fresh.state.business_contact == "(980) 555-0100"
    assert portal_phone.current_values(fresh.state)["business_line"] == "+17045550100"
    assert portal_phone.current_values(fresh.state)["carrier"] == "verizon"
    # Blanks clear the optional values.
    values, _ = portal_phone.validate(portal_phone.read_form({**FORM, "business_name": "Oak & Pine"}), state)
    portal_phone.save(state, values, NOW)
    assert again.setting("business_line") is None and again.setting("carrier") is None
    assert again.setting("business_contact") == ""


# --- owner mobile, two steps -----------------------------------------------------------

def test_owner_mobile_change_sends_code_to_new_number_and_keep_escape_works(tmp_path, monkeypatch):
    state, telecom, clock = make_state(tmp_path, monkeypatch)
    values, errors = portal_phone.validate(portal_phone.read_form({**FORM, "owner_mobile": "980 555 0199"}), state)
    assert errors == {}
    assert portal_phone.verify(state, "owner_mobile", values) == ("info", "Save to text a code to (980) 555-0199.")
    assert portal_phone.save(state, values, NOW) == NEW_MOBILE
    assert portal_phone.pending_mobile(state) == NEW_MOBILE
    code = code_texted_to(telecom, NEW_MOBILE)
    assert not [m for m in telecom.outbound if m.kind == "login_code" and m.to == OWNER]
    # Nothing changed yet: the old mobile still signs in.
    assert state.owner_mobile == OWNER and state.store.setting("owner_mobile") is None
    # A wrong code changes nothing.
    assert portal_phone.confirm_new_mobile(state, "000000", NOW) is None
    assert state.owner_mobile == OWNER and portal_phone.pending_mobile(state) == NEW_MOBILE
    # The right code moves sign-in to the new number and clears the pending change.
    assert portal_phone.confirm_new_mobile(state, code, NOW) == NEW_MOBILE
    assert state.owner_mobile == NEW_MOBILE and state.store.setting("owner_mobile") == NEW_MOBILE
    assert portal_phone.pending_mobile(state) is None
    assert portal_phone.NEW_MOBILE_SAVED.format(n="(980) 555-0199") == (
        "Saved. Sign-in codes now go to (980) 555-0199. Other devices stay signed in.")  # m7
    assert portal_phone.SAVED_CONFIRM_MOBILE == "Saved. Now confirm your new mobile."
    # Keep my current mobile: a second change is cancelled without a code.
    values, _ = portal_phone.validate(portal_phone.read_form({**FORM, "owner_mobile": "980 555 0123"}), state)
    assert portal_phone.save(state, values, NOW) == OWNER
    assert portal_phone.pending_mobile(state) == OWNER
    portal_phone.keep_current_mobile(state, NOW)
    assert portal_phone.pending_mobile(state) is None and state.owner_mobile == NEW_MOBILE
    assert portal_phone.confirm_new_mobile(state, code_texted_to(telecom, OWNER), NOW) is None  # nothing pending
    assert state.owner_mobile == NEW_MOBILE
    assert portal_phone.KEPT == "Kept your current mobile."


def test_keeping_the_current_mobile_cancels_the_pending_change(tmp_path, monkeypatch):
    state, telecom, clock = make_state(tmp_path, monkeypatch)
    values, _ = portal_phone.validate(portal_phone.read_form({**FORM, "owner_mobile": "980 555 0199"}), state)
    portal_phone.save(state, values, NOW)
    assert portal_phone.pending_mobile(state) == NEW_MOBILE
    portal_phone.keep_current_mobile(state, NOW)
    assert portal_phone.pending_mobile(state) is None
    assert state.owner_mobile == OWNER and state.store.setting("owner_mobile") is None
    assert portal_phone.current_values(state)["owner_mobile"] == OWNER
    # The code that was texted is useless now.
    code = code_texted_to(telecom, NEW_MOBILE)
    assert portal_phone.confirm_new_mobile(state, code, NOW) is None and state.owner_mobile == OWNER


def test_resend_texts_a_fresh_code_to_the_pending_number_only(tmp_path, monkeypatch):
    state, telecom, clock = make_state(tmp_path, monkeypatch)
    assert portal_phone.resend_mobile_code(state, NOW) is None  # nothing pending
    values, _ = portal_phone.validate(portal_phone.read_form({**FORM, "owner_mobile": "980 555 0199"}), state)
    portal_phone.save(state, values, NOW)
    before = len([m for m in telecom.outbound if m.kind == "login_code"])
    clock[0] = NOW + timedelta(minutes=1)
    assert portal_phone.resend_mobile_code(state, clock[0]) == NEW_MOBILE
    texts = [m for m in telecom.outbound if m.kind == "login_code"]
    assert len(texts) == before + 1 and texts[-1].to == NEW_MOBILE
    assert portal_phone.confirm_new_mobile(state, code_texted_to(telecom, NEW_MOBILE), clock[0]) == NEW_MOBILE


# --- verify ----------------------------------------------------------------------------

def test_verify_checks_format_only_and_saves_nothing(tmp_path, monkeypatch):
    state, telecom, clock = make_state(tmp_path, monkeypatch)
    values, _ = portal_phone.validate(portal_phone.read_form({
        **FORM, "business_name": "Changed", "business_line": "704 555 0100", "owner_mobile": "980 555 0199"}), state)
    kind, text = portal_phone.verify(state, "business_line", values)
    assert kind == "ok" and "(704) 555-0100" in text
    assert "format" in text.lower()  # we only check the digits, never whether it rings
    assert portal_phone.verify(state, "business_line", {**values, "business_line": ""}) == ("warn", "Enter a number to check.")
    assert portal_phone.verify(state, "owner_mobile", {**values, "owner_mobile": OWNER}) == ("ok", "This is the number that signs you in.")
    assert portal_phone.verify(state, "business_name", values) is None
    assert portal_phone.verify(state, "text_back_number", values) is None
    # Nothing was written or texted.
    assert state.business_name == "Oak & Pine Tree Care" and state.store.setting("business_line") is None
    assert state.store.setting("owner_mobile_pending") is None
    assert not [m for m in telecom.outbound if m.kind == "login_code"]


# --- rename offer ----------------------------------------------------------------------

def test_rename_offer_counts_texts_that_still_say_the_old_name():
    old, new = "Oak & Pine Tree Care", "Riley's Tree & Stump Co."
    templates = {
        "missed_call_intro": "Hey, sorry we missed your call—this is Oak & Pine Tree Care's scheduling assistant.",
        "booking_confirmation": "You're booked with Oak & Pine Tree Care for {slot}.",
        "followup_sms": "Still want a visit? Reply with a day and time.",
        "help_reply": "oak & pine tree care can help: reply with your question.",  # different case: not literal
    }
    assert portal_phone.texts_with_old_name(templates, old) == ["missed_call_intro", "booking_confirmation"]
    updated = portal_phone.rename_in_texts(templates, old, new)
    assert updated["missed_call_intro"] == "Hey, sorry we missed your call—this is Riley's Tree & Stump Co.'s scheduling assistant."
    assert updated["booking_confirmation"] == "You're booked with Riley's Tree & Stump Co. for {slot}."
    assert updated["followup_sms"] == templates["followup_sms"]
    assert updated["help_reply"] == templates["help_reply"]
    assert templates["missed_call_intro"].startswith("Hey, sorry we missed your call—this is Oak")  # input untouched
    # A name with an apostrophe and an ampersand is matched literally, never as a pattern.
    assert portal_phone.texts_with_old_name(updated, new) == ["missed_call_intro", "booking_confirmation"]
    assert portal_phone.texts_with_old_name(updated, "Oak & Pine (Tree) Care") == []
    assert portal_phone.texts_with_old_name({}, old) == []
    assert portal_phone.texts_with_old_name(templates, "") == []
    # The offer carries the deck's words and the count.
    offer = portal_phone.rename_offer(templates, old, new)
    assert offer["count"] == 2 and offer["keys"] == ["missed_call_intro", "booking_confirmation"]
    assert offer["text"] == "2 texts still say “Oak & Pine Tree Care”. Update them to the new name?"
    assert offer["accept"] == "Update them" and offer["decline"] == "Leave them"
    assert offer["done"] == "Updated 2 texts."
    assert portal_phone.rename_offer(templates, old, old) is None  # the name did not change
    assert portal_phone.rename_offer({"followup_sms": "no name here"}, old, new) is None
    one = portal_phone.rename_offer({"k": f"Thanks from {old}."}, old, new)
    assert one["text"] == "1 text still says “Oak & Pine Tree Care”. Update it to the new name?" and one["done"] == "Updated 1 text."


# --- carrier codes ---------------------------------------------------------------------

def test_carrier_codes_substitute_the_texting_number_and_keep_verified_flags():
    verizon = portal_phone.forwarding_codes("verizon", TEXTING)
    assert verizon["enable"] == [("Busy and no answer", "*719805550177")]
    assert verizon["disable"] == [("Reset all forwarding", "*73")]
    assert verizon["verified"] is True and verizon["name"] == "Verizon"
    assert verizon["note"] == "Covers busy and no answer. Dial from your phone while on Verizon's network, then press Call."
    assert portal_phone.turn_off_code("verizon", TEXTING) == "*73"

    tmobile = portal_phone.forwarding_codes("tmobile", "(980) 555-0177")  # any format of the same number
    assert tmobile["enable"] == [("No answer", "**61*19805550177#"), ("Busy", "**67*19805550177#"),
                                 ("Unreachable", "**62*19805550177#"),
                                 ("No answer, ring 20 seconds first", "**61*19805550177**20#")]
    assert tmobile["disable"] == [("No answer", "##61#"), ("Busy", "##67#"), ("Unreachable", "##62#"),
                                  ("Reset all forwarding", "##004#")]
    assert tmobile["verified"] is True and tmobile["note"] == "Dial each code, then press Call."

    att = portal_phone.forwarding_codes("att", TEXTING)
    assert att["verified"] is False
    assert att["enable"] == [("No answer", "**61*19805550177#"), ("Busy", "**67*19805550177#")]
    assert att["disable"] == [("No answer", "##61#"), ("Busy", "##67#"), ("Reset all forwarding", "##004#")]
    assert att["steps"] == ('Android: open the Phone app, then Settings, then Call forwarding. '
                            'Set "When busy" and "When unanswered" to (980) 555-0177.')
    assert att["note"] == "On iPhone, skip the Settings toggle: it forwards every call. Dial the codes instead."
    assert att["unverified"] == "We haven't confirmed these codes on AT&T. Make a test call afterwards to check."

    cricket = portal_phone.forwarding_codes("cricket", TEXTING)
    assert cricket["verified"] is False and cricket["enable"] == att["enable"] and cricket["disable"] == att["disable"]
    assert cricket["note"] == "Cricket doesn't publish codes. Check with *#61# and *#67#. If forwarding won't turn off, call 611."
    assert cricket["unverified"] == "We haven't confirmed these codes on Cricket. Make a test call afterwards to check."

    other = portal_phone.forwarding_codes("other", TEXTING)
    assert other["enable"] == [] and other["disable"] == [] and other["verified"] is True
    assert other["steps"] == ("Ask your carrier to forward only busy and unanswered calls to (980) 555-0177. "
                              "They call it conditional call forwarding. Never forward all calls.")
    assert portal_phone.turn_off_code("other", TEXTING) == ""

    for carrier, _ in portal_phone.CARRIERS:
        codes = portal_phone.forwarding_codes(carrier, TEXTING)
        assert codes["unverified"] == ("" if codes["verified"] else portal_phone.UNVERIFIED.format(carrier=codes["name"]))
        for _, code in codes["enable"] + codes["disable"]:
            assert "{" not in code and "<" not in code
    # No carrier, an unknown carrier, or no texting number: no codes to copy, and a plain note.
    assert portal_phone.forwarding_codes("", TEXTING)["note"] == "Pick your carrier to see the codes."
    assert portal_phone.forwarding_codes("sprint", TEXTING)["enable"] == []
    none = portal_phone.forwarding_codes("verizon", "")
    assert none["enable"] == [] and none["disable"] == []
    assert none["note"] == "The codes fill in once FluxWorks assigns your texting number."
    assert portal_phone.turn_off_code("verizon", "") == ""


# --- checklist wrapper -----------------------------------------------------------------

def test_checklist_context_names_manual_steps_and_carries_the_turn_off_code(tmp_path, monkeypatch):
    state, telecom, clock = make_state(tmp_path, monkeypatch)
    checklist = portal_phone.checklist_context(state, NOW, carrier="verizon")
    names = {step["n"]: step["name"] for step in checklist["steps"]}
    assert names == {1: "", 2: "", 3: "check_answered_no_text", 4: "", 5: "check_deactivation_saved"}
    assert checklist["steps"][4]["code"] == "*73" and checklist["steps"][0]["code"] == ""
    assert all(step["state_word"] == "Not yet" for step in checklist["steps"])
    assert portal_phone.checklist_context(state, NOW, carrier="")["steps"][4]["code"] == ""
    # Manual ticks persist, keep their first timestamp and drop on untick.
    portal_phone.save_checklist(state, {"check_answered_no_text": "1", "check_deactivation_saved": "1"}, NOW)
    saved = json.loads(state.store.setting("forwarding_checklist"))
    assert saved == {"answered_no_text": NOW.isoformat(), "deactivation_saved": NOW.isoformat()}
    later = NOW + timedelta(hours=1)
    portal_phone.save_checklist(state, {"check_answered_no_text": "1"}, later)
    saved = json.loads(state.store.setting("forwarding_checklist"))
    assert saved == {"answered_no_text": NOW.isoformat()}
    words = [s["state_word"] for s in portal_phone.checklist_context(state, later, carrier="verizon")["steps"]]
    assert words == ["Not yet", "Not yet", "You checked this", "Not yet", "Not yet"]
    assert portal_phone.CHECKS_SAVED == "Checks saved."


# --- words -----------------------------------------------------------------------------

def test_owner_facing_strings_carry_no_vendor_or_repository_names():
    banned = re.compile(r"signalwire|twilio|text_back|textback\b(?!\.)|\bAI\b|forward-all", re.I)
    strings = {name: value for name, value in vars(portal_phone).items()
               if name.isupper() and isinstance(value, str)}
    assert strings, "no string constants found"
    for name, value in strings.items():
        if name.startswith("_"):
            continue
        assert not re.search(r"signalwire|twilio|text_back|forward-all", value, re.I), (name, value)
    for value in portal_phone.LABELS.values():
        assert not banned.search(value), value
    for carrier, _ in portal_phone.CARRIERS:
        codes = portal_phone.forwarding_codes(carrier, TEXTING)
        for text in (codes["note"], codes["steps"], codes["unverified"]):
            assert not re.search(r"signalwire|twilio|text_back", text, re.I), text
    assert portal_phone.FORWARD_ALL_WARNING == (
        "Only forward busy and unanswered calls. Forwarding every call stops answered calls from reaching you.")
    from text_back import portal_forwarding
    assert portal_forwarding.EVIDENCE_NOTE == "Checks 1, 2 and 4 tick from calls TextBack recorded."
    assert portal_phone.SAVED == "Saved."
    assert portal_phone.LABELS["business_contact"] == "Number in the HELP reply"
