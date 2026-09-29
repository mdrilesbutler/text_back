from datetime import datetime, timedelta, timezone
from text_back.app import create_app
from text_back.calendar_stub import CalendarStub
from text_back.calendars.protocol import CalendarProviderError
from text_back.handlers import handle_sms_event
from text_back.telecom import FakeTelecom
from text_back.worker import run_once

NOW=datetime(2026,9,17,14,tzinfo=timezone.utc)
CALLER='+15551112222'


def test_transient_calendar_failure_recovers_in_worker_without_customer_reply(tmp_path):
    class FlakyCalendar(CalendarStub):
        fail=True
        def is_free(self,start,end):
            if self.fail:
                raise CalendarProviderError('temporary outage')
            return super().is_free(start,end)
    clock=[NOW]
    calendar=FlakyCalendar()
    app=create_app(db_path=str(tmp_path/'booking.db'),calendar=calendar,telecom=FakeTelecom(),now_provider=lambda:clock[0])
    for i,body in enumerate(['trimming','Oak St','2026-09-18 14:00','Test']):
        handle_sms_event(store=app.state.store,calendar=calendar,telecom=app.state.telecom,
            handoff_notifier=app.state.handoff_notifier,handoff_destination='queue',message_sid=f'm{i}',
            from_number=CALLER,to_number='+15553334444',body=body,business_name='Test',timezone_name='UTC',appointment_duration_minutes=60,now=NOW)
    assert app.state.store.get_conversation_fields(CALLER)['preferred_time']=='2026-09-18 14:00'
    assert not app.state.store.appointment_by_conversation(CALLER)
    calendar.fail=False
    clock[0]+=timedelta(minutes=2)
    run_once(app.state)
    assert app.state.store.appointment_by_conversation(CALLER)
    assert len(calendar.events)==1
    assert sum(s.kind=='booking_confirmation' for s in app.state.telecom.outbound)==1


class _UnavailableCalendar(CalendarStub):
    def __init__(self):
        super().__init__()
        self.unavailable = True
        self.availability_checks = 0
        self.create_attempts = 0

    def is_free(self, start, end):
        self.availability_checks += 1
        if self.unavailable:
            raise CalendarProviderError("temporary calendar outage")
        return super().is_free(start, end)

    def create_event(self, **kwargs):
        self.create_attempts += 1
        return super().create_event(**kwargs)


def _booking_message(app, *, message_sid, body, now):
    return handle_sms_event(
        store=app.state.store,
        calendar=app.state.calendar,
        telecom=app.state.telecom,
        handoff_notifier=app.state.handoff_notifier,
        handoff_destination="operator-queue",
        message_sid=message_sid,
        from_number=CALLER,
        to_number="+15553334444",
        body=body,
        business_name="Recovery Fixture",
        timezone_name="UTC",
        appointment_duration_minutes=60,
        now=now,
    )


def _qualified_pending_booking(tmp_path):
    clock = [NOW]
    calendar = _UnavailableCalendar()
    app = create_app(
        db_path=str(tmp_path / "pending-booking.db"),
        calendar=calendar,
        telecom=FakeTelecom(),
        handoff_destination="operator-queue",
        now_provider=lambda: clock[0],
        timezone_name="UTC",
    )
    for index, body in enumerate(("tree trimming", "12 Oak St", "2026-09-19 14:00", "Test Customer")):
        _booking_message(app, message_sid=f"SM-qualify-{index}", body=body, now=clock[0])
    job = dict(app.state.store.conn.execute("SELECT * FROM booking_jobs").fetchone())
    assert job["status"] == "pending"
    assert calendar.availability_checks == 1
    return app, clock, calendar, job["key"]


def _booking_job(app, key):
    return dict(app.state.store.conn.execute("SELECT * FROM booking_jobs WHERE key=?", (key,)).fetchone())


