"""Single-owner app access, distinct from upstream provider credentials."""

import asyncio
import hmac
import json
import os

from fastapi import WebSocket

MAX_AUTH_FRAME_BYTES = 4096


def app_token() -> str:
    return os.getenv("APP_ACCESS_TOKEN", "").strip()


def authorized(header: str) -> bool:
    expected = app_token()
    return bool(expected) and hmac.compare_digest(
        header.encode(), f"Bearer {expected}".encode()
    )


async def authenticate_socket(socket: WebSocket) -> bool:
    # Native clients may send a header. Browsers send an initial auth frame;
    # no long-lived credentials are put in URLs or access logs.
    if authorized(socket.headers.get("authorization", "")):
        return True
    try:
        async with asyncio.timeout(10):
            message = await socket.receive()
        raw = message.get('text')
        if not isinstance(raw, str) or len(raw.encode('utf-8')) > MAX_AUTH_FRAME_BYTES:
            raise ValueError('Invalid authentication frame')
        event = json.loads(raw)
        if (isinstance(event, dict) and event.get("type") == "auth"
                and isinstance(event.get("token"), str)
                and authorized(f"Bearer {event['token']}")):
            return True
    except Exception:
        pass
    await socket.close(code=1008, reason="App access denied")
    return False
