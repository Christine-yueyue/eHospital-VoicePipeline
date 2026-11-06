# Stage 01 — Current-State Review and Requirements

You are the QA analyst. Read COMMON.md. This stage is design only: inspect non-sensitive source and write English Markdown design deliverables under outputs/. Do not write code or run the application or tests.

## Inspect

Read README.md; frontend/lib/voice_controller.dart, main.dart, and connection_page.dart; backend/app.py, live.py, services.py, and voice_feedback.py; backend/tests/test_backend.py and current frontend tests; and .github/workflows/security-tests.yml. Follow relevant imports as needed. Do not read private configuration, persisted data, or recordings.

## Work

1. Document actual Upload and Live paths, including authentication, audio input, provider calls, UI state, stop/finalization, errors, and persistence.
2. Separate source-verified behavior from expected behavior and unverified assumptions.
3. Write numbered REQ and AC items for shared-fixture provenance, successful Upload and Live, user-visible results, final-word delivery, disconnect recovery, a new session, microphone denial/no audio, persistence isolation, and deterministic CI safety.
4. Limit phase-one browser scope to the same approved non-sensitive recording sent once as an Upload file and once as a Chromium virtual-microphone source. Record that Upload WAV bytes and Live captured PCM bytes differ.
5. Summarize existing backend/Flutter coverage without implying it has run successfully. Identify the browser-level gaps.
6. Exclude WhatsApp delivery/assistant and native iOS device behavior from this phase.
7. Record evidence paths and distinguish unknown toolchain or browser facts as pending validation.

## Deliverables

- outputs/01-requirements.md
- outputs/01-current-flow.md with a Mermaid diagram of both paths.

## Completion criteria

Each phase-one requirement has an observable acceptance criterion and source or assumption marker. Both flows run from user action to rendered result in the diagram. Existing coverage and proposed browser coverage are clearly distinguished. List validation gaps, then stop.
