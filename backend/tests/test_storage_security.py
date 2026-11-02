"""Storage security tests that also run without third-party test dependencies."""

import os
import sqlite3
import stat
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import voice_feedback


class StorageSecurityTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(prefix='voice-storage-security-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        environment = patch.dict(os.environ, {
            'VOICE_FEEDBACK_DB_PATH': str(self.root / 'feedback.db'),
            'VOICE_FEEDBACK_AUDIO_DIR': str(self.root / 'audio'),
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.source = self.root / 'source.wav'
        self.source.write_bytes(b'private-audio')

    def test_new_audio_and_existing_database_have_private_permissions(self):
        database = voice_feedback.database_path()
        database.touch(mode=0o644)
        record = voice_feedback.store_audio(self.source, extension='.wav', mime_type='audio/wav')
        stored = voice_feedback.audio_directory() / record['file_name']
        self.assertEqual(stat.S_IMODE(stored.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(database.stat().st_mode), 0o600)
        self.assertEqual(stored.read_bytes(), b'private-audio')
        self.assertEqual(list(voice_feedback.audio_directory().glob('*.upload')), [])

    def test_untrusted_extension_cannot_introduce_directories(self):
        record = voice_feedback.store_audio(self.source, extension='../escape', mime_type=None)
        stored = voice_feedback.audio_directory() / record['file_name']
        self.assertEqual(stored.parent, voice_feedback.audio_directory())
        self.assertEqual(stored.suffix, '.audio')
        self.assertTrue(stored.exists())

    def test_failed_copy_leaves_no_audio_or_pending_record(self):
        def fail_copy(_input, output):
            output.write(b'partial-private-audio')
            raise OSError('Simulated disk failure')

        with patch.object(voice_feedback.shutil, 'copyfileobj', side_effect=fail_copy):
            with self.assertRaises(OSError):
                voice_feedback.store_audio(self.source, extension='.wav', mime_type='audio/wav')
        self.assertEqual(list(voice_feedback.audio_directory().iterdir()), [])
        with sqlite3.connect(voice_feedback.database_path()) as database:
            self.assertEqual(database.execute('SELECT COUNT(*) FROM voice_feedback').fetchone()[0], 0)

    def test_disabled_persistence_does_not_save_live_text(self):
        voice_feedback.set_save_to_database(False)
        self.assertIsNone(voice_feedback.save_live_feedback('private words', 'private translation', 'fr'))
        with sqlite3.connect(voice_feedback.database_path()) as database:
            self.assertEqual(database.execute('SELECT COUNT(*) FROM voice_feedback').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
