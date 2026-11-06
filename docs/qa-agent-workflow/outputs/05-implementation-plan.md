# 05 — Implementation Plan

Status: proposed tasks only. No implementation or test runs were performed in stages 01–05.

## Code separation rule

Keep all new test source, fixtures, Python dependencies, pytest setup, launch helpers, and local test documentation in qa/voice_pipeline. Put CI orchestration in its own .github/workflows/voice-pipeline-regression.yml file. Make no edits under frontend/lib, frontend/test, backend, or existing security workflow in this plan.

If reliable Playwright selectors require production Flutter accessibility changes, or service patching cannot support the browser/backend harness without a production seam, stop and produce a separate narrowly scoped app-code proposal. Do not smuggle product changes into the test commit.

## Ordered tasks

| Task | Priority | Goal and likely files | Prerequisites | Completion criteria |
| --- | --- | --- | --- | --- |
| TASK-001 | P1 | Prove locators, web build/serve, file picker input, fake-mic permissions and WAV playback in hosted-equivalent Chromium. Temporary probe or discarded spike within qa/voice_pipeline only. | Flutter and Playwright versions selected. | Can find and interact with target controls; documents how a one-shot fixture starts, ends, and resets. No product file changed. |
| TASK-002 | P1 | Prepare and approve FIX-EN-001 and manifest in qa/voice_pipeline/fixtures. | Provenance/permission and human reference review. | Same checked-in WAV/hash works as Upload input and virtual microphone source and fits upload limit. |
| TASK-003 | P1 | Create isolated pytest setup and local ASGI/Flutter server fixtures under qa/voice_pipeline. | TASK-001; PYTHON_DOTENV_DISABLED; temporary DB configuration. | Dynamic ports, health checks, cleanup, local token, provider stubs, no real credentials, no persistent data. |
| TASK-004 | P1 | Add TC-001 Upload happy-path browser test in qa/voice_pipeline/test_upload_flow.py. | TASK-002, TASK-003. | Real browser submits the fixture to test backend; doubles assert; result panes and isolated saved row assert. |
| TASK-005 | P1 | Add TC-004/TC-005 Live audio and Stop final-word browser regression in qa/voice_pipeline/test_live_flow.py. | TASK-001, TASK-003. | Non-empty PCM arrives at both fake upstreams; final corrected word is sent only after Stop and shown after done. |
| TASK-006 | P1 | Add disconnect/recovery and save-disabled cases. | TASK-004, TASK-005. | Existing text survives interruption, next session is isolated, disabled setting adds no test DB/audio content. |
| TASK-007 | P2 | Add auth, translation-error, invalid file, permission and silent-input browser cases where deterministic. | Stable initial smoke. | Each UI assertion has isolated evidence and no redundant exhaustive API status matrix. |
| TASK-008 | P1 | Add a standalone GitHub Actions workflow and maintain instructions. | TASK-001 to TASK-005 stable locally. | Pull-request, push, and manual triggers; offline mocked path; bounded run; redacted failure artifacts; no provider secrets. |
| TASK-009 | P1 | Run repeated clean-runner regressions and review artifacts. | TASK-008. | At least three clean headless runs pass without retries; no outbound provider calls; cleanup and artifacts reviewed; workflow is eligible for branch protection configuration. |

## Proposed developer commands

These are command-shape proposals; they are not confirmed as executable until TASK-001/003 create the runner and TASK-008 adds its workflow:

- Install application and browser-test dependencies: documented setup script or explicit steps in qa/voice_pipeline/README.md.
- Run a single Upload case: pytest selection by TC-001.
- Run one Live stop case: pytest selection by TC-005.
- Run stable suite locally: pytest using qa/voice_pipeline/pytest.ini.
- Run the CI workflow: push a branch/open a pull request or start workflow_dispatch after the file exists.
- Run the real-provider quality check: separate opt-in command requiring the documented cost cap and user-provided authorization.

Do not publish invented commands as working scripts until their exact command, port, Flutter mode, and dependencies have been verified.
