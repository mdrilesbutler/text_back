from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from text_back.policy import WIRING_MODE_FORWARDED

DEFAULT_WEBHOOK_SECRET = "dev-secret-not-for-production"


@dataclass(frozen=True)
class AppConfig:
    webhook_secret: str
    public_base_url: str
    db_path: str
    wiring_mode: str
    telecom_mode: str
    signalwire_space_url: str
    signalwire_project_id: str
    signalwire_api_token: str = field(repr=False)
    signalwire_from_number: str
    business_name: str
    timezone_name: str
    appointment_duration_minutes: int
    handoff_destination: str
    followup_delays_minutes: str
    followup_expiry_minutes: int
    quiet_hours_start: str
    quiet_hours_end: str
    handoff_delivery_channel: str
    handoff_delivery_retry_minutes: str
    calendar_provider: str
    google_calendar_id: str
    google_token_file: str
    ms_user: str
    ms_token_file: str
    icloud_username: str
    icloud_app_password_file: str
    icloud_calendar_url: str
    google_client_file: str = ""
    operator_api_key: str = field(default="", repr=False)
    telegram_bot_token: str = field(default="", repr=False)
    telegram_chat_id: str = field(default="", repr=False)
    pilot_recipients: tuple[str, ...] | None = field(default=None, repr=False)
    business_contact: str = ""
    messages_file: str = ""
    owner_mobile: str = ""


def load_config() -> AppConfig:
    """Load app configuration from the process environment."""
    raw_recipients = os.environ.get('TEXT_BACK_PILOT_RECIPIENTS')
    pilot_recipients = None if raw_recipients is None else tuple(
        dict.fromkeys(number.strip() for number in raw_recipients.split(',') if number.strip()))
    if pilot_recipients and any(not re.fullmatch(r'\+[1-9][0-9]{7,14}', number) for number in pilot_recipients):
        raise ValueError('TEXT_BACK_PILOT_RECIPIENTS must contain E.164 numbers')
    return AppConfig(
        pilot_recipients=pilot_recipients,
        business_contact=os.environ.get("TEXT_BACK_BUSINESS_CONTACT", ""),
        messages_file=os.environ.get("TEXT_BACK_MESSAGES_FILE", ""),
        owner_mobile=os.environ.get("TEXT_BACK_OWNER_MOBILE", "").strip(),
        telegram_bot_token=os.environ.get("TEXT_BACK_TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.environ.get("TEXT_BACK_TELEGRAM_CHAT_ID", ""),
        google_client_file=os.environ.get("TEXT_BACK_GOOGLE_CLIENT_FILE", ""),
        operator_api_key=os.environ.get("TEXT_BACK_OPERATOR_API_KEY", ""),
        webhook_secret=os.environ.get(
            "TEXT_BACK_WEBHOOK_SECRET", DEFAULT_WEBHOOK_SECRET
        ),
        public_base_url=os.environ.get(
            "TEXT_BACK_PUBLIC_BASE_URL", "http://127.0.0.1:8000"
        ),
        db_path=os.environ.get("TEXT_BACK_DB_PATH", ":memory:"),
        wiring_mode=os.environ.get("TEXT_BACK_WIRING_MODE", WIRING_MODE_FORWARDED),
        telecom_mode=os.environ.get("TEXT_BACK_TELECOM_MODE", "stub"),
        signalwire_space_url=os.environ.get("TEXT_BACK_SIGNALWIRE_SPACE_URL", ""),
        signalwire_project_id=os.environ.get("TEXT_BACK_SIGNALWIRE_PROJECT_ID", ""),
        signalwire_api_token=os.environ.get("TEXT_BACK_SIGNALWIRE_API_TOKEN", ""),
        signalwire_from_number=os.environ.get("TEXT_BACK_SIGNALWIRE_FROM_NUMBER", ""),
        business_name=os.environ.get("TEXT_BACK_BUSINESS_NAME", "the business"),
        timezone_name=os.environ.get("TEXT_BACK_TIMEZONE", "UTC"),
        appointment_duration_minutes=int(
            os.environ.get("TEXT_BACK_APPOINTMENT_DURATION_MINUTES", "60")
        ),
        handoff_destination=os.environ.get(
            "TEXT_BACK_HANDOFF_DESTINATION", "unconfigured"
        ),
        followup_delays_minutes=os.environ.get(
            "TEXT_BACK_FOLLOWUP_DELAYS_MINUTES", "120,1440"
        ),
        followup_expiry_minutes=int(
            os.environ.get("TEXT_BACK_FOLLOWUP_EXPIRY_MINUTES", "2880")
        ),
        quiet_hours_start=os.environ.get("TEXT_BACK_QUIET_HOURS_START", "21:00"),
        quiet_hours_end=os.environ.get("TEXT_BACK_QUIET_HOURS_END", "08:00"),
        handoff_delivery_channel=os.environ.get(
            "TEXT_BACK_HANDOFF_DELIVERY_CHANNEL", "disabled"
        ),
        handoff_delivery_retry_minutes=os.environ.get(
            "TEXT_BACK_HANDOFF_DELIVERY_RETRY_MINUTES", "1,5,15"
        ),
        calendar_provider=os.environ.get("TEXT_BACK_CALENDAR_PROVIDER", "stub"),
        google_calendar_id=os.environ.get("TEXT_BACK_GOOGLE_CALENDAR_ID", ""),
        google_token_file=os.environ.get("TEXT_BACK_GOOGLE_TOKEN_FILE", ""),
        ms_user=os.environ.get("TEXT_BACK_MS_USER", ""),
        ms_token_file=os.environ.get("TEXT_BACK_MS_TOKEN_FILE", ""),
        icloud_username=os.environ.get("TEXT_BACK_ICLOUD_USERNAME", ""),
        icloud_app_password_file=os.environ.get(
            "TEXT_BACK_ICLOUD_APP_PASSWORD_FILE", ""
        ),
        icloud_calendar_url=os.environ.get("TEXT_BACK_ICLOUD_CALENDAR_URL", ""),
    )
