# 03 — Continuous Integration Plan

Status: design proposal. No GitHub Actions configuration was added or run.

## Placement and trigger

Add a separate .github/workflows/voice-pipeline-regression.yml and keep its Playwright source, dependencies, fixtures, and test-server helpers in qa/voice_pipeline. Trigger on pull_request, push, and workflow_dispatch. Retain .github/workflows/security-tests.yml for its present backend/security coverage and dependency audit.

This workflow is CI configuration; it does not belong in Flutter UI or FastAPI application code. New production modules, branches, settings, and dependencies are not required in the design.

## Proposed job

Run one Ubuntu job with a fixed supported Python and pinned Flutter channel/version. Install backend requirements, qa/voice_pipeline test requirements, the Playwright Chromium browser, Flutter packages, and any required FFmpeg binary. Build frontend/web or use the supported local web-server mode established by the feasibility spike. Do not install WhatsApp provider secrets or call real OpenAI endpoints.

Run the Playwright pytest suite from qa/voice_pipeline with an isolated environment. Use temporary SQLite/audio paths and a local app token. Start the Flutter Web frontend locally; pytest owns the test FastAPI/ASGI server and the fake provider contexts. Readiness checks must wait for a defined HTTP health endpoint and frontend response, then fail within a bounded time.

The job runs stable cases for:

- Shared WAV fixture chosen from the real file picker in Upload.
- Upload original/translation result rendering and temporary-database save assertion.
- Upload translation outage retaining the original transcript.
- The same WAV fixture injected through Chromium's virtual microphone.
- Non-empty Live PCM reaching both fake upstreams.
- Source/translation delta rendering and corrected final source after Stop.
- Partial text retention after mid-session disconnect and clean recovery on session two.
- Microphone denial and the disabled persistence path.

Initial concurrency should be one Playwright worker because save-to-database is global and audio device state is process-wide. If one isolated process/database per worker is later proven, parallelization can be revisited.

## Safety

The test environment contains no real-provider key. Provider connectors are monkeypatched before the local ASGI server accepts requests. An unexpected outbound provider call should fail the test. The CI token is random and local; only temporary storage is used. Traces/screenshots are retained for failures only after credential/content redaction is verified.

The CI never sends a WhatsApp message and never reads the developer's .env or persistent business data. A real-provider quality check is a separately authorized, manually triggered process with a declared cost cap; it is not a PR check.

## Reporting and gates

Job checks:

1. Fixture and workflow setup completed.
2. Backend test server and Flutter app became ready before timeout.
3. Each test observed the expected scripted double, not a live network provider.
4. All functional assertions passed; audio evidence confirms non-empty captured frames.
5. Failure artifact contains test ID and safe reproduction information.

A passing pipeline establishes deterministic browser/integration behavior against fake provider results. It does not establish transcription accuracy, translated meaning, actual provider latency, iOS behavior, or physical microphone quality. State these limits in the workflow summary.

## Existing CI relationship

The current security-tests.yml already runs backend pytest on pull requests and pushes. Do not duplicate the entire backend suite in the new browser workflow unless shared preparation is required and justified. The new workflow can depend on relevant existing CI results at the repository branch-protection level; branch protection itself is repository configuration and is not changed by this design.
