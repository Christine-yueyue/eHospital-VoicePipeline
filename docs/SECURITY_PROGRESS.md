# Security work progress

Updated: 2026-11-02. Status: in progress.

User request: improve security design and tests; all deliverables must be in English.

## Findings and intended changes

- Add authenticated, bounded HTTP request ingestion before multipart/JSON parsing, with a read deadline and concurrency limit.
- Prevent AI output from directly granting contact consent; require a separate operator confirmation through the existing authenticated consent endpoint, with a UI for it.
- Bound WebSocket authentication/control frames before JSON parsing.
- Add isolated security regressions for authentication, oversized/chunked requests, prompt injection, consent, send deduplication, and stale template previews.
- Document the single-owner trust boundary and production requirements, especially data retention/deletion, identity, encryption, and deployment controls.

## Existing work to preserve

`docs/LOAD_TEST_AI_WORKFLOW.md` and `docs/qa-agent-workflow/` were already untracked before this task. Do not overwrite them.

## Verification and environment

- No tests run yet. The project Python at `backend/.venv/bin/python` fails because the sandbox blocks its Python 3.13 framework, including after an escalation attempt.
- Never load `.env` or real credentials. Tests must use temporary databases and mocked providers, and must not send real messages.
- An hourly thread heartbeat was created successfully with automation ID `automation`. Stop it when the task is complete. It can attempt continuation while the desktop scheduler and usage are available; it cannot bypass usage limits.
- Git works with `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1`; scope status/diff commands to changed source files to avoid touching denied `.env.example` metadata.

## Next steps

Implement the changes, add and run regressions, write `docs/SECURITY_DESIGN.md`, then update this checkpoint with actual verification results and remaining production requirements.
