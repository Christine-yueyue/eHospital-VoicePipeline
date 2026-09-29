# Decisions, Resources and Risks — Voice Notes v4

**Revision:** 1.0 · **Status:** Open items for professor/TA review

Roles below are proposed owners, not evidence that anyone has accepted responsibility. No live acceptance or production approval has been recorded.

## Decision register

| ID | Decision required | Current prototype assumption | Proposed decision owner | Status |
| --- | --- | --- | --- | --- |
| D-01 | Which input modes are mandatory? Is post-call delivery sufficient? | Meta post-call transcripts plus inherited upload, voice message and microphone modes | Professor | Pending |
| D-02 | Who owns the Meta app, WABA, number and existing call system? | An external system connects/accepts calls and enables transcription | TA / Meta administrator | Pending |
| D-03 | Existing database/table or a new table? | Separate local SQLite `messages` table | TA / database owner | Pending |
| D-04 | Required languages and acceptable transcript/translation quality? | English/French translation; no approved accuracy target or evaluation set | Professor | Pending |
| D-05 | Acceptable post-call delay, concurrent users and call volume? | One worker, bounded queue, five-second foreground polling; no SLA | Professor / operator | Pending |
| D-06 | Retention, deletion, participant notice and use of external providers? | 24-hour results and seven-day receipt-based tombstones | Professor / data owner | Pending |
| D-07 | Who may view results? Is a shared token sufficient? | Single-owner Inbox with one shared token | Professor / administrator | Pending |
| D-08 | Hosting, domain, TLS, operational owner and budget? | Local prototype; public HTTPS needed for Meta | TA / operator | Pending |
| D-09 | Delivery target and Apple signing ownership? | Simulator debug build; physical device and distribution unverified | Professor / developer | Pending |
| D-10 | What constitutes final acceptance and who signs it? | Local tests passed; live UAT required | Professor | Pending |

Record each resolution with its date, reviewer, agreed value, affected requirement IDs, evidence and follow-up owner. Preserve unresolved items rather than silently treating defaults as approved requirements.

## Resource and account responsibilities

| Resource | Professor / TA / administrator supplies | Developer / student action |
| --- | --- | --- |
| Meta app access | Invite the student's actual Facebook account to an appropriate app role; grant required business-asset access separately | Complete Meta developer registration if required, accept invitation, verify the app is visible and permitted assets are accessible |
| Existing Meta app | App ID, owner/contact, relevant role and configuration access | Use the existing app after invitation; no separate app is inherently required |
| WABA and business number | WABA ID, phone-number ID, eligibility and Calling API availability | Configure exact IDs and run authorized test scenarios |
| Provider credentials | Approved access token/access procedure, app secret, supported Graph version; project OpenAI account/key and billing owner | Store backend-only secrets securely; verify granted access using the test plan |
| Webhook | Approval for the callback/subscription change; app/business subscription access | Supply deployed HTTPS callback and locally generated verify token; test challenge and signed delivery |
| Call transcription | Access to the system that sends connect/accept requests; eligible test participants | Enable transcription in that system with its owner and verify a real available event |
| Database | Engine, schema/table decision, roles and retention/backup policy | Map schema, implement an adapter/migration if required and test it |
| Hosting | Approved environment, domain, TLS and operational budget | Deploy backend, restrict access and collect readiness evidence |
| iOS | Test device and signing/distribution decision | Configure signing, test on the device and record UAT |
| Evaluation | Approved representative audio/calls, expected meaning and quality thresholds | Execute bilingual review, record timings and discrepancies |

Seeing developers.facebook.com or having no apps listed does not alone prove registration completion. Verify the account can access the developer dashboard and accept the app invitation; the owner should confirm the accepted role. Share the account identifier/email requested by the administrator through the agreed channel, never a password or personal access token. An app role and business-asset permission are separate checks. Exact dashboard labels and eligibility must be checked in the actual account.

There is no separate developer account for “call keys” versus “voice-message keys.” Event payloads distinguish the two. A personal Meta developer identity does not by itself provide a business phone number, production permissions, transcription eligibility or access to another person's assets. Likewise, a Meta account does not provide Apple signing or OpenAI billing access.

## Risk register

| ID | Risk / practical effect | Current mitigation or next action |
| --- | --- | --- |
| R-01 | No real provider integration evidence; actual account payload/access may differ | Obtain D-02 resources and execute UAT-02/03; retain redacted evidence |
| R-02 | Changing a shared app callback can divert v3 events | Agree subscription ownership; use an isolated test app or planned routing |
| R-03 | One shared token exposes all results to every token holder | Keep prototype access limited; decide D-07 before broader use |
| R-04 | One worker can delay following jobs behind a long call | Measure D-05 workload; do not claim multiworker or load qualification |
| R-05 | Provider outages/limits or repeat chunk translation increase delays/cost | Bounded attempts and queue; monitor failures and agree budget |
| R-06 | Local retention does not erase backups; tombstones retain identifiers | Agree D-06, minimize backups and review restoration procedures |
| R-07 | Old events can be ignored; listing has no pagination | Deliver promptly, keep clocks correct, agree maximum volume and recovery needs |
| R-08 | Speech/translation can misinterpret names, numbers or meaning | Approved bilingual evaluation set and human review before relying on results |
| R-09 | Simulator/widget success does not qualify microphones, devices, accessibility or distribution | Execute physical-device UAT and signing checks |
| R-10 | Dependencies/source are not an immutable release | Record environment and hashes; pin validated dependencies and create a reviewed release revision before deployment |
| R-11 | Audio-event BSUID-only senders are not supported by the current voice parser | Confirm expected voice payloads; add support/tests if needed |
| R-12 | Cleanup is delayed while server is stopped; a crash can leave temporary files | Restricted storage, scheduled operational checks, approved cleanup/backup policy |

## Ready-to-send requirement confirmation draft

> v4 now implements a separate post-call workflow: it receives a signed `call_transcription_available` event, retrieves and validates Meta's transcript JSON, parses the original text and speaker segments, translates the text, and displays the result in the iOS Inbox. The local automated tests and simulator build pass. Real Meta delivery and physical-device acceptance have not yet been verified.
>
> Could we confirm the required input modes, whether post-call results meet the project objective, the target languages, quality and latency criteria, retention/access rules, and final delivery platform? We also need access to the existing Meta app and business assets, the call system that enables transcription, a public HTTPS environment, provider credentials through a secure channel, and the database/table decision. Please confirm who will provide each resource and who will approve the live acceptance results.

This is a draft for the user to review/send; no message has been sent externally.
