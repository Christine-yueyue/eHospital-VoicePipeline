# Voice Notes: AI-Executed Load Testing Workflow

This file provides phased task prompts. It is not a completed design or test report. Only the workflow is defined here; no test code has been implemented, the system has not been started, and no load test has been run.

Project directory: `/Users/christine/Documents/ChatGPT/voice-text-project`

The software development process is divided into seven phases. Phases 01-04 are design-only; phases 05-07 are reserved for later implementation. Send only one phase instruction to the AI at a time. After completing that phase, the AI must stop and must not enter the next phase automatically.

| Phase | Activity | Primary artifacts | Allowed execution in this phase |
| --- | --- | --- | --- |
| 01 | Requirements analysis | Test requirements and scope | Read code, write documentation |
| 02 | System and test architecture design | Isolation plan, load model, observability plan | Read code, write documentation |
| 03 | QA test design | Test cases, test data, traceability matrix | Read code, write documentation |
| 04 | Implementation plan and design review | Task breakdown, definition of done, execution agreement | Read code, write documentation |
| 05 | Implementation and local validation | Test tools, run instructions, validation record | Write code and run small isolated validation |
| 06 | Test execution | Raw results, environment inventory, experiment records | Run the designed isolated tests |
| 07 | Analysis and quality review | Test report, defect report, regression plan | Analyze results, write documentation |

## How to use this file

In an AI coding tool that can access the project files, copy one of the following prompts. These are instructions for the AI and do not need to be executed in a terminal.

```text
Read /Users/christine/Documents/ChatGPT/voice-text-project/docs/LOAD_TEST_AI_WORKFLOW.md, follow its "Rules shared by all phases", and execute only the complete prompt for Phase 01. Complete the artifacts and self-check, then stop.
```

```text
Read /Users/christine/Documents/ChatGPT/voice-text-project/docs/LOAD_TEST_AI_WORKFLOW.md, follow its "Rules shared by all phases", and execute only the complete prompt for Phase 02. Complete the artifacts and self-check, then stop.
```

```text
Read /Users/christine/Documents/ChatGPT/voice-text-project/docs/LOAD_TEST_AI_WORKFLOW.md, follow its "Rules shared by all phases", and execute only the complete prompt for Phase 03. Complete the artifacts and self-check, then stop.
```

```text
Read /Users/christine/Documents/ChatGPT/voice-text-project/docs/LOAD_TEST_AI_WORKFLOW.md, follow its "Rules shared by all phases", and execute only the complete prompt for Phase 04. Complete the artifacts and self-check, then stop.
```

Use the following three prompts only after the design is complete; creating this file does not authorize them now.

```text
Read /Users/christine/Documents/ChatGPT/voice-text-project/docs/LOAD_TEST_AI_WORKFLOW.md, follow its "Rules shared by all phases", and execute only the complete prompt for Phase 05. This run authorizes implementation of the test code according to the Phase 01-04 design and the required small isolated validation; complete it, then stop.
```

```text
Read /Users/christine/Documents/ChatGPT/voice-text-project/docs/LOAD_TEST_AI_WORKFLOW.md, follow its "Rules shared by all phases", and execute only the complete prompt for Phase 06. This run authorizes execution of the defined tests in an isolated test environment; do not call real external services or send real messages; complete it, then stop.
```

```text
Read /Users/christine/Documents/ChatGPT/voice-text-project/docs/LOAD_TEST_AI_WORKFLOW.md, follow its "Rules shared by all phases", and execute only the complete prompt for Phase 07. Analyze the existing test evidence and generate reports; do not fix issues automatically or rerun load tests; complete it, then stop.
```

## Rules shared by all phases

