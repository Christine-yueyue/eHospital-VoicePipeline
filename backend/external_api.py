"""Read-only API for approved third-party integrations."""

from pathlib import Path
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

import voice_feedback

router = APIRouter(prefix='/api/external/v1', tags=['third-party read API'])

PUBLIC_FIELDS = (
    'id', 'created_time', 'updated_time', 'source', 'transcription_status',
    'feedback_message', 'translation_message', 'target_language',
    'audio_mime_type', 'audio_duration_seconds', 'size_bytes', 'last_error',
)


def _public_record(row: sqlite3.Row) -> dict:
    item = {field: row[field] for field in PUBLIC_FIELDS}
    item['has_audio'] = bool(row['audio_path']) and row['source'] != 'live'
    item['audio_url'] = (
        f"voice-feedback/{row['id']}/audio"
        if item['has_audio'] else None
    )
    return item


def _record(record_id: int) -> sqlite3.Row:
    voice_feedback.initialize()
    with sqlite3.connect(voice_feedback.database_path(), timeout=10) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            'SELECT * FROM voice_feedback WHERE id=?', (record_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, 'Voice feedback record not found.')
    return row


def _utc_timestamp(value: str | None, parameter: str) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(422, f'{parameter} must be an ISO 8601 timestamp.') from None
    if parsed.tzinfo is None:
        raise HTTPException(422, f'{parameter} must include a timezone.')
    return parsed.astimezone(timezone.utc).isoformat(timespec='microseconds')


@router.get('/voice-feedback')
async def list_voice_feedback(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0, le=1_000_000),
    source: str | None = Query(None, pattern=r'^(upload|whatsapp|live)$'),
    status: str | None = Query(None, pattern=r'^(pending|completed|failed)$'),
    since: str | None = Query(None, min_length=10, max_length=40),
    until: str | None = Query(None, min_length=10, max_length=40),
):
    """Return paginated transcript metadata and text; audio is a separate download."""
    voice_feedback.initialize()
    since = _utc_timestamp(since, 'since')
    until = _utc_timestamp(until, 'until')
    if since and until and since > until:
        raise HTTPException(422, 'since must not be later than until.')
    clauses = []
    values: list[object] = []
    for column, value in (('source', source), ('transcription_status', status)):
        if value is not None:
            clauses.append(f'{column}=?')
            values.append(value)
    for value, op in ((since, '>='), (until, '<=')):
        if value is not None:
            clauses.append(f'julianday(created_time){op}julianday(?)')
            values.append(value)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ''
    with sqlite3.connect(voice_feedback.database_path(), timeout=10) as db:
        db.row_factory = sqlite3.Row
        total = db.execute(
            f'SELECT COUNT(*) FROM voice_feedback{where}', values
        ).fetchone()[0]
        rows = db.execute(
            f'SELECT * FROM voice_feedback{where} ORDER BY created_time DESC, id DESC LIMIT ? OFFSET ?',
            [*values, limit, offset],
        ).fetchall()
    return {
        'records': [_public_record(row) for row in rows],
        'pagination': {'limit': limit, 'offset': offset, 'total': total},
    }


@router.get('/voice-feedback/{record_id}')
async def get_voice_feedback(record_id: int):
    return {'record': _public_record(_record(record_id))}


@router.get('/voice-feedback/{record_id}/audio')
async def get_voice_feedback_audio(record_id: int):
    row = _record(record_id)
    if not row['audio_path'] or row['source'] == 'live':
        raise HTTPException(404, 'This record has no saved audio.')
    audio_root = voice_feedback.audio_directory().resolve()
    filename = Path(row['file_name']).name
    audio_path = (audio_root / filename).resolve()
    if audio_path.parent != audio_root or not audio_path.is_file():
        raise HTTPException(404, 'Saved audio file not found.')
    return FileResponse(
        audio_path,
        media_type=row['audio_mime_type'] or 'application/octet-stream',
        filename=filename,
        headers={'Cache-Control': 'no-store'},
    )
