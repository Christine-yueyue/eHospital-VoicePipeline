# 02 — Test Strategy

Status: proposed strategy. The existing suite and new browser harness were not run during design.

## Modes and claims

| Mode | What runs | What a pass establishes | What it does not establish |
| --- | --- | --- | --- |
| Existing component regressions | Current backend pytest and Flutter widget/connection tests. | Existing service, API, and widget behavior passes in their own test environment. | That a browser can complete Upload or Live. |
| Stable Playwright CI regression | Headless Chromium with the Flutter Web app, a temporary FastAPI app, monkeypatched Upload provider functions, scripted paired Live upstreams, a temporary database/audio directory, and the shared fixture. | The browser can complete each deterministic UI flow; actual captured bytes reach the backend/test doubles; the controller renders expected scripted events and recovers from faults. | Actual speech recognition, translation quality, physical microphone behavior, or external provider availability. |
| Real voice quality check | A small manually authorized run with the same non-sensitive fixture through the configured provider. | In the observed sample, actual transcription and translation preserve checked facts and measured latency is recorded. | A deterministic PR gate, population-level accuracy, or guaranteed provider uptime. |
| Exploratory Agent review | A bounded browser session using test services to probe unusual sequences and report traces. | Additional operation sequences were attempted and any reproduced issue has evidence. | CI pass status unless a finding becomes a fixed regression with an objective assertion. |

The browser integration server should run in the pytest process. Its fixtures isolate the real app object by monkeypatching existing functions before starting the local ASGI server. Upload patches the imported transcription and translation functions. Live patches the existing upstream connector with two scripted async iterators. This follows patterns already present in backend/tests/test_backend.py and avoids changes to backend application modules.

If the same-process ASGI/Playwright harness proves too fragile, keep browser UI tests on Playwright route mocks and continue to rely on existing FastAPI tests for backend integration. Label that combination accurately as separate UI and backend coverage, not a browser-through-backend E2E path. Do not introduce a production-only mock mode to make CI work.

## CI scope

Add one dedicated workflow, .github/workflows/voice-pipeline-regression.yml, for the stable Playwright regression. Keep its test code and environment under qa/voice_pipeline. The existing security-tests workflow remains the owner of the backend/security suite. The new workflow should run for pull requests and pushes and support a manual run.

CI runs two browser flows from one fixture:

1. Upload path: select the WAV fixture, submit it to the isolated backend, assert request metadata and recorded bytes, assert transcript and translation panes, and verify persistence in the temporary database when enabled.
2. Live path: open the isolated authenticated WebSocket, grant the virtual microphone, verify actual non-empty captured PCM reaches both scripted upstreams, render source/translation deltas, press Stop, receive final words only after Stop, verify done and the completed temporary record.

Regression cases also cover upload translation failure, saving disabled, permission denial, mid-session disconnect with partial text, and a clean second Live session. Failure evidence uses safe snapshots, step logs, and sanitized traces.

## CI safety and reliability

- Do not configure OPENAI_API_KEY or WhatsApp secrets in the CI job.
- Use a per-run generated local app access token, loopback listeners, isolated temporary storage, and an explicit allowlist that denies all external network traffic from test-controlled application/provider code.
- Put a positive timeout on the job, each Playwright test, and server readiness. Fail on unexpected provider connections; do not retry flaky functional assertions to manufacture a pass.
- Keep browser tests sequential around the global save setting, or give each test its own process/database. Prefer per-run configuration with one suite worker initially.
- Start and stop only processes created by that job; always clean up temporary databases, audio, and browser profiles. Upload screenshots/traces only from a failure after masking form values, authorization headers, and content. The only fixture may be the approved non-sensitive test recording.
- Report backend and browser results independently. A passed browser flow must show both the relevant UI assertions and fake-upstream observations.
- Keep real-provider checks out of pull-request CI to avoid fees, secret provisioning, nondeterministic output, and network dependence.

## Coverage priorities

1. First gate: fixture select/upload success and Live stop/final-word success.
2. Add: Live partial caption + disconnect + fresh session.
3. Add: translation-only failure, permission denied, save enabled/disabled.
4. Add a real-service run only after stable regression exists and the fixture/reference answer is approved.

## Exit criteria

P1 cases pass repeatedly in a clean runner; test doubles are proven active before each test; no real provider traffic is observed; each flow uses the declared fixture; UI state returns to idle or displays the expected recoverable error; artifacts contain no credentials; and the workflow fails visibly on any assertion or runner error.
