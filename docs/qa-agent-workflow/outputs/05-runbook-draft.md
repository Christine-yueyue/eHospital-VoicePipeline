# 05 — CI Runbook Draft

Status: proposal only. None of these commands exists in the new qa/voice_pipeline layout yet.

## Planned workflow behavior

The dedicated voice-pipeline workflow runs three distinct parts:

1. Install Python, Flutter, backend packages, isolated QA dependencies, Chromium, and the audio decoder required by the installed backend test requirements.
2. Build or serve the Flutter Web frontend on a loopback port. Run the Playwright pytest process, which starts an isolated ASGI backend on a second loopback port with patched Upload functions and paired scripted Live upstreams.
3. Report case status; on failure retain only reviewed/redacted screenshots or traces. Exit nonzero for a failed assertion, provider-double bypass, readiness timeout, or incomplete cleanup.

The existing security workflow remains in place. The PR browser job must need no OpenAI or Meta secret. No real WhatsApp or provider call is part of the run.

## Proposed commands after implementation

The exact script names, port arguments, browser command, and working directory must be verified in TASK-001 through TASK-008 before this draft becomes a runbook. The implementation must supply:

- dependency installation;
- one TC-001 Upload test;
- one TC-005 Live final-word test;
- the complete offline regression suite;
- test evidence path and interpretation;
- opt-in real-service test with explicit budget input;
- cleanup for only test-started servers and temporary data.

Until those items exist, do not paste proposed command names into personal shell history or wire them into branch protection.

## Failure triage

- App did not become ready: inspect Flutter build/server log and backend /health readiness separately.
- Browser cannot locate a control: first inspect Flutter Web semantics and screenshot; do not default to coordinates.
- No Live audio reached fakes: inspect Chromium capture flags, permission and fixture playback; this is not a transcription failure.
- A fake was not called: the test harness may not have patched the imported connector used by the ASGI app; fail closed and stop before provider use.
- Mock event reached backend but UI failed: compare received WebSocket event sequence to the rendered result and controller lifecycle.
- CI trace contains a credential or real utterance: block artifact upload and tighten capture/redaction before rerunning.
- Real-service output differs from the reference: file an observed content-quality result with actual transcript/translation; do not modify deterministic mock expectations to match it.
