"""Candidate C, layer 3: the Schedule page from mockup d1 round 3, plus the cross-layer review fixes
(announced server notices, no floating toast left, "this device", the Home headline's Example tag)."""
import html
import re
from pathlib import Path

from text_back import portal_status
from text_back import portal_scheduling as ps
from test_client_portal import csrf_of, make, sign_in

STATIC = Path(__file__).resolve().parents[1] / "src" / "text_back" / "static"
TEMPLATES = Path(__file__).resolve().parents[1] / "src" / "text_back" / "templates" / "client"


def signed_in(tmp_path, monkeypatch):
    client, telecom, clock, path = make(tmp_path, monkeypatch)
    sign_in(client, telecom)
    return client, csrf_of(client.get("/client/account").text)


def form(csrf, **changes):
    data = {"csrf": csrf, "quiet_switch": "1", "quiet_on": "1", "appointment_duration_minutes": "60",
            "appointment_duration_custom": "60", "appointment_duration_shown": "60", "timezone": "UTC",
            "hours_mode": "any", "quiet_hours_start": "21:00", "quiet_hours_end": "08:00", "followup_delay_1": "120",
            "followup_delay_2": "1440", "followup_expiry_minutes": "2880"}
    data.update(changes)
    return {k: v for k, v in data.items() if v is not None}


def slot(page):
    match = re.search(r"<div class=status-slot id=notice role=status>(?:<div class=\"notice [^\"]*\" data-notice>.*?"
                      r"<p class=notice__text>(.*?)</p>)?", page, re.S)
    return html.unescape(match.group(1) or "")


# --- the page --------------------------------------------------------------------------------

