# Security work progress

Updated: 2026-11-03. Status: implementation and security design are present; full verification is pending.

All implementation, documentation, and test artifacts for this work are in English.

## Implemented

- Added `backend/security.py` to authenticate API requests before reading request bodies, enforce declared and streamed body limits, reject inconsistent HTTP framing and compressed request bodies, spool bounded bodies before multipart parsing, apply a read deadline, and cap concurrent API requests per process.
- Limited WebSocket authentication and control-message frames.
- Added strict local validation of assistant output. AI-created contacts start with unknown permission, AI permission updates produce a confirmation card, and an operator must separately record a permission status and source before preparing a fresh invitation.
- Added restrictive permissions for the SQLite database and saved audio, safe filename-extension validation, and tests for partial-copy cleanup.
- Preserved existing WhatsApp signature/account/media protections and expanded SSRF regression cases.
- Added backend security regressions, a Flutter consent widget regression, and a CI workflow for backend tests and dependency auditing.
- Wrote the threat model, implemented-control inventory, data lifecycle assessment, production requirements, and verification record in `docs/SECURITY_DESIGN.md`.

## Verification

- Four standard-library storage security tests passed: `PYTHONPATH=backend /usr/bin/python3 -m unittest discover -s backend/tests -p test_storage_security.py -v`.
- Python syntax parsing and Git whitespace checks passed.
- The full backend pytest suite, Flutter analyzer/tests/build, CI workflow, and dependency audit have not been run successfully. The available project Python runtime is blocked by the environment; the system Python is 3.9.6 and cannot run the FastAPI suite. Flutter is not available on the command path. Do not represent the unrun checks as passing.
- Tests are designed to avoid external calls, read no `.env` file, use temporary storage, and mock provider APIs. No real WhatsApp message was sent.

## Remaining production work

- Run the full backend suite and Flutter analyzer/tests/build in an environment with the project's supported Python and Flutter toolchains. Check the CI result when the workflow runs.
- Resolve every failure; audit dependencies and check the dependency set against a lockfile.
- Add a complete retention and deletion lifecycle for persisted audio, feedback, consent, follow-up data, and backups. The existing inbox's 24-hour expiry does not cover this persisted data.
- Before adding multiple users or handling production sensitive data, add identity, user/record authorization, audit history, encryption/key management, and reviewed provider/data-retention controls.
- Configure deployment-level TLS, route restrictions, connection and shared rate/cost limits, and WebSocket admission. The current HTTP concurrency limit is per process and does not protect all ingress paths.

## User changes to preserve

`docs/LOAD_TEST_AI_WORKFLOW.md` and `docs/qa-agent-workflow/` existed as untracked user work before this security task. Preserve them.
