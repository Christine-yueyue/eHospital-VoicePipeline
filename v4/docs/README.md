# Voice Notes v4 — Technical Documentation

**Document set:** 1.0 · **Software:** 4.0.0+1 · **Date:** September 28, 2026 (America/Toronto)

This package describes the implemented prototype and provides candidate requirements, reproducible verification evidence, and a path to live acceptance. The requirements are **draft for professor/TA review**. No stakeholder approval, production readiness, or successful live Meta integration is implied.

| Document | Purpose | Primary reader |
| --- | --- | --- |
| [Software requirements specification](REQUIREMENTS.md) | Scope, numbered requirements, acceptance conditions and exclusions | Professor, TA, developer |
| [Architecture and design](ARCHITECTURE.md) | Components, data flows, worker lifecycle and design decisions | Developer, reviewer |
| [API reference](API_REFERENCE.md) | REST, webhook and WebSocket contracts with examples | Integration developer |
| [Database specification](DATABASE.md) | Actual SQLite schema, data lifecycle and integration decisions | TA, database owner |
| [Test plan and UAT](TEST_PLAN.md) | Test strategy, live test procedures and acceptance gates | Tester, professor |
| [Test report](TEST_REPORT.md) | Fresh execution results, evidence, limitations and release assessment | All reviewers |
| [Requirements traceability](TRACEABILITY.md) | Requirements → code → tests → remaining evidence | Reviewer |
| [Deployment and operations](DEPLOYMENT_OPERATIONS.md) | Installation, configuration, monitoring, recovery and handover | Developer, operator |
| [Decisions and risks](DECISIONS_AND_RISKS.md) | Unresolved requirements, owners and release dependencies | Professor, TA |
| [Release notes](RELEASE_NOTES.md) | v4 changes, compatibility and known limitations | All users |

For a review meeting, read Requirements, Test Report, and Decisions and Risks first. For integration work, continue with API Reference, Database, and Deployment and Operations.

## Evidence and provenance

The test report links the exact evidence directory, including command exit codes, tool versions, backend JUnit XML, Flutter machine-readable results and source SHA-256 hashes. The source is currently uncommitted; a Git release tag is not available. The manifest identifies the tested working files. The runner is [validate_release.py](../scripts/validate_release.py).

This documentation task adds documentation and a verification runner; it does not change the application behavior. External-provider operations are mocked in automated tests. A simulator build is compilation evidence, not a physical-device or real-call test.

Existing [setup/resource discussion](SETUP_AND_REQUIREMENTS.md) and [professor email draft](PROFESSOR_UPDATE_DRAFT.md) remain available as background. Where a technical detail differs, use this package's code-derived specification and the current test evidence. External provider eligibility must be reconfirmed for the actual account before deployment.

## Document maintenance

Change the candidate requirement and its traceability row when scope changes; update code and tests as needed; rerun verification; retain the previous evidence directory; then revise the test report and release notes. Record the reviewer, decision and date in the decision register. Never label a proposed target or unexecuted test as passed.
