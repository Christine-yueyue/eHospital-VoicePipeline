# 04 — Requirements and Risk Traceability

Status: design mapping. A check is considered planned until implementation and execution evidence exist.

| Requirement / acceptance criterion | Risk | Planned test coverage | CI gate |
| --- | --- | --- | --- |
| REQ-001 / AC-001 shared fixture identity | RISK-010 | TC-001, TC-004, TC-012; 04-audio-fixtures.md checksum | Verify manifest and test uses; CI only checks deterministic mocked flows |
| REQ-002 / AC-002 upload success | RISK-005 | TC-001 | Yes |
| REQ-003 / AC-003 upload validation and partial translation success | RISK-005 | TC-002, TC-003; existing API tests for detailed statuses | Yes for translation failure; API suite owns exhaustive boundaries |
| REQ-004 / AC-004 isolated persistence behavior | RISK-006 | TC-001, TC-008, TC-009 | Yes |
| REQ-005 / AC-005 authenticated Live audio reaches both upstreams | RISK-004, RISK-007 | TC-004, TC-010 | Yes |
| REQ-006 / AC-006 live UI event rendering and completion | RISK-001 | TC-004, TC-005, TC-009 | Yes |
| REQ-007 / AC-007 last word after Stop | RISK-001 | TC-005 | Yes; highest priority |
| REQ-008 / AC-008 disconnect and next session isolation | RISK-002, RISK-003 | TC-006, TC-011 | Yes |
| REQ-009 / AC-009 microphone errors | RISK-004 | TC-007 | Yes if headless permission control and silence signal prove deterministic |
| REQ-010 / AC-010 safe CI | RISK-007, RISK-010 | All mocked Playwright tests; CI outbound-call guard | Workflow design and implementation checks |
| REQ-011 / AC-011 test/product code separation | RISK-009 | CI diff/scope review; directory layout in 03-test-architecture.md | Yes; any app-code change requires separate design review |

## Coverage boundaries

- Existing backend tests already exercise upload validation, provider failures, persistence settings, Live fake upstreams, and final-word draining. The browser suite should assert user-visible paths and cross-layer request/event behavior rather than repeat every API parameter.
- Existing Flutter widget tests exercise a widget/tester environment, not a real browser microphone, browser semantics, or Playwright locators.
- Mocked CI checks event wiring and text/state behavior. It does not prove ASR accuracy or French translation quality.
- TC-012 is an optional manual real-provider observation. It is not a pull-request gate and needs separate cost authorization.
- Native iOS permissions, physical microphone devices, WhatsApp delivery, throughput, and production reliability are out of scope.
