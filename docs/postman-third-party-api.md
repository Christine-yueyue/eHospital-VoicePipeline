# Third-party read API: Postman test collection

Import [`postman-third-party-api.collection.json`](postman-third-party-api.collection.json) into Postman. The collection contains read-path, filter, pagination, audio, validation, authentication-separation, and read-only-boundary checks for the third-party voice-feedback API.

## Configure Postman

Create or select an environment and set:

- `base_url`: backend origin and mount prefix, without a trailing slash. For local use: `http://127.0.0.1:8003`. For the deployed backend, use its HTTPS mount, for example `https://your-backend.example/voice`.
- `third_party_api_token`: the same secret configured as `THIRD_PARTY_API_TOKEN` in the backend runtime. Keep it in a Postman secret variable and do not export/share it in a collection.
- `app_access_token`: the local or deployed app token, used only by the negative test that proves it cannot authenticate to the third-party API. Store it as a secret.

Collection authorization uses **Bearer Token** with `{{third_party_api_token}}`. The requests that test missing or wrong tokens override collection authorization. No database credentials are used.

## Recommended run order

Run requests 1–8 in order. Request 1 stores the first returned record ID in `record_id` and the first audio-bearing record ID in `audio_record_id`. Request 7 expects the database to contain at least one record; request 8 expects at least one record with saved audio. If no saved data exists yet, create an upload with **Save to Database** enabled and run request 1 again. Live records do not have audio.

Requests 9–20 are negative and boundary checks. The API intentionally returns `400` for query schema validation errors because the app has a custom validation handler; explicit timestamp validation raises `422`. A missing/incorrect token returns `401` when `THIRD_PARTY_API_TOKEN` is configured. If it is absent, the backend returns `503` before checking the request token. Request 21 verifies that configuration failure only; run it only on an isolated staging instance while the backend token is deliberately unset, never by changing production configuration just for this test.

## Cases covered

1. List records and capture IDs for follow-up requests.
2. Pagination limit.
3. Filter by source.
4. Filter by transcription status.
5. Combine source and status filters.
6. Filter by a generated UTC timestamp range.
7. Read a specific record.
8. Download its saved audio.
9–10. Unknown record and audio IDs return `404`.
11–14. Missing token, invalid token, and app/third-party token separation.
15–18. Invalid source, out-of-range page size, timezone-less time, and reversed time range.
19. `POST` to the read-only endpoint is rejected with `405`.
20. Arbitrary SQL endpoint is absent (`404`); the request uses the third-party token so authentication succeeds before the route lookup.
21. Missing backend token configuration returns `503` (isolated staging only).

There is no automated API run result in this file. The collection must be run against a configured local or AWS backend to confirm the runtime token, public route, database contents, and audio persistence.
