import asyncio
import base64
import json
import shutil
import ssl
import subprocess
import wave
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app as backend
import live
import services


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Never call a paid API during these tests.
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("APP_ACCESS_TOKEN", "test-app-token")
    monkeypatch.setenv("INBOX_DB_PATH", str(tmp_path / 'inbox.sqlite3'))
    with TestClient(backend.app, headers={'Authorization': 'Bearer test-app-token'}) as client:
        yield client


def test_upload_returns_both_languages_and_cleans_file(client, monkeypatch):
    paths = []

    async def transcribe(path):
        paths.append(Path(path))
        assert Path(path).read_bytes() == b"sample"
        return "I need an appointment on Friday."

    translate = AsyncMock(return_value="J’ai besoin d’un rendez-vous vendredi.")
    monkeypatch.setattr(backend, "transcribe_audio", transcribe)
    monkeypatch.setattr(backend, "translate_text", translate)
    response = client.post("/api/transcribe", files={"file": ("../../note.ogg", b"sample")}, data={"target_language": "fr"})
    assert response.status_code == 200
    assert response.json()["filename"] == "note.ogg"
    assert response.json()["translation"] == "J’ai besoin d’un rendez-vous vendredi."
    assert not paths[0].exists()
    translate.assert_awaited_once_with("I need an appointment on Friday.", "fr")


def test_old_transcription_client_still_works(client, monkeypatch):
    monkeypatch.setattr(backend, "transcribe_audio", AsyncMock(return_value="Hello"))
    translate = AsyncMock()
    monkeypatch.setattr(backend, "translate_text", translate)
    response = client.post("/api/transcribe", files={"file": ("hello.wav", b"sample")})
    assert response.json()["transcript"] == "Hello"
    translate.assert_not_called()


@pytest.mark.parametrize("files,status", [
    ({}, 400), ({"file": ("empty.ogg", b"")}, 400),
    ({"file": ("bad.exe", b"data")}, 400),
])
def test_bad_upload_rejected_before_provider(client, monkeypatch, files, status):
    provider = AsyncMock()
    monkeypatch.setattr(backend, "transcribe_audio", provider)
    assert client.post("/api/transcribe", files=files).status_code == status
    provider.assert_not_called()


def test_upload_limit(client, monkeypatch):
    monkeypatch.setattr(backend, "MAX_UPLOAD_BYTES", 3)
    assert client.post("/api/transcribe", files={"file": ("a.wav", b"1234")}).status_code == 413


def test_invalid_target(client):
    assert client.post("/api/transcribe", files={"file": ("a.wav", b"sample")}, data={"target_language": "zh"}).status_code == 400


def test_translation_failure_keeps_transcript(client, monkeypatch):
    monkeypatch.setattr(backend, "transcribe_audio", AsyncMock(return_value="Bonjour"))
    monkeypatch.setattr(backend, "translate_text", AsyncMock(side_effect=HTTPException(429, "Usage limit")))
    result = client.post("/api/transcribe", files={"file": ("a.wav", b"sample")}, data={"target_language": "en"}).json()
    assert result["success"]
    assert result["transcript"] == "Bonjour"
    assert result["translation_error"] == "Usage limit"


def test_provider_failure_cleans_upload(client, monkeypatch):
    paths = []

    async def fail(path):
        paths.append(Path(path))
        raise HTTPException(503, "Provider unavailable")

    monkeypatch.setattr(backend, "transcribe_audio", fail)
    assert client.post("/api/transcribe", files={"file": ("a.wav", b"sample")}).status_code == 503
    assert not paths[0].exists()


def test_missing_key(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    response = client.post("/api/transcribe", files={"file": ("a.wav", b"sample")})
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["error"]


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg is required")
def test_real_ogg_is_decoded_to_wav_before_api(tmp_path, monkeypatch):
    source = tmp_path / "voice.ogg"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.3", "-c:a", "libopus", str(source)], check=True)
    converted_paths = []

    async def transcription(**kwargs):
        audio = kwargs["file"]
        converted_paths.append(Path(audio.name))
        assert audio.name.endswith(".wav")
        with wave.open(audio.name) as wav:
            assert wav.getframerate() == 16000
            assert wav.getnchannels() == 1
            assert wav.getnframes() > 0
        return SimpleNamespace(text="A mock transcript")

    @asynccontextmanager
    async def provider():
        yield SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=transcription)))

    monkeypatch.setattr(services, "provider", provider)
    assert asyncio.run(services.transcribe_audio(str(source))) == "A mock transcript"
    assert not converted_paths[0].exists()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg is required")
def test_invalid_ogg_does_not_reach_api(tmp_path):
    source = tmp_path / "fake.ogg"
    source.write_bytes(b"not audio")
    with pytest.raises(HTTPException) as error:
        asyncio.run(services.ogg_to_wav(source, tmp_path / "out.wav"))
    assert error.value.status_code == 400


