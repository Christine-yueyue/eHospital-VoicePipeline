# Deployment and Operations — Voice Notes v4

**Revision:** 1.0 · **Scope:** Local setup and a proposed controlled integration deployment

No production deployment is claimed. Use the [test report](TEST_REPORT.md) for the tested toolchain and [resource register](DECISIONS_AND_RISKS.md) for account/hosting ownership.

## Local setup

Install Python, FFmpeg, Flutter and Xcode with simulator support. From the repository root:

```bash
cd v4/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python ../scripts/init_env.py
uvicorn app:app --reload --host 127.0.0.1 --port 8004
```

The initializer creates `.env` only when absent, generates a new app access token and webhook verify token, and does not print secrets. Populate provider values locally. Optional `--reuse-v3-settings` reads selected v3 provider settings while still generating new app/verify tokens; it does not copy the database. Exported environment values take precedence over `.env`. Restart after changes.

In a second terminal, from the repository root:

```bash
cd v4/frontend
flutter pub get
flutter devices
flutter run -d <ios-simulator-device-id>
```

Enter simulator backend URL `http://127.0.0.1:8004` and the v4 app access token in Connection settings. For optional web development, use `flutter run -d chrome --web-port 5175`. For physical debug testing, bind the backend to a reachable interface and use the Mac's private LAN address; configure Apple signing and local network access. A release client requires trusted HTTPS.

## Configuration inventory

Use [the checked-in example](../backend/.env.example), never commit the populated `.env`.

| Variable | Purpose / owner |
| --- | --- |
| `APP_ACCESS_TOKEN` | Separate locally generated app-to-backend secret; entered by authorized app user |
| `OPENAI_API_KEY` | Project provider access for voice/upload ASR, translation and live modes; project billing owner |
| `WHATSAPP_ACCESS_TOKEN` | Approved Meta access token authorized for the configured business assets; administrator |
| `WHATSAPP_APP_SECRET` | Owning Meta app secret used to verify delivery signatures; administrator |
| `WHATSAPP_VERIFY_TOKEN` | Locally chosen challenge token, also entered in Meta webhook setup; developer/admin |
| `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_WABA_ID` | Exact business phone and WABA IDs; administrator |
| `WHATSAPP_GRAPH_VERSION` | Supported `vN.N` version from the actual integration environment; administrator/developer |
| `WHATSAPP_TARGET_LANGUAGE` | `fr` default or `en`; affects newly enqueued jobs |
| `WHATSAPP_ALLOWED_SENDERS` | Optional comma-separated allowed phone numbers or supported call BSUIDs; empty permits any otherwise-valid sender |
| `INBOX_DB_PATH` | Optional absolute SQLite file path; default `backend/data/inbox.sqlite3` |
| `ALLOWED_ORIGINS` | Exact permitted browser origins; set to the intended web client origins |
| `MAX_UPLOAD_MB` | Integer 1–25; default 20 decimal MB |
| `TRANSCRIPTION_MODEL` | Uploaded/voice audio model; example `gpt-4o-mini-transcribe` |
| `TRANSLATION_MODEL` | Text translation model; example `gpt-4.1-mini` |
| `REALTIME_TRANSLATION_MODEL` | Live translation model; example `gpt-realtime-translate` |
| `REALTIME_TRANSCRIPTION_SESSION_MODEL` | Companion live source-caption session model; example `gpt-realtime` |
| `REALTIME_TRANSCRIPTION_MODEL` | Source-caption transcription model; example `gpt-live-transcribe` |

Model values describe the current configuration, not independently verified availability for the project's account. Meta calls use Meta's existing transcript and only require the text translation provider path inside v4. Live microphone access is a separate capability to test if retained in scope.

The verify token, app access token, Meta access token and Meta app secret serve different purposes and are not interchangeable. Do not embed provider credentials in Flutter builds. Prefer runtime entry for the app token over compiled defaults in distributed clients.

## Controlled integration deployment

