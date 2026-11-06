"""Scheduled WhatsApp behavior; all provider requests are mocked."""

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import httpx
import pytest
from fastapi.testclient import TestClient

import app as backend
import followup
import scheduled_messages as scheduled
import voice_feedback


@pytest.fixture
def client(monkeypatch, tmp_path):
    for key, value in {
        'APP_ACCESS_TOKEN': 'schedule-app-token', 'WHATSAPP_ACCESS_TOKEN': 'meta-test-token',
        'WHATSAPP_PHONE_NUMBER_ID': '111', 'WHATSAPP_WABA_ID': '222',
        'WHATSAPP_GRAPH_VERSION': 'v23.0', 'WHATSAPP_FOLLOWUP_TEMPLATE_NAME': 'custom_template',
        'WHATSAPP_ALLOWED_SENDERS': '', 'VOICE_FEEDBACK_DB_PATH': str(tmp_path / 'feedback.db'),
        'VOICE_FEEDBACK_AUDIO_DIR': str(tmp_path / 'audio'), 'INBOX_DB_PATH': str(tmp_path / 'inbox.db'),
    }.items():
        monkeypatch.setenv(key, value)
    with TestClient(backend.app, headers={'Authorization': 'Bearer schedule-app-token'}) as test_client:
        yield test_client


TEMPLATE = {'name': 'hello_world', 'language': 'en_US', 'body': 'Hello {{1}}',
           'parameter_count': 1, 'preview': 'Hello {{1}}'}


def _recipient():
    return followup.create_contact('Test Contact', '+14165550123', consent='granted',
                                   consent_source='Test consent record')['wa_id']


def _request(phone, **updates):
    body = {'recipients': [phone], 'template_name': 'hello_world', 'template_language': 'en_US',
            'template_parameters': ['Pat'],
            'scheduled_time': '2030-01-02T10:00:00-05:00', 'timezone': 'America/Toronto'}
    body.update(updates)
    return body


def _set_due(schedule_id):
    with sqlite3.connect(voice_feedback.database_path()) as db:
        db.execute('UPDATE scheduled_messages SET scheduled_time=? WHERE schedule_id=?',
                   (time.time() - 1, schedule_id))


def test_create_schedule_persists_group_and_requires_verified_template(client, monkeypatch):
    phone = _recipient()
    monkeypatch.setattr(scheduled, 'verify_template', lambda *args, **kwargs: asyncio.sleep(0, result=dict(TEMPLATE)))
    response = client.post('/api/whatsapp/schedules', json=_request(phone))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['status'] == 'pending'
    assert result['recipient_count'] == 1
    listed = client.get('/api/whatsapp/schedules').json()['schedules']
    assert listed[0]['schedule_id'] == result['schedule_id']
    assert listed[0]['recipients'][0]['status'] == 'pending'


def test_distinct_schedule_times_round_trip_through_database_and_get(client, monkeypatch):
    phone = _recipient()
    monkeypatch.setattr(scheduled, 'verify_template', lambda *args, **kwargs: asyncio.sleep(0, result=dict(TEMPLATE)))
    local_times = [
        datetime(2030, 1, 2, 10, 0, tzinfo=ZoneInfo('America/Toronto')),
        datetime(2030, 1, 2, 12, 30, tzinfo=ZoneInfo('America/Toronto')),
    ]
    expected_utc = [value.astimezone(timezone.utc) for value in local_times]
    created = []

    for local_time in local_times:
        response = client.post('/api/whatsapp/schedules', json=_request(
            phone, scheduled_time=local_time.isoformat()))
        assert response.status_code == 200, response.text
        created.append(response.json())

    # SQLite stores epoch seconds in UTC; verify persistence independently of GET.
    with sqlite3.connect(voice_feedback.database_path()) as db:
        stored = [db.execute(
            'SELECT scheduled_time FROM scheduled_messages WHERE schedule_id=?',
            (item['schedule_id'],),
        ).fetchone()[0] for item in created]
    assert stored == pytest.approx([value.timestamp() for value in expected_utc])

    for item, expected in zip(created, expected_utc):
        assert datetime.fromisoformat(item['scheduled_time']) == expected

    listed = client.get('/api/whatsapp/schedules').json()['schedules']
    by_id = {item['schedule_id']: item for item in listed}
    assert set(by_id) == {item['schedule_id'] for item in created}
    for item, expected, local_time in zip(created, expected_utc, local_times):
        actual = datetime.fromisoformat(by_id[item['schedule_id']]['scheduled_time'])
        assert actual == expected
        assert actual.astimezone(ZoneInfo('America/Toronto')) == local_time


