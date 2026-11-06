# 03 — Test Architecture and Code Boundary

Status: proposed architecture. Playwright, Chromium audio injection, and the same-process backend harness have not yet been installed or exercised.

## Proposed layout

```text
qa/voice_pipeline/
  README.md
  requirements.txt
  pytest.ini
  conftest.py
  fixtures/
    manifest.json
    sample_en.wav
  test_upload_flow.py
  test_live_flow.py

.github/workflows/
  security-tests.yml
  voice-pipeline-regression.yml
```

All new Playwright tests, launcher/server fixtures, dependencies, test audio, and test-specific documentation stay under qa/voice_pipeline. The workflow file is CI infrastructure. The plan adds no product code or tests under backend/ or frontend/ and adds no production runtime test switch.

## Runner and provider doubles

Use Python pytest plus Playwright's Python API so the test module can import the FastAPI app, patch service functions/upstream connectors in-process, start a local Uvicorn server on a reserved ephemeral loopback port, and drive Chromium in the same Python process. Serve the Flutter web build from a second local port.

Before starting the app server, set a per-run APP_ACCESS_TOKEN, SQLite paths for VOICE_FEEDBACK_DB_PATH and INBOX_DB_PATH, and VOICE_FEEDBACK_AUDIO_DIR under pytest's temporary directory. Disable python-dotenv loading, remove provider keys from the child environment, and fail if a provider connector was not replaced by a test double. Never read a developer .env file.

For Upload, patch the function imported by backend.app for transcription and translation. Assert the transcription stub receives a non-empty supported fixture file, return deterministic known text, and return a separate deterministic translation. A second stub sequence raises only for translation to check the partial-success behavior.

For Live, patch live.connect with two independent scripted async context managers, one translation session and one source-transcription session, mirroring FakeUpstream and FakeTranscriptionUpstream in backend/tests/test_backend.py. Record every provider-directed audio append and control message. The fake source transcript ends in a corrected final word that is emitted only after the transcription commit. The translation stream emits a known translation; error schedules cover premature close and disconnect.

Start Chromium with the supported fake audio-capture flags pointing at the approved WAV fixture. Verify on the actual runner whether the device starts at the beginning, whether it loops, how it stops, and whether it captures nonzero samples. Reset/relaunch context for each Live test. If timing is unstable, use a test-owned Web Audio input with an explicit playback-complete signal; any injection must remain under qa/ and must exercise Flutter's normal getUserMedia/record path.

The fixture has two roles: Upload submits the file itself; Live plays that file to the virtual input and captures transformed PCM. Verify fixture identity through manifest/checksum and verify PCM delivery separately. Do not compare WAV bytes with resampled PCM bytes.

## Playwright locators and UI

The Flutter page uses Material widgets and text labels; existing Flutter tests address widgets using finder APIs. Browser semantics behavior is unverified. Start the first feasibility check with Playwright role/name and label locators for Connection settings, Server address, App access token, Connect, Choose audio file, Upload & transcribe, Start speaking, Stop & finish, result headings, and save switch.

If Chromium does not expose stable semantics, investigate Flutter Web accessibility activation and browser semantics before adding any code. If a production Flutter annotation or semantics edit is essential, record a separate production-code change request and stop the Playwright-only implementation. Do not bury production edits inside qa/ or ship a test-only build branch.

## Test data and storage

Prepare one short, clear English utterance, e.g. “My appointment is Friday at three.” It contains a date/time fact for later real-provider review and has no patient or private information. Record a synthetic/consented voice; document provenance, license/consent, human-checked reference text, SHA-256, WAV codec, channel count, sample rate, and duration in the manifest. The asset is a deliverable to prepare during implementation, not one already present.

Each pytest run owns its SQLite files, audio directory, browser context, server ports, logs, and test token. Tests read only their temporary database to assert record counts and fields. Close browsers, stop only fixture-started processes, and delete temporary files unless sanitized failure evidence is deliberately retained outside the database/audio directory.

## Evidence and redaction

Capture case ID and step, UI text/state, status outcome, backend test-double observations, browser errors, and a trace or screenshot on failure. Use a transient token with no access outside the ephemeral local test backend. Avoid preserving real speech, file contents, HTTP request bodies, authorization headers, or environment dumps in general CI artifacts. Keep the approved fixture's reference answer separately from runtime secrets.

## Dependency proposal

Keep browser-test dependencies separate from backend and Flutter application dependencies. Add a Python test requirements file under qa/voice_pipeline with version-bounded pytest and Playwright packages. Install the browser explicitly in the workflow. Use existing backend requirements through the workflow without editing backend/requirements*. Keep Flutter dependencies unchanged.

## Feasibility gates

1. Confirm flutter toolchain and web-server/build mode on the hosted runner.
2. Confirm the web app exposes controls/results through stable locators.
3. Confirm Playwright can inject the WAV into the actual record package and can detect/reset playback deterministically.
4. Confirm a pytest fixture can serve the backend with monkeypatched existing provider functions/upstreams while the browser communicates over local HTTP and WebSocket.
5. Confirm multipart request verification, double audio-frame observations, persistence isolation, cleanup, and trace sanitization.

Record every result as passed, failed, blocked, or untested. These are implementation-time spikes; the current design phase did not perform them.
