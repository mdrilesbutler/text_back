from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OutboundSms:
    to: str
    body: str
    from_number: str
    kind: str


@dataclass
class FakeTelecom:
    outbound: list[OutboundSms] = field(default_factory=list)

    def send_sms(self, *, to: str, body: str, from_number: str, kind: str) -> str:
        self.outbound.append(
            OutboundSms(to=to, body=body, from_number=from_number, kind=kind)
        )
        return f"SM-{len(self.outbound):04d}"
