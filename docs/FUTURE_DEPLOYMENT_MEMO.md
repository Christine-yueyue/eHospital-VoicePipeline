# Future Deployment Memo

## Recommendation

Wait until the professor's server and production database are ready, then deploy the backend once to the final environment. Do not use a temporary Render/Railway/Fly.io deployment first unless an immediate remote demo is required. A temporary deployment would create extra work for the database, domain, secrets, WhatsApp webhook, and iOS build configuration.

## Deployment order

1. Confirm the server owner, operating system, domain, DNS, HTTPS certificate, firewall rules, backups, and database engine.
2. Decide whether this application will keep SQLite for a single backend instance or migrate to the professor's production database. The current scheduler assumes one FastAPI process.
3. Create a dedicated production environment and a private secrets store. Never commit `.env`, API keys, access tokens, or database files.
4. Deploy the FastAPI backend and configure:
   - `OPENAI_API_KEY`
   - `APP_ACCESS_TOKEN`
   - WhatsApp access token, app secret, verify token, WABA ID, phone number ID, and Graph version
   - model and target-language settings
   - database and audio storage paths
   - production `ALLOWED_ORIGINS`
5. Put the backend behind a stable HTTPS reverse proxy. Verify:
   - `GET /health`
   - authenticated `/api/config`
   - WebSocket `/api/live`
   - upload and database persistence
6. Update Meta WhatsApp:
   - callback URL: `https://<domain>/webhooks/whatsapp`
   - verify token: the production `WHATSAPP_VERIFY_TOKEN`
   - subscribe the correct WABA to `messages`
   - send a fresh test voice message
7. Test the production database, audio retention, backups, scheduler recovery, consent checks, and webhook logs.
8. Build the iOS app with the final backend URL:

   ```bash
   cd frontend
   flutter build ipa --release \
     --dart-define=API_BASE_URL=https://<domain>
   ```

9. Upload the archive to App Store Connect/TestFlight and invite the required Apple IDs.

## iOS and backend requirements

- The release app must use HTTPS; `127.0.0.1` and temporary Quick Tunnel URLs are not production addresses.
- The backend must be reachable from an external iPhone, not only from the server itself.
- Keep WebSocket upgrade support enabled in the reverse proxy.
- If the app is distributed to multiple users, use a stable domain and production certificate.
- Keep the backend running independently of Xcode, Simulator, or the developer's laptop.

## Database and storage checklist

- Define ownership and retention for transcripts, translations, uploaded audio, and WhatsApp media.
- Configure automated backups and test restoration before real use.
- Use a persistent volume for SQLite/audio if SQLite remains in production.
- Do not run multiple FastAPI instances while using the current in-process scheduler without adding coordination.
- Restrict database and audio file permissions and monitor disk usage.
- Run the existing backend tests and QA tests before release.

## Pre-release verification

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest -q

cd ../frontend
flutter analyze
flutter test
```

Confirm these real flows with non-sensitive test data:

- Speak Live transcription and translation
- File upload and saved record
- WhatsApp webhook verification and inbound voice processing
- Scheduled message consent, template validation, send status, and restart recovery
- iOS microphone permission and TestFlight installation

## Immediate local testing before deployment

For a second iPhone on the same Wi-Fi, use the Mac's private LAN IP with a debug build. This is sufficient for local testing and does not require changing the application code. Switch to the final HTTPS URL only when the professor's server is ready.
