"""Persistent, single-process scheduler for approved WhatsApp templates."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

import followup
import voice_feedback
from whatsapp_templates import check_meta_response, list_approved_templates, template_payload, verify_template

router = APIRouter(prefix='/api/whatsapp/schedules', tags=['Scheduled WhatsApp messages'])
logger = logging.getLogger('uvicorn.error.whatsapp.scheduler')
POLL_SECONDS = 1


def _db():
    followup.initialize()
    db = sqlite3.connect(voice_feedback.database_path(), timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def initialize() -> None:
    with _db() as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id TEXT PRIMARY KEY,
                schedule_id TEXT NOT NULL,
                contact_id TEXT NOT NULL REFERENCES wa_contacts(id),
                recipient_phone TEXT NOT NULL,
                template_name TEXT NOT NULL,
                template_language TEXT NOT NULL,
                template_parameters TEXT NOT NULL DEFAULT '[]',
                scheduled_time REAL NOT NULL,
                timezone TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN
                    ('pending','processing','submitted','failed','unknown')),
                created_at REAL NOT NULL,
                executed_at REAL,
                error_message TEXT NOT NULL DEFAULT '',
                whatsapp_message_id TEXT UNIQUE
            );
            CREATE INDEX IF NOT EXISTS idx_scheduled_messages_due
                ON scheduled_messages(status, scheduled_time);
            CREATE INDEX IF NOT EXISTS idx_scheduled_messages_batch
                ON scheduled_messages(schedule_id, created_at);
        ''')


def recover_after_restart() -> None:
    """Keep pending jobs for the scheduler; never retry a possibly submitted call."""
    initialize()
    with _db() as db:
        db.execute("""UPDATE scheduled_messages SET status='unknown',
            error_message='Backend stopped during a send; verify the result manually.',
            executed_at=COALESCE(executed_at, ?)
            WHERE status='processing'""", (time.time(),))
    logger.info('Scheduled WhatsApp jobs recovered; interrupted sends require manual review.')


def _aware_time(value: str) -> float:
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(400, 'scheduled_time must be a valid ISO 8601 timestamp.') from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HTTPException(400, 'scheduled_time must include a UTC offset or Z timezone.')
    timestamp = parsed.astimezone(timezone.utc).timestamp()
    if timestamp <= time.time():
        raise HTTPException(400, 'scheduled_time must be in the future.')
    return timestamp


class ScheduleInput(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=100)
    template_name: str = Field(min_length=1, max_length=512)
    template_language: str = Field(min_length=2, max_length=20)
    template_parameters: list[str] = Field(default_factory=list, max_length=5)
    scheduled_time: str = Field(min_length=20, max_length=40)
    timezone: str = 'America/Toronto'

    @field_validator('recipients')
    @classmethod
    def validate_recipients(cls, values):
        normalized = []
        for value in values:
            digits = re.sub(r'\D', '', value)
            if not re.fullmatch(r'[1-9][0-9]{6,19}', digits):
                raise ValueError('Each recipient must be a WhatsApp number with a country code.')
            if digits in normalized:
                raise ValueError('A recipient cannot appear more than once in a schedule.')
            normalized.append(digits)
        return normalized

    @field_validator('template_name')
    @classmethod
    def validate_template_name(cls, value):
        if not re.fullmatch(r'[a-z0-9_]{1,512}', value.strip()):
            raise ValueError('Choose a valid Meta template name.')
        return value.strip()

    @field_validator('template_language')
    @classmethod
    def validate_language(cls, value):
        if not re.fullmatch(r'[a-z]{2,3}(?:_[A-Z]{2})?', value):
            raise ValueError('Use a valid template language code such as en or en_US.')
        return value

    @field_validator('template_parameters')
    @classmethod
    def validate_parameters(cls, values):
        if any(not isinstance(value, str) or not value.strip() or len(value) > 1024 for value in values):
            raise ValueError('Template parameter values must contain 1 to 1024 characters.')
        return [value.strip() for value in values]

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('Use a valid IANA timezone, for example America/Toronto.') from None
        return value


def _contact_rows(recipients: list[str]):
    with _db() as db:
        rows = []
        for phone in recipients:
            row = db.execute('SELECT id,wa_id,consent FROM wa_contacts WHERE wa_id=?', (phone,)).fetchone()
            if not row:
                raise HTTPException(400, 'Every recipient must be an existing contact.')
            if row['consent'] != 'granted':
                raise HTTPException(403, 'Every recipient must have recorded permission to receive WhatsApp messages.')
            allowed = {value.strip() for value in os.getenv('WHATSAPP_ALLOWED_SENDERS', '').split(',') if value.strip()}
            if allowed and phone not in allowed:
                raise HTTPException(403, 'A recipient is outside WHATSAPP_ALLOWED_SENDERS.')
            rows.append(dict(row))
    return rows


@router.get('/templates')
async def approved_templates(language: str | None = None):
    """Return actual Meta-approved text templates, optionally filtered by language."""
    return {'templates': await list_approved_templates(language)}


@router.post('')
async def create_schedule(request: ScheduleInput):
    when = _aware_time(request.scheduled_time)
    recipients = _contact_rows(request.recipients)
    template = await verify_template(request.template_language, request.template_name, max_parameters=5)
    if len(request.template_parameters) != template['parameter_count']:
        raise HTTPException(400, f"This template requires {template['parameter_count']} parameter value(s).")
    # Validate the resulting Meta component before persisting the batch.
    template_payload(template, '', request.template_parameters)
    schedule_id = str(uuid.uuid4())
    now = time.time()
    with _db() as db:
        db.execute('BEGIN IMMEDIATE')
        for contact in recipients:
            # Recheck consent and allowlist at the write boundary.
            fresh = db.execute('SELECT consent FROM wa_contacts WHERE id=?', (contact['id'],)).fetchone()
            if not fresh or fresh['consent'] != 'granted':
                raise HTTPException(403, 'Recipient permission changed; no schedule was created.')
            db.execute('''INSERT INTO scheduled_messages
                (id,schedule_id,contact_id,recipient_phone,template_name,template_language,
                 template_parameters,scheduled_time,timezone,status,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,'pending',?)''',
                (str(uuid.uuid4()), schedule_id, contact['id'], contact['wa_id'],
                 request.template_name, request.template_language,
                 json.dumps(request.template_parameters), when, request.timezone, now))
    return {'schedule_id': schedule_id, 'status': 'pending', 'recipient_count': len(recipients),
            'template_name': request.template_name, 'template_language': request.template_language,
            'scheduled_time': datetime.fromtimestamp(when, timezone.utc).isoformat(),
            'timezone': request.timezone}


def list_schedules():
    initialize()
    with _db() as db:
        rows = db.execute('''SELECT s.*,c.name AS contact_name FROM scheduled_messages s
            JOIN wa_contacts c ON c.id=s.contact_id
            ORDER BY s.scheduled_time DESC,s.created_at DESC LIMIT 500''').fetchall()
    groups: dict[str, dict] = {}
    for row in rows:
        value = dict(row)
        item = groups.get(value['schedule_id'])
        if item is None:
            item = {'schedule_id': value['schedule_id'], 'template_name': value['template_name'],
                    'template_language': value['template_language'],
                    'template_parameters': json.loads(value['template_parameters']),
                    'scheduled_time': datetime.fromtimestamp(value['scheduled_time'], timezone.utc).isoformat(),
                    'timezone': value['timezone'], 'created_at': datetime.fromtimestamp(value['created_at'], timezone.utc).isoformat(),
                    'recipients': [], 'status': 'pending'}
            groups[value['schedule_id']] = item
        item['recipients'].append({'contact_name': value['contact_name'],
            'phone': '+' + value['recipient_phone'], 'status': value['status'],
            'executed_at': datetime.fromtimestamp(value['executed_at'], timezone.utc).isoformat()
                if value['executed_at'] else None,
            'error': value['error_message'], 'whatsapp_message_id': value['whatsapp_message_id']})
    for item in groups.values():
        statuses = {recipient['status'] for recipient in item['recipients']}
        item['status'] = (next(iter(statuses)) if len(statuses) == 1 else
                          'partial' if statuses <= {'submitted', 'failed', 'unknown'} else 'processing')
    return list(groups.values())


@router.get('')
async def schedules_list():
    return {'schedules': list_schedules()}


async def _submit(row: dict) -> None:
    """One HTTP attempt after a durable claim. Ambiguous outcomes are never retried."""
    try:
        template = await verify_template(row['template_language'], row['template_name'], max_parameters=5)
        parameters = json.loads(row['template_parameters'])
        body = {'messaging_product': 'whatsapp', 'recipient_type': 'individual',
                'to': row['recipient_phone'], 'type': 'template',
                'template': template_payload(template, '', parameters)}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"https://graph.facebook.com/{os.environ['WHATSAPP_GRAPH_VERSION']}/"
                f"{os.environ['WHATSAPP_PHONE_NUMBER_ID']}/messages",
                headers={'Authorization': f"Bearer {os.environ['WHATSAPP_ACCESS_TOKEN']}",
                         'Content-Type': 'application/json'}, json=body)
        if not response.is_success:
            try:
                check_meta_response(response)
            except HTTPException as exc:
                _finish(row['id'], 'failed', error=str(exc.detail))
                return
            _finish(row['id'], 'failed', error='WhatsApp rejected the template request.')
            return
        payload = response.json()
        provider_id = payload['messages'][0]['id']
        if not isinstance(provider_id, str) or not provider_id:
            raise ValueError('Missing WhatsApp message ID')
        _finish(row['id'], 'submitted', provider_id=provider_id)
    except HTTPException as exc:
        # Template/account verification failed before a message POST was made.
        _finish(row['id'], 'failed', error=str(exc.detail))
    except (httpx.TimeoutException, httpx.TransportError, ValueError, KeyError, TypeError):
        # Transport failure or unreadable response may have happened after acceptance.
        _finish(row['id'], 'unknown', error='WhatsApp submission outcome is uncertain; verify manually before retrying.')
    except Exception:
        _finish(row['id'], 'unknown', error='WhatsApp submission outcome is uncertain; verify manually before retrying.')
        logger.warning('Scheduled WhatsApp send ended with an uncertain outcome.')


def _finish(identifier: str, status: Literal['submitted', 'failed', 'unknown'],
            *, error: str = '', provider_id: str | None = None) -> None:
    with _db() as db:
        db.execute('''UPDATE scheduled_messages SET status=?,executed_at=?,error_message=?,
            whatsapp_message_id=? WHERE id=? AND status='processing' ''',
            (status, time.time(), error[:240], provider_id, identifier))
    logger.info('Scheduled WhatsApp recipient completed: status=%s.', status)


async def run_due_once() -> int:
    initialize()
    claimed = []
    now = time.time()
    with _db() as db:
        db.execute('BEGIN IMMEDIATE')
        rows = db.execute("""SELECT * FROM scheduled_messages
            WHERE status='pending' AND scheduled_time<=? ORDER BY scheduled_time,created_at""", (now,)).fetchall()
        for row in rows:
            changed = db.execute("UPDATE scheduled_messages SET status='processing' WHERE id=? AND status='pending'",
                                 (row['id'],))
            if changed.rowcount:
                claimed.append(dict(row))
    for row in claimed:
        await _submit(row)
    return len(claimed)


async def scheduler_worker() -> None:
    recover_after_restart()
    logger.info('Scheduled WhatsApp worker started.')
    while True:
        try:
            await run_due_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning('Scheduled WhatsApp worker could not process the queue; it will retry the scan.')
        await asyncio.sleep(POLL_SECONDS)
