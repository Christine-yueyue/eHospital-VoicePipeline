# Stage 02 — Risk Analysis and Test Strategy

You are the QA lead. Read COMMON.md and the stage 01 deliverables. Write English design documents only; do not implement tests.

## Work

1. Rank user-impact risks for lost final Live words, clearing partial text, lingering busy state, stale events entering a new session, silent/denied microphone, Upload/translation partial success, persistent-data leakage, unmocked external calls, Flutter Web semantics, and shared global persistence configuration.
2. Use qualitative likelihood based on source and coverage; do not invent production failure rates.
3. Map each P1/P2/P3 risk to requirements, observable evidence, and the lowest test layer that can detect it.
4. Define three distinct modes: stable offline Playwright CI, a separately authorized real-provider voice-quality review, and bounded Agent exploration. Explain what each result can and cannot claim.
5. Reuse existing backend unit tests for exhaustive API boundaries. Design the browser suite to cover the visible cross-layer workflows rather than duplicate the whole API matrix.
6. Propose a separate GitHub Actions workflow for deterministic PR regression. Keep test code/assets/dependencies under qa/voice_pipeline. Do not edit the existing security workflow. Put CI orchestration in its own .github/workflows file. Do not change application code in this design.
7. Require no provider secrets, deny unmocked external service calls, use temporary databases/audio directories, use bounded timeouts, and do not retry failures to manufacture a pass.
8. Write entry/exit gates and PASS/FAIL/BLOCKED/NOT RUN result rules.

## Deliverables

- outputs/02-risk-matrix.md
- outputs/02-test-strategy.md

## Completion criteria

Every P1 risk has an assigned test layer, required evidence, and criterion. CI claims stop at mock-provider integration. Real ASR/translation quality, iOS, WhatsApp, and production reliability are clearly out of scope for a mock pass. Stop after this stage.
