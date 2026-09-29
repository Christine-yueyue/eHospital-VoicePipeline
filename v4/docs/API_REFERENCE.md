# API Reference — Voice Notes v4

**Revision:** 1.0 · **Software:** 4.0.0 · **Status:** Implemented prototype contract

This reference describes the code in [app.py](../backend/app.py), [whatsapp.py](../backend/whatsapp.py), [call_transcripts.py](../backend/call_transcripts.py) and [live.py](../backend/live.py). Examples are synthetic. Provider payload compatibility still requires a real-account integration test.

## Authentication and conventions

Use a trusted HTTPS base URL in deployment; local simulator development uses `http://127.0.0.1:8004`. HTTP paths beginning `/api/` require `Authorization: Bearer <APP_ACCESS_TOKEN>` except OPTIONS. A missing server app token produces 503; a wrong/missing client token produces 401. Meta webhook authentication is independent of this token. Never send a Meta/OpenAI token to the client.

Handled HTTP errors have the form `{"success":false,"error":"Readable message"}`. Request-validation errors are mapped to HTTP 400. Unhandled infrastructure errors are not guaranteed to use this envelope. Protected normal responses use `Cache-Control: no-store`; early authentication failures return before this header is added. Browser origins must match `ALLOWED_ORIGINS`.

## Endpoint inventory

| Method/path | Authentication | Request | Successful response |
| --- | --- | --- | --- |
| GET `/health` | Public | None | `{"status":"ok","version":"4.0.0"}` |
| GET `/api/config` | App bearer | None | Limits, languages, version and WhatsApp configuration status |
| POST `/api/transcribe` | App bearer | Multipart `file`, optional `target_language` | Original transcript and optional translation |
| GET `/webhooks/whatsapp` | Verify token query | Meta subscription challenge | Plain-text challenge |
| POST `/webhooks/whatsapp` | Raw-body HMAC | Meta JSON event | `{"received":true,"queued":1}` |
| GET `/api/whatsapp/messages` | App bearer | None | `{"messages":[...],"whatsapp":{...}}` |
| POST `/api/whatsapp/retry` | App bearer | `{"id":"call:wacid.example"}` | `{"success":true}` |
| POST `/api/whatsapp/delete` | App bearer | Same ID object | `{"success":true}` |
| WS `/api/live?target_language=fr` | Bearer header or first auth frame | PCM stream and Stop frame | Ready, text events, Done or Error |

FastAPI also exposes `/docs`, `/redoc` and `/openapi.json` without app authentication. Restrict them at the deployment boundary if required. `/health` is liveness only: it does not contact either provider or prove that credentials work.

## Configuration and uploaded files

`/api/config` returns `version`, `max_upload_bytes`, `allowed_extensions`, `languages` (`en`, `fr`), `live_sample_rate` (24000), and `whatsapp`. The latter contains `configured`, `missing`, `invalid`, `target_language`, `retention_hours` and `supported_events`. Configuration readiness means local presence/syntax checks only. Secret values are not returned.

Uploads accept `.ogg`, `.opus`, `.mp3`, `.wav`, `.m4a`, `.webm`. Omit `target_language` or use an empty string for transcription only; use `en` or `fr` for translation. The default cap is 20 MB in decimal bytes. Files are processed synchronously and do not create Inbox rows.

```json
{
  "success": true,
  "filename": "sample.wav",
  "transcript": "Please call tomorrow.",
  "translation": "Veuillez appeler demain.",
  "target_language": "fr"
}
```

When transcription succeeds but translation fails, the response remains HTTP 200 with `success: true`, the original transcript and a `translation_error` field. Missing/invalid files or language produce 400; excessive size produces 413. Provider failures can produce 429, 503 or other handled 5xx responses. Temporary files are removed by normal success/failure cleanup.

## Meta subscription and event handling

Verification requires query parameters `hub.mode=subscribe`, `hub.verify_token` matching the backend secret, and a non-empty `hub.challenge` of at most 256 characters. Token/mode failures produce 403; an invalid challenge produces 400. This request does not use the app bearer token.

