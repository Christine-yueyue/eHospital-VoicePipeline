# Stage 04 — Detailed Test Cases and Fixture Design

You are the QA engineer. Read COMMON.md and stages 01–03. Write English Markdown design artifacts only. Do not create audio or test source.

## Work

1. Define 10–15 non-duplicative cases, each with TC ID, linked REQ/AC/RISK, priority, mode/layer, preconditions, test data, steps, scripted failure point, assertion, timeout, cleanup, and evidence.
2. Make Upload and Live use the same source WAV. Test file identity/checksum; do not assert Uploaded WAV bytes equal browser-resampled Live PCM.
3. Cover Upload success; translation failure preserving transcript; invalid input; Live audio reaching both upstreams; partial-to-final source correction after Stop; final translated result and done; mid-session disconnect preserving text; a clean second session; permission denied; permission granted but silent; Save to Database on/off; wrong app token.
4. Avoid duplicating every existing backend API edge test in Playwright. Link those boundaries to backend tests instead.
5. Specify a fixture manifest with ID, language, natural speech, reference transcript, translation fact checks, WAV format, sample rate, duration, size, provenance/permission, checksum, and target phrase timing. Mark absent fixture values pending.
6. Include a short non-personal sentence with a date/time or other verifiable fact. Never use actual patient speech or real inbox data. A sine tone is only a transport fixture.
7. Design a repeatable virtual microphone start/end/reset. Do not rely on unverified WAV looping rules or arbitrary sleeps; add a feasibility check and fallback.
8. Define assertion rules: exact equality for scripted mock output; meaning/facts and human review for real translations; avoid exact punctuation or a single phrasing as the only real-provider oracle.
9. Trace every P1 acceptance criterion to a case or explicitly documented blocker.

## Deliverables

- outputs/04-test-cases.md
- outputs/04-audio-fixtures.md
- outputs/04-traceability.md

## Completion criteria

The cases give the next engineer actionable steps and final expected state; the shared WAV identity is explicit; all unprepared assets/thresholds are marked pending; the test scope explains what CI and real-provider checks each establish. Stop after this stage.
