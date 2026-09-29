"""Single-owner app access, distinct from upstream provider credentials."""

import asyncio
import hmac
import os

from fastapi import WebSocket


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
            event = await socket.receive_json()
        if (isinstance(event, dict) and event.get("type") == "auth"
                and isinstance(event.get("token"), str)
                and authorized(f"Bearer {event['token']}")):
            return True
    except Exception:
        pass
    await socket.close(code=1008, reason="App access denied")
    return False
