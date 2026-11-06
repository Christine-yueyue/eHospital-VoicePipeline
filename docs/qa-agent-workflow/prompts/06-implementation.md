# Stage 06 — Implement the Isolated QA Suite

Run this prompt only when the user explicitly starts implementation. Read COMMON.md and stages 01–05.

## Work

1. Implement the agreed test runner, Playwright cases, fixture manifest/assets, test dependencies, CI workflow, and runbook only inside qa/voice_pipeline and the new .github/workflows/voice-pipeline-regression.yml.
2. Do not edit application modules under backend/ or frontend/, existing backend/frontend tests, or existing workflow. If implementation cannot proceed without an app-level test seam, semantics change, or runtime switch, stop and return a separate proposal before making such an edit.
3. Use a non-sensitive consented speech fixture. Verify its checksum, supported WAV format, recording length, and reviewed reference.
4. Use an isolated test ASGI server and test-local Upload/paired Live doubles. Fail closed if an external provider can be reached. Use a per-run test token and temporary SQLite/audio paths.
5. Prove Upload uses the fixture file and Live captures non-empty PCM from the same fixture. Keep the two payload encodings distinct. Verify browser end-of-file and restart behavior.
6. Add stable success, final-word-after-Stop, disconnect/recovery, translation failure, persistence on/off, and permission/error tests in priority order.
7. Add a standalone CI workflow without provider/WhatsApp secrets and with bounded timeouts and reviewed failure artifact redaction.
8. Run only user-authorized local/offline validations; report exact commands and actual results. Never run real provider calls or send WhatsApp messages unless separately authorized.
9. Replace runbook draft commands only with commands verified against the resulting files and dependencies.

## Deliverables

- QA test source, test-only helper code, approved non-sensitive fixtures, and separate CI workflow.
- An English implementation report listing modified files, exact checks, failures, and limitations.
- An English runbook with verified local commands and clear mock-versus-real boundaries.

## Completion criteria

The mocked regression runs in isolation without provider secrets, persistent user data, or production module changes. Reports distinguish implemented, executed, and pending coverage. If the UI or test harness needs a production change, stop and propose it separately.
