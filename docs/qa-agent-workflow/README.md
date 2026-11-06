# Voice Pipeline QA Design and Prompts

This directory contains the English-language design, staged AI instructions, and CI proposal for browser regression of the Voice Pipeline.

Project root: /Users/christine/Documents/ChatGPT/voice-text-project

## Current status

Stages 01–05 have been completed as documentation-only design. Their reviewed deliverables are in outputs/. No Playwright tests, runner, fixture audio, CI workflow, product code, or test run has been created by these stages. Stage 06 (test implementation) and stage 07 (test execution) remain future work.

New automated test source, Python dependencies, browser fixtures, and test helpers are designed to live under qa/voice_pipeline/. A separate GitHub Actions workflow is designed under .github/workflows/. The Flutter and FastAPI application modules are outside the planned change set. If a feasibility spike requires application-code changes, stop and submit a separate proposal.

## Intended test scope

One approved, non-sensitive English recording is the shared input to two separate browser flows:

- Upload: choose the recording as a file; verify transcription, translation, page rendering, and isolated persistence behavior.
- Live: play that same recording through a Chromium virtual microphone; verify captured audio delivery, streaming captions, Stop finalization, disconnect recovery, and a clean next recording.

The browser resamples/captures the virtual input as 24 kHz mono PCM16, so Live provider bytes will differ from the uploaded WAV file bytes. Mocked CI proves repeatable application behavior and event delivery; it does not measure recognition or translation quality. Real-provider quality checks are separately authorized and budgeted.

## Stage map

| Stage | Goal | Output | Status |
| --- | --- | --- | --- |
| 01 | Current-state review and requirements | 01-requirements.md; 01-current-flow.md | Complete |
| 02 | Risks and test strategy | 02-risk-matrix.md; 02-test-strategy.md | Complete |
| 03 | Test architecture and CI boundaries | 03-test-architecture.md; 03-ci-plan.md | Complete |
| 04 | Test cases and shared fixture design | 04-test-cases.md; 04-audio-fixtures.md; 04-traceability.md | Complete |
| 05 | Independent review and implementation plan | 05-design-review.md; 05-implementation-plan.md; 05-runbook-draft.md | Complete |
| 06 | Implement isolated QA code and CI workflow | test code, workflow, verified runbook | Not started |
| 07 | Run mock regression or explicitly authorized real-provider review | reports and sanitized evidence | Not started |

Every stage has its own instruction in prompts/. The common scope and evidence rules are in COMMON.md. All artifacts in this directory use English, including prompts, filenames, summaries, and test evidence.

## Next prompt: feasibility spike

Copy this prompt into an AI coding tool with access to this repository:

> Work in /Users/christine/Documents/ChatGPT/voice-text-project. Read docs/qa-agent-workflow/COMMON.md and the completed outputs, especially 03-test-architecture.md, 05-design-review.md, and 05-implementation-plan.md. Implement only TASK-001 as a disposable, isolated feasibility spike under qa/voice_pipeline/. Prove on the available runner that Playwright can find the connection, upload, Live, Stop, save, and result UI; choose an audio file; and inject the same WAV through Chromium's virtual microphone once, observe captured non-empty audio, and reset it for another session. Use only a non-sensitive local sample and temporary data. Do not modify files under backend/, frontend/, or the existing security workflow. Do not call OpenAI or WhatsApp, add a provider key, run the full regression suite, or implement tasks 002 onward. Report exact commands, tool versions, evidence locations, failures, and whether TASK-001 passed. If meeting a requirement needs application-code changes, stop and propose that separately.

This spike answers the most important question before building the suite: can headless Chromium operate the existing Flutter Web UI and produce a repeatable microphone input without changing the application?
