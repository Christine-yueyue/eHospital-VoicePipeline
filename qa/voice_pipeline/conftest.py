"""Isolated FastAPI server and provider doubles for browser tests.

The app normally reads backend/.env during import. Replace python-dotenv's
loader before importing any application module so this test process never
opens a developer .env file.
"""

import os
import socket
import sys
import threading
import time
from pathlib import Path

import pytest
import uvicorn


QA_DIR = Path(__file__).resolve().parent
FRONTEND_URL = os.environ.get("QA_FRONTEND_URL", "http://127.0.0.1:5174")
if str(QA_DIR) not in sys.path:
    sys.path.insert(0, str(QA_DIR))

from bootstrap import TEST_TOKEN, backend_app, live_module, voice_feedback  # noqa: E402


@pytest.fixture
def backend_server(tmp_path, monkeypatch):
    """Start the real ASGI app on an ephemeral loopback port with temp storage."""
    monkeypatch.setenv("APP_ACCESS_TOKEN", TEST_TOKEN)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-not-a-provider-key")
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("INBOX_DB_PATH", str(tmp_path / "inbox.sqlite3"))
    monkeypatch.setenv("VOICE_FEEDBACK_DB_PATH", str(tmp_path / "voice_feedback.db"))
    monkeypatch.setenv("VOICE_FEEDBACK_AUDIO_DIR", str(tmp_path / "audio"))
    monkeypatch.setenv("ALLOWED_ORIGINS", FRONTEND_URL)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    config = uvicorn.Config(backend_app.app, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not server.started:
        if not thread.is_alive():
            raise RuntimeError("Isolated test backend exited before startup.")
        time.sleep(0.05)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("Isolated test backend did not become ready in 10 seconds.")

    yield {
        "url": "http://127.0.0.1:{0}".format(port),
        "token": TEST_TOKEN,
        "tmp_path": tmp_path,
    }

    server.should_exit = True
    thread.join(timeout=10)
    sock.close()
    if thread.is_alive():
        raise RuntimeError("Isolated test backend did not stop cleanly.")


@pytest.fixture(scope="session")
def browser():
    """Launch Chromium with the QA WAV as its virtual microphone input."""
    from playwright.sync_api import sync_playwright

    fixture = QA_DIR / "fixtures" / "pipeline_tone.wav"
    if not fixture.exists():
        import subprocess

        subprocess.run([sys.executable, str(QA_DIR / "create_fixture.py")], check=True)
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(
            headless=os.environ.get("QA_HEADLESS", "1") != "0",
            args=[
                "--use-fake-device-for-media-stream",
                "--use-fake-ui-for-media-stream",
                "--use-file-for-fake-audio-capture={0}".format(fixture),
            ],
        )
        yield instance
        instance.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(permissions=["microphone"])
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def live_observation(monkeypatch):
    """Replace both live provider sockets and expose the observed PCM frames."""
    import asyncio
    import json
    from contextlib import asynccontextmanager

    class FakeUpstream:
        def __init__(self, kind):
            self.kind = kind
            self.events = asyncio.Queue()
            self.audio_bytes = 0
            self.sent = []

        async def send(self, raw):
            event = json.loads(raw)
            self.sent.append(event)
            if event.get("type") == "session.update":
                await self.events.put({"type": "session.updated"})
            elif event.get("type") == "session.close" and self.kind == "translation":
                await self.events.put({"type": "session.output_transcript.delta", "delta": "Mon rendez-vous est vendredi à quinze heures."})
                await self.events.put({"type": "session.closed"})
            elif event.get("type") == "input_audio_buffer.append" and self.kind == "transcription":
                import base64
                self.audio_bytes += len(base64.b64decode(event["audio"]))
            elif event.get("type") == "session.input_audio_buffer.append" and self.kind == "translation":
                import base64
                self.audio_bytes += len(base64.b64decode(event["audio"]))
            elif event.get("type") == "input_audio_buffer.commit" and self.kind == "transcription":
                await self.events.put({
                    "type": "conversation.item.input_audio_transcription.completed",
                    "transcript": "My appointment is Friday at three.",
                })

        async def recv(self):
            return json.dumps(await self.events.get())

        def __aiter__(self):
            return self

        async def __anext__(self):
            return await self.recv()

    streams = []

    @asynccontextmanager
    async def fake_connect(_uri, **_kwargs):
        kind = "translation" if not streams else "transcription"
        upstream = FakeUpstream(kind)
        streams.append(upstream)
        yield upstream

    monkeypatch.setattr(live_module, "connect", fake_connect)
    return streams