@pytest.mark.parametrize('changes', [
    {'recipients': []},
    {'recipients': ['not-a-number']},
    {'recipients': ['+14165550123', '14165550123']},
    {'scheduled_time': '2020-01-01T10:00:00-05:00'},
    {'scheduled_time': '2030-01-02T10:00:00'},
    {'template_parameters': []},
    {'timezone': 'No/Such_Zone'},
])
def test_invalid_schedules_are_rejected_without_rows(client, monkeypatch, changes):
    phone = _recipient()
    monkeypatch.setattr(scheduled, 'verify_template', lambda *args, **kwargs: asyncio.sleep(0, result=dict(TEMPLATE)))
    response = client.post('/api/whatsapp/schedules', json=_request(phone, **changes))
    assert response.status_code in {400, 422}
    assert client.get('/api/whatsapp/schedules').json()['schedules'] == []


def test_due_schedule_submits_correct_template_once(client, monkeypatch):
    phone = _recipient()
    monkeypatch.setattr(scheduled, 'verify_template', lambda *args, **kwargs: asyncio.sleep(0, result=dict(TEMPLATE)))
    result = client.post('/api/whatsapp/schedules', json=_request(phone)).json()
    _set_due(result['schedule_id'])
    calls = []

    class Response:
        is_success = True

        @staticmethod
        def json():
            return {'messages': [{'id': 'wamid.scheduled-test'}]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()

    monkeypatch.setattr(scheduled.httpx, 'AsyncClient', lambda **_kwargs: Client())
    assert asyncio.run(scheduled.run_due_once()) == 1
    assert asyncio.run(scheduled.run_due_once()) == 0
    assert len(calls) == 1
    payload = calls[0][1]['json']
    assert payload['to'] == phone
    assert payload['type'] == 'template'
    assert payload['template']['name'] == 'hello_world'
    assert payload['template']['language']['code'] == 'en_US'
    assert payload['template']['components'][0]['parameters'][0]['text'] == 'Pat'
    listed = client.get('/api/whatsapp/schedules').json()['schedules'][0]
    assert listed['status'] == 'submitted'
    assert listed['recipients'][0]['whatsapp_message_id'] == 'wamid.scheduled-test'


def test_timeout_becomes_unknown_and_restart_does_not_resend(client, monkeypatch):
    phone = _recipient()
    monkeypatch.setattr(scheduled, 'verify_template', lambda *args, **kwargs: asyncio.sleep(0, result=dict(TEMPLATE)))
    result = client.post('/api/whatsapp/schedules', json=_request(phone)).json()
    _set_due(result['schedule_id'])

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, *_args, **_kwargs):
            raise httpx.ReadTimeout('private detail should not escape')

    monkeypatch.setattr(scheduled.httpx, 'AsyncClient', lambda **_kwargs: Client())
    assert asyncio.run(scheduled.run_due_once()) == 1
    assert client.get('/api/whatsapp/schedules').json()['schedules'][0]['status'] == 'unknown'
    scheduled.recover_after_restart()
    assert asyncio.run(scheduled.run_due_once()) == 0
    assert client.get('/api/whatsapp/schedules').json()['schedules'][0]['status'] == 'unknown'


def test_interrupted_processing_is_flagged_after_restart(client):
    phone = _recipient()
    scheduled.initialize()
    with sqlite3.connect(voice_feedback.database_path()) as db:
        db.execute('''INSERT INTO scheduled_messages
            (id,schedule_id,contact_id,recipient_phone,template_name,template_language,
             template_parameters,scheduled_time,timezone,status,created_at)
            SELECT 'row-test','batch-test',id,?,'hello_world','en_US','[]',?,'America/Toronto','processing',?
            FROM wa_contacts WHERE wa_id=?''', (phone, time.time() - 10, time.time(), phone))
    scheduled.recover_after_restart()
    assert client.get('/api/whatsapp/schedules').json()['schedules'][0]['status'] == 'unknown'
