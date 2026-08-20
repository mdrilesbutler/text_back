from __future__ import annotations

from fastapi import FastAPI, Form, Header, HTTPException, Request

from text_back.config import load_config
from text_back.handlers import handle_sms_event, handle_voice_event
from text_back.policy import WIRING_MODES
from text_back.signatures import SignatureError, verify_twilio_compat
from text_back.store import Store
from text_back.telecom import FakeTelecom


def create_app(
    *,
    webhook_secret: str | None = None,
    public_base_url: str | None = None,
    db_path: str | None = None,
    telecom: FakeTelecom | None = None,
    store: Store | None = None,
    wiring_mode: str | None = None,
) -> FastAPI:
    config = load_config()
    webhook_secret = webhook_secret if webhook_secret is not None else config.webhook_secret
    public_base_url = (
        public_base_url if public_base_url is not None else config.public_base_url
    )
    db_path = db_path if db_path is not None else config.db_path
    wiring_mode = wiring_mode if wiring_mode is not None else config.wiring_mode
    if wiring_mode not in WIRING_MODES:
        raise ValueError(
            f"invalid wiring_mode: {wiring_mode!r}; must be one of {sorted(WIRING_MODES)}"
        )
    app = FastAPI(title="text_back", version="0.1.0")
    app.state.webhook_secret = webhook_secret
    app.state.public_base_url = public_base_url.rstrip("/")
    app.state.telecom = telecom or FakeTelecom()
    app.state.store = store or Store(db_path)
    app.state.db_path = db_path
    app.state.wiring_mode = wiring_mode

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "production": False,
            "telecom": "stub",
            "public_base_url": app.state.public_base_url,
            "wiring_mode": app.state.wiring_mode,
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
    ) -> dict:
        form = await request.form()
        params = {str(k): str(v) for k, v in form.items()}
        url = f"{request.app.state.public_base_url}/webhooks/voice"
        try:
            verify_twilio_compat(url, params, x_twilio_signature, request.app.state.webhook_secret)
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
        )
        result.update({"call_sid": call_sid, "call_status": call_status, "direction": direction})
        return result

    @app.post("/webhooks/sms")
    async def sms_webhook(
        request: Request,
        message_sid: str = Form(alias="MessageSid"),
        from_number: str = Form(alias="From"),
        to_number: str = Form(alias="To"),
        body: str = Form(alias="Body"),
        x_twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
    ) -> dict:
        form = await request.form()
        params = {str(k): str(v) for k, v in form.items()}
        url = f"{request.app.state.public_base_url}/webhooks/sms"
        try:
            verify_twilio_compat(url, params, x_twilio_signature, request.app.state.webhook_secret)
        except SignatureError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        result = handle_sms_event(
            store=request.app.state.store,
            telecom=request.app.state.telecom,
            message_sid=message_sid,
            from_number=from_number,
            to_number=to_number,
            body=body,
        )
        result["message_sid"] = message_sid
        return result

    return app
