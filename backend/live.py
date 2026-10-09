"""Relay Flutter PCM audio to a dedicated OpenAI translation session."""

import asyncio
import base64
import json
import os
import ssl
from contextlib import suppress
from urllib.parse import urlencode

import certifi
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from services import api_key, check_target
from auth import authenticate_socket
import voice_feedback

live_router = APIRouter()
MAX_SESSION_SECONDS = 600
DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8003,http://127.0.0.1:8003"


def upstream_error(event: dict) -> HTTPException:
    code = event.get("error", {}).get("code", "")
    if code in {"insufficient_quota", "rate_limit_exceeded"}:
        return HTTPException(429, "Live translation reached an API usage limit. Check billing or retry later.")
    if code in {"invalid_api_key", "authentication_error"}:
        return HTTPException(503, "OpenAI rejected OPENAI_API_KEY. Replace it in backend/.env and restart FastAPI.")
    if code in {"model_not_found", "permission_denied"}:
        return HTTPException(503, "The OpenAI live translation model is unavailable for this project. Check model access and permissions.")
    return HTTPException(502, "Live translation is unavailable. Check API key access, target language and REALTIME_TRANSLATION_MODEL on the backend.")


def closed_error(exc: ConnectionClosed) -> str:
    """Turn provider close reasons into an actionable, safe client message."""
    received = getattr(exc, "rcvd", None)
    reason = getattr(received, "reason", "") or ""
    details = f"{reason} {received or ''} {exc}"
    if "invalid_api_key" in details or "authentication" in details:
        return "OpenAI rejected OPENAI_API_KEY. Replace it in backend/.env and restart FastAPI."
    if "permission" in details or "model_not_found" in details:
        return "The OpenAI live translation model is unavailable for this project. Check model access and permissions."
    return "Could not connect to live translation. Check the backend connection, API billing and model access."


async def _wait_for_session_update(upstream) -> None:
    """Wait until a newly opened provider session accepts its configuration."""
    async with asyncio.timeout(15):
        while True:
            event = json.loads(await upstream.recv())
            if event.get("type") == "error":
                raise upstream_error(event)
            if event.get("type") == "session.updated":
                return


