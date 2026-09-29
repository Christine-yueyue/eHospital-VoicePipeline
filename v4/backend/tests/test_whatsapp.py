import asyncio
import hashlib
import hmac
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app as backend
import inbox
import whatsapp


@pytest.fixture
def configured(monkeypatch, tmp_path):
    values = {
        'APP_ACCESS_TOKEN': 'app-test-token', 'OPENAI_API_KEY': 'not-a-real-openai-key',
        'WHATSAPP_ACCESS_TOKEN': 'meta-test-token', 'WHATSAPP_APP_SECRET': 'meta-secret',
        'WHATSAPP_VERIFY_TOKEN': 'verify-secret', 'WHATSAPP_PHONE_NUMBER_ID': '111',
        'WHATSAPP_WABA_ID': '222', 'WHATSAPP_GRAPH_VERSION': 'v23.0',
        'WHATSAPP_TARGET_LANGUAGE': 'fr', 'WHATSAPP_ALLOWED_SENDERS': '',
        'INBOX_DB_PATH': str(tmp_path / 'inbox.sqlite3'),
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    async def idle_worker():
        await asyncio.Event().wait()
    monkeypatch.setattr(whatsapp, 'worker', idle_worker)
    return values


@pytest.fixture
def client(configured):
    with TestClient(backend.app, headers={'Authorization': 'Bearer app-test-token'}) as client:
        yield client


def payload(message_id='wamid.test', media_id='333', phone='111', waba='222'):
    return {'object': 'whatsapp_business_account', 'entry': [{
        'id': waba, 'changes': [{'field': 'messages', 'value': {
            'metadata': {'phone_number_id': phone},
            'messages': [{'id': message_id, 'type': 'audio', 'from': '14165550123',
                          'timestamp': str(int(time.time())), 'audio': {'id': media_id}}],
        }}],
    }]}


def send(client, body):
    raw = json.dumps(body).encode()
    signature = 'sha256=' + hmac.new(b'meta-secret', raw, hashlib.sha256).hexdigest()
    return client.post('/webhooks/whatsapp', content=raw,
        headers={'Content-Type': 'application/json', 'X-Hub-Signature-256': signature})


def test_verify_challenge_and_reject_wrong_token(client):
    params = {'hub.mode': 'subscribe', 'hub.verify_token': 'verify-secret', 'hub.challenge': '12345'}
    response = client.get('/webhooks/whatsapp', params=params)
    assert response.status_code == 200
    assert response.text == '12345'
    params['hub.verify_token'] = 'wrong'
    assert client.get('/webhooks/whatsapp', params=params).status_code == 403


def test_webhook_has_independent_signature_auth(configured):
    with TestClient(backend.app) as client:
        assert client.post('/webhooks/whatsapp', json=payload()).status_code == 403
        assert send(client, payload()).json()['queued'] == 1
        assert client.get('/api/whatsapp/messages').status_code == 401
        assert client.get('/api/config').status_code == 401
        assert client.post('/api/transcribe').status_code == 401
        assert client.get('/health').status_code == 200


def test_unconfigured_app_fails_closed(client, monkeypatch):
    monkeypatch.delenv('APP_ACCESS_TOKEN')
    assert client.get('/api/config').status_code == 503


def test_unsigned_and_tampered_body_never_enqueued(client):
    response = client.post('/webhooks/whatsapp', json=payload(),
        headers={'X-Hub-Signature-256': 'sha256=wrong'})
    assert response.status_code == 403
    assert inbox.list_messages() == []


def test_signature_checked_before_json(client):
    assert client.post('/webhooks/whatsapp', content=b'not json').status_code == 403
    assert send(client, []).status_code == 400


def test_webhook_body_size_is_bounded(client, monkeypatch):
    monkeypatch.setattr(whatsapp, 'MAX_WEBHOOK_BYTES', 10)
    assert send(client, payload()).status_code == 413


def test_durable_deduplication_and_tenant_filter(client, monkeypatch):
    assert send(client, payload()).json()['queued'] == 1
    assert send(client, payload()).json()['queued'] == 0
    assert send(client, payload('other-phone', phone='999')).json()['queued'] == 0
    assert send(client, payload('other-waba', waba='999')).json()['queued'] == 0
    monkeypatch.setenv('WHATSAPP_ALLOWED_SENDERS', '19995550123')
    assert send(client, payload('other-sender')).json()['queued'] == 0
    records = client.get('/api/whatsapp/messages').json()['messages']
    assert len(records) == 1
    assert records[0]['sender'] == '…0123'
    assert 'media_id' not in records[0]
    # Opening a fresh DB connection sees the committed job.
    with inbox.database() as db:
        assert db.execute('SELECT COUNT(*) FROM messages').fetchone()[0] == 1


def test_status_and_non_audio_events_are_acknowledged(client):
    data = payload()
    value = data['entry'][0]['changes'][0]['value']
    value.pop('messages')
    value['statuses'] = [{'id': 'status', 'status': 'delivered'}]
    assert send(client, data).json()['queued'] == 0
    value['messages'] = [{'id': 'text', 'type': 'text'}]
    assert send(client, data).json()['queued'] == 0


def test_queue_limit_rolls_back_webhook_batch(client, monkeypatch):
    monkeypatch.setattr(inbox, 'MAX_PENDING', 1)
    data = payload()
    messages = data['entry'][0]['changes'][0]['value']['messages']
    messages.append({**messages[0], 'id': 'second'})
    assert send(client, data).status_code == 503
    assert inbox.list_messages() == []


@pytest.fixture
def processing(monkeypatch):
    paths = []

    async def download(_id, directory):
        path = directory / 'note.ogg'
        path.write_bytes(b'mocked audio')
        paths.append(path)
        return path
    monkeypatch.setattr(whatsapp, 'download_audio', download)
    transcription = AsyncMock(return_value='Friday at three.')
    translation = AsyncMock(return_value='Vendredi à quinze heures.')
    monkeypatch.setattr(whatsapp, 'transcribe_audio', transcription)
    monkeypatch.setattr(whatsapp, 'translate_text', translation)
    return paths, transcription, translation


def test_worker_processes_queued_audio_and_cleans_temporary_file(client, processing):
    send(client, payload())
    assert asyncio.run(whatsapp.process_once()) is True
    row = inbox.list_messages()[0]
    assert row['status'] == 'completed'
    assert row['transcript'] == 'Friday at three.'
    assert row['translation'] == 'Vendredi à quinze heures.'
    assert not processing[0][0].exists()
    assert asyncio.run(whatsapp.process_once()) is False


def test_retry_reuses_successful_transcript(client, processing):
    processing[2].side_effect = HTTPException(429, 'Translation quota reached.')
    send(client, payload())
    asyncio.run(whatsapp.process_once())
    assert inbox.list_messages()[0]['status'] == 'queued'
    assert inbox.list_messages()[0]['transcript'] == 'Friday at three.'
    with inbox.database() as db:
        db.execute('UPDATE messages SET available=0')
        db.commit()
    processing[2].side_effect = None
    asyncio.run(whatsapp.process_once())
    assert inbox.list_messages()[0]['status'] == 'completed'
    processing[1].assert_awaited_once()


def test_failed_jobs_are_visible_and_can_retry(client, processing):
    processing[1].side_effect = HTTPException(400, 'Invalid audio')
    send(client, payload())
    asyncio.run(whatsapp.process_once())
    assert inbox.list_messages()[0]['status'] == 'failed'
    assert not processing[0][0].exists()
    response = client.post('/api/whatsapp/retry', json={'id': 'wamid.test'})
    assert response.status_code == 200
    processing[1].side_effect = None
    asyncio.run(whatsapp.process_once())
    assert inbox.list_messages()[0]['status'] == 'completed'


def test_deleted_result_not_resurrected_by_worker_or_meta(client):
    send(client, payload())
    message = inbox.claim()
    client.post('/api/whatsapp/delete', json={'id': 'wamid.test'})
    inbox.finish(message, status='completed', transcript='must not return')
    assert inbox.list_messages() == []
    assert send(client, payload()).json()['queued'] == 0
    assert client.post('/api/whatsapp/retry', json={'id': 'wamid.test'}).status_code == 409


def test_stale_lease_recovered_after_restart(client):
    send(client, payload())
    first = inbox.claim()
    assert inbox.claim() is None
    with inbox.database() as db:
        db.execute('UPDATE messages SET available=0')
        db.commit()
    second = inbox.claim()
    assert first['id'] == second['id']
    assert second['attempts'] == 2


def test_retention_removes_content_but_keeps_dedupe_tombstone(client):
    send(client, payload())
    with inbox.database() as db:
        db.execute('UPDATE messages SET created=?,transcript=?', (time.time() - 90000, 'private transcript'))
        db.commit()
    assert inbox.list_messages() == []
    with inbox.database() as db:
        row = db.execute('SELECT * FROM messages').fetchone()
        assert row['media_id'] == row['transcript'] == row['sender'] == ''
    assert send(client, payload()).json()['queued'] == 0


def test_old_webhook_is_ignored(client):
    data = payload()
    data['entry'][0]['changes'][0]['value']['messages'][0]['timestamp'] = str(int(time.time()) - 90000)
    assert send(client, data).json()['queued'] == 0


def test_websocket_rejects_wrong_app_auth_before_provider(configured):
    with TestClient(backend.app) as client:
        with client.websocket_connect('/api/live') as ws:
            ws.send_json({'type': 'auth', 'token': 'wrong'})
            with pytest.raises(WebSocketDisconnect) as error:
                ws.receive_json()
            assert error.value.code == 1008


def test_cors_allows_app_auth_header(client):
    response = client.options('/api/config', headers={
        'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'authorization'})
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'


def test_no_provider_secrets_in_config(client, configured):
    response = client.get('/api/config')
    for key in ('OPENAI_API_KEY', 'WHATSAPP_APP_SECRET', 'WHATSAPP_ACCESS_TOKEN', 'APP_ACCESS_TOKEN'):
        assert configured[key] not in response.text
    assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('url', ['http://lookaside.fbsbx.com/a', 'https://evil.example/a',
    'https://lookaside.fbsbx.com.evil.example/a', 'https://lookaside.fbsbx.com:444/a'])
def test_download_rejects_untrusted_urls(configured, monkeypatch, tmp_path, url):
    requests = []
    real_client = httpx.AsyncClient

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={'url': url, 'mime_type': 'audio/ogg'})
    monkeypatch.setattr(whatsapp.httpx, 'AsyncClient', lambda **kw: real_client(
        transport=httpx.MockTransport(handler), **kw))
    with pytest.raises(HTTPException):
        asyncio.run(whatsapp.download_audio('333', tmp_path))
    assert len(requests) == 1


def test_download_auth_integrity_and_stream_size(configured, monkeypatch, tmp_path):
    data = b'some audio'
    real_client = httpx.AsyncClient

    def handler(request):
        assert request.headers['authorization'] == 'Bearer meta-test-token'
        if request.url.host == 'graph.facebook.com':
            assert request.url.params['phone_number_id'] == '111'
            return httpx.Response(200, json={'url': 'https://lookaside.fbsbx.com/audio',
                'mime_type': 'audio/ogg; codecs=opus', 'sha256': hashlib.sha256(data).hexdigest()})
        return httpx.Response(200, content=data)
    monkeypatch.setattr(whatsapp.httpx, 'AsyncClient', lambda **kw: real_client(
        transport=httpx.MockTransport(handler), **kw))
    path = asyncio.run(whatsapp.download_audio('333', tmp_path))
    assert path.read_bytes() == data
    monkeypatch.setattr(whatsapp, 'MAX_MEDIA_BYTES', 3)
    with pytest.raises(HTTPException) as error:
        asyncio.run(whatsapp.download_audio('333', tmp_path))
    assert error.value.status_code == 413
