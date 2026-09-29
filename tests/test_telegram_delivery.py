from datetime import datetime, timezone
from urllib.error import HTTPError

import pytest

from text_back.config import load_config
from text_back.delivery import DeliveryError, DeliveryPolicy, enqueue_handoff_alert, run_due_deliveries, transport_from_config
from text_back.handoff import HandoffAlert
from text_back.store import Store
from text_back.telegram import TelegramTransport


TOKEN = 'test-bot-token'
CHAT = '12345'
NOW = datetime(2026, 9, 19, tzinfo=timezone.utc)
ALERT = HandoffAlert('operator', '+15555550101', '+15555550102', 'test', '', {},
                     'Test alert <literal text> https://example.test/calendar/connect?token=test')


def test_telegram_sends_plain_text_without_preview_and_records_provider_receipt():
    requests = []
    def post(url, payload):
        requests.append((url, payload))
        return {'ok': True, 'result': {'message_id': 17, 'chat': {'id': int(CHAT)}}}
    transport = TelegramTransport(TOKEN, CHAT, post=post)
    store = Store()
    enqueue_handoff_alert(store=store, alert=ALERT, alert_id='test-alert', now=NOW)
    run_due_deliveries(store=store, transport=transport,
                       policy=DeliveryPolicy((1,)), now=NOW)
    assert store.get_handoff_delivery('test-alert')['status'] == 'delivered'
    assert requests[0][1]['text'].endswith(ALERT.summary)
    assert requests[0][1]['chat_id'] == CHAT
    assert 'parse_mode' not in requests[0][1]
    assert requests[0][1]['link_preview_options'] == {'is_disabled': True}
    assert TOKEN not in repr(transport)
    assert CHAT not in repr(transport)


@pytest.mark.parametrize('response', [
    {'ok': False, 'description': TOKEN},
    {'ok': True, 'result': {}},
    {'ok': True, 'result': {'message_id': 1, 'chat': {'id': 999}}},
    {'ok': True, 'result': {'message_id': True, 'chat': {'id': int(CHAT)}}},
    [],
])
def test_invalid_telegram_receipts_fail_without_leaking_secrets(response):
    transport = TelegramTransport(TOKEN, CHAT, post=lambda *_: response)
    with pytest.raises(DeliveryError) as error:
        transport.deliver(ALERT)
    assert TOKEN not in str(error.value)


def test_http_failure_uses_existing_durable_retry_without_saving_url_or_token():
    def fail(url, payload):
        raise HTTPError(url, 429, TOKEN, {}, None)
    store = Store()
    enqueue_handoff_alert(store=store, alert=ALERT, alert_id='test-alert', now=NOW)
    run_due_deliveries(store=store, transport=TelegramTransport(TOKEN, CHAT, post=fail),
                       policy=DeliveryPolicy((1,)), now=NOW)
    row = store.get_handoff_delivery('test-alert')
    assert row['status'] == 'pending'
    assert row['attempts'] == 1
    assert row['next_attempt_at'] == '2026-09-19T00:01:00+00:00'
    assert TOKEN not in row['last_error']
    assert 'api.telegram.org' not in row['last_error']


def test_telegram_limits_unicode_message_size():
    requests = []
    def post(url, payload):
        requests.append(payload)
        return {'ok': True, 'result': {'message_id': 1, 'chat': {'id': int(CHAT)}}}
    from dataclasses import replace
    TelegramTransport(TOKEN, CHAT, post=post).deliver(replace(ALERT, summary='🌳' * 5000))
    assert len(requests[0]['text'].encode('utf-16-le')) <= 7800


def test_telegram_configuration_requires_both_credentials(monkeypatch):
    monkeypatch.setenv('TEXT_BACK_HANDOFF_DELIVERY_CHANNEL', 'telegram')
    monkeypatch.delenv('TEXT_BACK_TELEGRAM_BOT_TOKEN', raising=False)
    monkeypatch.delenv('TEXT_BACK_TELEGRAM_CHAT_ID', raising=False)
    with pytest.raises(ValueError, match='TEXT_BACK_TELEGRAM'):
        transport_from_config(load_config())
    monkeypatch.setenv('TEXT_BACK_TELEGRAM_BOT_TOKEN', TOKEN)
    monkeypatch.setenv('TEXT_BACK_TELEGRAM_CHAT_ID', CHAT)
    assert isinstance(transport_from_config(load_config()), TelegramTransport)
