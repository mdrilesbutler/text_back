"""Telegram delivery for the durable operator alert outbox."""
from dataclasses import dataclass, field
import hashlib
import json
from typing import Callable, ClassVar
from urllib.request import Request, urlopen

from text_back.delivery import DeliveryError
from text_back.handoff import HandoffAlert


def _post(url, payload):
    request = Request(url, data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(request, timeout=15) as response:
        return json.load(response)


@dataclass
class TelegramTransport:
    token: str = field(repr=False)
    chat_id: str = field(repr=False)
    post: Callable = field(default=_post, repr=False)
    channel_name: ClassVar[str] = 'telegram'

    def deliver(self, alert: HandoffAlert) -> str:
        # Plain text prevents caller content from becoming Telegram markup.
        text = ('Recover: action needed\n'+alert.summary)
        text = text.encode('utf-16-le', errors='replace')[:7800].decode('utf-16-le', errors='ignore')
        try:
            payload = self.post('https://api.telegram.org/bot'+self.token+'/sendMessage', {
                'chat_id': self.chat_id, 'text': text,
                'link_preview_options': {'is_disabled': True},
            })
            message = payload.get('result', {})
            message_id = message.get('message_id')
            if (payload.get('ok') is not True or type(message_id) is not int
                    or message_id <= 0 or str(message.get('chat', {}).get('id')) != self.chat_id):
                raise ValueError('unverified delivery receipt')
        except Exception:
            # Telegram URLs contain the bot token. Never persist exception text,
            # HTTP response bodies, or the request URL in outbox errors/logs.
            raise DeliveryError('Telegram operator alert was not acknowledged') from None
        chat_digest = hashlib.sha256(self.chat_id.encode()).hexdigest()[:12]
        return f'telegram-{chat_digest}-{message_id}'