1. Resolve the hosting/database/access decisions and create an isolated v4 environment with persistent storage. Retain a source revision, validated dependency versions and prior evidence.
2. Install dependencies and run the regression runner. Start one backend process under a service manager, without `--reload`; for a same-host reverse proxy, use `uvicorn app:app --host 127.0.0.1 --port 8004 --workers 1`.
3. Terminate trusted HTTPS at the proxy, enable WebSocket upgrades, set request limits/timeouts compatible with supported uploads/live sessions, and restrict diagnostic/docs routes as required. Restrict filesystem permissions on secrets and SQLite storage. The current application has no built-in deployment template or production monitoring stack.
4. Check `/health`, then authenticated `/api/config`. Inspect missing/invalid settings. Neither check proves provider authorization; execute an approved provider test.
5. Configure `https://<backend-host>/webhooks/whatsapp` with the v4 verify token. Subscribe `calls` and, if required, `messages`; ensure the appropriate app/business subscriptions and asset permissions are active.
6. In the existing call system, enable transcription in connect/accept requests with the agreed purpose/announcement settings. v4 itself does not establish or accept calls. Confirm current Meta eligibility with the account owner.
7. Execute the agreed [UAT cases](TEST_PLAN.md), record redacted evidence and obtain review before broader use.

v3 uses backend port 8003, web port 5174 and its own database/settings; v4 uses 8004/5175 and Bundle ID `com.christine.voiceNotesV4`. Local separation does not isolate a shared Meta callback. Coordinate changes so v3 events are not unexpectedly redirected.

## Monitoring and troubleshooting

Monitor process liveness, disk space, database access, queued/processing age, terminal failures, provider errors and end-to-visible delay. Avoid logging raw transcripts, authorization headers, signed webhook bodies or downloadable media URLs. There is no built-in metrics endpoint or notification service; assign an operational owner/tooling before relying on unattended delivery.

| Symptom | Check / action |
| --- | --- |
| Connection 401 | Confirm the app uses v4's app token, not a provider or verify token |
| Config/API 503 | Check required app configuration; webhook/retry also needs all Meta settings |
| Verification 403 | Check callback, subscribe mode and exact verify token |
| Delivery 403 | Check owning app secret and raw-body signature; do not bypass verification |
| Webhook 200, `queued: 0` | Check field/event, tenant/phone IDs, allowlist, timestamp and prior deduplication ID |
| Queue 503 | Inspect backlog and worker health; the webhook batch was not partly committed |
| Call stuck processing | Check worker/service logs and provider reachability; a recovered job waits for lease expiry |
| Original visible, translation failed | Check translation provider access/billing; Retry reuses saved original |
| Media/hash/type error | Confirm actual event/document contract and asset access; preserve redacted failure evidence |
| Result disappears | Check deletion and 24-hour receipt-based retention; only latest 100 visible rows are listed |
| Phone cannot connect | Check LAN/TLS, server binding, firewall, app version and signing/network permissions |

Do not repeatedly retry permanent account/configuration errors without fixing their cause. Automatic transient retries are capped at three attempts per cycle; manual retry starts another cycle and may incur provider cost.

## Recovery, retention and rollback

The SQLite file must persist across process restarts. Use a consistent SQLite backup method or stop the single writer for a controlled copy; copying a live file without consistency guarantees is not a recovery plan. Since results are intentionally short-lived, obtain an explicit decision on whether backups are needed and how quickly they expire. Backups and filesystem snapshots are outside application pruning.

Test restoration in an isolated environment before connecting a restored copy to webhooks. Old backups can restore previously deleted content and lose recent deduplication IDs. Apply the agreed retention/deletion policy and reconcile the recovery window before enabling processing. The current app has no backup scheduler or restore reconciler.

To roll back a v4 release, stop its service, preserve only policy-permitted diagnostic evidence, restore the prior compatible v4 source/configuration and approved database snapshot, then run smoke tests. If returning traffic to v3, explicitly coordinate callback routing and use the separate v3 app/backend. Do not feed v4's database to v3 or assume v3 supports call transcripts.

Rotate backend credentials through the owner's secure process, update server configuration and restart. Rotating `APP_ACCESS_TOKEN` requires users to reconnect with the new token. Coordinate verify-token changes with the Meta form and app-secret/access-token changes with the owning administrator. Keep secrets out of tickets and reports.

Handover requires a named service owner, credential owner, database owner, approved retention/backup procedure, observed UAT results and the exact release revision. These assignments remain pending.
