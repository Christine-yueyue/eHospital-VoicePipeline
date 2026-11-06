# Stage 07 — Execute and Report

Run this prompt only when the user requests test execution. Read COMMON.md, the implementation report, and the verified runbook. Default to offline mock mode.

## Work

1. Verify the current revision, test mode, fixture checksum, runner/tool versions, isolated DB/audio paths, and service readiness. Never inspect secret files or persistent business data.
2. Run the requested cases once, or use one bounded retry only to diagnose a suspected test-runner fault while preserving the first failure. Do not retry a product assertion to turn it green.
3. For mock mode, confirm Upload doubles and both Live upstream doubles were observed. Stop immediately if an unmocked provider connection is possible.
4. For real mode, run only when explicit authorization and a written cost cap are present. Include the Live translation and source-transcription upstreams in the estimate. If the total cannot be bounded or the requested fixture is not approved, do not call the provider.
5. Report each case as PASS, FAIL, BLOCKED, or NOT RUN. Attach sanitized logs, event chronology, traces, and screenshots. Redact tokens, headers, private file paths, and sensitive content before saving artifacts.
6. Separate product defects, app environment problems, test harness defects, and real model quality observations.
7. Give latency values with sample counts and measurement boundaries. Do not present a tiny sample as a reliable percentile. Do not use a model-generated quality judgment as the only pass criterion.
8. Stop only test-owned servers and clean up temporary DB/audio/browser resources. Do not begin repairs, CI configuration changes, deployments, or WhatsApp sends.

## Deliverables

- English run report with run ID, scope, environment, test results, limitations, and evidence.
- English defect list with clear reproduction steps and expected/actual behavior.
- Sanitized artifacts retained as specified in the runbook.

## Completion criteria

Every reported pass maps to an actual completed case and evidence. Unrun and blocked tests are counted separately. Conclusions stay within tested scope. Stop after reporting.