1. Write in English, retaining necessary English QA terminology and explaining each term on first use. Act in the role specified for the current phase; do not create other chats or subagents.
2. First read any applicable `AGENTS.md`, `README`, and code involved in the phase. Use the current implementation as the source of truth; do not treat target functionality in historical design documents as implemented.
3. Treat prior conversation only as background. Label items separately as "verified facts", "design assumptions", "suggested targets", and "measured results". Cite facts with file paths and line numbers. Do not invent results, command execution records, capacity, or tool capabilities.
4. Phases 01-04 may create or update design documents only. Do not modify application code, install dependencies, start services, run tests, or call external APIs. Permissions for phases 05-07 are defined by their individual prompts.
5. Do not read or output `.env`, real secrets, existing business databases, or real user audio. Do not send messages to real WhatsApp contacts. Do not allow test processes to load real configuration automatically.
6. By default, phases 05-06 use an independent database, audio directory, test credentials, and mocked external services. Preserve real authentication, signature verification, queueing, storage, state transitions, and transcoding paths; do not skip these steps to produce attractive results.
7. Do not overwrite uncommitted user changes. Do not commit, push, publish, or adjust production environments without authorization. When access is restricted, use the tool's prescribed permission flow and do not attempt to bypass it.
8. Execute only the specified phase. Record work needed by later phases in the plan; do not implement it incidentally. At the end of the phase, state the artifacts, key decisions, open items, and whether the phase is complete.
9. For information gaps that do not block the current phase, use explicit, changeable assumptions. For critical gaps that determine the test subject or correctness judgment, complete the unaffected work first and then ask the necessary questions.
10. Before running a phase, check that the preceding artifacts exist and are sufficient. Do not pretend missing inputs are complete, and do not cross phases to fill them in without authorization.
11. Read existing artifacts with the same name before updating them and preserve human decisions. Use REQ identifiers for requirements, LT identifiers for test cases, TASK identifiers for implementation tasks, and BUG identifiers for defects so they remain traceable.
12. End every phase with a brief self-check: what this phase did, what lacks evidence, and what inputs are needed for the next phase. Do not repeatedly ask for permission for routine document edits.

## Known background: re-verify during later execution

- The frontend is Flutter and the backend is FastAPI; the system supports upload transcription, optional translation, a WhatsApp inbox, Live, and a chat assistant.
- `/api/transcribe` waits for transcription and optional translation before returning; a translation failure may be expressed through `translation_error` in the response body, so HTTP 200 does not necessarily mean complete business success.
- `/webhooks/whatsapp` accepts inbound messages; the WhatsApp background worker handles media download, transcription, translation, and persistence.
- The current default single-process startup has one serial WhatsApp worker. Each application process starts its own worker; this conclusion must not be generalized to all deployment modes.
- `backend/inbox.py` has `MAX_PENDING = 100`, limiting the combined queued and processing count. When capacity is exceeded, the enqueue batch is rolled back and returns 503.
- The current work lease is 300 seconds. Recovery timing must account for the lease, processing time, and tasks already waiting in the queue.
- The inbox currently refreshes every 5 seconds; the assistant has separate polling behavior that should be checked when mixed load is defined.
- SQLite and local files participate in persistence; the save setting is global rather than per-client.
- Each Live client creates two upstream connections. Live is not required in the first phase.
- Existing pytest functional tests cover some deduplication, capacity, failure, and recovery logic, but they do not prove concurrent performance.
- This project is not a system with verified multi-account isolation; a virtual user means a concurrent client.

## Phase 01: Requirements analysis

### Complete prompt

You are the QA analyst responsible for Voice Notes performance testing. The goal is to turn the idea of "applying load testing to QA for the current project" into verifiable requirements. This phase performs requirements analysis and writes documentation only.

Inputs: `README.md`, `backend/app.py`, `backend/inbox.py`, `backend/whatsapp.py`, `backend/services.py`, `backend/voice_feedback.py`, relevant frontend calls, and existing tests. Read only the necessary files.

Complete the following:

