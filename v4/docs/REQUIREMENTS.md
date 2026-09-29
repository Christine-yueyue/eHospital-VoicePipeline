# Software Requirements Specification — Voice Notes v4

**ID:** SRS-V4 · **Revision:** 1.0 · **Date:** September 28, 2026

**Status:** Draft for stakeholder review. This is a specification of the existing prototype plus explicitly identified acceptance work. It is not a signed project contract.

## 1. Purpose and scope

The requested v4 increment preserves v3 and implements:

`calls webhook → call_transcription_available → retrieve Meta transcript → parse → translate → iOS Inbox`.

The prototype also retains uploaded-file transcription, business voice-message intake and local microphone caption/translation modes. Calls in this document mean WhatsApp Business Cloud API calls that have transcription enabled. An external system must establish and handle the call. Meta provides a result after the call; v4 consumes that result.

### Requirement origin

- **Requested:** preserve v3 and add the post-call Meta transcript workflow, as requested in the project conversation.
- **Baseline:** existing code behavior retained or selected during implementation; confirm that it meets stakeholder needs.
- **Pending decision:** a scope, quality or resource choice without stakeholder approval. See [decision register](DECISIONS_AND_RISKS.md).

“Shall” below describes a candidate acceptance baseline. It does not convert implementation choices into approved requirements. All requirements are must-pass for the scope eventually accepted; exclusions and new requests require an agreed change.

## 2. Actors and operating assumptions

| Actor | Responsibility |
| --- | --- |
| App user | Connect to the server; upload audio/use microphone; read, retry or delete Inbox results |
| WhatsApp participant | Send a voice message or take part in an opted-in business call |
| Meta platform | Deliver signed webhooks and provide media/transcript assets |
| Translation/transcription provider | Produce audio transcripts where required and translate text |
| Project administrator / TA | Grant asset access; supply configuration and database/hosting decisions |
| Professor / product owner | Confirm scope, languages, quality measures, data handling and acceptance |
| Developer / operator | Maintain the application, deploy it and collect test evidence |

The baseline is a single-owner backend, one configured WABA and business phone number, and one shared app access token. Call handling, HTTPS hosting and valid provider access are external dependencies. Local automated tests do not depend on a real Meta account.

## 3. Functional requirements

| ID | Candidate requirement and observable acceptance condition | Origin |
| --- | --- | --- |
| FR-01 | The client shall authenticate with a separate app token and only enable connection after `/api/config` reports version `4.0.0`. Wrong credentials or incompatible versions produce a visible error. Disconnect clears session results and credentials. | Baseline |
| FR-02 | The server shall accept non-empty uploaded `.ogg`, `.opus`, `.mp3`, `.wav`, `.m4a` and `.webm` files within the configured size limit, reject invalid inputs, and return an original transcript. Temporary upload files are removed after normal success/failure handling. | Baseline |
| FR-03 | File processing shall support English/French translation when requested. If translation fails after successful transcription, the original is returned with a translation error. The same two target languages apply to Inbox translation, selected by server configuration. | Baseline |
| FR-04 | Local microphone mode shall accept authenticated 24 kHz mono PCM16 audio, display source/translation text, and drain final results on Stop. It shall surface connection/provider errors and enforce a ten-minute session limit. | Baseline |
| FR-05 | The webhook verification endpoint shall echo a valid subscription challenge only when the configured verify token matches. Invalid verification requests shall fail. | Baseline |
| FR-06 | The webhook receiver shall validate its raw-body HMAC signature, enforce a body limit, filter WABA/phone/sender identifiers, commit accepted jobs atomically before acknowledgement, and reject queue overflow without partial batch insertion. | Baseline |
| FR-07 | Valid `messages` events with `type=audio` shall produce voice-message jobs that retrieve media, transcribe it, translate it and expose the result in Inbox. Non-audio events shall not create such jobs. | Baseline |
| FR-08 | Valid `calls` events with `event=call_transcription_available` shall create one job per call. Connect/terminate/recording events shall not create transcript jobs. Phone or supported business-scoped user identifiers shall satisfy caller filtering. | Requested |
| FR-09 | A call job shall resolve its media ID to a fresh authenticated download URL, enforce the permitted media hosts/type/size, reject redirects, and verify the downloaded bytes against the signed event's SHA-256. It shall not invoke audio transcription. | Requested |
| FR-10 | The parser shall extract original text and available language, duration, confidence and speaker/time segments from Meta JSON. It shall reconstruct text from valid segments when flat text is empty; invalid, empty or oversized documents shall produce visible job failures. | Requested |
| FR-11 | Call text and speaker metadata shall be persisted before translation. Long call text shall be divided into requests of at most 6,000 characters and translated in order. A translation retry shall reuse the saved original. | Requested / baseline limits |
| FR-12 | Inbox shall distinguish calls and voice messages, display progress, original/translated text, errors, and call speaker timelines, and refresh every five seconds while its screen is active. Users shall be able to copy displayed result text and manually refresh. | Requested / baseline UI |
| FR-13 | Jobs shall survive process restarts through a durable queue and recover expired processing leases. Transient errors shall receive up to three attempts per retry cycle; failed/partial jobs shall support manual retry. Obsolete workers shall not overwrite a new lease or deleted result. | Baseline |
| FR-14 | Delete shall clear saved content and hide a result while retaining a deduplication tombstone. Results older than 24 hours since receipt shall be pruned; tombstones shall be removed after seven days since receipt. | Baseline; retention approval pending |
| FR-15 | v4 shall use a separate source directory, default database/settings, backend port and iOS Bundle ID, while preserving v3 source. A duplicate/reissued call event shall not create a second result during the deduplication window. | Requested |

