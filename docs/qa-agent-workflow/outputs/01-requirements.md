# 01 — Requirements and Acceptance Criteria

Status: design based on source inspection. No browser test, provider call, or application test was run.

## Scope

The first release target is the English-language Flutter Web UI and FastAPI backend. The same short, non-sensitive voice fixture is the input asset for two separately tested flows:

1. Upload the fixture as a file and verify backend transcription, translation, UI results, and persistence behavior.
2. Play the fixture through Chromium's virtual microphone and verify WebSocket audio delivery, live captions, stop finalization, disconnect recovery, and a clean next session.

The fixture's recording is the same source asset in both flows. The live browser captures and resamples it as 24 kHz mono PCM16, so the bytes sent to the Live upstream are expected to differ from the uploaded WAV bytes. Mocked regressions verify transport and event handling; only real-provider checks assess speech recognition and translation quality.

Out of scope: WhatsApp delivery or assistant behavior, iOS hardware and permission behavior, production deployment, and automatic real-provider checks on each commit.

## Current implementation evidence

- The web page presents Upload and Speak Live controls, target language selection, persistence setting, and separate original/translation results: frontend/lib/main.dart.
- Upload accepts ogg, opus, mp3, wav, m4a, and webm, checks a configured size limit, posts to /api/transcribe, and displays returned transcript and translation: frontend/lib/voice_controller.dart; backend/app.py.
- Upload stores audio and a completed transcript record when the global Save to Database setting is enabled. A translation error can accompany a successful transcript: backend/app.py; backend/voice_feedback.py.
- Live requests microphone permission, opens /api/live as a WebSocket, sends an authentication frame before audio, and records mono 24 kHz PCM16: frontend/lib/voice_controller.dart.
- Live source captions and translation deltas arrive independently. A final source transcript can replace partial text. Stop requests a provider close and a transcription commit, then waits for both upstream sessions before done: frontend/lib/voice_controller.dart; backend/live.py.
- Live persists completed text and translation when saving is enabled; it does not persist live audio: backend/live.py; backend/voice_feedback.py.
- The connection page asks for backend address and app token: frontend/lib/connection_page.dart.
- Backend unit tests already use monkeypatched transcription/translation functions and fake paired Live upstreams. The security-tests workflow runs backend pytest on pull requests and pushes: backend/tests/test_backend.py; .github/workflows/security-tests.yml.
- Existing source shows Flutter widget and connection tests. They are not browser Playwright tests.

## Requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| REQ-001 | The test suite uses one approved, repeatable, non-sensitive voice fixture for both Upload and Live. | AC-001: The fixture manifest identifies the same immutable source recording and verified checksum in both test cases; each test creates its own input instance from it. |
| REQ-002 | Upload handles a valid supported audio file. | AC-002: The UI selects the fixture, sends the expected target language, renders the returned original and translation in their correct result areas, and returns to idle. |
| REQ-003 | Upload errors remain useful and recoverable. | AC-003: Empty/unsupported or oversized input produces an actionable error; a transcription error is visible; translation failure preserves the successful original transcript. |
| REQ-004 | Save behavior is verifiable in an isolated database. | AC-004: With saving enabled, exactly one completed upload record contains the expected source and transcript; with saving disabled, no new record or audio file is written. |
| REQ-005 | Live sends browser-captured audio through the authenticated WebSocket. | AC-005: The test observes ready, authentication before binary audio, and non-empty audio reaching both expected upstream sessions; the run contains no real provider request. |
| REQ-006 | Live preserves and finalizes source and translation text. | AC-006: The test observes source deltas, a final source transcript that may correct partial text, translation deltas, and done; Stop resolves to idle and the final text remains displayed. |
| REQ-007 | Live Stop drains the final words. | AC-007: The scripted upstream emits a final-word correction only after the test presses Stop; the final UI contains that correction after done. |
| REQ-008 | Live disconnect and recovery do not lose displayed text or contaminate the next session. | AC-008: A forced mid-session disconnect preserves existing text and displays a recoverable error; a subsequent session starts clean and shows only its own scripted result. |
| REQ-009 | Microphone denial and absent audio fail visibly. | AC-009: A denied permission does not enter listening; a granted but silent/missing input reports a useful error within the defined watchdog window. |
| REQ-010 | The repeatable regression is safe for CI. | AC-010: Pull-request CI runs only local deterministic doubles and non-sensitive fixture data, writes to a temporary database, needs no external API secrets, and fails on any unmocked outbound network attempt. |
| REQ-011 | Tests and test helpers are separated from application implementation. | AC-011: New browser tests, fixtures, Python dependencies, launch helpers, and docs are kept under qa/voice_pipeline; one dedicated GitHub Actions workflow references that directory. No files under backend application modules, frontend/lib, backend/tests, or frontend/test are changed by the planned Playwright implementation. |

## Open validation

- Playwright's supported Python version and browser installation must be aligned with the existing CI Python matrix.
- Flutter Web semantic locators and file picker injection must be verified in the actual headless CI runner.
- Chromium fake microphone playback termination/restart behavior must be verified to prevent fixture looping between Live sessions.
- A stable upstream test seam must be proven without changing application modules. The design proposes starting the ASGI app in the test process with existing functions monkeypatched, and using scripted Live upstreams as existing backend tests do.
- Fixture provenance, human-verified speech content, checksum, duration, sample rate, and license/permission must be recorded when the real recording is prepared.
- The exact persistence tables/columns are implementation details for the future test harness and must be checked against voice_feedback.py before assertions are implemented.

## Next phase

Use these requirements to rank risks and choose a layered test strategy. Treat all environment-dependent claims above as unverified until a feasibility check is executed.
