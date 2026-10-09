# Voice Notes v3 — iOS + Meta WhatsApp Cloud API

v3 is a separate copy of the v2 Flutter + FastAPI app. It keeps file upload, English/French translation, and live microphone modes, and adds a generated iOS/Xcode project, a protected server connection screen, a WhatsApp voice-message inbox, Meta webhook signature verification, WABA/phone-number filtering, authenticated media checks, a durable SQLite queue, retries, crash recovery, 24-hour retention, and delete actions.

The app never contains OpenAI or Meta credentials. The iOS app only receives the separate `APP_ACCESS_TOKEN` used to access this backend.

## Requirements

- Python 3.11 or newer. The backend uses `asyncio.timeout`, which is available from Python 3.11.
- Flutter with Dart 3.10 or newer, as declared in `frontend/pubspec.yaml`.
- FFmpeg on `PATH` for the OGG/Opus conversion path. On macOS, the backend error message recommends `brew install ffmpeg`; on other systems, install FFmpeg using the platform's package manager and verify with `ffmpeg -version`.
- An OpenAI Platform API key for transcription and translation.
- A Meta app and WhatsApp Cloud API test number to use the WhatsApp inbox.

## Local backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python ../scripts/init_env.py
```

The helper creates `backend/.env` with mode `0600` and generates separate values for `APP_ACCESS_TOKEN` and `WHATSAPP_VERIFY_TOKEN` without printing them. Then edit `backend/.env` locally: set `OPENAI_API_KEY` and the Meta values listed below. The helper exits without changing an existing `.env`.

To start from the example file instead, use `cp .env.example .env` and fill the required values locally. Generate distinct random values for `APP_ACCESS_TOKEN` and `WHATSAPP_VERIFY_TOKEN`; never reuse either provider token for these settings. Do not commit `.env` or paste its values into the app or chat.

`OPENAI_API_KEY` is a separate OpenAI Platform API key. `APP_ACCESS_TOKEN` only protects this app, and `WHATSAPP_ACCESS_TOKEN` only calls Meta's WhatsApp API; neither one can transcribe or translate audio.

If this checkout sits beside the older project and its `.env` is one directory above the checkout, the helper can copy only the existing OpenAI key and model settings:

```bash
python ../scripts/init_env.py --reuse-v2-openai
```

Start the backend on port 8003:

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8003 --no-access-log
```

`uvicorn` loads `backend/.env` when it starts. If a value is already exported in the shell, `python-dotenv` does not override it; clear stale exported values before starting the backend. For example, run `unset APP_ACCESS_TOKEN` if that variable is set in the shell. Restart FastAPI after changing `.env` so it loads the new settings.

If live translation or file transcription reports that OpenAI rejected the key, replace `OPENAI_API_KEY` with an active key from the OpenAI Platform and restart FastAPI. A WhatsApp Cloud API token cannot be used for these two features.

Live microphone mode uses two server-side Realtime sessions: the translation session and a companion transcription session for the original-language captions. The defaults are `REALTIME_TRANSCRIPTION_SESSION_MODEL=gpt-realtime` and `REALTIME_TRANSCRIPTION_MODEL=gpt-live-transcribe`; override them in `.env` only if your OpenAI project uses different model access.

When the target is English and the speaker is already speaking English, the app mirrors the original transcript into the English translation panel because the translation endpoint can correctly omit a no-op translation event.

The backend keeps its WhatsApp worker queue in `backend/data/inbox.sqlite3`. Persisted voice feedback uses `backend/data/voice_feedback.db`; uploaded and WhatsApp audio is stored under `backend/data/audio/`. Completed Live Translate sessions save their original-language transcript and translation, but not the live audio. The SQLite schemas and audio directory are created automatically as the app uses them; there is no separate migration command. These paths are relative to the backend project, and `backend/data/` is excluded from Git. Data stays on the machine running FastAPI; it is not automatically synced to the iPhone. The `voice_feedback` table does not use or modify the legacy `patient_feedback` table or collection.

