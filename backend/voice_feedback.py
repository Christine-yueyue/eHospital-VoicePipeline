"""SQLite metadata and backend-local audio storage for voice feedback."""

import hashlib
import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def database_path() -> Path:
    return Path(os.getenv('VOICE_FEEDBACK_DB_PATH', str(BACKEND_DIR / 'data/voice_feedback.db'))).resolve()


def audio_directory() -> Path:
    return Path(os.getenv('VOICE_FEEDBACK_AUDIO_DIR', str(BACKEND_DIR / 'data/audio'))).resolve()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize() -> None:
    """Create local storage and the voice_feedback schema/indexes idempotently."""
    db_path = database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    audio_directory().mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=10) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS voice_feedback (
            id INTEGER PRIMARY KEY,
            record_id TEXT,
            feedback_message TEXT,
            created_time TEXT NOT NULL,
            transcription_status TEXT NOT NULL CHECK (
                transcription_status IN ('pending', 'completed', 'failed')),
            audio_path TEXT NOT NULL,
            audio_mime_type TEXT,
            audio_duration_seconds REAL,
            source_message_id TEXT,
            file_name TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            last_error TEXT,
            updated_time TEXT NOT NULL
        )''')
        columns = {row[1] for row in db.execute('PRAGMA table_info(voice_feedback)')}
        if 'source' not in columns:
            db.execute("ALTER TABLE voice_feedback ADD COLUMN source TEXT NOT NULL DEFAULT 'upload'")
            db.execute("UPDATE voice_feedback SET source='whatsapp' WHERE source_message_id IS NOT NULL AND source_message_id <> ''")
        if 'translation_message' not in columns:
            db.execute('ALTER TABLE voice_feedback ADD COLUMN translation_message TEXT')
        if 'target_language' not in columns:
            db.execute('ALTER TABLE voice_feedback ADD COLUMN target_language TEXT')
        db.execute('''CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )''')
        db.execute("INSERT OR IGNORE INTO app_settings(key, value) VALUES ('save_to_database', '1')")
        db.execute('''CREATE UNIQUE INDEX IF NOT EXISTS
            idx_voice_feedback_source_message_id
            ON voice_feedback(source_message_id)
            WHERE source_message_id IS NOT NULL AND source_message_id <> '' ''')
        db.execute('''CREATE INDEX IF NOT EXISTS idx_voice_feedback_record_time
            ON voice_feedback(record_id, created_time)''')
        db.execute('''CREATE INDEX IF NOT EXISTS idx_voice_feedback_status
            ON voice_feedback(transcription_status)''')


def _created_time(value=None) -> str:
    if value is None:
        return utc_now()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def store_audio(source_path: Path, *, extension: str, mime_type: str | None,
                source_message_id: str | None = None, created_time=None,
                source: str = 'upload') -> dict:
    """Copy original bytes to a generated local filename and create a pending row.

    WhatsApp retries use the same hashed filename and source-message row. Manual
    uploads receive a fresh UUID filename and have no source message ID.
    """
    initialize()
    suffix = extension.lower()
    if not suffix.startswith('.') or len(suffix) > 12:
        suffix = '.audio'
    if source_message_id:
        file_name = f'{hashlib.sha256(source_message_id.encode()).hexdigest()}{suffix}'
    else:
        file_name = f'{uuid.uuid4().hex}{suffix}'
    relative_path = (Path('data') / 'audio' / file_name).as_posix()
    destination = audio_directory() / file_name
    temporary = audio_directory() / f'.{uuid.uuid4().hex}.upload'
    try:
        shutil.copyfile(source_path, temporary)
        size_bytes = temporary.stat().st_size
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    created = _created_time(created_time)
    now = utc_now()
    db_path = database_path()
    with sqlite3.connect(db_path, timeout=10) as db:
        db.row_factory = sqlite3.Row
        if source_message_id:
            row = db.execute('SELECT id FROM voice_feedback WHERE source_message_id=?',
                             (source_message_id,)).fetchone()
        else:
            row = None
        if row:
            record_id = row['id']
            db.execute('''UPDATE voice_feedback SET source='whatsapp', audio_path=?, audio_mime_type=?,
                audio_duration_seconds=NULL, file_name=?, size_bytes=?,
                transcription_status='pending', last_error=NULL, updated_time=?
                WHERE id=?''', (relative_path, mime_type, file_name, size_bytes, now, record_id))
        else:
            cursor = db.execute('''INSERT INTO voice_feedback
                (record_id, feedback_message, created_time, transcription_status,
                 audio_path, audio_mime_type, audio_duration_seconds,
                 source_message_id, file_name, size_bytes, last_error, updated_time, source)
                VALUES (NULL, NULL, ?, 'pending', ?, ?, NULL, ?, ?, ?, NULL, ?, ?)''',
                (created, relative_path, mime_type, source_message_id, file_name, size_bytes, now,
                 source))
            record_id = cursor.lastrowid
    return {'id': record_id, 'audio_path': relative_path, 'file_name': file_name,
            'size_bytes': size_bytes, 'audio_mime_type': mime_type}


def _update(audio_path: str, *, status: str, feedback_message=None, error=None) -> None:
    initialize()
    with sqlite3.connect(database_path(), timeout=10) as db:
        db.execute('''UPDATE voice_feedback SET feedback_message=?, transcription_status=?,
            last_error=?, updated_time=? WHERE audio_path=?''',
            (feedback_message, status, error, utc_now(), audio_path))


def mark_completed(audio_path: str, transcript: str) -> None:
    _update(audio_path, status='completed', feedback_message=transcript)


def mark_failed(audio_path: str, summary: str) -> None:
    _update(audio_path, status='failed', error=summary[:240])


def get_save_to_database() -> bool:
    initialize()
    with sqlite3.connect(database_path(), timeout=10) as db:
        row = db.execute("SELECT value FROM app_settings WHERE key='save_to_database'").fetchone()
    return bool(row and row[0] == '1')


def set_save_to_database(enabled: bool) -> bool:
    initialize()
    with sqlite3.connect(database_path(), timeout=10) as db:
        db.execute("INSERT INTO app_settings(key, value) VALUES ('save_to_database', ?) "
                   "ON CONFLICT(key) DO UPDATE SET value=excluded.value", ('1' if enabled else '0',))
    return enabled


def save_live_feedback(transcript: str, translation: str, target_language: str) -> int | None:
    """Save completed live text only while the global persistence setting is on."""
    if not get_save_to_database():
        return None
    initialize()
    now = utc_now()
    with sqlite3.connect(database_path(), timeout=10) as db:
        cursor = db.execute('''INSERT INTO voice_feedback
            (record_id, feedback_message, created_time, transcription_status, audio_path,
             audio_mime_type, audio_duration_seconds, source_message_id, file_name,
             size_bytes, last_error, updated_time, source, translation_message, target_language)
            VALUES (NULL, ?, ?, 'completed', '', NULL, NULL, NULL, '', 0, NULL, ?, 'live', ?, ?)''',
            (transcript, now, now, translation, target_language))
        return cursor.lastrowid
