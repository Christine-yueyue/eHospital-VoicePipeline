# Third-party read API

The backend exposes a read-only API for approved external applications. It reads saved records from the backend's SQLite database and serves associated saved audio files. Third-party clients do not connect directly to SQLite or the server's filesystem.

## Configure access

1. Generate a new random bearer token in a secure environment, for example with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`.
2. Store it in AWS Secrets Manager or Systems Manager Parameter Store and inject it into the backend as `THIRD_PARTY_API_TOKEN`. Do not commit the value, put it in a browser/mobile app, or reuse `APP_ACCESS_TOKEN`.
3. Restart or redeploy the backend so it loads the setting. If the variable is empty, third-party API requests return `503`.
4. Give the token only to the approved server-side integration. Rotate it by updating the AWS secret and restarting/redeploying the backend. This token grants read access to all saved voice feedback records and audio; it has no write/delete permission.

All requests require HTTPS and this header:

```http
Authorization: Bearer <THIRD_PARTY_API_TOKEN>
```

The deployed API base uses the backend's existing `/voice` mount when applicable, for example `https://your-backend.example/voice/api/external/v1`. The route suffixes below are appended to that base. Confirm the actual public backend URL and reverse-proxy path for your AWS deployment.

## Endpoints

### `GET /voice-feedback`

Returns a page of saved records, newest first. Query parameters:

| Parameter | Default | Allowed values |
| --- | --- | --- |
| `limit` | `50` | 1–100 |
| `offset` | `0` | 0–1,000,000 |
| `source` | all | `upload`, `whatsapp`, `live` |
| `status` | all | `pending`, `completed`, `failed` |
| `since` | none | Timezone-aware ISO 8601 timestamp, inclusive |
| `until` | none | Timezone-aware ISO 8601 timestamp, inclusive |

Example:

```sh
curl --fail-with-body \
  -H "Authorization: Bearer $THIRD_PARTY_API_TOKEN" \
  "https://your-backend.example/voice/api/external/v1/voice-feedback?source=upload&limit=25&offset=0"
```

The response contains `records` and `pagination`. Each record includes its ID, timestamps, source, transcription status, original transcript, translation text and target language, audio metadata, and an `audio_url` relative to the API base when an audio file was saved. For example, append `voice-feedback/123/audio` to `/voice/api/external/v1/`. Live sessions have no audio file. Internal filesystem paths, WhatsApp source message IDs, and device metadata are not exposed.

Example response:

```json
{
  "records": [
    {
      "id": 123,
      "created_time": "2026-11-18T14:30:00+00:00",
      "updated_time": "2026-11-18T14:30:03+00:00",
      "source": "upload",
      "transcription_status": "completed",
      "feedback_message": "Original transcript text",
      "translation_message": "Texte traduit",
      "target_language": "fr",
      "audio_mime_type": "audio/mpeg",
      "audio_duration_seconds": null,
      "size_bytes": 45678,
      "last_error": null,
      "has_audio": true,
      "audio_url": "voice-feedback/123/audio"
    }
  ],
  "pagination": {"limit": 50, "offset": 0, "total": 1}
}
```

### `GET /voice-feedback/{id}`

Returns one record in the same shape as the list endpoint. Missing IDs return `404`.

### `GET /voice-feedback/{id}/audio`

Downloads the saved original audio for upload and WhatsApp records. Live records and records without an available file return `404`. Use the same bearer token; do not expose or cache the downloaded audio publicly.

## Status and errors

| Status | Meaning |
| --- | --- |
| `200` | Request succeeded |
| `401` | Missing or incorrect bearer token |
| `404` | Record or audio not found |
| `400` | Query schema validation error (the app's global validation handler returns 400) |
| `422` | Invalid timestamp value or reversed time range |
| `503` | `THIRD_PARTY_API_TOKEN` is not configured |

Response records may contain sensitive transcript text and audio. Apply the third party's own access controls and retention policy. For a public AWS deployment, restrict network access where practical and configure rate limiting at the load balancer, API gateway, or reverse proxy.
