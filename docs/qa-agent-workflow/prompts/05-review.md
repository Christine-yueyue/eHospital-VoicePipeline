# Stage 05 — Design Review and Implementation Plan

You are an independent reviewer. Read COMMON.md and all stage 01–04 deliverables; verify important claims against source. Do not implement code or run tests.

## Work

1. Check traceability across current source, requirements, risks, architecture, fixture, cases, and CI strategy. Explicitly look for missing post-Stop final events, virtual mic failure/looping, stale-session events, global Save to Database races, and a mock being misrepresented as real speech quality.
2. Review the code boundary. Keep all new Playwright source, helpers, dependencies and fixture assets under qa/voice_pipeline. Keep GitHub Actions orchestration in its standalone workflow. Do not edit app modules or existing tests. If the design needs an application-code change, stop and create a separate proposal.
3. Check the CI can fail closed when a provider fake is bypassed; verify no real API keys/secrets are required. Confirm persistence and browser state are isolated.
4. Correct internal design conflicts and record review findings. Distinguish a source-level verified fact from an untested browser assumption.
5. Give a go/no-go decision: ready for a limited feasibility spike, ready for full implementation, or blocked on a named fact.
6. Create ordered TASK items with prerequisites, expected files, completion criteria, and validation steps. First milestone must be a bounded feasibility spike, not a broad implementation.
7. Draft the future runbook structure without inventing runnable commands, workflow state, asset files, or tool availability.
8. List the small set of true decision blockers. Resolve ordinary implementation details with a reasoned recommendation.

## Deliverables

- outputs/05-design-review.md
- outputs/05-implementation-plan.md
- outputs/05-runbook-draft.md

## Completion criteria

Review is evidence-based and calls out any blockers. The next implementation step is scoped and reversible. Application-code edits are explicitly separated. No code, tests, CI edits, or execution were performed. Stop after this design review.
