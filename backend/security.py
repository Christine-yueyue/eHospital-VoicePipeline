"""Bound authenticated API input before FastAPI parses multipart or JSON bodies."""

import asyncio
from tempfile import SpooledTemporaryFile
from threading import Lock

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse

from auth import app_token, authorized

JSON_BODY_BYTES = 64 * 1024
MULTIPART_OVERHEAD_BYTES = 64 * 1024
BODY_READ_SECONDS = 30
MAX_ACTIVE_REQUESTS = 8


class APIProtectionMiddleware:
    """Single-process admission control; edge rate limits are still required.

    Authenticate before reading. Spool bounded bodies before the multipart
    parser runs, so rejected uploads cannot leave parser-created temp files.
    Each admitted request holds its slot until processing and cleanup finish.
    """

    def __init__(self, app, upload_bytes: int):
        self.app = app
        self.upload_bytes = upload_bytes
        self.active = 0
        self.lock = Lock()

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        if scope['type'] != 'http' or not (path == '/api' or path.startswith('/api/')):
            await self.app(scope, receive, send)
            return

        async def private_send(message):
            if message['type'] == 'http.response.start':
                headers = MutableHeaders(scope=message)
                headers['Cache-Control'] = 'no-store'
                headers['X-Content-Type-Options'] = 'nosniff'
                headers['Referrer-Policy'] = 'no-referrer'
            await send(message)

        async def reject(status, error, headers=None):
            await JSONResponse({'success': False, 'error': error}, status_code=status,
                               headers=headers)(scope, receive, private_send)

        headers = Headers(scope=scope)
        if not app_token():
            await reject(503, 'Set APP_ACCESS_TOKEN in the backend .env file.')
            return
        if len(headers.getlist('authorization')) != 1 or not authorized(headers.get('authorization', '')):
            await reject(401, 'Enter the correct app access token in Connection settings.',
                         {'WWW-Authenticate': 'Bearer'})
            return

        if path.rstrip('/') == '/api/transcribe':
            limit = self.upload_bytes + MULTIPART_OVERHEAD_BYTES
        elif path.rstrip('/') == '/api/assistant/transcribe':
            limit = min(self.upload_bytes, 10_000_000) + MULTIPART_OVERHEAD_BYTES
        else:
            limit = JSON_BODY_BYTES
        lengths = headers.getlist('content-length')
        declared = None
        if lengths:
            raw = lengths[0]
            if (len(lengths) != 1 or not raw.isascii() or not raw.isdecimal()
                    or len(raw) > 20 or headers.get('transfer-encoding')):
                await reject(400, 'Invalid request length.')
                return
            declared = int(raw)
            if declared > limit:
                await reject(413, 'Request body is too large.')
                return
        if headers.get('content-encoding', 'identity').lower() != 'identity':
            await reject(415, 'Compressed request bodies are not supported.')
            return

        with self.lock:
            admitted = self.active < MAX_ACTIVE_REQUESTS
            if admitted:
                self.active += 1
        if not admitted:
            await reject(429, 'The server is busy. Try again shortly.', {'Retry-After': '5'})
            return
        try:
            with SpooledTemporaryFile(max_size=JSON_BODY_BYTES, mode='w+b') as body:
                size = 0
                try:
                    async with asyncio.timeout(BODY_READ_SECONDS):
                        while True:
                            message = await receive()
                            if message['type'] == 'http.disconnect':
                                return
                            chunk = message.get('body', b'')
                            size += len(chunk)
                            if size > limit:
                                await reject(413, 'Request body is too large.')
                                return
                            body.write(chunk)
                            if not message.get('more_body', False):
                                break
                except TimeoutError:
                    await reject(408, 'Request body timed out.')
                    return
                if declared is not None and declared != size:
                    await reject(400, 'Request length does not match its body.')
                    return
                body.seek(0)
                remaining = size
                delivered = False

                async def replay():
                    nonlocal remaining, delivered
                    if delivered:
                        return await receive()
                    chunk = body.read(64 * 1024)
                    remaining -= len(chunk)
                    delivered = remaining == 0
                    return {'type': 'http.request', 'body': chunk, 'more_body': not delivered}

                await self.app(scope, replay, private_send)
        finally:
            with self.lock:
                self.active -= 1
