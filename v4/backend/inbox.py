"""Durable bounded queue and short-lived results for a single-owner inbox."""

import os
import json
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
            translation TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT ''
        )""")
        # v4 has its own DB; this also supports opening an older schema safely.
        columns = {row['name'] for row in db.execute('PRAGMA table_info(messages)')}
        for name, definition in {
            'kind': "TEXT NOT NULL DEFAULT 'voice_message'",
            'call_id': "TEXT NOT NULL DEFAULT ''",
            'media_sha256': "TEXT NOT NULL DEFAULT ''",
            'event_at': 'REAL NOT NULL DEFAULT 0',
            'details': "TEXT NOT NULL DEFAULT '{}'",
            'stage': "TEXT NOT NULL DEFAULT ''",
            'lease_token': "TEXT NOT NULL DEFAULT ''",
        }.items():
            if name not in columns:
                db.execute(f'ALTER TABLE messages ADD COLUMN {name} {definition}')
        db.commit()
        yield db
    finally:
        db.close()


def prune(db):
    now = time.time()
    # Keep only message IDs as tombstones after result deletion/expiration so
    # Meta retries do not re-process or resurrect deleted audio messages.
    db.execute("""UPDATE messages SET status='deleted', media_id='', sender='',
        transcript='', translation='', error='', call_id='', media_sha256='',
        event_at=0, details='{}', stage='', lease_token=''
        WHERE created < ? AND status != 'deleted'""",
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
            if db.execute("SELECT 1 FROM messages WHERE id=?", (event['id'],)).fetchone():
                continue
            if pending + inserted >= MAX_PENDING:
                # Roll back the whole webhook batch. Meta can retry it safely.
                raise HTTPException(503, "WhatsApp inbox is busy. Retry later.")
            db.execute("""INSERT INTO messages
                (id,media_id,sender,target,created,updated,kind,call_id,media_sha256,event_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""", (event['id'], event['media_id'],
                f"…{event['sender'][-4:]}", target, now, now,
                event.get('kind', 'voice_message'), event.get('call_id', ''),
                event.get('media_sha256', ''), event.get('event_at', now)))
            inserted += 1
        db.commit()
        return inserted


def claim() -> dict | None:
    now = time.time()
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        prune(db)
        # Leases also recover a job after a process restart/crash.
        db.execute("""UPDATE messages SET status=CASE WHEN transcript='' THEN 'failed' ELSE 'partial' END,
            error='Processing was interrupted. Tap Retry.', stage=''
            WHERE status='processing' AND available <= ? AND attempts >= 3""", (now,))
        row = db.execute("""SELECT * FROM messages WHERE status IN ('queued','processing')
            AND available <= ? AND attempts < 3 ORDER BY created LIMIT 1""", (now,)).fetchone()
        if row:
            lease_token = uuid.uuid4().hex
            db.execute("""UPDATE messages SET status='processing', attempts=attempts+1,
                updated=?, available=?, lease_token=? WHERE id=?""", (now, now + 660, lease_token, row['id']))
        db.commit()
        if not row:
            return None
        result = dict(row)
        result['attempts'] += 1
        result['lease_token'] = lease_token
        return result


def checkpoint(message: dict, stage: str, *, transcript=None, details=None) -> bool:
    """Persist fetched text before translating; a stale/deleted job cannot write."""
    now = time.time()
    with database() as db:
        result = db.execute("""UPDATE messages SET stage=?, updated=?,
            transcript=COALESCE(?, transcript), details=COALESCE(?, details)
            WHERE id=? AND status='processing' AND lease_token=? AND created>=?""",
            (stage, now, transcript, json.dumps(details, ensure_ascii=False) if details is not None else None,
             message['id'], message['lease_token'], now - RETENTION_SECONDS))
        db.commit()
        return bool(result.rowcount)


def finish(message: dict, *, status: str, transcript='', translation='', error='', retry=False):
    now = time.time()
    if retry and message['attempts'] < 3:
        status = 'queued'
    with database() as db:
        db.execute("""UPDATE messages SET status=?, transcript=?, translation=?, error=?,
            updated=?, available=?, stage='' WHERE id=? AND status='processing'
            AND lease_token=? AND created>=?""",
            (status, transcript, translation, error, now,
             now + 10 * message['attempts'] if status == 'queued' else 0, message['id'],
             message['lease_token'], now - RETENTION_SECONDS))
        db.commit()


def list_messages() -> list[dict]:
    with database() as db:
        prune(db)
        rows = db.execute("""SELECT id,sender,target,created,status,transcript,translation,error,
            kind,call_id,event_at,details,stage
            FROM messages WHERE status != 'deleted' ORDER BY created DESC LIMIT 100""").fetchall()
        db.commit()
        return [{**dict(row), 'details': json.loads(row['details'])} for row in rows]


def expire_results():
    with database() as db:
        prune(db)
        db.commit()


def retry_message(message_id: str):
    with database() as db:
        prune(db)
        result = db.execute("""UPDATE messages SET status='queued', attempts=0, available=0,
            error='', stage='', updated=? WHERE id=? AND status IN ('failed','partial')""", (time.time(), message_id))
        db.commit()
        if not result.rowcount:
            raise HTTPException(409, "Only a failed or partially translated message can be retried.")


def delete_message(message_id: str):
    with database() as db:
        db.execute("""UPDATE messages SET status='deleted', media_id='', sender='',
            transcript='', translation='', error='', call_id='', media_sha256='',
            event_at=0, details='{}', stage='', lease_token='' WHERE id=?""", (message_id,))
        db.commit()
