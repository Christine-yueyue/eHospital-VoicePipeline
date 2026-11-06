# Stage 03 — Test Architecture and CI Design

You are the QA test architect. Read COMMON.md and stages 01–02. Create English Markdown design deliverables only. Do not install or probe tools.

## Work

1. Propose an isolated test layout under qa/voice_pipeline for Python Playwright pytest code, test requirements, server fixtures, test docs, and a shared approved WAV.
2. Propose a standalone .github/workflows/voice-pipeline-regression.yml without changing the existing security-tests workflow or production application modules.
3. Evaluate a same-process pytest runner that starts the ASGI app with existing Upload service functions monkeypatched and the paired Live connector replaced by scripted upstreams, then runs headless Playwright against Flutter Web. Compare it with UI-only route mocks and accurately state the coverage gap of each.
4. Document how a disposable app token, loopback ports, pytest temporary SQLite/audio paths, dotenv disabling, external network blocking, and fixture cleanup avoid secrets/data leakage.
5. Identify feasibility questions for Flutter browser semantics, visible result locators, file-picker injection, Chromium fake-audio playback EOF/restart, captured non-empty PCM, and server startup/shutdown. Do not assume a verified answer.
6. Define how the same recording is reused: WAV for Upload and virtual microphone source for Live. Explain resampling and distinct transported bytes.
7. Specify event-based waits and bounded timeouts. The Stop case must verify both upstreams finish and the final text is rendered. Do not equate HTTP success with full pipeline success.
8. Keep all new test support out of frontend/ and backend/. If an app-level selector or service seam proves necessary, mark it as a separate proposal and gate.
9. Define redacted CI evidence and dependency pin/version review. Avoid recording tokens, authorization headers, private audio, or unredacted trace state.

## Deliverables

- outputs/03-test-architecture.md
- outputs/03-ci-plan.md

## Completion criteria

The architecture names each process, boundary, data store, fake provider, and evidence source. All runner assumptions have concrete validation spikes. Proposed CI requires no real provider key or network. No implementation is claimed. Stop after this stage.
