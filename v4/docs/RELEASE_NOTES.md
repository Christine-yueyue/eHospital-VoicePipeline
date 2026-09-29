# Release Notes — Voice Notes v4

**Version:** 4.0.0+1 · **Status:** Local prototype / integration candidate

v4 adds a post-call path that receives Meta's `call_transcription_available` webhook, retrieves and validates the transcript JSON, parses source text and speaker segments, translates the text and displays both in the iOS Inbox. Calls use Meta's existing transcript; audio recognition remains part of the separate voice-message/upload paths.

## Changes

- Separate v4 source, settings, default database, ports and iOS Bundle ID preserve v3 as an independent application.
- Signed call-event filtering, call-ID deduplication, fresh media lookup, trusted-host download restrictions and SHA-256 validation.
- Durable original-text/speaker-data checkpoints, bounded translation chunks, retries and stale-worker protection.
- Inbox call/voice labels, progress, original/translated text, available metadata, speaker timeline, retry and deletion.
- Technical documentation, requirement traceability, live UAT plan and a repeatable verification runner.

Uploaded audio, WhatsApp voice messages and local microphone caption/translation remain available. No dialer, call-acceptance service, personal WhatsApp history access, APNs push or multi-user access model is added.

## Compatibility and configuration

The v4 client requires backend version `4.0.0`; it rejects v3. Default backend/web ports are 8004/5175 and the iOS Bundle ID is `com.christine.voiceNotesV4`. Existing v3 data is not automatically migrated. The v4 SQLite initializer can add its new columns to a compatible older schema, but shared use of v3's database is not the deployment plan.

Meta app/business permissions, webhook subscriptions and transcription-enabled call handling must be supplied/configured externally. A shared Meta app callback can redirect traffic from v3; coordinate that change. See [Deployment and Operations](DEPLOYMENT_OPERATIONS.md).

## Verification and limitations

[TR-V4-001](TEST_REPORT.md) records 97 passing backend tests, nine passing Flutter tests, clean analysis and a successful iOS Simulator debug build. Provider interactions were mocked. Real Meta delivery, real-model quality/latency, physical-device behavior, signed distribution and stakeholder acceptance remain unverified.

The baseline is single-owner with a shared access token, one worker, the latest 100 Inbox rows, 24-hour content retention and seven-day receipt-based tombstones. Foreground polling does not guarantee background delivery. Quality, scale, storage destination, retention and operational ownership require review in the [decision register](DECISIONS_AND_RISKS.md).

Documentation revision 1.0 describes the implemented prototype and adds validation evidence; it does not modify application behavior. The source remains an uncommitted working tree, identified for this test run by its saved manifest.