The page has one **Save to Database** switch shared by WhatsApp, Upload, and Speak Live. When enabled, uploads and WhatsApp messages save their original audio plus transcript; completed live sessions save their transcript and translation. Each row records its `source`. When disabled, transcription and the temporary WhatsApp inbox still work, but new items are not written to `voice_feedback`. The setting is stored in the same local database and defaults to enabled on first initialization. Upload uses **Upload & transcribe** and a generated server-side filename. A transcription failure retains saved audio and marks its row `failed`.

The Meta webhook continues to verify the GET challenge and validate `X-Hub-Signature-256` before accepting a POST. Configure Meta's callback URL as `https://<backend-host>/webhooks/whatsapp`, subscribe the WhatsApp Business Account to `messages`, and put the same verify token and app secret in the backend configuration. With saving enabled, the worker acknowledges after queueing, downloads media from trusted Meta hosts, copies original bytes to `backend/data/audio/`, creates a pending `voice_feedback` row, and transcribes it. `source_message_id` is unique when present, so webhook retries reuse the same record. Queue/result retention does not automatically delete rows or audio from `voice_feedback`.

The frontend language menu switches the current pages between English, French, and Arabic; Arabic uses right-to-left layout. Shared page copy is in `frontend/lib/app_strings.dart` so translations can be extended for additional pages.

To initialize local storage, install the normal backend requirements and run FastAPI as described above. The database and audio directory are created automatically on the first upload or WhatsApp audio message. Tests use temporary database/audio locations and mocked external providers. FFmpeg is still needed for the existing OGG/Opus transcription path.

## Run the Flutter app

```bash
cd frontend
export PATH="/path/to/flutter/bin:$PATH"
flutter pub get
flutter run -d chrome --web-port 5174
```

If Chrome is not available as a Flutter device, use `flutter run -d web-server --web-port 5174 --web-hostname 127.0.0.1` and open `http://127.0.0.1:5174` in a browser. In **Connection settings**, enter `http://127.0.0.1:8003` and the local `APP_ACCESS_TOKEN` from `backend/.env`. The token is held in memory for this prototype and cleared when you disconnect or close the app. Release builds require an HTTPS backend.

On a physical iPhone during a debug run, use the Mac's private LAN address instead, for example `http://192.168.1.20:8003`. Keep the phone and Mac on the same Wi-Fi network and allow incoming connections to Python when macOS asks. `127.0.0.1` on a physical iPhone means the iPhone itself, not the Mac.

The iOS project includes microphone and local-network permission strings. To run on a simulator or iPhone, install the full Xcode app, select it with `xcode-select`, then run:

```bash
export PATH="/path/to/flutter/bin:$PATH"
flutter doctor
flutter run -d ios
```

For a physical device, choose an Apple signing team in Xcode. A production deployment also needs an HTTPS backend whose certificate is trusted by iOS. Flutter's official guide covers Xcode signing, TestFlight, and `flutter build ipa`: [Flutter iOS deployment guide](https://docs.flutter.dev/deployment/ios).

## Configure Meta WhatsApp Cloud API

Set these values in `backend/.env`:

```text
OPENAI_API_KEY
APP_ACCESS_TOKEN
WHATSAPP_ACCESS_TOKEN
WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_WABA_ID
WHATSAPP_APP_SECRET
WHATSAPP_VERIFY_TOKEN
WHATSAPP_GRAPH_VERSION
WHATSAPP_TARGET_LANGUAGE
WHATSAPP_ALLOWED_SENDERS
```

`WHATSAPP_GRAPH_VERSION` must use the version shown in Meta API Setup (for example, the `vNN.N` format). `WHATSAPP_TARGET_LANGUAGE` defaults to `fr`. Set `WHATSAPP_ALLOWED_SENDERS` to the personal/test sender number as country code plus digits, without `+`, spaces, or hyphens. This allowlist is optional in code, but leaving it empty accepts any sender whose message arrives for the configured WABA and phone number. Keep `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`, and `WHATSAPP_VERIFY_TOKEN` private. The verify token in Meta must exactly match the value in `backend/.env`.

