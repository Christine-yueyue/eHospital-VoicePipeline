import sqlite3
import time
from pathlib import Path

from bootstrap import backend_app, voice_feedback
from support import FIXTURE


def test_upload_reaches_isolated_backend_and_persists_result(backend_server, monkeypatch):
    fixture_bytes = FIXTURE.read_bytes()
    observed = {"transcribe": [], "translate": []}

    async def fake_transcribe(path):
        observed["transcribe"].append(Path(path).read_bytes())
        return "My appointment is Friday at three."

    async def fake_translate(text, target):
        observed["translate"].append((text, target))
        return "Mon rendez-vous est vendredi à quinze heures."

    monkeypatch.setattr(backend_app, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(backend_app, "translate_text", fake_translate)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        request = playwright.request.new_context(
            base_url=backend_server["url"],
            extra_http_headers={"Authorization": f"Bearer {backend_server['token']}"},
        )
        response = request.post(
            "/api/transcribe",
            multipart={
                "target_language": "fr",
                "file": {
                    "name": FIXTURE.name,
                    "mimeType": "audio/wav",
                    "buffer": fixture_bytes,
                },
            },
        )
        assert response.ok
        body = response.json()
        request.dispose()

    assert body["success"] is True
    assert body["transcript"] == "My appointment is Friday at three."
    assert body["translation"] == "Mon rendez-vous est vendredi à quinze heures."
    assert observed == {
        "transcribe": [fixture_bytes],
        "translate": [("My appointment is Friday at three.", "fr")],
    }

    deadline = time.monotonic() + 5
    db_path = Path(voice_feedback.database_path())
    row = None
    while time.monotonic() < deadline:
        if db_path.exists():
            with sqlite3.connect(db_path) as db:
                row = db.execute(
                    "SELECT feedback_message, translation_message, target_language, source, transcription_status FROM voice_feedback"
                ).fetchone()
            if row is not None:
                break
        time.sleep(0.05)
    assert row == (
        "My appointment is Friday at three.",
        None,
        None,
        "upload",
        "completed",
    )
