"""Durable bounded queue and short-lived results for a single-owner inbox."""

import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException

RETENTION_SECONDS = 24 * 3600
DEDUPE_SECONDS = 7 * 24 * 3600
MAX_PENDING = 100


@contextmanager
def database():
    path = Path(os.getenv("INBOX_DB_PATH", str(Path(__file__).parent / "data/inbox.sqlite3")))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5)
    try:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA secure_delete=ON')
        db.execute("""CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY, media_id TEXT NOT NULL, sender TEXT NOT NULL,
            target TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued', attempts INTEGER NOT NULL DEFAULT 0,
            available REAL NOT NULL DEFAULT 0, transcript TEXT NOT NULL DEFAULT '',
            translation TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '',
            message_id TEXT, audio_path TEXT
        )""")
        # Existing queue databases gain optional source/audio metadata
        # without requiring a destructive migration.
        columns = {row['name'] for row in db.execute('PRAGMA table_info(messages)')}
        if 'message_id' not in columns:
            db.execute('ALTER TABLE messages ADD COLUMN message_id TEXT')
        if 'audio_path' not in columns:
            db.execute('ALTER TABLE messages ADD COLUMN audio_path TEXT')
        yield db
    finally:
        db.close()


def prune(db):
    now = time.time()
    # Keep only message IDs as tombstones after result deletion/expiration so
    # Meta retries do not re-process or resurrect deleted audio messages.
    db.execute("""UPDATE messages SET status='deleted', media_id='', sender='', audio_path=NULL,
        transcript='', translation='', error='' WHERE created < ? AND status != 'deleted'""",
        (now - RETENTION_SECONDS,))
    db.execute("DELETE FROM messages WHERE created < ?", (now - DEDUPE_SECONDS,))


def enqueue(events: list[dict], target: str) -> int:
    now = time.time()
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        prune(db)
        pending = db.execute("SELECT COUNT(*) FROM messages WHERE status IN ('queued','processing')").fetchone()[0]
        inserted = 0
        for event in events:
            queue_id = event.get('id') or str(uuid.uuid4())
            if db.execute("SELECT 1 FROM messages WHERE id=?", (queue_id,)).fetchone():
                continue
            if pending + inserted >= MAX_PENDING:
                # Roll back the whole webhook batch. Meta can retry it safely.
                raise HTTPException(503, "WhatsApp inbox is busy. Retry later.")
            created = event.get('received_at') or now
            db.execute("""INSERT INTO messages (id,media_id,sender,target,created,updated,message_id)
                VALUES (?,?,?,?,?,?,?)""", (queue_id, event['media_id'],
                f"…{event.get('sender', '')[-4:]}", target, created, now,
                event.get('message_id')))
            inserted += 1
        db.commit()
        return inserted


def claim() -> dict | None:
    now = time.time()
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        prune(db)
        # Leases also recover a job after a process restart/crash.
        db.execute("""UPDATE messages SET status='failed', error='Processing was interrupted. Tap Retry.'
            WHERE status='processing' AND available <= ? AND attempts >= 3""", (now,))
        row = db.execute("""SELECT * FROM messages WHERE status IN ('queued','processing')
            AND available <= ? AND attempts < 3 ORDER BY created LIMIT 1""", (now,)).fetchone()
        if row:
            db.execute("""UPDATE messages SET status='processing', attempts=attempts+1,
                updated=?, available=? WHERE id=?""", (now, now + 300, row['id']))
        db.commit()
        if not row:
            return None
        result = dict(row)
        result['attempts'] += 1
        return result


def finish(message: dict, *, status: str, transcript='', translation='', error='', retry=False):
    now = time.time()
    if retry and message['attempts'] < 3:
        status = 'queued'
    with database() as db:
        db.execute("""UPDATE messages SET status=?, transcript=?, translation=?, error=?,
            updated=?, available=? WHERE id=? AND status='processing'""",
            (status, transcript, translation, error, now,
             now + 10 * message['attempts'] if status == 'queued' else 0, message['id']))
        db.commit()


def set_audio_path(message: dict, audio_path: str):
    """Remember the local audio path for retries, including events without a Meta ID."""
    with database() as db:
        db.execute("UPDATE messages SET audio_path=? WHERE id=? AND status='processing'",
                   (audio_path, message['id']))
        db.commit()


def list_messages() -> list[dict]:
    with database() as db:
        prune(db)
        rows = db.execute("""SELECT id,sender,target,created,status,transcript,translation,error
            FROM messages WHERE status != 'deleted' ORDER BY created DESC LIMIT 100""").fetchall()
        db.commit()
        return [dict(row) for row in rows]


def expire_results():
    with database() as db:
        prune(db)
        db.commit()


def retry_message(message_id: str):
    with database() as db:
        prune(db)
        result = db.execute("""UPDATE messages SET status='queued', attempts=0, available=0,
            error='', updated=? WHERE id=? AND status IN ('failed','partial')""", (time.time(), message_id))
        db.commit()
        if not result.rowcount:
            raise HTTPException(409, "Only a failed or partially translated message can be retried.")


def delete_message(message_id: str):
    with database() as db:
        db.execute("""UPDATE messages SET status='deleted', media_id='', sender='',
            transcript='', translation='', error='' WHERE id=?""", (message_id,))
        db.commit()
