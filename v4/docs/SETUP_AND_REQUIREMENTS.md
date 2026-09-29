# Voice Notes v4: settings, ownership and requirements to confirm

Prepared September 27, 2026. This is a proposed scope and resource checklist for discussion; it does not claim that the professor has approved these requirements. The implementation status comes from the current v4 repository and its local validation.

## What is implemented

v3 is preserved. v4 has a separate source directory, backend configuration, SQLite database path, app access token, port 8004 and iOS Bundle ID `com.christine.voiceNotesV4`.

| Input | Current processing | Where the user sees the result |
| --- | --- | --- |
| Uploaded audio file | OpenAI transcription → optional English/French translation | Upload screen |
| WhatsApp voice message sent to the configured business number | `messages` webhook → download audio → OpenAI transcription → translation | iOS Inbox |
| Opted-in WhatsApp Business Cloud API call | `calls` / `call_transcription_available` → download Meta transcript JSON → parse → OpenAI text translation | iOS Inbox with speaker timeline |
| App microphone | Existing live microphone transcription/translation mode | Live screen; this does not capture WhatsApp call audio |

The call path preserves Meta’s transcript and speaker segments; it does not retranscribe call audio with OpenAI. Authentication, webhook signatures, business-asset filtering, a durable queue, duplicate handling, retries, result deletion and 24-hour retention are implemented. Inbox refresh is every five seconds while open. The prototype has a single-owner app token, not multi-user accounts or per-user Inbox isolation.

Local verification passed: 97 backend tests, 9 Flutter tests, Flutter analysis and an iOS Simulator build. The Meta and translation integrations in automated tests use simulated provider responses. Real external delivery, account eligibility, API billing/model access, physical-device signing and TestFlight distribution remain to be verified.

The code receives post-call results. It does not answer/place calls, implement WebRTC/SIP call handling, read personal WhatsApp call history, or provide live subtitles for a WhatsApp call.

## Settings and their owners

All secret values belong in `v4/backend/.env`, not in the iOS app. The app needs only the backend URL and its separate `APP_ACCESS_TOKEN`. The settings template is `v4/backend/.env.example`.

| Setting/resource | Upload | WhatsApp voice messages | Meta call transcripts | Where it comes from / proposed owner |
| --- | --- | --- | --- | --- |
| `OPENAI_API_KEY` | Required for transcription/translation | Required | Required for translation only | Project OpenAI API account; professor/lab confirms account ownership and budget, developer configures it |
| `TRANSCRIPTION_MODEL` | Used | Used | Not used | Current project default: `gpt-4o-mini-transcribe`; verify access on the selected API project |
| `TRANSLATION_MODEL` | Used when translation is requested | Used | Used | Current project default: `gpt-4.1-mini`; verify access on the selected API project |
| `APP_ACCESS_TOKEN` | Required | Required for Inbox | Required for Inbox | Generated locally; a separate v4 value already exists |
| `WHATSAPP_ACCESS_TOKEN` | Not needed | Required | Required | Token for the project’s Meta app/business assets; obtain via the authorized project admin |
| `WHATSAPP_APP_SECRET` | Not needed | Required for webhook signature checks | Required for webhook signature checks | Meta app settings, supplied/configured by an authorized app admin |
| `WHATSAPP_PHONE_NUMBER_ID` | Not needed | Required | Required | Meta API Setup; this is an asset ID, not the phone number itself |
| `WHATSAPP_WABA_ID` | Not needed | Required | Required | WhatsApp Business/Messaging account ID in Meta API Setup; not the Meta app ID |
| `WHATSAPP_GRAPH_VERSION` | Not needed | Required | Required | Supported version for the chosen app/API; copy from its setup rather than assuming the test version |
| `WHATSAPP_VERIFY_TOKEN` | Not needed | Required | Required | Locally generated string entered both in backend settings and Meta’s webhook setup; a v4 value already exists |
| `WHATSAPP_TARGET_LANGUAGE` | Upload UI chooses target | `en` or `fr` | `en` or `fr` | Professor confirms language requirements; developer configures it |
| `WHATSAPP_ALLOWED_SENDERS` | Not needed | Optional restriction | Optional restriction | Agreed test participants; digits-only phone numbers, or supported call business-scoped user IDs |
| Public HTTPS callback | Not needed for local upload testing | Required | Required | Project hosting or an approved development tunnel; developer configures `/webhooks/whatsapp` |
| Meta webhook field | None | `messages` | `calls` | Developer/admin subscribes the app and connects it to the correct WABA |
| Calling enablement and an operational call-handling system | Not needed | Not needed | Required to produce the event | Existing lab/partner integration, or an additional development deliverable |

