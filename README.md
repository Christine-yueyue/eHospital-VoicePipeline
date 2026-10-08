# Voice Notes v3 — iOS + Meta WhatsApp Cloud API

v3 is a separate copy of the v2 Flutter + FastAPI app. It keeps file upload, English/French translation, and live microphone modes, and adds a generated iOS/Xcode project, a protected server connection screen, a WhatsApp voice-message inbox, Meta webhook signature verification, WABA/phone-number filtering, authenticated media checks, a durable SQLite queue, retries, crash recovery, 24-hour retention, and delete actions.

The app never contains OpenAI or Meta credentials. The iOS app only receives the separate `APP_ACCESS_TOKEN` used to access your v3 backend.

## Local backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Generate private values with `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`. Put one into `APP_ACCESS_TOKEN` and another into `WHATSAPP_VERIFY_TOKEN`. Fill the Meta fields in `.env` locally. Do not commit `.env` or paste its values into the app.

`OPENAI_API_KEY` is a separate OpenAI Platform API key. `APP_ACCESS_TOKEN` only protects this app, and `WHATSAPP_ACCESS_TOKEN` only calls Meta's WhatsApp API; neither one can transcribe or translate audio.

To create a private development file that reuses only the existing local OpenAI settings:

```bash
python ../scripts/init_env.py --reuse-v2-openai
```

Start v3 on port 8003 so it does not collide with v2:

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8003 --no-access-log
```

If you change `APP_ACCESS_TOKEN` and the app still reports an invalid token, stop the old backend process and start it again. For a local run, clear a token that may already be exported in the terminal first: `unset APP_ACCESS_TOKEN`. The backend then reloads the value from `v3/backend/.env`.

If live translation or file transcription reports that OpenAI rejected the key, replace `OPENAI_API_KEY` with an active key from the OpenAI Platform and restart FastAPI. A WhatsApp Cloud API token cannot be used for these two features.

Live microphone mode uses two server-side Realtime sessions: the translation session and a companion transcription session for the original-language captions. The defaults are `REALTIME_TRANSCRIPTION_SESSION_MODEL=gpt-realtime` and `REALTIME_TRANSCRIPTION_MODEL=gpt-live-transcribe`; override them in `.env` only if your OpenAI project uses different model access.

When the target is English and the speaker is already speaking English, the app mirrors the original transcript into the English translation panel because the translation endpoint can correctly omit a no-op translation event.

The backend keeps its WhatsApp worker queue in `backend/data/inbox.sqlite3`. Persisted voice feedback uses `backend/data/voice_feedback.db` and stores original audio under `backend/data/audio/`. These paths are resolved relative to the backend project, and `backend/data/` is excluded from Git. Data stays on the machine running FastAPI; it is not automatically synced to the iPhone. The `voice_feedback` table does not use or modify the legacy `patient_feedback` table or collection.

The page has one **Save to Database** switch shared by WhatsApp, Upload, and Speak Live. When enabled, uploads and WhatsApp messages save their original audio plus transcript; completed live sessions save their transcript and translation. Each row records its `source`. When disabled, transcription and the temporary WhatsApp inbox still work, but new items are not written to `voice_feedback`. The setting is stored in the same local database. Upload uses **Upload & transcribe** and a generated server-side filename. A transcription failure retains saved audio and marks its row `failed`.

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

Choose Connection settings, enter `http://127.0.0.1:8003` for a local debug run, and paste `APP_ACCESS_TOKEN`. Release builds require an HTTPS backend. The token is held in memory for this prototype and cleared when you disconnect or close the app.

On a physical iPhone during a debug run, use the Mac's private LAN address instead, for example `http://192.168.1.20:8003`. Keep the phone and Mac on the same Wi-Fi network and allow incoming connections to Python when macOS asks. `127.0.0.1` on a physical iPhone means the iPhone itself, not the Mac.

The iOS project includes microphone and local-network permission strings. To run on a simulator or iPhone, install the full Xcode app, select it with `xcode-select`, then run:

```bash
export PATH="/path/to/flutter/bin:$PATH"
flutter doctor
flutter run -d ios
```

For a physical device, choose an Apple signing team in Xcode. A production deployment also needs an HTTPS backend whose certificate is trusted by iOS. Flutter's official guide covers Xcode signing, TestFlight, and `flutter build ipa`: [Flutter iOS deployment guide](https://docs.flutter.dev/deployment/ios).

## Configure Meta WhatsApp Cloud API

Fill these backend values:

```text
WHATSAPP_ACCESS_TOKEN
WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_WABA_ID
WHATSAPP_APP_SECRET
WHATSAPP_VERIFY_TOKEN
WHATSAPP_GRAPH_VERSION
WHATSAPP_TARGET_LANGUAGE=fr
WHATSAPP_ALLOWED_SENDERS=14165550123
```

Use the same random verify token in Meta's webhook form and `.env`. Set `WHATSAPP_ALLOWED_SENDERS` to your test sender number with country code and digits; leaving it empty accepts any sender whose message arrives for the configured WABA and phone number.

Expose only the webhook through a public HTTPS endpoint and configure the callback URL as `/webhooks/whatsapp`. Meta calls `GET /webhooks/whatsapp` with `hub.mode`, `hub.verify_token`, and `hub.challenge`; the backend validates the token and returns the challenge. Incoming `POST` events must carry a valid `X-Hub-Signature-256`, checked with the app secret before any payload is parsed or queued.

The handler accepts audio messages only after checking the WABA ID and `metadata.phone_number_id`. It queues the media ID and acknowledges quickly. A worker retrieves the media URL with the bearer token, downloads only trusted HTTPS Meta media hosts, verifies the advertised hash, transcribes the temporary file, and translates it. Meta's collection documents the media-ID to URL lookup, short-lived URL, bearer token, and supported audio types: [Meta Cloud API media reference](https://www.postman.com/meta/whatsapp-business-platform/request/fpj02x0/retrieve-media-url) and [media collection](https://www.postman.com/meta/whatsapp-business-platform/folder/13382743-ecb27be5-4d27-4763-bbee-6a8002c04bf3).

For a privacy-safe local run, keep Uvicorn access logging disabled: Meta's GET verification request includes the verify token in its query string. The worker logs successful audio download, transcription, and completion stages without message content, sender numbers, media IDs, or credentials.

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
