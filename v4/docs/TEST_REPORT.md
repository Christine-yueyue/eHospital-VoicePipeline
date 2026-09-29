# Test Report — Voice Notes v4

**Report:** TR-V4-001 · **Revision:** 1.0 · **Software:** 4.0.0+1

**Outcome:** Local automated regression passed. Real Meta/OpenAI integration, physical-device validation and stakeholder acceptance remain unverified.

## Execution identity

The run began on **September 29, 2026 at 03:19:41 UTC**, equivalent to **September 28 at 23:19:41 America/Toronto**. The evidence directory is [20260929T031940Z](evidence/20260929T031940Z/run.json). Source was an uncommitted working tree; no release commit/tag is asserted. [Source SHA-256 manifest](evidence/20260929T031940Z/source-manifest.json) identifies the selected tested files.

The [runner](../scripts/validate_release.py) executed backend tests, Flutter analysis/tests and a simulator build sequentially. It captured source hashes before and after execution. [Preservation evidence](evidence/20260929T031940Z/preservation.json) confirms that the **28 selected v3 files** checked by this runner were unchanged and selected v4 source files did not change during the run. This is not a hash audit of every file in either directory.

## Results

| Check | Actual result | Command duration | Evidence |
| --- | --- | --- | --- |
| Backend pytest | **97 passed**, 0 failed, 0 errors, 0 skipped; one deprecation warning | 1.75 s | [Log](evidence/20260929T031940Z/backend-tests.log), [JUnit](evidence/20260929T031940Z/backend-junit.xml) |
| Flutter static analysis | **No issues found** | 2.39 s | [Log](evidence/20260929T031940Z/flutter-analyze.log) |
| Flutter widget tests | **9 passed**, 0 failed, 0 skipped | 3.42 s | [Machine log](evidence/20260929T031940Z/flutter-tests.log), [case results](evidence/20260929T031940Z/flutter-cases.json) |
| iOS Simulator debug build | **Succeeded**, `com.christine.voiceNotesV4` | 22.80 s | [Build log](evidence/20260929T031940Z/ios-build.log) |

All seven recorded commands, including the three tool-version probes, exited with code 0. Durations above include subprocess overhead; pytest's own console summary reports 1.26 seconds. The artifact was produced at `v4/frontend/build/ios/iphonesimulator/Runner.app`. Compilation does not demonstrate that a physical iPhone or a real call was exercised.

| Automated group | Executed cases | Scope |
| --- | --- | --- |
| `test_backend.py` | 20 | Upload validation/conversion/cleanup; translation partial success; live relay/auth/errors; safe config |
| `test_whatsapp.py` | 24 | Verification/signatures, filtering, durable voice queue, retries, retention, media validation |
| `test_calls.py` | 53 | Call filtering, download integrity, parsing, translation chunks, checkpoints, stale leases, deletion and schema upgrade |
| Flutter: connection / call Inbox / widget | 5 / 3 / 1 | Auth/version checks, Inbox rendering/actions/polling, phone-width language controls |

Parameterized backend cases are counted individually. Flutter loader events are excluded. [Backend case inventory](evidence/20260929T031940Z/backend-cases.json) and the Flutter case results were derived from the saved raw outputs. These counts are test execution results, **not code or requirement coverage percentages**.

## Environment

| Component | Recorded version |
| --- | --- |
| Host | macOS 27.0, arm64 |
| Python / pytest | 3.13.5 / 9.1.1 |
| FastAPI / Starlette | 0.141.1 / 1.7.0 |
| httpx / OpenAI SDK / uvicorn | 0.28.1 / 2.54.0 / 0.54.0 |
| Flutter / Dart | 3.47.5 stable / 3.13.4 |
| Xcode | 27.0, build 27A266a |

See [environment](evidence/20260929T031940Z/environment.json), [Flutter](evidence/20260929T031940Z/toolchain.log), [Xcode](evidence/20260929T031940Z/xcode.log), [FFmpeg](evidence/20260929T031940Z/ffmpeg.log) and [commands](evidence/20260929T031940Z/run.json) for recorded details. Dependency ranges permit future installations to differ from this run.

## Findings and interpretation

The signed-call integration regression exercises the actual application, SQLite queue, worker and parser with mocked Meta HTTP responses and mocked translation. It confirms local request-to-Inbox behavior and asserts that the call path does not invoke audio transcription. It is not a real Meta-to-iOS end-to-end test. Flutter tests exercise a separate simulated client boundary.

Retry/checkpoint tests demonstrate saved-original reuse and stale-worker rejection. Retention tests use controlled database times; they do not measure wall-clock deletion on an always-running deployed server. Restart tests simulate lease/recovery conditions rather than terminating and restarting a production process. The audio conversion case decodes real synthetic audio with FFmpeg but mocks speech recognition.

One non-failing dependency warning was observed: Starlette's TestClient reports that its use of `httpx` is deprecated and recommends `httpx2`. Review this during a planned compatible dependency update; changing the test dependency was outside this documentation task. No failing assertions or analyzer issues were observed. This does not establish that the application has no defects.

## Unexecuted checks and release assessment

All eight [manual/UAT cases](TEST_PLAN.md) remain **NOT RUN**. No live Meta delivery, account permission/transcription eligibility check, real-provider accuracy/latency measurement, load/soak test, penetration test, physical-device microphone test, accessibility assessment, signed distribution build or stakeholder sign-off is included.

The evidence supports continued local development and a controlled integration trial after resources are supplied. It does **not** support a claim of production readiness or completed acceptance. Resolve the [decision register](DECISIONS_AND_RISKS.md), execute the agreed UAT cases and issue a new report before that claim is made.