1. Describe the system's actual business flows, distinguishing synchronous upload processing from asynchronous WhatsApp processing. Draw a simple flowchart or provide clear numbered steps.
2. Define the first-phase scope as upload transcription/translation, validly signed inbound WhatsApp messages, inbox queries, deduplication, and failure recovery. Defer Live, assistant conversations, and real outbound messaging; do not add them incidentally.
3. Create a requirements table starting at REQ-001. Each requirement must include business value, trigger, expected behavior, verification method, and priority. Cover performance and data correctness.
4. Decompose load into concurrent client count, upload frequency, message arrival frequency, audio length/size, database scale, and test duration; do not equate user count with request count.
5. Propose initial performance targets. Query P95 <= 500 ms, webhook P95 <= 1 second while the queue is not full, and an unexpected error rate below 1% may be used as calibration drafts. Identify the applicable environment and pending confirmation status; do not call them existing SLAs.
6. Define HTTP success, complete business success, partial success, expected rejection, and unexpected failure separately. Handle `translation_error`, full queues, duplicate events, and invalid signatures explicitly.
7. Define data correctness requirements: every accepted independent valid message is traceable, not lost, and not mixed with another result; duplicate deliveries do not create duplicate business records; failure and retry states are explainable.
8. Document risks, assumptions, unresolved questions, and how later phases will answer them.

Artifact: `docs/load-testing/01-requirements.md`.

Definition of done: Every core requirement is testable; scope, terminology, load assumptions, and success criteria are clear; verified facts have source references; there are no test results or capacity conclusions.

At the end, output the document link, the three most important requirements, and the inputs needed for the next phase, then stop.

## Phase 02: Test architecture and observability design

### Complete prompt

You are the test architect responsible for performance testing this project. Read the Phase 01 artifact and relevant implementation, then design a reproducible test architecture that can locate bottlenecks. This phase writes design documentation only; do not write or execute code.

Complete the following:

1. Show the relationships among the load generator, test backend, SQLite, audio directory, FFmpeg, mocked Meta/OpenAI services, and metrics collection.
2. Use Locust as the first-phase HTTP test candidate and briefly explain the choice and limitations. In particular, state that ordinary loop-user tasks do not automatically provide a fixed arrival rate independent of response speed; WhatsApp arrival rates require an independent scheduler and measurement of actual sending deviation.
3. Design the integration boundary for mocked external services. Preserve real signature verification, authentication, media validation, queueing, file operations, state transitions, and OGG transcoding. Specify whether mocking occurs at the SDK, HTTP transport, or upstream protocol layer. Test trust rules must not weaken production media URL validation.
4. Inspect configuration loading at app startup and design protection against loading a real `.env`, accessing existing data, or calling real providers. Configuring a test database alone is not sufficient proof of isolation.
5. Define the load model: readers poll at the current refresh interval; uploaders wait after completing an operation; inbound messages arrive on an independent schedule. Record planned and actual request/message counts, actual rates, and generator resource usage.
6. Fix the process count, worker count, audio samples, external latency, save setting, and preloaded data volume for the baseline. Run saving enabled and disabled as separate experiments. Single-process and multi-process runs must be separate experiments and must not be compared as if they were the same setup.
7. Define timestamps and statistical semantics: HTTP request start/end, enqueue, claim, processing completion, and client-observed result. Distinguish queueing, processing, and polling-observation delay. Do not treat the first poll that discovers a result as the exact completion time.
8. Compare existing logs and database fields and list which metrics have evidence and which require minimal observation points in Phase 05. Use a test run ID/message ID to correlate data; do not collect real message content or credentials.
9. Define correctness checks: compare the injection manifest, receipt acknowledgements, database records, and corresponding audio files. Do not rely only on inbox lists with a maximum result count; distinguish execution attempts from final business record count.
10. Design an environment inventory, independent directory per run, pre-run state, post-run draining, and resource cleanup. Stop processes started by the test without affecting existing services; retain results for reporting.
11. Explain the limitations of running the generator and service on the same host and when a separate-host rerun is needed. Upstream simulation capacity describes only local-system behavior under the stated conditions.

Artifacts: `docs/load-testing/02-architecture.md`, containing the architecture diagram, load model, mock protocol, isolation strategy, metric dictionary, and minimal integration points to implement.

