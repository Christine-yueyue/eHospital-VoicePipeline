# Voice Notes browser and API tests

All files in this directory are test infrastructure. The tests do not add or
change application code under `backend/` or `frontend/`.

## Coverage

- Playwright sends the upload request to a real, isolated FastAPI app running on
  an ephemeral loopback port.
- The upload provider calls are replaced in-process with scripted doubles.
  Backend validation, transcription, translation, and temporary SQLite
  persistence are exercised. No OpenAI or WhatsApp request is made.
- The shared WAV is a generated tone. It verifies non-empty captured PCM and
  request wiring only; it is not speech-recognition input.
- Artillery runs a bounded, read-only HTTP smoke against `/health` and
  authenticated `/api/config`. It does not send audio or mutate app settings.

The test location is intentionally separate from all business code. Do not put
test helpers or test-only switches in `backend/` or `frontend/`.

## Local setup

Requirements: Python 3.11+, the project's backend requirements, Node.js with
npm, and Flutter/Dart versions from `frontend/pubspec.yaml`.

From the repository root:

```sh
python3 -m pip install -r backend/requirements.txt -r qa/voice_pipeline/requirements.txt
python3 -m playwright install chromium
python3 qa/voice_pipeline/create_fixture.py
```

In another terminal, from the repository root:

```sh
PYTHONPYCACHEPREFIX=/tmp/voice-pipeline-pycache python3 -m pytest -c qa/voice_pipeline/pytest.ini qa/voice_pipeline/tests
```

The Playwright fixture starts its own backend and uses a random app token plus
temporary database and audio paths. It disables `python-dotenv` before the app
is imported and never opens a developer `.env` file. The Flutter Web app can
still be started separately for manual UI verification.

## Artillery smoke

In a terminal from the repository root, start a disposable backend on loopback.
These paths and credentials are test-only and remain under `/tmp`:

```sh
mkdir -p /tmp/voice-pipeline-artillery/audio
cd backend
APP_ACCESS_TOKEN=qa-local-only-token \
PYTHON_DOTENV_DISABLED=1 \
INBOX_DB_PATH=/tmp/voice-pipeline-artillery/inbox.sqlite3 \
VOICE_FEEDBACK_DB_PATH=/tmp/voice-pipeline-artillery/voice_feedback.sqlite3 \
VOICE_FEEDBACK_AUDIO_DIR=/tmp/voice-pipeline-artillery/audio \
python3 -m uvicorn app:app --host 127.0.0.1 --port 8003 --no-access-log
```

In a second terminal, run the bounded Artillery script:

```sh
cd qa/voice_pipeline
APP_ACCESS_TOKEN=qa-local-only-token \
npx --yes artillery@2.0.25 run artillery/smoke.yml
```

The Artillery script makes only GET requests. Its target is loopback, its
traffic is limited to one new virtual user per second for ten seconds, and its
API request uses `APP_ACCESS_TOKEN` from the process environment.

## Results and limits

Playwright reports case names and assertions through pytest. Traces and
screenshots are not enabled by default, to avoid recording user-entered values.
The Artillery smoke is a connectivity/load-generator check, not a capacity
benchmark. The fixed waveform and fake provider responses establish no claim
about real transcription quality, external availability, or production
throughput.

Flutter Web accessibility semantics and Chromium's one-shot fake audio behavior
must be checked on the target runner. The Live test explicitly stops the
session after both doubles observe non-empty PCM, so it does not rely on WAV
end-of-file behavior.
