# Test Plan and User Acceptance — Voice Notes v4

**Revision:** 1.0 · **Status:** Local regression executed; live acceptance planned

## Objective and strategy

Verify that v4 safely turns an eligible Meta post-call transcript into an original/translated Inbox result while retaining v3 and existing input modes. Requirements are identified in [SRS](REQUIREMENTS.md); [traceability](TRACEABILITY.md) connects them to implemented tests. The [test report](TEST_REPORT.md) records actual outcomes separately from this plan.

Automated backend tests exercise the HTTP boundary, raw-body signatures, queue transactions, parser, download validation, retry/lease/deletion behavior and provider error mapping. Provider calls are mocked; real FFmpeg decoding is exercised by a synthetic audio case. Flutter widget tests use simulated server responses to check connection, rendering, polling, retry and deletion. Static analysis and a simulator build supplement these tests. No code-coverage percentage, load qualification or security certification is asserted.

Prioritize call-event filtering, transcript integrity, no audio-ASR call on the call path, original-text preservation during translation failures, and preventing deleted content from reappearing. Include wrong-token, wrong-tenant, invalid-signature, malformed/oversized media, untrusted-host, queue-overflow and stale-worker cases.

## Entry conditions and reproducibility

For local regression, install the backend development dependencies, FFmpeg, Flutter dependencies and Xcode simulator support. Run from the repository root:

```bash
v4/backend/.venv/bin/python v4/scripts/validate_release.py
```

The runner saves commands, environment, logs, JUnit and source/preservation manifests under a new `docs/evidence/<UTC timestamp>` directory. It does not deploy or require live Meta calls. Review logs and exit codes rather than relying only on a summary count.

For live tests, obtain the resources in [D-02 through D-09](DECISIONS_AND_RISKS.md): authorized app/business assets, test participants, transcription-enabled call handling, valid provider access, HTTPS hosting, an isolated v4 database and an iPhone if device acceptance is required. Use approved synthetic/non-sensitive speech first. Synchronize clocks. Record baseline version and configuration names without secret values.

## Manual integration and UAT cases

All cases below are **NOT RUN** in this documentation release. A suggested owner does not constitute assignment. Use real providers unless the case explicitly requests controlled failure injection.

| ID / proposed owner | Procedure | Expected result / evidence |
| --- | --- | --- |
| UAT-01 / developer + reviewer | Connect the intended iPhone to the HTTPS v4 backend; try a wrong token; connect correctly; upload approved English/French samples; test microphone permission, Stop and reconnect | Wrong credentials rejected; valid connection works; original/translation readable; final words retained; record device/OS, sample IDs and observed results |
| UAT-02 / TA + developer | Subscribe `messages`; send an approved WhatsApp voice message from the configured test sender to the business number; open Inbox | Signed event reaches v4, exactly one voice-message result appears with source and target text; record redacted event discriminator and timestamps |
| UAT-03 / call-system owner + developer | Subscribe `calls`; enable transcription in the real connect/accept request; complete an approved call; inspect the available event and Inbox | One call result from Meta JSON; media integrity verified; original and translation available; language/duration/speaker timeline shown when supplied; record event/media/result linkage without credentials |
| UAT-04 / developer | In a controlled test environment, redeliver the same signed call event within its valid window; repeat with a new media reference for the same call; send a non-transcript call event | No duplicate result; irrelevant event acknowledged without a transcript job; capture row counts and responses |
| UAT-05 / developer | In an isolated environment, inject a transient translation failure after the original is saved, then restore service; exercise manual retry after terminal failure | Original/details remain available; recovery uses saved text; no repeated media download after checkpoint; failure and recovery visible |
| UAT-06 / operator + developer | On a disposable database, stop the worker after a checkpoint and restart it; wait for lease expiry; delete a separate in-progress job; exercise retention with controlled timestamps | Recovery after lease eligibility; obsolete work cannot restore a deleted result; content cleared at pruning and tombstone removed after its window; record timings and DB checks |
| UAT-07 / bilingual reviewer + professor | Review an approved set of calls/voice samples containing names, numbers, accents, silence and speaker changes; compare source transcript and translated meaning to expected results | Record sample-level errors and quality scores using the D-04 rubric; acceptance remains pending until a rubric and thresholds are agreed |
| UAT-08 / operator + professor | Measure representative short/long calls at the agreed workload; test foreground/background/resume, slow network, retry/delete confirmation and device layout/accessibility | Record end-of-call→event, event→queue, queue→completion, completion→visible times; meet D-05 targets and agreed device criteria; no background-push guarantee assumed |

UAT-06 timestamp manipulation is for disposable test data only. A simulated restart regression is not evidence of actual process recovery on the deployment host. Meta's event availability delay and v4 processing delay must be measured separately.

## Evidence template and defect handling

For each execution record: case ID; requirement IDs; date/time/timezone; tester/reviewer; source revision; device/backend environment; preconditions; redacted sample/event IDs; steps; expected and actual results; pass/fail/blocked/not-run; screenshots or logs; defect ID and retest result. Keep participant data and secrets out of broadly shared reports.

Classify defects by impact: blocked ingestion/data loss/access violation, incorrect result/recovery, or minor presentation issue. Assign an owner and resolution, link the failing evidence, and rerun affected checks after a fix. “Blocked” means a prerequisite prevents execution; “not run” means execution has not taken place. Neither is a pass.

## Exit and sign-off

Local regression exit: required commands return zero, recorded tests have no failures/skips, analyzer is clean, simulator build succeeds, and the source/preservation manifest is retained. This is a local engineering gate only.

Live acceptance exit: mandatory UAT cases pass on the agreed environment; D-04/D-05 quality and delay targets are satisfied; database, retention, access and operational ownership are approved; unresolved deviations have explicit reviewer disposition. Record the approver, date, accepted scope and evidence references. Current sign-off status: **pending**.
