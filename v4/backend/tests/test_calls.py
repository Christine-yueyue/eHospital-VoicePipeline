import asyncio
import base64
import hashlib
import json
import sqlite3
import time
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

import call_transcripts as calls
import inbox
import whatsapp
from test_whatsapp import client, configured, payload, send  # noqa: F401


def document():
    # Fictional conversation using the documented Meta JSON structure.
    return {'metadata': {'audio': {'duration': 12.5}}, 'transcript': {
        'text': '[Business] Your table is booked. [Customer] Thank you.',
        'language': 'en', 'duration': 12.5, 'confidence': 0.93,
        'segments': [
            {'id': 1, 'speaker': 'Business', 'channel': 0, 'start': 0.4,
             'end': 2.7, 'text': 'Your table is booked.', 'words': []},
            {'id': 2, 'speaker': 'Customer', 'channel': 1, 'start': 3.2,
             'end': 4.8, 'text': 'Thank you.', 'words': []},
        ],
    }}


def content():
    return json.dumps(document()).encode()


def digest(data=None):
    return base64.b64encode(hashlib.sha256(content() if data is None else data).digest()).decode()


def event():
    return {'object': 'whatsapp_business_account', 'entry': [{
        'id': '222', 'changes': [{'field': 'calls', 'value': {
            'messaging_product': 'whatsapp', 'metadata': {'phone_number_id': '111'},
            'calls': [{'id': 'wacid.test', 'from': '14165550123',
                       'timestamp': str(int(time.time())), 'event': 'call_transcription_available',
                       'call_transcript': {'document': {'id': '444', 'sha256': digest(),
                           'mime_type': 'application/json',
                           'url': 'https://lookaside.fbsbx.com/expired-webhook-url'}}}],
        }}],
    }]}


def call(body):
    return body['entry'][0]['changes'][0]['value']['calls'][0]


def transport(monkeypatch, handler):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(calls.httpx, 'AsyncClient', lambda **kw: real_client(
        transport=httpx.MockTransport(handler), **kw))