Definition of done: The load generator, application, storage, transcoding, and external latency are distinct; every metric has a source and timing definition; capabilities not yet available are listed and are not presented as runnable commands.

At the end, output the document link, main design decisions, and unresolved limitations, then stop.

## Phase 03: QA test case and data design

### Complete prompt

You are the test design lead. Read phases 01 and 02 and write executable, traceable, and objectively judgeable performance and reliability test cases. Do not implement scripts or run tests in this phase.

Complete the following:

1. Assign an LT identifier to each case and specify linked REQs, purpose, priority, preconditions, data, load, steps, duration, observation points, expected results, stop conditions, and post-test processing.
2. Include at least: single-client baseline, 5/10-client step load, 20/50-message bursts, deduplication, queue-capacity boundaries, batch rollback, sustained load, upstream rate limiting/timeouts, restart recovery during processing, partial upload-translation failure, and separate save-enabled/save-disabled experiments.
3. Design one explicit case: inject 50 independent messages within 10 seconds, redeliver 10 of them, and have five clients query the inbox. Verify 50 independent business results, duplicate record count, association correctness, query latency, and drain time.
4. Construct queue-capacity cases at 99/100/101 combined queued-plus-processing items and explain how consumption is controlled to avoid races. Distinguish controlled pre-test state from normal load. Verify whole-batch rollback at a full queue and results after redelivery when capacity recovers.
5. Assert explicitly that duplicate events are accepted without creating new records, invalid signatures are rejected, normal messages succeed, and transcription-success/translation-failure is handled correctly. Do not substitute a single HTTP 200 assertion for business assertions.
6. Define the restart-recovery observation window using the current lease and retry mechanism. Distinguish not-yet-recovered, recovered, permanently failed, and permanently stuck states; record failure windows that can and cannot be verified.
7. Define the audio set: 10-second, 30-second, and 2-minute samples; MP3, WAV, and OGG; valid, empty, corrupted, and oversized samples. Report functional negatives separately from normal performance load. Use self-recorded or synthetic data, never real business recordings.
8. Have mocked services return stable, verifiable results, but do not bypass real media validation or transcoding. Explain how audio-to-result mapping is verified.
9. For every performance threshold, specify load, mock latency, data scale, minimum sample size, and repetition rules. If the sample is insufficient, report "insufficient evidence" rather than forcing pass. Define rerun triggers in advance; do not repeat until a run happens to pass.
10. Define injection stop conditions, such as loss of service responsiveness, resource reaching the declared limit, data corruption, or actual requests deviating from the isolation target. Stopping injection does not mean immediately discarding in-flight tasks; collect evidence and perform bounded draining.
11. Build a REQ-to-LT traceability matrix and mark uncovered or deferred requirements.

Artifacts: `docs/load-testing/03-test-cases.md`, `docs/load-testing/03-test-data.md`, and `docs/load-testing/03-traceability.md`.

Definition of done: Another engineer can reproduce each experiment from the documents; every case can be judged pass, fail, or insufficient evidence; load, correctness checks, and end conditions are clear.

At the end, output the document links, coverage overview, and uncovered items, then stop.

## Phase 04: Implementation plan and design review

### Complete prompt

You are the technical lead for this project's test engineering. Read phases 01-03, check whether the plan is implementable, and break it into small, verifiable implementation tasks. This is the final design phase; write documentation only and do not implement code.

Complete the following:

