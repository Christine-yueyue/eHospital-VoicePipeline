# Voice Notes v4 — Meta call transcripts → iOS Inbox

The [English technical documentation package](docs/README.md) includes the requirements specification, architecture, API/database contracts, test plan and report, traceability, deployment runbook, open decisions and release notes.

v4 is an independent copy of v3. It adds this path:

```text
POST /webhooks/whatsapp (field: calls)
  → verify X-Hub-Signature-256 + WABA/phone/sender filters
  → call_transcription_available
  → commit a call job to SQLite, then acknowledge
  → document.id → authenticated Media API lookup → fresh download URL
  → download JSON + verify SHA-256 from the signed webhook
  → parse transcript.text, language, duration and speaker segments
  → save the original transcript → translate text into English/French
  → authenticated iOS Inbox (refreshes every 5 seconds while open)
```

The call path uses Meta's existing transcript. It never sends call audio to OpenAI transcription. v3's voice-message, file-upload and live microphone modes remain available in v4. Translation still uses the existing OpenAI text service.

## Version isolation

| Item | v3 | v4 |
| --- | --- | --- |
| Source directory | `v3/` | `v4/` |
| Backend port | 8003 | 8004 |
| Web development port | 5174 | 5175 |
| Backend settings | `v3/backend/.env` | `v4/backend/.env` |
| SQLite database | `v3/backend/data/inbox.sqlite3` | `v4/backend/data/inbox.sqlite3` |
| iOS Bundle ID | `com.christine.voiceNotes` | `com.christine.voiceNotesV4` |
| iOS display name | Voice Notes | Voice Notes v4 |

The two iOS apps can coexist. v4 requires backend version `4.0.0`. Do not set `INBOX_DB_PATH` to v3's database when running both. Existing v3 results, credentials and source files are not migrated or overwritten.

## Run locally

```bash
cd /Users/christine/Documents/ChatGPT/voice-text-project/v4/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python ../scripts/init_env.py --reuse-v3-settings
uvicorn app:app --reload --host 127.0.0.1 --port 8004
```

The initializer only reads v3's known provider settings and creates **new** app and webhook verification tokens. It never overwrites an existing v4 `.env`, prints credentials, or copies v3's database. Omit `--reuse-v3-settings` for empty provider settings. Fill any missing values in `v4/backend/.env` locally. Restart the backend after editing settings; shell environment variables take precedence over `.env`.

```bash
cd /Users/christine/Documents/ChatGPT/voice-text-project/v4/frontend
export PATH="/Users/christine/Documents/flutter/bin:$PATH"
flutter pub get
flutter devices
flutter run -d <ios-simulator-device-id>
```

In **Connection settings**, use `http://127.0.0.1:8004` on the iOS simulator and the new v4 `APP_ACCESS_TOKEN`. Open **WhatsApp inbox**. Cards distinguish Meta call transcripts from voice messages, show download/parse/translation progress, and provide the original text, translation, detected language, call duration, expandable speaker timeline, retry and delete actions.

For a physical iPhone in a local debug run, bind the backend to `0.0.0.0` and use the Mac's private LAN address, such as `http://192.168.1.20:8004`. The phone and Mac must share a network. Select an Apple signing team for a device build. Release builds need a trusted HTTPS backend. The app token stays in memory; OpenAI and Meta credentials stay on the backend.

Optional web development: `flutter run -d chrome --web-port 5175`.

## Connect Meta

The implementation follows Meta's [Call transcription reference](https://developers.facebook.com/documentation/business-messaging/whatsapp/calling/call-transcription/) (reviewed September 27, 2026; page updated August 31, 2026) and its [Media API](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media).

