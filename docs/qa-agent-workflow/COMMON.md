# Shared Instructions for Every Stage

## Project and source of truth

You are designing or implementing Agent-assisted QA for this Voice Pipeline repository. Follow repository instructions and use the current source code as evidence. Do not assume a statement in an old conversation or design note is still true without checking the relevant source.

The existing system has Flutter Web and iOS clients and a FastAPI backend. Upload uses POST /api/transcribe. Speak Live uses the /api/live WebSocket with a translation upstream and a paired source-transcription upstream. A shared Save to Database setting controls persistence. The project also has a WhatsApp inbox, which is outside this first release.

The security-tests GitHub Actions workflow runs backend tests. Existing backend tests already monkeypatch Upload provider functions and use two scripted Live upstreams. Existing Flutter tests use Flutter's widget tester. None of those facts prove that Playwright browser tests currently exist or pass.

## Scope and code ownership

- Stages 01–05 are documentation-only. Read non-sensitive source and existing documents. Write design deliverables only under docs/qa-agent-workflow/outputs/. Do not write application code, test code, runnable helpers, or CI configuration. Do not install dependencies, start services, run tests, or contact external services.
- New browser tests, test helpers, Python test dependencies, test-owned audio fixtures, and test documentation belong under qa/voice_pipeline/.
- CI configuration is test infrastructure, kept in its own workflow under .github/workflows/.
- Do not change Flutter application files, FastAPI application modules, existing backend tests, existing Flutter tests, or the existing security workflow as part of the planned Playwright implementation.
- If the test design proves that a new application-level test seam or semantic annotation is necessary, stop and propose a separate application-code change. Do not hide it in a test branch or test harness.
- Do not start a stage the user has not invoked. Design approval does not by itself authorize real-provider calls, WhatsApp sends, releases, or deployments.
- Never read or print .env, credentials, private keys, real business databases, personal messages, or private voice recordings. Use temporary data and non-sensitive fixtures.
- Do not create agents, commits, pull requests, deployments, messages, or scheduled jobs for this task.

## Evidence and language

- Write design and test documentation entirely in English.
- Mark conclusions as source-verified, proposed, or awaiting validation. Do not claim a test, tool, browser, fixture, or CI workflow was run or exists unless it was actually verified.
- Use identifiers REQ-xxx for requirements, AC-xxx for acceptance criteria, RISK-xxx for risks, TC-xxx for tests, and TASK-xxx for implementation tasks.
- Distinguish UI mock tests, browser-to-backend tests with upstream doubles, and real-provider quality checks. Browser route mocks do not verify backend integration.
- Every test result uses PASS, FAIL, BLOCKED, or NOT RUN. A screenshot or HTTP 200 alone is not proof of the full voice path.
- Preserve test and application boundaries. The same fixture source may be shared by Upload and Live; note that Web microphone capture converts it to PCM, so the transported bytes are not identical.
- Do not add real provider keys to CI. The deterministic regression must be offline, use local service doubles, temporary storage, and bounded timeouts.
- Do not claim that Flutter Web exposes stable browser locators, or that Chromium microphone-file input plays once and resets, until verified on the target runner.
- For genuine speech quality, use a consented/non-sensitive source with a human-reviewed reference. A tone or mock result is not a speech-recognition test.
- Agent exploration is diagnostic. A fixed test assertion is what decides pass or fail.

## Stage completion

Check each deliverable exists and meets its prompt's completion criteria. Report a short summary, link deliverables, record unverified assumptions, and stop at the requested stage boundary.