1. Check consistency among requirements, architecture, and test cases; list conflicts and gaps. You may correct documents within the existing design scope and record the reason; do not lower correctness requirements to hide implementation difficulty.
2. Assign TASK identifiers to implementation tasks and specify linked REQs/LTs, expected files to modify, implementation purpose, dependencies, acceptance method, and definition of done. Order by dependency; do not rely on multiple people or subagents working in parallel.
3. At minimum, separate: test-run configuration and isolation, upstream mocking, samples and manifests, HTTP user model, fixed-rate injection, task-completion observation, data verification, result export, run instructions, and required validation.
4. State which work is limited to test directories and which may require a minimal injectable interface in the application. Without evidence, do not introduce Redis, replace the database, add workers, or make broad architecture changes in advance.
5. Define load, duration, expected upstream call count, output files, and stop/cleanup behavior for each test configuration. Design a run manifest recording version, machine information, process count, scenario, samples, thresholds, start/end time, and exit status.
6. Propose future `startup`, `smoke`, `baseline`, `load`, `spike`, `boundary`, `soak`, `recovery`, and report command interfaces. Mark them clearly as "planned"; do not present nonexistent scripts or commands as available.
7. Define Phase 05 validation scope: related functional tests and a small isolated smoke test; execute the full load only in Phase 06. After existing checks pass, do not expand testing unless there is new change or failure evidence.
8. Create a design-readiness checklist: preceding documents complete, isolation implementable, arrival rate measurable, business success asserted, key metrics sourced, recovery window reasonable, thresholds predetermined, and no real external sending.
9. Estimate engineering effort and state uncertainty; do not promise unverified throughput.

Artifacts: `docs/load-testing/04-implementation-plan.md` and `docs/load-testing/04-design-review.md`.

Definition of done: Implementation tasks are independently verifiable; key design gaps are resolved or clearly blocking; command interfaces are clearly marked as planned; no application or test code is added.

At the end, state whether the design is "ready" or has "blocking items", with the evidence, then stop. Do not start Phase 05 automatically.

## Phase 05: Implementation and small-scale validation (later)

### Complete prompt

You are the engineer implementing the load-testing tools. The user has explicitly requested Phase 05 and authorizes implementation of test code according to phases 01-04 and the required small isolated validation. First check the preceding artifacts and design-readiness status; do not fill in a complete missing design independently.

Complete the following:

1. Read relevant code, existing tests, and workspace status. Implement tasks in TASK order, reuse project conventions, and preserve user changes.
2. Implement isolated configuration, mocked upstreams, test samples, load models, independent arrival-rate injection, business assertions, required metrics, and result export. Keep necessary application changes minimal and explain whether default behavior is affected.
3. The test mode must be explicitly enabled and must not silently change normal runtime behavior. If mock configuration is missing, do not fall back to real services.
4. Add meaningful verification for queue completion, duplicate records, file mapping, and expected rejections. Do not write tests that merely repeat implementation details for the sake of quantity.
5. Implement the command interfaces planned in Phase 04 and document commands that actually exist and run in the runbook. State working directory, dependencies, parameters, artifact location, resource scope, and cleanup. Do not put real credentials in commands.
6. Run required related functional checks and the pre-limited small isolated smoke. Ensure zero calls to real services and inspect actual output and exit status.
7. Provide preflight, startup, execution, drain, and cleanup methods for Phase 06. Mark unverified commands explicitly and do not claim that everything passed.

Artifacts: implementation code/configuration, `docs/load-testing/05-runbook.md`, and `docs/load-testing/05-validation.md`. Use the code directory selected in Phase 04.

Definition of done: The core test path is reproducible; smoke and related functional validation have real evidence; production behavior has no unexpected change; no full load/spike/soak test was run and no real provider was called.

At the end, summarize changes, commands run and results, and remaining limitations, then stop.

## Phase 06: Test execution and evidence collection (later)

### Complete prompt

You are the test execution lead. The user has explicitly requested Phase 06 and authorizes running the designed tests in an isolated test environment. Read phases 01-05 and the runbook; use only implemented commands; do not call real external services or send real messages.

Complete the following:

