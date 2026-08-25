from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, Form, Header, HTTPException, Request, Response

from text_back.config import DEFAULT_WEBHOOK_SECRET, load_config
from text_back.cxml import empty_response, forwarded_call_response
from text_back.calendar_stub import CalendarStub
from text_back.followup import FollowupPolicy
from text_back.handoff import FakeHandoffNotifier, HandoffNotifier
from text_back.handlers import handle_sms_event, handle_voice_event
from text_back.policy import WIRING_MODES, WIRING_MODE_FORWARDED
from text_back.signatures import SignatureError, verify_twilio_compat
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
    calendar: CalendarStub | None = None,
    timezone_name: str | None = None,
    appointment_duration_minutes: int | None = None,
    handoff_notifier: HandoffNotifier | None = None,
    handoff_destination: str | None = None,
    now_provider: Callable[[], datetime] | None = None,
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
    selected_telecom = telecom if telecom is not None else _telecom_from_config(config)
    if selected_telecom.provider_name == "signalwire":
        _validate_signalwire_boundary(
            webhook_secret=webhook_secret,
            public_base_url=public_base_url,
        )

    app = FastAPI(title="text_back", version="0.1.0")
    app.state.webhook_secret = webhook_secret
    app.state.public_base_url = public_base_url.rstrip("/")
    app.state.telecom = selected_telecom
    app.state.store = store or Store(db_path)
    app.state.db_path = db_path
    app.state.wiring_mode = wiring_mode
    app.state.business_name = business_name.strip()
    app.state.timezone_name = timezone_name
    app.state.appointment_duration_minutes = appointment_duration_minutes
    app.state.calendar = calendar or CalendarStub(timezone_name=timezone_name)
    app.state.handoff_notifier = handoff_notifier or FakeHandoffNotifier()
    app.state.handoff_destination = handoff_destination
    app.state.now_provider = now_provider
    app.state.followup_policy = FollowupPolicy.from_config(config)

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "production": False,
            "telecom": app.state.telecom.provider_name,
            "public_base_url": app.state.public_base_url,
            "wiring_mode": app.state.wiring_mode,
            "timezone": app.state.timezone_name,
            "appointment_duration_minutes": app.state.appointment_duration_minutes,
            "handoff_notifier": app.state.handoff_notifier.provider_name,
            "handoff_destination_configured": (
                bool(app.state.handoff_destination)
                and app.state.handoff_destination != "unconfigured"
            ),
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
        result = handle_voice_event(
            store=request.app.state.store,
            telecom=request.app.state.telecom,
            call_sid=call_sid,
            call_status=call_status,
            from_number=from_number,
            to_number=to_number,
            wiring_mode=request.app.state.wiring_mode,
            business_name=request.app.state.business_name,
            followup_policy=request.app.state.followup_policy,
            now=(
                request.app.state.now_provider()
                if request.app.state.now_provider is not None
                else datetime.now(timezone.utc)
            ),
        )
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
        result = handle_sms_event(
            store=request.app.state.store,
            calendar=request.app.state.calendar,
            telecom=request.app.state.telecom,
            handoff_notifier=request.app.state.handoff_notifier,
            handoff_destination=request.app.state.handoff_destination,
            message_sid=message_sid,
            from_number=from_number,
            to_number=to_number,
            body=body,
            business_name=request.app.state.business_name,
            timezone_name=request.app.state.timezone_name,
            appointment_duration_minutes=request.app.state.appointment_duration_minutes,
            now=(
                request.app.state.now_provider()
                if request.app.state.now_provider is not None
                else None
            ),
        )
        result["message_sid"] = message_sid
        if request.app.state.telecom.provider_name == "signalwire":
            return Response(content=empty_response(), media_type="application/xml")
        return result

    return app