def test_signed_event_through_real_worker_download_parse_translate_inbox(client, monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.headers['authorization'] == 'Bearer meta-test-token'
        if request.url.host == 'graph.facebook.com':
            assert request.url.path == '/v23.0/444'
            assert request.url.params['phone_number_id'] == '111'
            return httpx.Response(200, json={'url': 'https://lookaside.fbsbx.com/fresh',
                'mime_type': 'application/json', 'sha256': digest()})
        assert request.url.path == '/fresh'
        return httpx.Response(200, content=content())

    transport(monkeypatch, handler)
    transcribe = AsyncMock(side_effect=AssertionError('Call transcripts must not use audio ASR'))
    translate = AsyncMock(return_value='[Business] Votre table est réservée. [Customer] Merci.')
    monkeypatch.setattr(whatsapp, 'transcribe_audio', transcribe)
    monkeypatch.setattr(whatsapp, 'translate_text', translate)
    assert send(client, event()).json() == {'received': True, 'queued': 1}
    assert requests == []  # Webhook acknowledges only after durable enqueue, before provider calls.
    assert asyncio.run(whatsapp.process_once())
    response = client.get('/api/whatsapp/messages')
    row = response.json()['messages'][0]
    assert row['id'] == 'call:wacid.test'
    assert row['kind'] == 'call_transcript'
    assert row['call_id'] == 'wacid.test'
    assert row['status'] == 'completed'
    assert row['transcript'] == document()['transcript']['text']
    assert row['translation'].startswith('[Business] Votre')
    assert row['details']['language'] == 'en'
    assert row['details']['segments'][1]['speaker'] == 'Customer'
    assert row['details']['segments'][1]['start'] == 3.2
    assert row['details']['duration'] == 12.5
    assert row['sender'] == '…0123'
    assert response.headers['cache-control'] == 'no-store'
    assert 'media_sha256' not in row and 'media_id' not in row
    assert 'expired-webhook-url' not in response.text and 'meta-test-token' not in response.text
    assert len(requests) == 2
    transcribe.assert_not_awaited()
    translate.assert_awaited_once_with(row['transcript'], 'fr')
    assert send(client, event()).json()['queued'] == 0


@pytest.mark.parametrize('field,value', [
    ('event', 'connect'), ('event', 'terminate'), ('event', 'call_recording_available'),
    ('id', None), ('id', 'unrecognized'), ('timestamp', 'bad'),
    ('timestamp', '1'), ('timestamp', str(int(time.time()) + 10000)),
    ('call_transcript', None), ('call_transcript', {'document': None}),
])
def test_irrelevant_or_invalid_calls_ignored(client, field, value):
    body = event()
    call(body)[field] = value
    assert send(client, body).json()['queued'] == 0


@pytest.mark.parametrize('field,value', [
    ('id', '../secrets'), ('id', 444), ('sha256', ''), ('sha256', 'invalid'),
    ('mime_type', 'audio/ogg'),
])
def test_invalid_document_references_not_queued(client, field, value):
    body = event()
    call(body)['call_transcript']['document'][field] = value
    assert send(client, body).json()['queued'] == 0


def test_call_signature_tenant_sender_and_bsuid_filters(client, monkeypatch):
    body = event()
    assert client.post('/webhooks/whatsapp', json=body).status_code == 403
    body['entry'][0]['id'] = '999'
    assert send(client, body).json()['queued'] == 0
    body['entry'][0]['id'] = '222'
    body['entry'][0]['changes'][0]['value']['metadata']['phone_number_id'] = '999'
    assert send(client, body).json()['queued'] == 0
    body = event()
    monkeypatch.setenv('WHATSAPP_ALLOWED_SENDERS', '19995550123')
    assert send(client, body).json()['queued'] == 0
    call(body).pop('from')
    call(body)['from_user_id'] = 'US.1234567890'
    assert send(client, body).json()['queued'] == 0
    monkeypatch.setenv('WHATSAPP_ALLOWED_SENDERS', 'US.1234567890')
    assert send(client, body).json()['queued'] == 1


def test_mixed_batch_dedupes_calls_and_voice_messages_atomically(client, monkeypatch):
    body = event()
    body['entry'][0]['changes'] += payload()['entry'][0]['changes']
    monkeypatch.setattr(inbox, 'MAX_PENDING', 1)
    assert send(client, body).status_code == 503
    assert inbox.list_messages() == []
    monkeypatch.setattr(inbox, 'MAX_PENDING', 2)
    assert send(client, body).json()['queued'] == 2
    call(body)['call_transcript']['document']['id'] = '555'
    assert send(client, body).json()['queued'] == 0


def test_parser_preserves_text_and_can_render_segments():
    parsed, details = calls.parse_transcript(content())
    assert parsed == document()['transcript']['text']
    assert len(details['segments']) == 2
    body = document()
    body['transcript']['text'] = ''
    body['transcript']['segments'][0].pop('speaker')
    parsed, _ = calls.parse_transcript(json.dumps(body).encode())
    assert parsed == '[Business] Your table is booked.\n[Customer] Thank you.'
    assert calls.parse_transcript(b'{"transcript":{"text":"Bonjour"}}')[0] == 'Bonjour'


@pytest.mark.parametrize('data', [b'not-json', b'[]', b'{}', b'{"transcript":null}',
    b'{"transcript":{"text":45}}', b'{"transcript":{"text":""}}',
    b'{"transcript":{"text":"hello","segments":null}}',
    b'{"transcript":{"text":"hello","confidence":NaN}}',
    b'{"transcript":{"text":"hello","duration":true}}',
])
def test_invalid_or_empty_documents_have_clear_failure(data):
    with pytest.raises(HTTPException) as exc:
        calls.parse_transcript(data)
    assert exc.value.status_code == 422


def test_parser_rejects_bad_segments_and_oversized_transcripts(monkeypatch):
    body = document()
    body['transcript']['segments'][0]['end'] = 0
    with pytest.raises(HTTPException):
        calls.parse_transcript(json.dumps(body).encode())
    monkeypatch.setattr(calls, 'MAX_TRANSCRIPT_CHARS', 5)
    with pytest.raises(HTTPException) as exc:
        calls.parse_transcript(content())
    assert exc.value.status_code == 413


@pytest.mark.parametrize('url', ['http://lookaside.fbsbx.com/a', 'https://evil.example/a',
    'https://lookaside.fbsbx.com.evil.example/a', 'https://lookaside.fbsbx.com:444/a',
    'https://user:pass@lookaside.fbsbx.com/a', 'https://lookaside.fbsbx.com:bad/a'])
def test_download_only_sends_bearer_to_trusted_hosts(configured, monkeypatch, url):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={'url': url, 'mime_type': 'application/json'})
    transport(monkeypatch, handler)
    with pytest.raises(HTTPException):
        asyncio.run(calls.download_transcript('444', digest()))
    assert len(requests) == 1


@pytest.mark.parametrize('mode', ['hash', 'metadata_hash', 'mime', 'size', 'stream_size', 'empty', 'redirect'])
def test_download_integrity_mime_size_and_redirects(configured, monkeypatch, mode):
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.host == 'graph.facebook.com':
            metadata = {'url': 'https://lookaside.fbsbx.com/fresh', 'mime_type': 'application/json'}
            if mode == 'mime':
                metadata['mime_type'] = 'audio/ogg'
            if mode == 'metadata_hash':
                metadata['sha256'] = digest(b'wrong')
            if mode == 'size':
                metadata['file_size'] = calls.MAX_DOCUMENT_BYTES + 1
            return httpx.Response(200, json=metadata)
        if mode == 'redirect':
            return httpx.Response(302, headers={'Location': 'https://evil.example/a'})
        return httpx.Response(200, content=b'' if mode == 'empty' else content())
    transport(monkeypatch, handler)
    if mode == 'stream_size':
        monkeypatch.setattr(calls, 'MAX_DOCUMENT_BYTES', 5)
    with pytest.raises((HTTPException, httpx.HTTPStatusError)):
        asyncio.run(calls.download_transcript('444', digest(b'wrong') if mode == 'hash' else digest()))
    assert len(requests) <= 2