def test_schedule_is_one_form_on_the_spine_with_applies_lines_and_a_reset_per_rule(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    page = client.get("/client/schedule").text
    heads = re.findall(r'<li class="node node--icon" id=([\w-]+)>.*?<h2 tabindex=-1>([^<]+)</h2>', page, re.S)
    # m14: the one-tap hours land at #working-hours.
    assert heads == [("appointments", "Appointments"), ("working-hours", "Working hours"), ("quiet_hours", "Quiet hours"),
                     ("reminders", "Reminders")]
    shown = html.unescape(page)
    for line in ps.APPLIES.values():
        assert f"<p class=applies>Once saved: {line}</p>" in shown, line  # before saving, under its field
    # m11: "Reset" with JavaScript, "Reset and save" without; hidden while the rule is at its default.
    resets = re.findall(r'<button type=submit class="btn btn--ghost rule-foot__reset" name=reset value=(\w+) '
                        r'data-reset-values="[^"]*" hidden><span class=msg__reset-js>Reset</span>'
                        r'<span class=msg__reset-nojs>Reset and save</span><span class=vh> ([^<]+)</span>', page)
    assert [g for g, _ in resets] == ["appointment_duration_minutes", "timezone", "working_hours", "quiet_hours",
                                      "followup_delay_1", "followup_delay_2", "followup_expiry_minutes"]
    assert "<p class=default>Default: 60 minutes</p>" in shown and "<p class=default>Default: Any day, any time</p>" in shown
    the_form = re.search(r"<form method=post action=/client/schedule id=schedule-form [^>]*>", page).group(0)
    for attr in ("data-track-changes", "data-topsave", 'data-changed-one="1 rule changed"', 'data-changed-many="{n} rules changed"'):
        assert attr in the_form, attr
    assert '<div class="savebar" data-state=clean data-savebar data-form=schedule-form>' in page
    # Working hours: both parts are rendered; CSS shows the grid for "Set hours" and the warning for "Any day".
    assert "data-any-time-warning" in page and "data-suggest-hours" in page and "<fieldset class=hours>" in page
    assert page.count('<span class="hrow__word hrow__word--on" aria-hidden=true>Open</span>') == 7
    assert '<label class=switch-row for=quiet_on><span class=switch-row__text>Quiet hours</span>' in page
    assert "<legend class=field__label>Hold reminders between</legend>" in page


def test_a_typed_length_wins_over_an_untouched_chip_and_a_chip_over_an_untouched_number(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    client.post("/client/schedule", data=form(csrf, appointment_duration_minutes="90"))
    assert state.appointment_duration_minutes == 90  # chip picked, number left as shown (60)
    client.post("/client/schedule", data=form(csrf, appointment_duration_minutes="90", appointment_duration_custom="75",
                                              appointment_duration_shown="90"))
    assert state.appointment_duration_minutes == 75  # number changed, chip left as it was


def test_the_quiet_hours_switch_turns_quiet_hours_off_and_back_on(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    off = client.post("/client/schedule", data=form(csrf, quiet_on=None)).text
    assert state.followup_policy.quiet_start == state.followup_policy.quiet_end
    assert "id=quiet_on name=quiet_on value=1>" in off  # unchecked
    # The selects offer the default window again rather than an empty one.
    assert re.search(r'name=quiet_hours_start [^>]*>.*?<option value="21:00" selected>', off, re.S)
    client.post("/client/schedule", data=form(csrf, quiet_hours_start="22:00", quiet_hours_end="06:00"))
    assert state.followup_policy.quiet_start.hour == 22 and state.followup_policy.quiet_end.hour == 6


def test_discard_without_javascript_writes_nothing(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    page = client.post("/client/schedule", data=form(csrf, appointment_duration_minutes="90", discard="1")).text
    assert slot(page) == "Changes discarded." and state.appointment_duration_minutes == 60
    assert state.store.setting("appointment_duration_minutes") is None


def test_unsaved_answers_raise_the_save_bar_in_the_header_and_at_the_bottom(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    filled = client.post("/client/schedule", data=form(csrf, suggest_hours="1")).text
    header = re.search(r'<header class="topbar topbar--dirty" data-topbar>.*?</header>', filled, re.S).group(0)
    assert "<span class=topsave__count>1 rule changed</span>" in header and '<a href="#working-hours">Working hours</a>' in header
    assert "data-dirty-initial" in filled and '<div class="savebar savebar--on" data-state=dirty' in filled
    bad = client.post("/client/schedule", data=form(csrf, appointment_duration_minutes="custom",
                                                   appointment_duration_custom="7", appointment_duration_shown="60")).text
    assert "<span class=topsave__count>Not saved · 1 rule changed</span>" in bad
    assert '<a href="#rule-duration">Appointment length</a>' in bad and 'id=rule-duration data-change-label="Appointment length"' in bad


def test_the_save_notice_names_the_rules_and_the_reminder_clause(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    page = client.post("/client/schedule", data=form(csrf, followup_delay_1="240", timezone="America/Chicago")).text
    # m10: each rule's own note, never "mid-conversation" beside "reminders keep their time".
    assert slot(page) == ("Saved. You changed “Time zone”, “If there's no reply, send a reminder after”. Time zone: applies "
                          "right away to the times in texts. Reminders: a reminder that is already scheduled keeps its "
                          "time. Later reminders use the new delays.")
    page = client.post("/client/schedule", data=form(csrf, followup_delay_1="240", timezone="America/Chicago")).text
    assert slot(page) == "Saved."


# --- cross-layer review fixes ------------------------------------------------------------------

def test_server_notices_are_re_announced_and_no_floating_toast_is_left(tmp_path):
    js = (STATIC / "portal.js").read_text()
    assert "requestAnimationFrame(() => { slot.append(node); syncDismiss(); })" in js  # F7: Dismiss follows, outside the slot
    assert "if (!e.defaultPrevented) submitting = true" in js
    css = (STATIC / "portal.css").read_text()
    for gone in (".toast-region", ".toast--floating", "tb-toast-in"):
        assert gone not in css, gone
    assert "macro toast(" not in (TEMPLATES / "_macros.html.j2").read_text()


def test_account_and_sign_in_say_this_device_and_take_the_notes_from_the_view(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    page = html.unescape(client.get("/client/account").text)
    assert "Remember this device for 30 days" in page and "this phone" not in page.lower()
    assert 'data-note-on="On. This device stays signed in for 30 days." data-note-off="Off. This device signs out after 12 hours."' in page
    assert "On. This device" not in (TEMPLATES / "account.html.j2").read_text()


def test_home_headline_counts_every_card_so_it_never_contradicts_one(tmp_path, monkeypatch):
    client, csrf = signed_in(tmp_path, monkeypatch)
    state = client.app.state
    line = lambda: re.search(r"<p class=status-line data-status-line>.*?</p>", client.get("/client/home").text).group(0)
    assert line() == "<p class=status-line data-status-line>Not working yet: 1 step for you, 2 waiting on others.</p>"  # forwarding
    state.preview_example_setup = {"forwarding"}
    assert line() == "<p class=status-line data-status-line>Not working yet: 1 step for you, 2 waiting on others.</p>"
    items = [dict(key="calendar", state_word="Needs you", example=True), dict(key="forwarding", state_word="Done", example=False),
             dict(key="approval", state_word="Waiting on phone companies", example=False)]
    assert portal_status.headline(portal_status.counted(items)) == "Not working yet: 1 step for you, 1 waiting on others."

