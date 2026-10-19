from __future__ import annotations

from datetime import datetime, timezone
import asyncio
import os
from typing import Callable
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, Form, Header, HTTPException, Request, Response

from text_back.config import DEFAULT_WEBHOOK_SECRET, load_config
from text_back.cxml import empty_response, forwarded_call_response
from text_back.calendars import CalendarProvider, calendar_from_config
from text_back.delivery import (
    DeliveryPolicy,
    DeliveryTransport,
    transport_from_config,
)
from text_back.followup import FollowupPolicy
from text_back.handoff import FakeHandoffNotifier, HandoffNotifier
from text_back.messages import MessageSource
from text_back.policy import WIRING_MODES, WIRING_MODE_FORWARDED
from text_back.signatures import SignatureError, verify_twilio_compat
from text_back.sms import reconcile_sms
from text_back.worker import lifespan
from text_back.inbox import submit_event
from text_back.reconnect import install_routes
from text_back.store import Store
from text_back.telecom import FakeTelecom, SignalWireTelecom, Telecom


def _telecom_from_config(config) -> Telecom:
    if config.telecom_mode == "stub":
        return FakeTelecom()
    if config.telecom_mode != "signalwire":
        raise ValueError(
            "invalid TEXT_BACK_TELECOM_MODE; must be 'stub' or 'signalwire'"
        )
    required = {
        "TEXT_BACK_SIGNALWIRE_SPACE_URL": config.signalwire_space_url,
        "TEXT_BACK_SIGNALWIRE_PROJECT_ID": config.signalwire_project_id,
        "TEXT_BACK_SIGNALWIRE_API_TOKEN": config.signalwire_api_token,
        "TEXT_BACK_SIGNALWIRE_FROM_NUMBER": config.signalwire_from_number,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError(
            "SignalWire telecom mode is missing required configuration: "
            + ", ".join(missing)
        )
    return SignalWireTelecom(
        space_url=config.signalwire_space_url,
        project_id=config.signalwire_project_id,
        api_token=config.signalwire_api_token,
        allowed_from_number=config.signalwire_from_number,
        allowed_to_numbers=config.pilot_recipients,
    )


def _validate_signalwire_boundary(*, webhook_secret: str, public_base_url: str) -> None:
    if not webhook_secret or webhook_secret == DEFAULT_WEBHOOK_SECRET:
        raise ValueError(
            "SignalWire mode requires TEXT_BACK_WEBHOOK_SECRET to contain "
            "the Project signing key"
        )
    parsed = urlsplit(public_base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("SignalWire mode requires an HTTPS public base URL")


def create_app(
    *,
    webhook_secret: str | None = None,
    public_base_url: str | None = None,
    db_path: str | None = None,
    telecom: Telecom | None = None,
    store: Store | None = None,
    wiring_mode: str | None = None,
    business_name: str | None = None,
    calendar: CalendarProvider | None = None,
    timezone_name: str | None = None,
    appointment_duration_minutes: int | None = None,
    handoff_notifier: HandoffNotifier | None = None,
    handoff_destination: str | None = None,
    now_provider: Callable[[], datetime] | None = None,
    delivery_transport: DeliveryTransport | None = None,
    worker_interval_seconds: float = 5.0,
) -> FastAPI:
    config = load_config()
    webhook_secret = webhook_secret if webhook_secret is not None else config.webhook_secret
    public_base_url = (
        public_base_url if public_base_url is not None else config.public_base_url
    )
    db_path = db_path if db_path is not None else config.db_path
    wiring_mode = wiring_mode if wiring_mode is not None else config.wiring_mode
    business_name = business_name if business_name is not None else config.business_name
    timezone_name = timezone_name if timezone_name is not None else config.timezone_name
    appointment_duration_minutes = (
        appointment_duration_minutes
        if appointment_duration_minutes is not None
        else config.appointment_duration_minutes
    )
    handoff_destination = (
        handoff_destination
        if handoff_destination is not None
        else config.handoff_destination
    )
    if not business_name.strip():
        raise ValueError("business_name is required")
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        raise ValueError("timezone_name must be a valid IANA timezone") from None
    if appointment_duration_minutes <= 0:
        raise ValueError("appointment_duration_minutes must be positive")
    if wiring_mode not in WIRING_MODES:
        raise ValueError(
            f"invalid wiring_mode: {wiring_mode!r}; must be one of {sorted(WIRING_MODES)}"
        )
    # Fail closed at startup on a bad delivery channel or retry schedule,
    # the same way telecom_mode/wiring_mode do.
    delivery_policy = DeliveryPolicy.from_config(config)
    selected_delivery_transport = (
        delivery_transport
        if delivery_transport is not None
        else transport_from_config(config)
    )
    # Fail closed at startup on a bad calendar provider or missing credentials,
    # regardless of how the app is constructed (mirrors DeliveryPolicy above);
    # an injected calendar bypasses env validation like an injected telecom.
    selected_calendar = (
        calendar
        if calendar is not None
        else calendar_from_config(config, timezone_name=timezone_name)
    )
    selected_telecom = telecom if telecom is not None else _telecom_from_config(config)
    if selected_telecom.provider_name == "signalwire":
        _validate_signalwire_boundary(
            webhook_secret=webhook_secret,
            public_base_url=public_base_url,
        )
        # A production telecom must never confirm real customer bookings
        # against the in-memory stub calendar: the customer would get a
        # confirmation SMS while no calendar anywhere records the job. An
        # explicitly injected calendar (tests) is exempt, mirroring how
        # injection bypasses env validation above.
        if calendar is None and selected_calendar.provider_name == "stub":
            raise ValueError(
                "SignalWire telecom mode requires a real calendar provider; "
                "set TEXT_BACK_CALENDAR_PROVIDER (the default stub calendar "
                "would fabricate booking confirmations)"
            )

    if telecom is None and selected_telecom.provider_name == 'signalwire' and db_path == ':memory:' and store is None:
        raise ValueError('SignalWire runtime requires a persistent TEXT_BACK_DB_PATH')

    if worker_interval_seconds <= 0:
        raise ValueError("worker interval must be positive")
    app = FastAPI(title="text_back", version="0.1.0", lifespan=lifespan)
    app.state.worker_interval_seconds = worker_interval_seconds
    app.state.worker_running = False
    app.state.worker_errors = []
    app.state.calendar_check_at = None
    app.state.operator_api_key = config.operator_api_key
    app.state.worker_last_run = None
    app.state.owns_store = store is None
    app.state.business_number = config.signalwire_from_number
    app.state.webhook_secret = webhook_secret
    app.state.public_base_url = public_base_url.rstrip("/")
    app.state.telecom = selected_telecom
    app.state.store = store or Store(db_path)
    app.state.db_path = db_path
    app.state.wiring_mode = wiring_mode
    app.state.business_name = business_name.strip()
    app.state.business_contact = config.business_contact
    app.state.messages = MessageSource(config.messages_file or None)  # fails closed on a bad file at boot
    app.state.owner_mobile = config.owner_mobile
    app.state.timezone_name = timezone_name
    app.state.appointment_duration_minutes = appointment_duration_minutes
    app.state.calendar = selected_calendar
    app.state.handoff_notifier = handoff_notifier or FakeHandoffNotifier()
    app.state.handoff_destination = handoff_destination
    app.state.now_provider = now_provider
    from dataclasses import replace
    app.state.followup_policy = FollowupPolicy.from_config(replace(config, timezone_name=timezone_name))
    # Handler outbox drains use the same policy and signed callback route.
    app.state.store.sms_policy = app.state.followup_policy
    app.state.store.callback_base_url = app.state.public_base_url
    from text_back.calendar_links import CalendarLinks
    app.state.store.calendar_links = CalendarLinks(app.state.public_base_url, webhook_secret)
    app.state.delivery_policy = delivery_policy
    app.state.delivery_transport = selected_delivery_transport
    # The owner's saved business details and calendar choice override the env defaults.
    from text_back.client_settings import apply_settings
    apply_settings(app.state)

    @app.get("/health")
    def health() -> dict:
        from text_back.calendars.credentials import GoogleCredentials
        credentials = getattr(app.state.calendar, 'token_provider', None)
        try:
            credential_status = credentials.status() if isinstance(credentials, GoogleCredentials) else 'not_managed'
        except Exception:
            credential_status = 'unavailable'
        with app.state.store.lock:
            sms_counts = {row[0]: row[1] for row in app.state.store.conn.execute('SELECT status,count(*) FROM sms_outbox GROUP BY status')}
            inbound_failed = app.state.store.conn.execute("SELECT count(*) FROM inbound_jobs WHERE status='dead_letter'").fetchone()[0]
        return {
            "status": "ok",
            "production": app.state.telecom.provider_name == 'signalwire' and app.state.calendar.provider_name != 'stub',
            "calendar_credentials": credential_status,
            "messages": {"source": "file" if app.state.messages.path else "default", "last_error": app.state.messages.last_error},
            "persistent_database": app.state.db_path != ':memory:',
            "sms_queue": sms_counts,
            "inbound_dead_letters": inbound_failed,
            "worker_running": app.state.worker_running,
            "worker_errors": app.state.worker_errors,
            "worker_last_run": app.state.worker_last_run,
            "telecom": app.state.telecom.provider_name,
            "calendar": app.state.calendar.provider_name,
            "public_base_url": app.state.public_base_url,
            "wiring_mode": app.state.wiring_mode,
            "timezone": app.state.timezone_name,
            "appointment_duration_minutes": app.state.appointment_duration_minutes,
            "handoff_notifier": app.state.handoff_notifier.provider_name,
            "handoff_destination_configured": (
                bool(app.state.handoff_destination)
                and app.state.handoff_destination != "unconfigured"
            ),
            "handoff_delivery_channel": app.state.delivery_transport.channel_name,
            "pilot_recipient_count": None if config.pilot_recipients is None else len(config.pilot_recipients),
        }

    @app.post("/webhooks/voice")
    async def voice_webhook(
        request: Request,
        call_sid: str = Form(alias="CallSid"),
        call_status: str = Form(alias="CallStatus"),
        from_number: str = Form(alias="From"),
        to_number: str = Form(alias="To"),
        direction: str = Form(default="", alias="Direction"),
        x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
        x_signalwire_signature: str | None = Header(
            default=None, alias="X-SignalWire-Signature"
        ),
    ):
        form = await request.form()
        params = {str(k): str(v) for k, v in form.items()}
        url = f"{request.app.state.public_base_url}/webhooks/voice"
        try:
            signature = (
                x_signalwire_signature
                if request.app.state.telecom.provider_name == "signalwire"
                else x_twilio_signature
            )
            verify_twilio_compat(url, params, signature, request.app.state.webhook_secret)
        except SignatureError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        if config.pilot_recipients is not None and from_number not in config.pilot_recipients:
            # Outside the explicit pilot allowlist no work is created and no SMS is
            # queued. A forwarded caller still reached a live line, so give them the
            # branded greeting that does not promise a text instead of dead air.
            if (
                request.app.state.telecom.provider_name == "signalwire"
                and request.app.state.wiring_mode == WIRING_MODE_FORWARDED
            ):
                content = forwarded_call_response(
                    request.app.state.business_name, text_will_follow=False
                )
            else:
                content = empty_response()
            return Response(content=content, media_type='application/xml')
        result = await asyncio.to_thread(submit_event, state=app.state, kind='voice',
            params=dict(call_sid=call_sid, call_status=call_status, from_number=from_number, to_number=to_number))
        result.update({"call_sid": call_sid, "call_status": call_status, "direction": direction})
        if request.app.state.telecom.provider_name == "signalwire":
            content = (
                forwarded_call_response(
                    request.app.state.business_name,
                    text_will_follow=result.get("action") == "sent_intro",
                )
                if request.app.state.wiring_mode == WIRING_MODE_FORWARDED
                else empty_response()
            )
            return Response(content=content, media_type="application/xml")
        return result

    @app.post("/webhooks/sms")
    async def sms_webhook(
        request: Request,
        message_sid: str = Form(alias="MessageSid"),
        from_number: str = Form(alias="From"),
        to_number: str = Form(alias="To"),
        body: str = Form(alias="Body"),
        x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
        x_signalwire_signature: str | None = Header(
            default=None, alias="X-SignalWire-Signature"
        ),
    ):
        form = await request.form()
        params = {str(k): str(v) for k, v in form.items()}
        url = f"{request.app.state.public_base_url}/webhooks/sms"
        try:
            signature = (
                x_signalwire_signature
                if request.app.state.telecom.provider_name == "signalwire"
                else x_twilio_signature
            )
            verify_twilio_compat(url, params, signature, request.app.state.webhook_secret)
        except SignatureError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        if config.pilot_recipients is not None and from_number not in config.pilot_recipients:
            return Response(content=empty_response(), media_type='application/xml')
        result = await asyncio.to_thread(submit_event, state=app.state, kind='sms',
            params=dict(message_sid=message_sid, from_number=from_number, to_number=to_number, body=body))
        result["message_sid"] = message_sid
        if request.app.state.telecom.provider_name == "signalwire":
            return Response(content=empty_response(), media_type="application/xml")
        return result

    @app.post("/webhooks/sms-status")
    async def sms_status(request: Request, key: str):
        form = await request.form()
        params = {str(k): str(v) for k, v in form.items()}
        # Signatures cover the exact configured URL, including the intent key.
        url = app.state.public_base_url + str(request.url.path) + "?" + request.url.query
        try:
            verify_twilio_compat(url, params, request.headers.get("X-SignalWire-Signature"), app.state.webhook_secret)
        except SignatureError as exc:
            raise HTTPException(403, str(exc)) from exc
        sid = params.get("MessageSid", "")
        if not sid:
            raise HTTPException(400, "MessageSid required")
        now = app.state.now_provider() if app.state.now_provider else datetime.now(timezone.utc)
        accepted = await asyncio.to_thread(reconcile_sms, store=app.state.store, key=key, provider_id=sid, now=now, delivery_status=params.get("MessageStatus", ""))
        if not accepted:
            raise HTTPException(409, "Unrecognized message receipt")
        return Response(content=empty_response(), media_type="application/xml")

    install_routes(app)
    from text_back.client_portal import install_routes as install_client_routes
    install_client_routes(app)
    from text_back.client_settings import install_routes as install_settings_routes
    install_settings_routes(app)
    from text_back.calendar_links import install_routes as install_link_routes
    install_link_routes(app)
    if setup_directory := os.environ.get('TEXT_BACK_SETUP_DIRECTORY'):
        from text_back.setup_intake import install_routes as install_setup_routes
        install_setup_routes(app, directory=setup_directory, public_base_url=public_base_url)
    return app
