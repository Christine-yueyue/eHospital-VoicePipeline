# 04 — Browser Test Case Design

Status: planned; cases have not been implemented or run. Cases assert only scripted behavior unless explicitly marked as a real-provider check.

## Shared fixture

The Upload and Live path tests must use the same immutable English speech recording from 04-audio-fixtures.md. Upload passes the WAV file bytes. Live plays the same WAV through Chromium's virtual microphone; the browser/Flutter recorder sends captured mono 24 kHz PCM16. The transformed payload is not expected to be byte-identical.

All stable cases run with a temporary backend database and local provider doubles. All Live cases launch a fresh browser context with a fresh audio input so no earlier recording can remain in the device stream.

## Stable CI test cases

| Test ID | Priority | Mode / layer | Setup and action | Expected result and evidence |
| --- | --- | --- | --- | --- |
| TC-001 | P1 | Mock / browser + isolated FastAPI Upload | Connect using a per-run local token. Select the shared WAV fixture. Choose French. Submit Upload & transcribe. | The multipart call contains the WAV fixture, target language is French, the test transcription and translation doubles were each called once, UI panes contain their respective expected text, app returns idle, and the temporary DB contains one completed upload row and audio file. Capture case log and state. |
| TC-002 | P1 | Mock / browser + isolated FastAPI Upload | Select the same fixture. Configure the translation double to fail after transcription succeeds. Submit. | Original transcript remains visible, translation error is actionable, successful audio/transcript persistence follows the save setting, and the UI returns idle. |
| TC-003 | P2 | Mock / browser + isolated FastAPI Upload | Try an empty or unsupported file using the file picker. | No upstream double call occurs; visible validation explains the issue and a valid fixture can still be selected and submitted. Keep oversize limit testing in backend unit tests unless preparing an oversized browser asset adds value. |
| TC-004 | P1 | Mock / browser + isolated FastAPI Live | Start Live with the virtual capture device playing the shared fixture. Verify an audio frame reaches both fakes. When the controlled playback test signals the stop point, press Stop. | Button/state moves through connecting/listening/finishing back to idle; both upstreams receive audio; no real provider is contacted. Test evidence includes captured byte counts and observed event timeline. |
| TC-005 | P1 | Mock / browser + isolated FastAPI Live | Both fakes emit incremental source/translation text. On Stop, source transcription fake emits a final corrected sentence that changes the last word, then translation close and completion resolve. | The final original panel contains the corrected last word, the translation panel contains the scripted final translation, and the UI returns idle only after the done event. This is the key last-word regression. |
| TC-006 | P1 | Mock / browser + isolated FastAPI Live | Emit an initial source caption. Abort the backend WebSocket mid-session. Then start a second session with different scripted text and stop normally. | First caption stays visible alongside a useful error; busy state clears; second session starts clean; no old delta/final event appears in either second-session panel. |
| TC-007 | P2 | Mock / browser | Deny microphone permission, then allow it in a fresh context and provide a silent source. | Denial does not reach listening or the provider fakes; silent capture fails via the expected watchdog with a visible error. Make “permission denied” and “permission granted but no audio” separate result assertions. |
| TC-008 | P1 | Mock / browser + isolated database | Toggle Save to Database off. Run one successful Upload and one successful Live completion. Query only this test run's temporary DB and audio directory. | Both flows succeed while adding no new audio file or feedback row. Restore the setting only inside the isolated test fixture or dispose of its DB. |
| TC-009 | P2 | Mock / browser + isolated database | Toggle Save to Database on and complete a successful Live session. | Exactly one completed live record has the scripted original, translation, and target language. No live audio file is expected because the product saves completed Live text, not live audio. |
| TC-010 | P2 | Mock / browser + isolated FastAPI | Connect with a wrong test token; then connect with the correct temporary token. | Wrong token cannot enable the app, Upload, or Live; correct token connects without exposing the token in artifact output. Backend auth unit tests remain the source of protocol edge coverage. |
| TC-011 | P2 | Mock / browser + isolated FastAPI Live | Start Live, inject malformed or unexpected provider event/control sequence within the test double, and press Stop or allow a bounded wait. | UI surfaces a recoverable error, avoids a permanent busy state, keeps text already displayed, and accepts a fresh session. Reuse backend protocol tests for exhaustive invalid-frame cases. |
| TC-012 | P2 | Real provider / manual bounded run | Through each path, use the same approved recording once per authorized scenario, record source result, translation and latency, and compare key facts with the reference. | Human-reviewed result records correct/incorrect negation, date/time, language, and missing/added facts. Do not put this case in PR CI or assert one exact provider sentence. |

## Browser waiting and evidence rules

- Find controls and results by semantic role, visible label, or a verified stable accessible name. Do not use screen coordinates as the normal selector.
- Wait for expected request/response, WebSocket event, and rendered state using event-based conditions with explicit maximum timeouts.
- Do not use a generic quiet-network condition to decide a live WebSocket is finished.
- For Stop, assert the actual sequence: user action, both upstream completion signals, server done, UI idle, final original and translation.
- Every case reports PASS, FAIL, BLOCKED, or NOT RUN with the same test ID and sanitized evidence location.
- Model-generated explanations may help triage real content but cannot alone pass a deterministic CI case.

## Outstanding case details

TC-004 playback completion must not rely on an unverified fake WAV end-of-file behavior or arbitrary long sleeps. The feasibility spike must identify a deterministic signal for “one fixture playback reached its stop point.” If Chromium loops the file, use a test-owned one-shot audio playback source within qa/voice_pipeline while still exercising the app's normal browser capture API, or block and report the limitation.
