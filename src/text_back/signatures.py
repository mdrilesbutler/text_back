from __future__ import annotations

import base64
import hashlib
import hmac


class SignatureError(Exception):
    pass


def verify_twilio_compat(
    url: str,
    params: dict[str, str],
    signature: str | None,
    secret: str,
) -> bool:
    if not secret:
        raise SignatureError("webhook secret is required; failing closed")
    if not signature:
        raise SignatureError("missing webhook signature")
    data = url + "".join(f"{key}{value}" for key, value in sorted(params.items()))
    digest = hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("ascii")
    if not hmac.compare_digest(expected, signature):
        raise SignatureError("invalid webhook signature")
    return True