## 4. Non-functional requirements and constraints

| ID | Candidate baseline | Verification / qualification |
| --- | --- | --- |
| NFR-01 | Backend provider credentials shall not be returned by config or Inbox APIs. Protected API requests require an app token; webhook requests use independent Meta authentication. Browser origins are restricted. | Automated security cases and code review; not a penetration-test certification |
| NFR-02 | The deployed client connection shall use trusted HTTPS/WSS. Debug clients may connect to localhost/private LAN addresses. Tokens should be entered at runtime and remain in client memory. | Address validation tests; real TLS/signing checks pending |
| NFR-03 | Download sizes, queue admission and processing times shall be bounded as listed below. Webhook handling shall defer media/model work to a worker. | Automated functional limits; no measured production throughput or latency SLA |
| NFR-04 | Stored content shall be limited to operationally necessary result data, masked sender identifiers and media/call references. No raw webhook archive is created. | Schema/source review; data owner approval and backup retention policy pending |
| NFR-05 | The iOS project shall compile for the simulator and key screens shall render at tested phone widths without layout exceptions. | Build and widget evidence; physical-device/UAT/accessibility assessment pending |
| NFR-06 | A release candidate shall have reproducible commands, source identification, requirement-to-test mapping, documented limitations and an operator handover. | This documentation package and verification evidence |

### Implemented limits, not performance promises

| Parameter | Current value |
| --- | --- |
| Manual upload | 20,000,000 bytes default; `MAX_UPLOAD_MB` accepts integers 1–25 |
| Webhook body | 1,000,000 bytes |
| WhatsApp audio download | 16,000,000 bytes |
| Call JSON / extracted text / segment count | 8,000,000 bytes / 100,000 characters / 5,000 segments |
| Pending queued + processing jobs | 100; completed rows do not count toward admission |
| Inbox API listing | Latest 100 non-deleted results; no pagination |
| Worker deadline | 240 seconds for voice jobs; 600 seconds for call jobs |
| Processing lease | 660 seconds |
| Retry delays | 10 × failed-attempt number seconds before the next automatic attempt |
| Live microphone | 600 seconds; non-empty even-length PCM frames up to 48,000 bytes |
| Event age | Calls require timestamp within last 24 hours and at most 300 seconds in future; audio timestamp is checked when supplied |

Five-second polling is a UI refresh interval. It does not guarantee completion within five seconds. Speech accuracy, translation quality, maximum acceptable delay, availability and scale require an agreed test set and targets (D-04, D-05).

## 5. Out of scope for the current increment

- Answering or initiating calls, call permissions orchestration, WebRTC/SIP negotiation, or an agent call console.
- Reading personal WhatsApp messages/call history automatically, or transcribing an active WhatsApp call in real time.
- Multi-user login, tenant isolation, role-based Inbox access, push notifications, export, long-term archival, or database integration with a lab system.
- A production deployment, real provider-account qualification, signed device distribution, App Store/TestFlight release, or a quality/compliance certification.

The existing microphone feature operates on this app's microphone input; it is not a substitute for WhatsApp call capture.

## 6. Acceptance and change control

Automated checks establish local implementation behavior only. Acceptance requires the selected [UAT scenarios](TEST_PLAN.md), real resources, agreed quality/latency thresholds, and professor/TA review. Preserve failing evidence and resolve or explicitly accept deviations before sign-off.

| Review item | Decision maker | Status |
| --- | --- | --- |
| Mandatory input modes; post-call vs live scope | Professor | Pending |
| Call system, business assets and database destination | TA / project administrator | Pending |
| Quality, retention, access and delivery criteria | Professor with developer/TA | Pending |
| Live demonstration and release acceptance | Professor / nominated reviewer | Not executed |

For a change, record the request, affected requirement IDs, code/data/API impact, added tests, resource cost and review outcome. Do not change the approved baseline silently.
