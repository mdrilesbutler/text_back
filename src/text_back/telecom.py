from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Protocol

import httpx


class Telecom(Protocol):
    provider_name: str

    def send_sms(self, *, to: str, body: str, from_number: str, kind: str) -> str:
        """Send an SMS and return the provider's stable message identifier."""


class TelecomError(RuntimeError):
    """A redacted provider failure safe to surface without credentials/content."""


class RetryableSmsError(TelecomError):
    """Provider definitely did not accept; a bounded retry is safe."""


class AmbiguousSmsError(TelecomError):
    """Provider may have accepted; reconcile instead of resending."""


@dataclass
class OutboundSms:
    to: str
    body: str
    from_number: str
    kind: str


@dataclass
class FakeTelecom:
    provider_name: ClassVar[str] = "stub"
    outbound: list[OutboundSms] = field(default_factory=list)

    def send_sms(self, *, to: str, body: str, from_number: str, kind: str) -> str:
        self.outbound.append(
            OutboundSms(to=to, body=body, from_number=from_number, kind=kind)
        )
        return f"SM-{len(self.outbound):04d}"


@dataclass
class SignalWireTelecom:
    """SignalWire Compatibility REST adapter for outbound SMS.

    This direct REST path is expected to work under SignalWire's Platform Free
    Trial because it does not use the cXML/SWML messaging integrations the trial
    excludes; that reading is unverified until the first live send succeeds.
    See docs/SIGNALWIRE-INTEGRATION.md.
    """

    provider_name: ClassVar[str] = "signalwire"
    space_url: str
    project_id: str
    api_token: str = field(repr=False)
    allowed_from_number: str
    client: httpx.Client | None = None
    timeout_seconds: float = 10.0
    allowed_to_numbers: tuple[str, ...] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.space_url = self.space_url.rstrip("/")
        parsed = httpx.URL(self.space_url)
        if parsed.scheme != "https" or not parsed.host:
            raise ValueError("SignalWire Space URL must be a valid HTTPS URL")
        if not self.project_id:
            raise ValueError("SignalWire Project ID is required")
        if not self.api_token:
            raise ValueError("SignalWire API token is required")
        if not self.allowed_from_number.startswith("+"):
            raise ValueError("SignalWire sender number must use E.164 format")

    @property
    def messages_url(self) -> str:
        return (
            f"{self.space_url}/api/laml/2010-04-01/Accounts/"
            f"{self.project_id}/Messages"
        )

    def send_sms(self, *, to: str, body: str, from_number: str, kind: str) -> str:
        return self.send_sms_with_callback(to=to, body=body, from_number=from_number, kind=kind)

    def send_sms_with_callback(self, *, to, body, from_number, kind, callback_url=None):
        if from_number != self.allowed_from_number:
            raise TelecomError("SMS sender is not the configured SignalWire number")
        if self.allowed_to_numbers is not None and to not in self.allowed_to_numbers:
            raise TelecomError("SMS recipient is not an approved pilot recipient")
        request_client = self.client or httpx.Client()
        close_client = self.client is None
        try:
            response = request_client.post(
                self.messages_url,
                auth=httpx.BasicAuth(self.project_id, self.api_token),
                data={"To": to, "From": from_number, "Body": body, **({"StatusCallback": callback_url} if callback_url else {})},
                timeout=self.timeout_seconds,
            )
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise RetryableSmsError(f"SignalWire connection failed ({type(exc).__name__})") from None
        except httpx.RequestError as exc:
            raise AmbiguousSmsError(
                f"SignalWire SMS request failed ({type(exc).__name__})"
            ) from None
        finally:
            if close_client:
                request_client.close()

        if response.status_code == 429:
            raise RetryableSmsError("SignalWire SMS rate limited")
        if response.status_code >= 500:
            raise AmbiguousSmsError("SignalWire SMS acceptance unknown")
        if not response.is_success:
            raise TelecomError(
                f"SignalWire SMS request returned HTTP {response.status_code}"
            )
        try:
            payload = response.json()
        except ValueError:
            raise AmbiguousSmsError("SignalWire SMS response was not valid JSON") from None
        message_id = payload.get("sid")
        if not isinstance(message_id, str) or not message_id:
            raise AmbiguousSmsError("SignalWire SMS response did not include a message ID")
        return message_id
