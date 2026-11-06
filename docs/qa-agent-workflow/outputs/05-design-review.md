# 05 — Design Review

Status: review of stages 01–04. This review does not implement or execute the test suite.

## Decision

Design is ready for a limited implementation spike, not yet ready to claim stable Playwright CI. The scope and boundaries are concrete: reuse one approved recording through Upload and Live; put all new test code and assets under qa/voice_pipeline; add a separate GitHub Actions workflow; leave Flutter and backend application modules untouched.

The repo already has a security-test workflow, backend API tests, and paired fake Live upstreams. These are useful foundations. They do not prove that Flutter Web exposes stable Playwright locators or that Chromium can inject one-shot audio through the app's recorder.

## Review findings

| Finding | Disposition |
| --- | --- |
| “Same recording” could incorrectly imply identical provider bytes. | Clarified: same source WAV and checksum; Live capture produces resampled PCM bytes. |
| Mocked output could be mistaken for ASR quality. | Test strategy distinguishes deterministic CI wiring from manual real-provider quality review. |
| A fake Live provider could return text without receiving mic audio. | TC-004 records and requires non-empty audio on both fake upstreams. |
| Stop regression needs a final event only after user action. | TC-005 schedules a corrected final word after Stop/commit and checks displayed result after done. |
| An existing backend workflow already covers backend tests. | Keep it intact; add a separate Playwright browser workflow without rerunning all backend tests by default. |
| Flutter browser selectors and virtual mic end-of-file semantics are unknown. | Keep as blocking feasibility gates before committing to implementation details. |
| Test code could creep into product modules to ease mocking. | No app changes are in current scope. If the spike proves a seam impossible, return for a separate decision. |

## Go/no-go gates before a full browser suite

1. A headless Chromium locator can identify connection, Upload, Live, Stop, result panes, and save toggle by accessible semantics or a stable tested fallback.
2. The primary non-sensitive WAV can both pass through the real browser file picker and produce non-zero captured Live audio through the Flutter recorder.
3. Live input has a deterministic single-playback completion signal and can be reset for a second session.
4. The same-process pytest harness can start the isolated ASGI app and local frontend while patched Upload and paired Live services prove no provider call is made.
5. Browser traces/evidence pass a deliberate redaction review.

If a gate fails, stop before adding product code. Document the failing check and an isolated test-only alternative. Any required frontend semantics/test hook or backend provider seam is a separate application-code proposal and must be reviewed as such.

## Implementation order

Use the task plan in 05-implementation-plan.md. The first milestone is only one vertical path per mode: Upload success and Live Stop final-word regression. Add the other P1 cases after the runner and fixture are reliable.
