"""Offline-by-default tests: no private environment files or provider traffic."""

import os
import socket
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

# This must happen before test modules import app and call load_dotenv.
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
# Also support older installed dotenv versions until dependencies are refreshed.
_dotenv_patch = patch('dotenv.load_dotenv', return_value=False)
_dotenv_patch.start()
for name in list(os.environ):
    if name.startswith(('WHATSAPP_', 'OPENAI_', 'APP_ACCESS_', 'REALTIME_')):
        os.environ.pop(name)

# Keep collection/import-time initialization away from the real databases too.
_storage = TemporaryDirectory(prefix='voice-tests-')
os.environ['INBOX_DB_PATH'] = _storage.name + '/inbox.sqlite3'
os.environ['VOICE_FEEDBACK_DB_PATH'] = _storage.name + '/voice_feedback.db'
os.environ['VOICE_FEEDBACK_AUDIO_DIR'] = _storage.name + '/audio'
os.environ['ALLOWED_ORIGINS'] = 'http://localhost:5173,http://127.0.0.1:5173'


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    def blocked(*_args, **_kwargs):
        raise AssertionError('External network access is forbidden in tests. Mock the provider.')

    original_connect = socket.socket.connect

    def connect(sock, address):
        # asyncio uses local socket pairs; permit only Unix-domain sockets.
        if sock.family == socket.AF_UNIX:
            return original_connect(sock, address)
        return blocked()

    monkeypatch.setattr(socket, 'create_connection', blocked)
    monkeypatch.setattr(socket.socket, 'connect', connect)
    monkeypatch.setattr(socket.socket, 'connect_ex', blocked)


def pytest_sessionfinish(session, exitstatus):
    _dotenv_patch.stop()
    _storage.cleanup()