1. Configure `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_WABA_ID`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN` and the Graph version supported by your account in v4's `.env`. Configure `OPENAI_API_KEY` for text translation. `WHATSAPP_TARGET_LANGUAGE` is `fr` or `en`.
2. Expose v4's `/webhooks/whatsapp` through your HTTPS backend, use v4's verify token in Meta, and subscribe to the **`calls`** webhook field. Keep **`messages`** subscribed if using voice messages too. The API credentials must belong to the configured business assets.
3. Enable Calling API for the business number. In your existing call initiation (`connect`) or acceptance (`accept`) request, add the following object with the purpose and announcement language appropriate to the call:

```json
{
  "transcription": {
    "status": "ENABLED",
    "purpose": "translation and follow-up notes",
    "announcement_language": "en_US"
  }
}
```

This fragment belongs inside the existing Calling API request; it is not a standalone call request. Meta handles the announcement and produces the transcript after the call. Enabling recording alone does not enable transcription.

This version starts at webhook reception. It does not implement a dialer, accept calls, negotiate WebRTC/SIP, or change your Meta account settings. It receives transcripts for opted-in WhatsApp Business Cloud API calls; it cannot read personal WhatsApp call history. Changing an existing Meta app's callback can redirect its events away from v3, even though the local applications are separate. Use a separate test app/subscription if both must receive events independently.

Meta currently documents a five-minute download URL and seven-day media availability. v4 always obtains a fresh URL using `document.id`, so delayed jobs and retries do not depend on the URL from the webhook. It validates the downloaded bytes against `document.sha256`. It supports phone-number senders and `from_user_id` / `from_parent_user_id` identities. `WHATSAPP_ALLOWED_SENDERS` can contain phone numbers or these business-scoped user IDs.

## Storage and failure behavior

- Audio messages and calls share a bounded durable queue. One call produces one Inbox result; duplicate events or reissued media IDs do not produce duplicates.
- Original text and speaker metadata are checkpointed before translation. A translation retry or recovered worker reuses this data. Stale workers cannot overwrite a newer attempt or resurrect a deleted result.
- Temporary failures retry up to three attempts. Permanent failures and empty/unsupported transcripts remain visible with an error. Failed or partially translated results can be retried from the app.
- Calls are translated in chunks of at most 6,000 characters. Each call job has a 10-minute processing timeout. The prototype accepts JSON up to 8 MB, text up to 100,000 characters, and up to 5,000 segments; oversized results fail visibly.
- Results and speaker segments expire 24 hours after receipt. Old events are ignored. IDs remain as deduplication tombstones for seven days. Delete clears content immediately. The server stores masked participant identifiers; raw webhooks, media URLs and word-level metadata are not retained.
- Inbox refresh uses foreground polling. There are no APNs push notifications or guaranteed background refresh.

## Verification

Verified locally: **97 backend tests**, **9 Flutter tests**, clean Flutter analysis,
and a successful iOS Simulator debug build (`build/ios/iphonesimulator/Runner.app`,
version `4.0.0`, Bundle ID `com.christine.voiceNotesV4`). All 73 v3 source files
matched their pre-v4 SHA-256 hashes. Real Meta delivery and signed-device builds
have not been verified.

```bash
cd /Users/christine/Documents/ChatGPT/voice-text-project/v4/backend
.venv/bin/python -m pytest -q

cd ../frontend
export PATH="/Users/christine/Documents/flutter/bin:$PATH"
flutter analyze --no-pub
flutter test --no-pub
flutter build ios --simulator --debug --no-pub
```

`backend/tests/test_calls.py` includes a complete signed webhook → durable queue → authenticated Meta media lookup/download → JSON parser → translator → Inbox API test using synthetic provider responses. It also covers tenant/sender filters, duplicate/mixed batches, media integrity, URL restrictions, size limits, empty transcripts, retries, crash recovery, deletion, and schema migration. Flutter tests cover phone-width call cards, speaker timelines, polling, retries and rejecting a v3 backend.

Automated provider tests are offline and do not incur API charges. Real Meta webhook delivery and real translation require valid account settings and a call with transcription enabled; successful automated tests do not establish that those external settings are ready.