class FakeUpstream:
    def __init__(self):
        self.events = asyncio.Queue()
        self.sent = []

    async def send(self, raw):
        event = json.loads(raw)
        self.sent.append(event)
        if event["type"] == "session.update":
            await self.events.put({"type": "session.updated"})
        elif event["type"] == "session.input_audio_buffer.append":
            # Translation sessions only provide translated output in practice.
            # Source text is supplied by the paired transcription session.
            pass
        elif event["type"] == "session.close":
            # The last words must still be forwarded AFTER the client presses Stop.
            for item in [
                {"type": "session.output_transcript.delta", "delta": "Bonjour le monde."},
                {"type": "session.closed"},
            ]:
                await self.events.put(item)

    async def recv(self):
        return json.dumps(await self.events.get())

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.recv()


class FakeTranscriptionUpstream(FakeUpstream):
    async def send(self, raw):
        event = json.loads(raw)
        self.sent.append(event)
        if event["type"] == "session.update":
            await self.events.put({"type": "session.updated"})
        elif event["type"] == "input_audio_buffer.append":
            await self.events.put({
                "type": "conversation.item.input_audio_transcription.delta",
                "delta": "Hello ",
            })
        elif event["type"] == "input_audio_buffer.commit":
            await self.events.put({
                "type": "conversation.item.input_audio_transcription.delta",
                "delta": "world.",
            })
            await self.events.put({
                "type": "conversation.item.input_audio_transcription.completed",
                "transcript": "Hello world.",
            })


@pytest.fixture
def upstream(monkeypatch):
    translation = FakeUpstream()
    transcription = FakeTranscriptionUpstream()

    @asynccontextmanager
    async def connection(url, *args, **kwargs):
        assert kwargs["ssl"].verify_mode == ssl.CERT_REQUIRED
        assert kwargs["ssl"].check_hostname is True
        yield transcription if "/v1/realtime?" in url else translation

    monkeypatch.setattr(live, "connect", connection)
    return SimpleNamespace(translation=translation, transcription=transcription)


def test_live_stream_drains_final_words(client, upstream):
    with client.websocket_connect("/api/live?target_language=fr", headers={"origin": "http://localhost:5173"}) as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_bytes(b"\x01\x00" * 2400)
        assert ws.receive_json() == {"type": "source.delta", "delta": "Hello "}
        ws.send_json({"type": "stop"})
        messages = []
        while True:
            message = ws.receive_json()
            messages.append(message)
            if message["type"] == "done":
                break
        assert {m.get("delta") for m in messages} >= {"world.", "Bonjour le monde."}
        assert {m.get("transcript") for m in messages} >= {"Hello world."}
    assert upstream.translation.sent[0]["session"]["audio"]["output"]["language"] == "fr"
    assert base64.b64decode(upstream.translation.sent[1]["audio"]) == b"\x01\x00" * 2400
    assert base64.b64decode(upstream.transcription.sent[1]["audio"]) == b"\x01\x00" * 2400


def test_browser_auth_frame_precedes_stream(client, upstream):
    with client.websocket_connect('/api/live?target_language=en', headers={'Authorization': ''}) as ws:
        ws.send_json({'type': 'auth', 'token': 'test-app-token'})
        assert ws.receive_json()['type'] == 'ready'
        ws.send_json({'type': 'stop'})
        messages = []
        while True:
            message = ws.receive_json()
            messages.append(message)
            if message['type'] == 'done':
                break
        assert {m.get('delta') for m in messages} >= {'world.', 'Bonjour le monde.'}


def test_live_rejects_bad_origin(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/live", headers={"origin": "https://unrelated.example"}):
            pass


def test_live_missing_key_is_visible(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    with client.websocket_connect("/api/live") as ws:
        result = ws.receive_json()
        assert result["type"] == "error"
        assert "OPENAI_API_KEY" in result["message"]


def test_live_rejects_invalid_pcm(client, upstream):
    with client.websocket_connect("/api/live") as ws:
        assert ws.receive_json()["type"] == "ready"
        ws.send_bytes(b"123")
        assert ws.receive_json()["type"] == "error"


def test_live_provider_error_is_sanitized(client, upstream):
    async def fail_send(raw):
        await upstream.translation.events.put({"type": "error", "error": {"code": "bad", "message": "private diagnostic"}})

    upstream.translation.send = fail_send
    with client.websocket_connect("/api/live") as ws:
        message = ws.receive_json()
        assert message["type"] == "error"
        assert "private diagnostic" not in message["message"]


def test_live_invalid_api_key_is_actionable(client, upstream):
    async def fail_send(raw):
        await upstream.translation.events.put({"type": "error", "error": {"code": "invalid_api_key"}})

    upstream.translation.send = fail_send
    with client.websocket_connect("/api/live") as ws:
        message = ws.receive_json()
        assert message["type"] == "error"
        assert "OPENAI_API_KEY" in message["message"]


def test_config_does_not_leak_key(client):
    response = client.get("/api/config")
    assert response.json()["languages"] == {"en": "English", "fr": "French"}
    assert "test-key-not-real" not in response.text
