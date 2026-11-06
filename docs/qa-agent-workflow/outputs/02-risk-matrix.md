# 02 — Voice Pipeline Risk Matrix

Status: qualitative ranking from source review; no production incidence or test-run data was available.

| ID | Risk | Impact / likelihood basis | Priority | Requirements | Required evidence |
| --- | --- | --- | --- | --- | --- |
| RISK-001 | Stop commits audio, but the final source word or translation delta arrives afterward and is lost or overwritten. | High impact; event ordering is asynchronous by design. Existing backend unit coverage drains final words, but the browser path has no Playwright coverage. | P1 | REQ-006, REQ-007 | Scripted event timeline, final UI text, final source transcript, done event. |
| RISK-002 | A Live session returns an error or disconnects after partial text and the app clears useful results or remains busy. | High impact; several async streams, timers, and cleanup paths interact. | P1 | REQ-008 | Partial text before fault, disconnect event, visible error, resulting controller state. |
| RISK-003 | The previous session's late event appears in the next session. | High impact; the controller uses session identity and cancellation to discard late events. | P1 | REQ-008 | Two scripted session IDs/results; second UI result contains no first-session text. |
| RISK-004 | Browser recording is silent, permission is denied, or the virtual fixture loops rather than playing once. | High impact; capture setup, browser permissions, audio pipeline, and watchdog are environment-sensitive. | P1 | REQ-005, REQ-009 | Browser permission state, captured non-empty PCM, fixture playback completion and reset. |
| RISK-005 | UI shows Upload results in the wrong pane, remains busy, or loses a transcript after translation failure. | High impact; response parsing and independent outputs are separate behaviors. | P1 | REQ-002, REQ-003 | Multipart request, scripted response, both result panes, error and idle state. |
| RISK-006 | Saving leaks test data into an existing local database or does not honor the save toggle. | High impact; saving is a global setting and disk persistence is observable. | P1 | REQ-004, REQ-010 | Per-run DB/audio directory, before/after rows, output path containment. |
| RISK-007 | A CI test unexpectedly calls a paid external service or sends fixture text outside the runner. | High impact; Upload and both Live sessions can use provider credentials in normal execution. | P1 | REQ-010 | Fail-closed test doubles and denied-network verification; CI has no provider secrets. |
| RISK-008 | Flutter Web semantics differ on headless Chromium, leaving Playwright unable to find controls reliably. | High impact; Flutter widget tests use finders, not browser roles; rendered web tree has not been inspected. | P1 | REQ-002, REQ-005 | A headless locator spike; role/name locators or documented test-only semantics support. |
| RISK-009 | Browser test harness shares assertions/helpers with production code and creates a hidden test-only app branch. | Medium-high; weak boundaries make tests hard to audit and can change runtime behavior. | P2 | REQ-011 | Test code under qa/voice_pipeline; no production dependency or runtime toggle. |
| RISK-010 | Deterministic mock passes while real ASR/translation is wrong. | High impact; a mock intentionally returns known events and does not evaluate model accuracy. | P1 | REQ-001, REQ-010 | Reports state mock coverage; separate manual real-provider check with referenced transcription. |
| RISK-011 | Duplicate browser tests repeat backend API assertions that existing pytest already covers. | Medium; extra runtime without broader confidence. | P3 | REQ-002, REQ-006 | Traceability matrix links each assertion to new browser coverage and existing unit coverage. |

## Priority policy

P1 risks are represented in the initial regression suite. P2 risks are checked while building the isolated test harness. P3 risks are handled by the suite design rather than by adding duplicate cases. Re-rank only if new source evidence or executed tests change the assessment.