1. Confirm the test target, independent data directory, mocked services, test credentials, process ownership, resource limits, and free ports. Ensure configuration and output directories belong to this run and cannot point to existing business data.
2. Fix and save the experiment configuration and acceptance thresholds. Record the current source version; if uncommitted changes exist, record their file status or summary instead of relying only on a commit ID.
3. Run the environment smoke first, then baseline, step load, spike, boundary, soak, and recovery according to the design. Reset or preload data for each run as designed; do not use backlog from one run as the baseline for another.
4. Compare planned and actual arrival rates, generator resource usage, and backend resource usage. If the generator cannot produce the target load, mark the experiment invalid or the evidence insufficient; do not claim the system met the target load.
5. Record HTTP and business results, queue and completion times, maximum backlog, drain time, duplicate/missing records, and resource changes together. Report deliberately injected errors separately from unexpected errors.
6. When predetermined stop conditions are met, stop injection, retain raw results, and perform bounded draining and cleanup as planned. Clearly mark aborted, failed, or unexecuted scenarios.
7. When problems occur, preserve reproducible evidence; do not tune thresholds or change code during testing. Repeat only when a designed rerun condition or new diagnostic need exists.
8. Close processes started for this run after completion and retain raw data needed for reporting. Handle only temporary files belonging to this run; do not delete other runs or business materials.

Artifacts: raw metrics, environment inventory, redacted logs, data verification results saved by run ID, and `docs/load-testing/06-execution-log.md`.

Definition of done: Every planned scenario has an execution status and reason; environment and load are traceable; data correctness is checked; incomplete experiments are not reported as passing.

At the end, summarize execution scope, findings, and incomplete items, then stop. Do not automatically fix issues or produce unsupported capacity conclusions.

## Phase 07: Analysis, defect reports, and regression plan (later)

### Complete prompt

You are the QA reviewer responsible for quality conclusions. Read artifacts from phases 01-06 and the actual raw results, then produce a test report suitable for project review and QA portfolio presentation. This phase performs analysis and reporting only; do not change code or rerun load tests.

Complete the following:

1. Give each REQ and LT a status of pass, fail, insufficient evidence, or not executed, with links to the specific run and evidence. Do not judge pass/fail from average response time alone.
2. For each scenario, show request count, independent message count, sample size, actual load, P50/P95/P99, business success rate, expected rejections, unexpected failures, backlog, and data-correctness verification. Explain percentile limitations for small samples.
3. Distinguish observed symptoms, evidence-supported causes, and bottleneck hypotheses awaiting verification. Analyze resource and queue data; do not attribute every wait to FastAPI or SQLite.
4. Use standard static charts to show response time versus load, queue over time, and resource changes only where data supports them. Retain chart data and exports. When data is absent, do not create illustrative charts that look measured.
5. Create BUG identifiers for reproducible problems, including title, severity, linked REQ/LT, environment, reproduction steps, expected/actual result, evidence, and suggested investigation direction. Normal capacity-protection behavior is a defect only when it violates an established requirement.
6. State which targets have been verified under which environment, data, and mock latency, and at what load. Do not generalize mock-environment conclusions to real OpenAI/Meta services or production capacity.
7. Provide evidence-ranked improvement recommendations and a regression plan, specifying cases to rerun and control conditions to preserve. Leave fixes and reruns to later explicitly authorized tasks; do not execute them in this phase.
8. Prepare a QA-project presentation summary covering the business problem, test method, key findings, evidence, and limitations. Do not invent fixes, performance improvements, or personal experience.

Artifacts: `docs/load-testing/07-test-report.md`, `docs/load-testing/07-defects.md`, `docs/load-testing/07-regression-plan.md`, and charts backed by actual data.

Definition of done: Conclusions trace to data; defects are reproducible; scope and limitations are transparent; unsupported areas remain explicitly unknown.

At the end, provide the quality conclusion, main risks, next priorities, and artifact links, then stop.

## Manual review focus after design completion

When reviewing phases 01-04, focus on whether the goals match the QA skills being practiced, whether cases can judge business correctness, whether the load matches the current project, whether metrics can actually be collected, and whether tests are reproducible.

Sending an execution instruction for a phase means that you want the AI to complete that phase within its stated scope. There is no need to confirm again after every document edit. Real-provider testing, real message sending, production deployment, and architecture scaling are outside this default workflow.