def test_translation_retry_keeps_original_and_metadata(client, monkeypatch):
    download = AsyncMock(return_value=content())
    translate = AsyncMock(side_effect=HTTPException(400, 'Translation failed'))
    monkeypatch.setattr(whatsapp, 'download_transcript', download)
    monkeypatch.setattr(whatsapp, 'translate_text', translate)
    send(client, event())
    asyncio.run(whatsapp.process_once())
    row = inbox.list_messages()[0]
    assert row['status'] == 'partial'
    assert row['details']['language'] == 'en'
    assert row['transcript'] == document()['transcript']['text']
    assert client.post('/api/whatsapp/retry', json={'id': row['id']}).status_code == 200
    translate.side_effect = None
    translate.return_value = 'Traduit'
    asyncio.run(whatsapp.process_once())
    assert inbox.list_messages()[0]['status'] == 'completed'
    download.assert_awaited_once()


@pytest.mark.parametrize('status,retry', [(401, False), (403, False), (404, False), (429, True), (500, True)])
def test_meta_failures_visible_and_only_transient_errors_auto_retry(client, monkeypatch, status, retry):
    request = httpx.Request('GET', 'https://graph.facebook.com/media')
    error = httpx.HTTPStatusError('private provider error', request=request,
                                response=httpx.Response(status, request=request))
    monkeypatch.setattr(whatsapp, 'download_transcript', AsyncMock(side_effect=error))
    send(client, event())
    asyncio.run(whatsapp.process_once())
    row = inbox.list_messages()[0]
    assert row['status'] == ('queued' if retry else 'failed')
    assert 'private provider error' not in row['error']


def test_call_checkpoint_survives_restart_and_stale_worker_cannot_overwrite(client):
    send(client, event())
    first = inbox.claim()
    text, details = calls.parse_transcript(content())
    assert inbox.checkpoint(first, 'translating', transcript=text, details=details)
    with inbox.database() as db:
        db.execute('UPDATE messages SET available=0')
        db.commit()
    second = inbox.claim()
    assert second['transcript'] == text
    assert json.loads(second['details']) == details
    inbox.finish(first, status='completed', transcript='stale')
    assert inbox.list_messages()[0]['status'] == 'processing'
    assert not inbox.checkpoint(first, 'translating', transcript='stale')
    inbox.finish(second, status='completed', transcript=text, translation='Traduit')
    assert inbox.list_messages()[0]['translation'] == 'Traduit'


@pytest.mark.parametrize('method', ['delete', 'expire'])
def test_call_deletion_and_retention_erase_segments_and_block_resurrection(client, method):
    send(client, event())
    message = inbox.claim()
    text, details = calls.parse_transcript(content())
    inbox.checkpoint(message, 'translating', transcript=text, details=details)
    if method == 'delete':
        client.post('/api/whatsapp/delete', json={'id': message['id']})
    else:
        with inbox.database() as db:
            db.execute('UPDATE messages SET created=?', (time.time() - 90000,))
            db.commit()
        inbox.expire_results()
    assert not inbox.checkpoint(message, 'translating', transcript=text, details=details)
    inbox.finish(message, status='completed', transcript=text)
    assert inbox.list_messages() == []
    assert send(client, event()).json()['queued'] == 0
    with inbox.database() as db:
        row = db.execute('SELECT * FROM messages').fetchone()
        assert row['details'] == '{}'
        assert row['transcript'] == row['media_sha256'] == row['call_id'] == ''


def test_long_translation_requests_are_bounded_without_losing_content():
    text = ('[Business] A sentence.\n[Customer] Another sentence.\n' * 1000).strip()
    chunks = calls.translation_chunks(text)
    assert len(chunks) > 1
    assert ''.join(chunks) == text
    assert all(0 < len(c) <= 6000 for c in chunks)


def test_schema_upgrade_does_not_lose_old_messages(configured):
    db = sqlite3.connect(configured['INBOX_DB_PATH'])
    db.execute('''CREATE TABLE messages (id TEXT PRIMARY KEY, media_id TEXT NOT NULL,
        sender TEXT NOT NULL, target TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0,
        available REAL NOT NULL DEFAULT 0, transcript TEXT NOT NULL DEFAULT '',
        translation TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '')''')
    db.execute('INSERT INTO messages (id,media_id,sender,target,created,updated) VALUES (?,?,?,?,?,?)',
               ('old', '333', '…0123', 'fr', time.time(), time.time()))
    db.commit()
    db.close()
    assert inbox.list_messages()[0]['kind'] == 'voice_message'
    assert inbox.list_messages()[0]['id'] == 'old'