Delivery requires `X-Hub-Signature-256: sha256=<hex digest>`, calculated with the Meta app secret over the exact raw request bytes. Reformatting JSON changes the signature. The receiver enforces a 1,000,000-byte limit, rejects invalid signatures before parsing JSON, and checks configured WABA, phone number and optional sender allowlist.

| Discriminator | Voice message | Call transcript |
| --- | --- | --- |
| `changes[].field` | `messages` | `calls` |
| Nested event | `value.messages[]` with `type=audio` | `value.calls[]` with `event=call_transcription_available` |
| Media reference | `audio.id` | `call_transcript.document.id` |
| Processing | Download audio → audio transcription → text translation | Download JSON → parse existing text → text translation |
| Internal ID | Message ID | `call:` followed by call ID |

An API key does not identify the event type. The signed payload's field and event/type do. One Meta access token may authorize both paths, subject to the account's asset access and capabilities.

Call acceptance requires a valid `wacid.` call ID, numeric document media ID, `application/json` MIME type and a valid base64 SHA-256 digest. It also requires a timestamp within 24 hours, allowing at most 300 seconds of future clock skew. Supported call sender fields include phone number, `from_user_id` and `from_parent_user_id`; the audio-event parser currently expects a phone-number sender. See the [test fixtures](../backend/tests/test_calls.py) for exact synthetic event construction rather than posting a stale sample event.

Accepted jobs are committed before the 200 response. `queued` counts new jobs, not successful translations. Valid but irrelevant/duplicate events return 200 with zero queued jobs. Invalid signature: 403; oversized body: 413; malformed JSON: 400; missing configuration or full queue: 503. Queue overflow rolls back the whole batch. A 200 acknowledgement does not imply downstream success; inspect Inbox.

## Transcript and Inbox data

The parser consumes a JSON document with a `transcript` object containing `text`, optional `language`, `duration`, `confidence`, and `segments`. Flat text takes precedence; valid segment text is used as fallback. Segments are normalized to `speaker`, `start`, `end`, `text`; unsupported word-level metadata is discarded. The parser enforces finite non-negative times and end ≥ start. See [limits](REQUIREMENTS.md).

The Inbox returns the newest 100 non-deleted rows, with no pagination. Each item contains:

`id`, `sender` (masked), `target`, `created` (Unix seconds), `status`, `transcript`, `translation`, `error`, `kind`, `call_id`, `event_at`, `details`, `stage`.

`kind` is `voice_message` or `call_transcript`. Status is `queued`, `processing`, `completed`, `partial`, or `failed` in visible results. Call stages include `fetching_transcript`, `parsing_transcript`, `translating`; an empty stage is normal outside processing. Details contain parsed call metadata/segments when available. Clients must tolerate absent optional metadata and empty text while processing.

Retry accepts IDs of 1–512 characters, requires valid WhatsApp configuration, and only changes failed/partial rows; otherwise it returns 409. It resets the attempt count and retains saved original text/details. Delete clears content and hides a matching row; an unknown ID also returns success. Always submit the complete returned `id`, including a call's `call:` prefix.

## Live microphone WebSocket

Native clients may use an Authorization header. Browser clients send `{"type":"auth","token":"<APP_ACCESS_TOKEN>"}` as the first frame within ten seconds. Do not put credentials in the URL. An unacceptable Origin or failed authentication closes with code 1008. Target language is `en` or `fr`, default `fr`.

After `{"type":"ready","sample_rate":24000}`, send binary mono PCM16 audio at 24 kHz. Frames must be non-empty, even-length and no larger than 48,000 bytes. Send `{"type":"stop"}` to finish. The relay drains final output for up to 30 seconds and limits the session to 600 seconds.

| Server event | Payload |
| --- | --- |
| `ready` | `sample_rate` |
| `source.delta` | `delta` |
| `source.final` | `transcript` |
| `translation.delta` | `delta` |
| `done` | Completion signal |
| `error` | Sanitized `message` |

This mode uses the app microphone and two provider sessions. It does not capture a WhatsApp call or persist an Inbox entry.