async def relay(websocket: WebSocket, translation_upstream, transcription_upstream,
                target_language: str = 'fr') -> None:
    """Relay one microphone stream to translation and source-transcription sessions."""
    stop_requested = asyncio.Event()
    final_transcript = ''
    translated_text = ''

    def audio_event(chunk: bytes) -> str:
        return json.dumps({
            "type": "session.input_audio_buffer.append",
            "audio": base64.b64encode(chunk).decode("ascii"),
        })

    def transcription_audio_event(chunk: bytes) -> str:
        return json.dumps({
            "type": "input_audio_buffer.append",
            "audio": base64.b64encode(chunk).decode("ascii"),
        })

    async def from_microphone():
        total = 0
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect()
            chunk = message.get("bytes")
            if chunk is not None:
                if not chunk or len(chunk) > 48_000 or len(chunk) % 2:
                    raise HTTPException(400, "Invalid audio frame. Expected mono 24 kHz PCM16.")
                total += len(chunk)
                if total > MAX_SESSION_SECONDS * 48_000:
                    raise HTTPException(400, "The 10-minute demo limit was reached. Start a new session.")
                await translation_upstream.send(audio_event(chunk))
                await transcription_upstream.send(transcription_audio_event(chunk))
            elif message.get("text"):
                try:
                    control = json.loads(message["text"])
                except (ValueError, TypeError):
                    raise HTTPException(400, "Invalid live audio control message.") from None
                if control != {"type": "stop"}:
                    raise HTTPException(400, "Unsupported live audio message.")
                stop_requested.set()
                await translation_upstream.send(json.dumps({"type": "session.close"}))
                await transcription_upstream.send(json.dumps({"type": "input_audio_buffer.commit"}))
                return
            else:
                raise HTTPException(400, "Unsupported live audio message.")

    async def from_provider():
        nonlocal translated_text
        async for raw in translation_upstream:
            event = json.loads(raw)
            kind = event.get("type")
            if kind == "error":
                raise upstream_error(event)
            if kind in {"session.input_transcript.delta", "session.output_transcript.delta"}:
                if kind == 'session.output_transcript.delta':
                    translated_text += event.get('delta', '')
                await websocket.send_json({
                    "type": "source.delta" if kind == "session.input_transcript.delta" else "translation.delta",
                    "delta": event.get("delta", ""),
                })
            elif kind == "session.closed":
                if not stop_requested.is_set():
                    raise HTTPException(502, "The translation session closed before Stop. Please start again.")
                return
            # This text-caption demo does not play the provider's translated audio.
        raise HTTPException(502, "The live service disconnected before finishing. Please start again.")

    async def from_transcriber():
        nonlocal final_transcript
        async for raw in transcription_upstream:
            event = json.loads(raw)
            kind = event.get("type")
            if kind == "error":
                raise upstream_error(event)
            if kind == "conversation.item.input_audio_transcription.delta":
                await websocket.send_json({
                    "type": "source.delta",
                    "delta": event.get("delta", ""),
                })
            elif kind == "conversation.item.input_audio_transcription.completed":
                # A final event can correct earlier partial words. The Flutter
                # controller replaces its incremental value with this complete
                # transcript when it arrives.
                transcript = event.get("transcript", "")
                if transcript:
                    final_transcript = transcript
                    await websocket.send_json({
                        "type": "source.final",
                        "transcript": transcript,
                    })
                return
        raise HTTPException(502, "The source transcription disconnected before finishing. Please start again.")

    send_task = asyncio.create_task(from_microphone())
    translation_task = asyncio.create_task(from_provider())
    transcription_task = asyncio.create_task(from_transcriber())
    try:
        done, _ = await asyncio.wait(
            {send_task, translation_task, transcription_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if send_task in done:
            await send_task
            await asyncio.wait_for(
                asyncio.gather(translation_task, transcription_task),
                timeout=30,
            )
            if final_transcript.strip():
                voice_feedback.save_live_feedback(
                    final_transcript.strip(),
                    (translated_text or final_transcript).strip(),
                    target_language,
                )
            await websocket.send_json({"type": "done"})
        else:
            # Surface provider errors immediately instead of waiting for the
            # microphone to be stopped by the user.
            for task in done:
                await task
            await send_task
    finally:
        for task in (send_task, translation_task, transcription_task):
            task.cancel()
        await asyncio.gather(send_task, translation_task, transcription_task, return_exceptions=True)


@live_router.websocket("/api/live")
async def live(websocket: WebSocket):
    # CORS middleware does not protect WebSockets. Check browser origins here.
    origins = {v.strip() for v in os.getenv("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")}
    origin = websocket.headers.get("origin")
    if origin and origin not in origins:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    if not await authenticate_socket(websocket):
        return
    try:
        target = websocket.query_params.get("target_language", "fr")
        check_target(target)
        key = api_key()
        query = urlencode({"model": os.getenv("REALTIME_TRANSLATION_MODEL", "gpt-realtime-translate")})
        async with asyncio.timeout(MAX_SESSION_SECONDS):
            async with connect(
                f"wss://api.openai.com/v1/realtime/translations?{query}",
                additional_headers={"Authorization": f"Bearer {key}"},
                # Python.org macOS installs may lack usable system CA paths.
                # Use the maintained CA bundle, as the upload HTTP client does.
                ssl=ssl.create_default_context(cafile=certifi.where()),
                open_timeout=15, close_timeout=5, max_size=2**22,
            ) as upstream:
                await upstream.send(json.dumps({
                    "type": "session.update", "session": {"audio": {"output": {"language": target}}},
                }))
                await _wait_for_session_update(upstream)
                transcription_query = urlencode({
                    "model": os.getenv("REALTIME_TRANSCRIPTION_SESSION_MODEL", "gpt-realtime"),
                })
                async with connect(
                    f"wss://api.openai.com/v1/realtime?{transcription_query}",
                    additional_headers={"Authorization": f"Bearer {key}"},
                    ssl=ssl.create_default_context(cafile=certifi.where()),
                    open_timeout=15, close_timeout=5, max_size=2**22,
                ) as transcription_upstream:
                    await transcription_upstream.send(json.dumps({
                        "type": "session.update",
                        "session": {
                            "type": "realtime",
                            "audio": {
                                "input": {
                                    "format": {"type": "audio/pcm", "rate": 24000},
                                    "transcription": {
                                        "model": os.getenv("REALTIME_TRANSCRIPTION_MODEL", "gpt-live-transcribe"),
                                        "languages": ["en", "fr"],
                                        "delay": "low",
                                    },
                                    "turn_detection": None,
                                },
                            },
                        },
                    }))
                    await _wait_for_session_update(transcription_upstream)
                    await websocket.send_json({"type": "ready", "sample_rate": 24000})
                    await relay(websocket, upstream, transcription_upstream, target)
    except WebSocketDisconnect:
        pass
    except HTTPException as exc:
        with suppress(Exception):
            await websocket.send_json({"type": "error", "message": str(exc.detail)})
    except TimeoutError:
        with suppress(Exception):
            await websocket.send_json({"type": "error", "message": "Live session timed out. Your displayed text is kept; start a new session."})
    except ssl.SSLCertVerificationError:
        with suppress(Exception):
            await websocket.send_json({"type": "error", "message": "The backend could not verify the API server certificate. Update certifi in the Python environment; check any network proxy certificate setup."})
    except ConnectionClosed as exc:
        with suppress(Exception):
            await websocket.send_json({"type": "error", "message": closed_error(exc)})
    except (InvalidStatus, OSError):
        with suppress(Exception):
            await websocket.send_json({"type": "error", "message": "Could not connect to live translation. Check the backend connection, API billing and model access."})
    except Exception:
        with suppress(Exception):
            await websocket.send_json({"type": "error", "message": "Live translation failed. Please start a new session."})
    finally:
        with suppress(Exception):
            await websocket.close()
