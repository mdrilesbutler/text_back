from __future__ import annotations

import os
from dataclasses import dataclass

from text_back.policy import WIRING_MODE_FORWARDED


@dataclass(frozen=True)
class AppConfig:
    webhook_secret: str
    public_base_url: str
    db_path: str
    wiring_mode: str


def load_config() -> AppConfig:
    """Load app configuration from the process environment."""
    return AppConfig(
        webhook_secret=os.environ.get(
            "TEXT_BACK_WEBHOOK_SECRET", "dev-secret-not-for-production"
        ),
        public_base_url=os.environ.get(
            "TEXT_BACK_PUBLIC_BASE_URL", "http://127.0.0.1:8000"
        ),
        db_path=os.environ.get("TEXT_BACK_DB_PATH", ":memory:"),
        wiring_mode=os.environ.get("TEXT_BACK_WIRING_MODE", WIRING_MODE_FORWARDED),
    )