Expose the webhook through a public HTTPS endpoint and set Meta's callback URL to `https://<public-host>/webhooks/whatsapp`. This repository does not include a tunnel or reverse-proxy configuration. Configure your chosen HTTPS tunnel/proxy to forward the webhook route to `http://127.0.0.1:8003/webhooks/whatsapp`; avoid exposing other backend routes publicly. Subscribe the WhatsApp Business Account to the `messages` webhook field. Meta calls `GET /webhooks/whatsapp` with `hub.mode`, `hub.verify_token`, and `hub.challenge`; the backend validates the token and returns the challenge. Incoming `POST` events must carry a valid `X-Hub-Signature-256`, checked with the app secret before any payload is parsed or queued.

Meta's dashboard may allow an unpublished app to receive only synthetic test webhooks sent from the dashboard. Real WhatsApp messages are not delivered to the callback while the app is unpublished, including messages sent by app admins, developers, or testers. Follow the requirements shown by Meta and publish the app before expecting real inbound messages. A successful test-template send tests outbound sending; it does not verify inbound webhook delivery.

The handler accepts audio messages only after checking the WABA ID, `metadata.phone_number_id`, message type, sender allowlist, and message age. It queues the media ID and acknowledges quickly. `queued: 0` can mean the event did not match those filters or the message was already queued. A worker retrieves the media URL with the bearer token, downloads only trusted HTTPS Meta media hosts, verifies the advertised hash, transcribes the temporary file, and translates it. Meta's collection documents the media-ID to URL lookup, short-lived URL, bearer token, and supported audio types: [Meta Cloud API media reference](https://www.postman.com/meta/whatsapp-business-platform/request/fpj02x0/retrieve-media-url) and [media collection](https://www.postman.com/meta/whatsapp-business-platform/folder/13382743-ecb27be5-4d27-4763-bbee-6a8002c04bf3).

For a privacy-safe local run, keep Uvicorn access logging disabled: Meta's GET verification request includes the verify token in its query string. The worker logs successful audio download, transcription, and completion stages without message content, sender numbers, media IDs, or credentials.

## Troubleshooting

- `401` from `/api/` means the app access token in Connection settings does not match the backend's `APP_ACCESS_TOKEN`.
- `503` from `/api/` or an incomplete WhatsApp status means a required backend setting is missing or invalid. Restart FastAPI after editing `.env`.
- `403` during GET webhook verification means Meta's verify token does not match `WHATSAPP_VERIFY_TOKEN`. A `403` on POST means the request signature does not match `WHATSAPP_APP_SECRET`.
- A successful webhook response with `queued: 0` does not prove that an audio job was queued. Check the WABA ID, phone number ID, `messages` field, audio message type, sender allowlist, and whether Meta is redelivering a duplicate.
- If Meta's dashboard shows a delivery but the local queue stays empty, check whether the app is published and whether the public callback still reaches this backend.
- If media download fails, check that `WHATSAPP_ACCESS_TOKEN` is active and has access to the configured WhatsApp number. If transcription fails, check the separate `OPENAI_API_KEY` and the selected model access.
- If OGG/Opus processing reports that FFmpeg is missing, install FFmpeg and confirm `ffmpeg -version` works in the backend shell.

## Verification

```bash
cd backend
.venv/bin/python -m pytest -q

cd ../frontend
export PATH="/path/to/flutter/bin:$PATH"
flutter analyze
flutter test
flutter build web --release
```

The v3 backend suite covers app behavior, webhook verification, signature checks, queue deduplication, WABA filtering, retries, stale leases, retention, media integrity, local audio persistence, transcription outcomes, and app authentication.

The native iOS Simulator build has been verified with the `test` simulator. A signed device build, TestFlight upload, and App Store release still require selecting an Apple Developer Team and completing signing in Xcode.