def test_exhausted_calendar_retries_preserve_one_durable_operator_handoff(tmp_path):
    from text_back.delivery import alert_from_payload_json
    from text_back.store import Store

    app, clock, calendar, key = _qualified_pending_booking(tmp_path)

    for minute in (1, 6, 21):
        clock[0] = NOW + timedelta(minutes=minute)
        run_once(app.state)

    job = _booking_job(app, key)
    assert job["status"] == "dead_letter"
    assert job["attempts"] == 4
    assert calendar.availability_checks == 4
    assert calendar.create_attempts == 0
    assert calendar.events == {}
    assert app.state.store.appointment_by_conversation(CALLER) is None
    assert not any(sms.kind == "booking_confirmation" for sms in app.state.telecom.outbound)
    assert [sms.kind for sms in app.state.telecom.outbound].count("handoff_ack") == 1
    handoff = app.state.store.active_handoff(CALLER)
    assert handoff["reason"] == "calendar_unavailable"
    assert handoff["alert_id"]

    clock[0] = NOW + timedelta(hours=1)
    run_once(app.state)
    assert calendar.availability_checks == 4
    assert app.state.worker_errors == []
    assert [sms.kind for sms in app.state.telecom.outbound].count("handoff_ack") == 1

    # Disabled operator transport leaves a recoverable payload on disk.
    app.state.store.conn.close()
    restarted = Store(str(tmp_path / "pending-booking.db"))
    rows = restarted.due_handoff_deliveries(clock[0].isoformat())
    assert len(rows) == 1
    assert rows[0]["alert_id"] == handoff["alert_id"]
    alert = alert_from_payload_json(rows[0]["payload_json"])
    assert alert.caller == CALLER
    assert alert.reason == "calendar_unavailable"
    assert alert.collected_fields == {
        "service": "tree trimming",
        "location": "12 Oak St",
        "preferred_time": "2026-09-19 14:00",
        "name": "Test Customer",
    }
    assert len([
        event for event in restarted.list_outcome_events(CALLER)
        if event["event_type"] == "lead.handoff_requested"
    ]) == 1


def test_stop_cancels_pending_booking_before_provider_create(tmp_path):
    app, clock, calendar, key = _qualified_pending_booking(tmp_path)
    _booking_message(app, message_sid="SM-stop-booking", body="STOP", now=NOW)
    calendar.unavailable = False

    clock[0] = NOW + timedelta(minutes=2)
    run_once(app.state)

    assert _booking_job(app, key)["status"] == "cancelled"
    assert calendar.availability_checks == 1
    assert calendar.create_attempts == 0
    assert calendar.events == {}
    assert app.state.store.is_opted_out(CALLER)
    assert app.state.store.appointment_by_conversation(CALLER) is None
    assert not any(sms.kind == "booking_confirmation" for sms in app.state.telecom.outbound)


def test_active_handoff_cancels_pending_booking_before_provider_create(tmp_path):
    app, clock, calendar, key = _qualified_pending_booking(tmp_path)
    _booking_message(app, message_sid="SM-handoff-booking", body="human please", now=NOW)
    calendar.unavailable = False

    clock[0] = NOW + timedelta(minutes=2)
    run_once(app.state)

    assert _booking_job(app, key)["status"] == "cancelled"
    assert calendar.availability_checks == 1
    assert calendar.create_attempts == 0
    assert calendar.events == {}
    assert app.state.store.active_handoff(CALLER)
    assert app.state.store.appointment_by_conversation(CALLER) is None
    assert not any(sms.kind == "booking_confirmation" for sms in app.state.telecom.outbound)


def test_revoked_calendar_pauses_booking_attempts_then_resumes_after_reconnection(tmp_path):
    class CredentialStatus:
        current = "reauth_required"

        def status(self):
            return self.current

    app, clock, calendar, key = _qualified_pending_booking(tmp_path)
    credentials = CredentialStatus()
    calendar.token_provider = credentials
    calendar.unavailable = False
    attempts_before_pause = _booking_job(app, key)["attempts"]

    for minute in (1, 2, 6):
        clock[0] = NOW + timedelta(minutes=minute)
        run_once(app.state)
        assert _booking_job(app, key)["status"] == "pending"
        assert _booking_job(app, key)["attempts"] == attempts_before_pause
        assert calendar.availability_checks == 1
        assert calendar.create_attempts == 0
        assert app.state.store.active_handoff(CALLER) is None

    credentials.current = "ready"
    clock[0] = NOW + timedelta(minutes=7)
    run_once(app.state)

    assert _booking_job(app, key)["status"] == "done"
    assert _booking_job(app, key)["attempts"] == attempts_before_pause + 1
    assert calendar.create_attempts == 1
    assert len(calendar.events) == 1
    assert app.state.store.appointment_by_conversation(CALLER)["event_id"] in calendar.events
    assert [sms.kind for sms in app.state.telecom.outbound].count("booking_confirmation") == 1
    assert app.state.worker_errors == []
