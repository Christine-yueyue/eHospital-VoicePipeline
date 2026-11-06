# Scheduled WhatsApp messages: Postman smoke test

The backend exposes scheduling independently from Flutter. Keep FastAPI running for the local MVP; scheduled jobs execute in the backend process.

## Configure Postman

Create an environment with:

- `base_url`: `http://127.0.0.1:8003`
- `app_access_token`: the local `APP_ACCESS_TOKEN`
- `recipient`: an existing WhatsApp contact number in international digits, without `+`
- `template_name`: a template returned by the templates request
- `template_language`: the exact language code returned by Meta
- `template_parameters`: a JSON array with exactly the values required by that template, such as `["Pat"]`; use `[]` for a template with no variables
- `schedule_id`: leave empty; the create request fills it

Set Postman's collection authorization to **Bearer Token** and use `{{app_access_token}}`. Do not put Meta's token in Postman; the backend owns it.

## Requests

All requests use `{{base_url}}` and bearer authentication.

1. `GET /api/whatsapp/schedules/templates?language={{template_language}}`
   - Returns the actual approved text templates Meta reports for that language, including each template's parameter count.
2. `GET /api/whatsapp/contacts`
   - Confirm the recipient exists and has `consent: "granted"`. The number must also satisfy `WHATSAPP_ALLOWED_SENDERS` when configured.
3. `POST /api/whatsapp/schedules`

```json
{
  "recipients": ["{{recipient}}"],
  "template_name": "{{template_name}}",
  "template_language": "{{template_language}}",
  "template_parameters": {{template_parameters}},
  "scheduled_time": "2030-01-02T10:00:00-05:00",
  "timezone": "America/Toronto"
}
```

Use a timestamp a few minutes in the future with an explicit UTC offset. A `200` response returns a `schedule_id` and `pending` status.

4. `GET /api/whatsapp/schedules`
   - Refresh while the backend remains running. At the requested time, each recipient transitions through `processing` and then to `submitted` (Meta accepted the request), `failed` (Meta rejected it), or `unknown` (the request outcome is ambiguous and requires manual checking).
   - `submitted` does not mean delivered. Delivery receipts remain available through the existing WhatsApp webhook flow only if Meta sends those receipts.

## Safety and restart behavior

Scheduling requires an existing contact with recorded permission. Check that the number is an authorized test recipient in Meta before submitting a near-term schedule. The scheduler sends to Meta automatically; use a real test contact only when you intend to send that message.

SQLite stores one row per recipient and a common `schedule_id` per batch. Pending jobs survive restart. If a process stops while a row is `processing`, startup changes it to `unknown` and does not resend it, because Meta may already have accepted the request. Review that case manually.

This MVP assumes one FastAPI process. A production multi-instance deployment needs a dedicated scheduler worker or equivalent coordination to prevent two instances from claiming the same due work.
