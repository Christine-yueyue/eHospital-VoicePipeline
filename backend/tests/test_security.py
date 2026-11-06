"""Adversarial regressions for the API boundary and WebSocket authentication."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse
from starlette.websockets import WebSocketDisconnect

import app as backend
import security
from auth import MAX_AUTH_FRAME_BYTES
from security import APIProtectionMiddleware


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv('APP_ACCESS_TOKEN', 'security-test-token')
    monkeypatch.setenv('VOICE_FEEDBACK_DB_PATH', str(tmp_path / 'feedback.db'))
    monkeypatch.setenv('VOICE_FEEDBACK_AUDIO_DIR', str(tmp_path / 'audio'))
    monkeypatch.setenv('INBOX_DB_PATH', str(tmp_path / 'inbox.db'))
    return tmp_path


def scope(headers=(), path='/api/whatsapp/assistant/message'):
    return {'type': 'http', 'method': 'POST', 'path': path,
            'headers': list(headers), 'query_string': b''}


AUTH = (b'authorization', b'Bearer security-test-token')


async def invoke(middleware, request_scope, chunks=()):
    sent = []
    queue = list(chunks)
    reads = 0

    async def receive():
        nonlocal reads
        reads += 1
        if queue:
            return queue.pop(0)
        raise AssertionError('The application read an unexpected body chunk.')

    async def send(message):
        sent.append(message)

    await middleware(request_scope, receive, send)
    return sent, reads


def test_every_http_api_route_requires_authentication(isolated):
    with TestClient(backend.app) as client:
        routes = [
            (path, set(methods))
            for path, path_item in backend.app.openapi()['paths'].items()
            if path.startswith('/api/')
            for methods in [path_item.keys()]
        ]
        assert len(routes) >= 10
        for path, methods in routes:
            for method in methods - {'head', 'options'}:
                response = client.request(method, path.replace('{task_id}', 'missing'))
                assert response.status_code == 401, (method, path)
                assert response.headers['cache-control'] == 'no-store'
                assert response.headers['www-authenticate'] == 'Bearer'
        assert client.options('/api/config').status_code == 401


@pytest.mark.parametrize('headers,status', [
    ([], 401), ([AUTH, AUTH], 401),
    ([AUTH, (b'content-length', b'999999999')], 413),
    ([AUTH, (b'content-length', b'-1')], 400),
    ([AUTH, (b'content-length', b'1'), (b'content-length', b'1')], 400),
    ([AUTH, (b'content-length', b'1'), (b'transfer-encoding', b'chunked')], 400),
    ([AUTH, (b'content-encoding', b'gzip')], 415),
])
def test_rejects_before_reading_or_parsing(isolated, headers, status):
    inner = AsyncMock()
    messages, reads = asyncio.run(invoke(APIProtectionMiddleware(inner, 20_000_000), scope(headers)))
    assert messages[0]['status'] == status
    assert dict(messages[0]['headers'])[b'cache-control'] == b'no-store'
    assert reads == 0
    inner.assert_not_awaited()


@pytest.mark.parametrize('declared', [None, b'1'])
def test_stream_limit_does_not_trust_content_length(isolated, monkeypatch, declared):
    monkeypatch.setattr(security, 'JSON_BODY_BYTES', 4)
    inner = AsyncMock()
    middleware = APIProtectionMiddleware(inner, 20_000_000)
    headers = [AUTH] + ([(b'content-length', declared)] if declared else [])
    messages, reads = asyncio.run(invoke(middleware, scope(headers), [
        {'type': 'http.request', 'body': b'1234', 'more_body': True},
        {'type': 'http.request', 'body': b'5', 'more_body': False},
    ]))
    assert messages[0]['status'] == 413
    assert reads == 2
    assert middleware.active == 0
    inner.assert_not_awaited()


def test_large_multipart_rejected_before_parser_and_provider(isolated, monkeypatch):
    monkeypatch.setattr(security, 'MULTIPART_OVERHEAD_BYTES', 0)
    provider = AsyncMock()
    middleware = APIProtectionMiddleware(provider, 4)
    messages, _ = asyncio.run(invoke(middleware, scope([AUTH], '/api/transcribe'), [
        {'type': 'http.request', 'body': b'12345'},
    ]))
    assert messages[0]['status'] == 413
    provider.assert_not_awaited()


def test_exact_limit_replayed_without_corruption(isolated, monkeypatch):
    monkeypatch.setattr(security, 'JSON_BODY_BYTES', 4)

    async def inner(request_scope, receive, send):
        assert await receive() == {'type': 'http.request', 'body': b'1234', 'more_body': False}
        await JSONResponse({'ok': True})(request_scope, receive, send)

    middleware = APIProtectionMiddleware(inner, 100)
    messages, _ = asyncio.run(invoke(middleware, scope([AUTH, (b'content-length', b'4')]), [
        {'type': 'http.request', 'body': b'12', 'more_body': True},
        {'type': 'http.request', 'body': b'34'},
    ]))
    assert messages[0]['status'] == 200
    assert middleware.active == 0


def test_length_mismatch_and_disconnect_release_slot(isolated):
    middleware = APIProtectionMiddleware(AsyncMock(), 100)
    messages, _ = asyncio.run(invoke(middleware, scope([AUTH, (b'content-length', b'4')]), [
        {'type': 'http.request', 'body': b'1'},
    ]))
    assert messages[0]['status'] == 400
    assert middleware.active == 0
    messages, _ = asyncio.run(invoke(middleware, scope([AUTH]), [{'type': 'http.disconnect'}]))
    assert messages == []
    assert middleware.active == 0


def test_slow_upload_times_out_and_releases_slot(isolated, monkeypatch):
    monkeypatch.setattr(security, 'BODY_READ_SECONDS', 0.001)
    middleware = APIProtectionMiddleware(AsyncMock(), 100)
    sent = []

    async def run():
        async def stalled():
            await asyncio.Event().wait()

        async def send(message):
            sent.append(message)

        await middleware(scope([AUTH]), stalled, send)

    asyncio.run(run())
    assert sent[0]['status'] == 408
    assert middleware.active == 0


def test_concurrent_admission_and_failure_cleanup(isolated, monkeypatch):
    monkeypatch.setattr(security, 'MAX_ACTIVE_REQUESTS', 1)

    async def run():
        entered, finish = asyncio.Event(), asyncio.Event()

        async def inner(*args):
            entered.set()
            await finish.wait()
            raise RuntimeError('Simulated route failure')

        middleware = APIProtectionMiddleware(inner, 100)
        first = asyncio.create_task(invoke(middleware, scope([AUTH]), [{'type': 'http.request'}]))
        await entered.wait()
        messages, reads = await invoke(middleware, scope([AUTH]))
        assert messages[0]['status'] == 429
        assert dict(messages[0]['headers'])[b'retry-after'] == b'5'
        assert reads == 0
        finish.set()
        with pytest.raises(RuntimeError):
            await first
        assert middleware.active == 0

    asyncio.run(run())


@pytest.mark.parametrize('frame', [
    b'binary', 'not JSON', '[]',
    json.dumps({'type': 'auth', 'token': 'security-test-token', 'padding': 'x' * MAX_AUTH_FRAME_BYTES}),
])
def test_websocket_auth_rejects_bad_frames_without_provider(isolated, monkeypatch, frame):
    provider = AsyncMock()
    monkeypatch.setattr('live.connect', provider)
    with TestClient(backend.app) as client:
        with client.websocket_connect('/api/live') as ws:
            ws.send_bytes(frame) if isinstance(frame, bytes) else ws.send_text(frame)
            with pytest.raises(WebSocketDisconnect) as error:
                ws.receive_json()
            assert error.value.code == 1008
    provider.assert_not_called()