`ALLOWED_ORIGINS` concerns browser clients. `INBOX_DB_PATH` is optional; keep the default v4 database separate from v3. `MAX_UPLOAD_MB` defaults to 20 for manual uploads. The `REALTIME_*` settings are for the app microphone mode and are not prerequisites for post-call transcript retrieval.

At the time of this review, the v4 configuration contains an OpenAI key entry, app token and webhook verification token. This does not establish that the OpenAI key is active. The Meta access token, app secret, phone-number ID, WABA ID and Graph version are missing.

OpenAI requires an API key and access to the selected project/models. Agree who owns the project and pays for API usage; use backend environment variables for credentials. See [OpenAI quickstart](https://developers.openai.com/api/docs/quickstart) and [production/account setup](https://developers.openai.com/api/docs/guides/production-best-practices).

## Developer accounts versus project resources

**The developer can arrange:** a personal Facebook or managed Meta identity and Meta developer registration, development tooling, configuration work, local testing, and a WhatsApp-enabled test device. Registration provides the developer identity used to create a test app or receive access to an existing project. It does not automatically grant access to the lab’s business assets. Meta’s [Get Started guide](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started/) describes registration, the WhatsApp use case, business portfolio/account setup, test numbers and tokens.

**The professor/lab should confirm or arrange:** the required workflows, ownership of the Meta app/business portfolio/WABA/number, someone authorized to grant access or configure credentials, any production business details/verification, an existing call-handling integration or scope/budget to build one, OpenAI/hosting budgets, test participants and samples, and the required delivery format. This is a proposed division of responsibilities, not a claim that the professor must personally hold every account. If the lab has no resources, agree on ownership and costs before creating project assets under a personal account.

**For Apple:** no paid program membership is needed just to use the simulator. A personal Apple account can support limited on-device Xcode testing. TestFlight/App Store distribution needs suitable Apple Developer Program access; the lab can invite the developer to its team. See [Apple’s account and membership guide](https://developer.apple.com/help/account/basics/about-your-developer-account).

**For OpenAI:** the developer can create an account or join a project-owned organization. A separate personally funded API project is not required if the lab supplies an authorized project. Confirm who is responsible for billing and model access.

## Setup sequence

1. Confirm whether “normal transcription” means manual file upload, automatic WhatsApp voice-message intake, or both. Confirm whether “calls” means a post-call transcript or real-time call captions. Choose inbound/outbound scope and a test business number.
2. If testing uploads only, configure OpenAI and the app token, start the backend, connect the iOS app and upload a short sample. Meta registration is not needed for this path. OGG/Opus decoding uses FFmpeg in the existing backend.
3. For WhatsApp intake, register as a Meta developer or accept project access. Use the lab’s app/account where available. Otherwise create an agreed test app with the WhatsApp use case and follow Meta’s API Setup. A public test number is available through the Get Started flow. Add/verify the test participant number as required by that flow.
4. Obtain the WABA ID, phone-number ID, app secret, supported Graph version and a token for the correct assets. Temporary dashboard tokens are useful for initial tests; arrange a suitable system-user token for ongoing operation. The Meta setup guide lists `business_management`, `whatsapp_business_messaging` and `whatsapp_business_management` for its system-user setup. Runtime media/calling access and administrative asset/settings operations use different permissions; confirm the required permissions and asset assignments for the selected integration. See [Meta Get Started](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started/).
5. Run v4 on port 8004. Configure a public HTTPS callback ending in `/webhooks/whatsapp`, enter the same v4 verify token on both sides, and subscribe `messages`. Ensure the app is subscribed to the correct WABA, not just to a webhook field. Send one real voice message to the business number and verify the resulting original text and translation in Inbox.
6. For calls, check the number’s Calling eligibility and enable Calling in its settings. Subscribe `calls` in addition to `messages`. These are Meta account settings; adding an invented `CALLING_ENABLED` variable to `.env` will not enable Calling.
7. In the system that actually initiates or accepts the call, enable transcription for that call. The configuration below is a fragment of its existing `connect` or `accept` request, not a standalone request. The chosen purpose and announcement language need to match the test scenario.

```json
{
  "transcription": {
    "status": "ENABLED",
    "purpose": "translation and follow-up notes",
    "announcement_language": "en_US"
  }
}
```

Meta handles the announcement before transcription. The announcement language is distinct from the detected speech language and from v4’s translation target. Enabling call recording alone does not enable transcription. See [Meta Call transcription](https://developers.facebook.com/documentation/business-messaging/whatsapp/calling/call-transcription/).

8. Complete an opted-in call using the operational call system. Confirm that Meta delivers `call_transcription_available`, the backend fetches and parses the transcript, and one result appears in the authenticated Inbox. If SIP is used, confirm that the partner’s setup delivers the transcript event required by this workflow; do not assume it behaves like the Graph/webhook path.

The number-level Calling setting can be inspected with `GET /<PHONE_NUMBER_ID>/settings` and configured with `POST /<PHONE_NUMBER_ID>/settings`, using `{"calling":{"status":"ENABLED"}}` for enablement. WhatsApp Manager also exposes phone-number Calling controls. The settings reference documents `whatsapp_business_management` and Advanced Access when serving end-business clients. See [Configure Call Settings](https://developers.facebook.com/documentation/business-messaging/whatsapp/calling/call-settings/).

## Calling eligibility to check before choosing the demo

Meta’s current overview requires Cloud API business-number setup, the correct app/WABA subscription and messaging permission, Calling enablement, and a daily messaging limit of at least 2,000 unique recipients for standard production eligibility. Its public test numbers and eligible sandbox accounts have an exception to the messaging-limit requirement; Calling still needs to be enabled on a test number. The dedicated sandbox-account option is limited to Tech Partners. Test-number access should therefore not be described as proof of production eligibility.

Meta currently lists Canada and the United States among the countries excluded for **business-initiated calling**, based on the business number’s country. User-initiated calling follows a different availability rule. If the project plans to use a Canadian business number, explicitly confirm the intended call direction and account/test-number eligibility before promising outbound calling. See [Calling overview: prerequisites, testing and availability](https://developers.facebook.com/documentation/business-messaging/whatsapp/calling/).

## Requirements and acceptance criteria to agree

These are proposals for professor review, not validated user requirements:

| Decision | Current prototype | Confirmation needed |
| --- | --- | --- |
| Input scope | Uploads, business voice messages and post-call transcripts | Which are mandatory for the next milestone? |
| Call timing | After-call retrieval | Is in-call transcription/translation required? |
| Call handling | Supplied by an external integration | Does the lab have one, or must it be developed? |
| Account and call direction | Configurable business assets | Which number/country; inbound, outbound or both? |
| Languages | English/French translation targets | Which speech languages, accents and output languages must be evaluated? |
| Storage | 24-hour result retention, deletion, seven-day ID tombstones | Is this retention suitable? Is export/longer storage needed? |
| Access model | Single-owner token and shared Inbox | Is multi-user authentication/isolation required? |
| Delivery | Simulator build; foreground polling | Physical iPhone, TestFlight, background updates or push notifications? |
| Quality and speed | No agreed quality or latency threshold yet | Which samples, transcript/translation accuracy measures and timing targets? |

Suggested acceptance demonstration:

- Upload one agreed audio sample and review its transcript and translation against a reference.
- Send a real voice message to the configured business number and verify it reaches Inbox exactly once.
- Complete one opted-in business call, verify delivery of Meta’s transcript event, and review original text, speaker timeline and translated output.
- Measure latency separately from call end to Meta’s event and from event receipt to Inbox completion. The five-second Inbox refresh interval is not an end-to-end processing guarantee.
- Replay an event and confirm no duplicate result; exercise a translation failure/retry; confirm unauthorized Inbox access is rejected and deletion clears saved content.
- Agree the permitted latency, acceptable transcription/translation quality, sample set, and required device before declaring the requirement met.

A discussion email is provided separately in `PROFESSOR_UPDATE_DRAFT.md`.
