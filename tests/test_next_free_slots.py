"""availability.next_free_slots: step rounding, busy overlaps, no overlap between slots, working hours, horizon, DST."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from text_back.availability import format_slot, next_free_slots

NY = ZoneInfo("America/New_York")
HOURS = {**{d: {"open": "09:00", "close": "17:00"} for d in ("mon", "tue", "wed", "thu", "fri")}, "sat": None, "sun": None}


def local(*args):
    return datetime(*args, tzinfo=NY)


def test_starts_on_the_next_step_boundary_after_now_never_now_itself():
    assert next_free_slots([], local(2026, 10, 19, 10, 5), 60, None, "America/New_York")[0] == local(2026, 10, 19, 10, 30)
    assert next_free_slots([], local(2026, 10, 19, 10, 0), 60, None, "America/New_York")[0] == local(2026, 10, 19, 10, 30)
    assert next_free_slots([], local(2026, 10, 19, 10, 0, 1), 60, None, NY, step_minutes=15)[0] == local(2026, 10, 19, 10, 15)
    # A naive or UTC now is fine; results come back in the business zone.
    out = next_free_slots([], datetime(2026, 10, 19, 14, 5, tzinfo=timezone.utc), 60, None, "America/New_York")
    assert out[0] == local(2026, 10, 19, 10, 30) and out[0].tzinfo is NY and len(out) == 3


def test_skips_slots_that_overlap_busy_periods():
    busy = [(local(2026, 10, 19, 11, 30), local(2026, 10, 19, 12, 30))]
    out = next_free_slots(busy, local(2026, 10, 19, 11, 0), 60, None, NY)
    assert out == [local(2026, 10, 19, 12, 30), local(2026, 10, 19, 13, 30), local(2026, 10, 19, 14, 30)]
    # Touching is not overlapping: a slot may end exactly when a busy period starts.
    out = next_free_slots(busy, local(2026, 10, 19, 10, 0), 60, None, NY)
    assert out[0] == local(2026, 10, 19, 10, 30) and out[1] == local(2026, 10, 19, 12, 30)


def test_honours_working_hours_and_the_closed_weekend():
    # Friday 16:45: 17:00-18:00 is outside the window, so the next slots are Monday morning.
    out = next_free_slots([], local(2026, 10, 23, 16, 45), 60, HOURS, NY)
    assert out == [local(2026, 10, 26, 9, 0), local(2026, 10, 26, 10, 0), local(2026, 10, 26, 11, 0)]
    # Busy periods given in UTC are compared as instants.
    busy = [(datetime(2026, 10, 26, 13, 0, tzinfo=timezone.utc), datetime(2026, 10, 26, 14, 0, tzinfo=timezone.utc))]
    assert next_free_slots(busy, local(2026, 10, 23, 16, 45), 60, HOURS, NY)[0] == local(2026, 10, 26, 10, 0)


def test_returns_fewer_when_the_horizon_runs_out():
    monday_only = {"mon": {"open": "09:00", "close": "10:00"}, **{d: None for d in ("tue", "wed", "thu", "fri", "sat", "sun")}}
    out = next_free_slots([], local(2026, 10, 20, 8, 0), 60, monday_only, NY)  # a Tuesday
    assert out == [local(2026, 10, 26, 9, 0), local(2026, 11, 2, 9, 0)]
    assert next_free_slots([], local(2026, 10, 20, 8, 0), 60, monday_only, NY, horizon_days=3) == []
    assert next_free_slots([], local(2026, 10, 20, 8, 0), 0, None, NY) == []


def test_daylight_saving_days_produce_real_distinct_instants():
    # Fall back (2026-11-01, 2:00 -> 1:00): the repeated hour yields distinct instants in order.
    now = datetime(2026, 11, 1, 5, 0, tzinfo=timezone.utc)  # 01:00 EDT
    out = next_free_slots([], now, 60, None, NY)
    instants = [s.astimezone(timezone.utc) for s in out]
    assert instants == [now + timedelta(minutes=30 + 60 * i) for i in (0, 1, 2)]
    assert [s.strftime("%H:%M %Z") for s in out] == ["01:30 EDT", "01:30 EST", "02:30 EST"]
    # Spring forward (2026-03-08, 2:00 -> 3:00): no slot lands in the missing hour.
    now = datetime(2026, 3, 8, 6, 30, tzinfo=timezone.utc)  # 01:30 EST
    out = next_free_slots([], now, 60, None, NY)
    assert out[0].strftime("%H:%M %Z") == "03:00 EDT" and out[0].astimezone(timezone.utc) == now + timedelta(minutes=30)


def test_format_slot_reads_like_the_confirmation_text():
    assert format_slot(local(2026, 10, 22, 16, 0), 60) == "Thu, Oct 22 · 4:00–5:00 PM"
    assert format_slot(local(2026, 10, 23, 11, 30), 60) == "Fri, Oct 23 · 11:30 AM–12:30 PM"
    assert format_slot(local(2026, 10, 5, 8, 0), 45) == "Mon, Oct 5 · 8:00–8:45 AM"


def test_listed_times_never_overlap_and_step_by_the_appointment_length():
    # Round 3: after a free slot the next one starts when it ends, for any length; a busy gap still skips.
    out = next_free_slots([], local(2026, 10, 26, 8, 50), 45, HOURS, NY)
    assert out == [local(2026, 10, 26, 9, 0), local(2026, 10, 26, 9, 45), local(2026, 10, 26, 10, 30)]
    busy = [(local(2026, 10, 26, 10, 0), local(2026, 10, 26, 10, 15))]
    out = next_free_slots(busy, local(2026, 10, 26, 8, 50), 60, HOURS, NY)
    assert out == [local(2026, 10, 26, 9, 0), local(2026, 10, 26, 10, 30), local(2026, 10, 26, 11, 30)]
    for a, b in zip(out, out[1:]):
        assert a + timedelta(minutes=60) <= b
    # Only two fit before close on the last open day in the horizon: two are returned, never a third that overlaps.
    late = next_free_slots([], local(2026, 10, 23, 14, 50), 60, HOURS, NY, horizon_days=1)
    assert late == [local(2026, 10, 23, 15, 0), local(2026, 10, 23, 16, 0)]
