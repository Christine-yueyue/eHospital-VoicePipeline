Subject: Voice Notes v4 — requirements confirmation and resources for live testing

Dear Professor [Name],

I have preserved v3 and implemented a separate v4 prototype. Before moving on to live integration, I would like to confirm that the current scope matches the project requirements.

The application supports audio-file transcription and translation, and receiving WhatsApp voice messages through the business messaging API. v4 also implements the following call workflow:

calls webhook → call_transcription_available → retrieve Meta’s transcript → parse the text and speaker segments → translate → display in the iOS Inbox.

The Inbox displays the original transcript, translation, processing status and, for calls, a speaker timeline. The backend includes authentication, webhook signature verification, duplicate-event handling, persistent processing, retries and 24-hour result retention. English and French are the current translation targets.

The local checks passed: 97 backend tests, 9 Flutter tests, static analysis and an iOS Simulator build. The external-provider tests use simulated responses. Live Meta delivery, real call transcription and the complete live translation workflow have not yet been verified in v4.

Could you please confirm the following requirements?

1. Does “voice transcription” include uploaded recordings, WhatsApp voice messages, WhatsApp Business calls, or all three?
2. For calls, is the requirement to display a transcript after the call ends, or to provide transcription and translation during the call? v4 currently implements the post-call workflow.
3. Will the project provide an existing system that answers or initiates WhatsApp Business calls, or should building that system be part of my scope? v4 currently starts at webhook reception and does not answer or place calls.
4. Are we targeting user-initiated calls, business-initiated calls, or both, and which country’s business number will we use?
5. Are English/French output, 24-hour retention and an Inbox that refreshes while open sufficient? Do we need other languages, multiple users, notifications or longer storage?

For live testing, I need access to a project-owned Meta app, WhatsApp Business Account and suitable test/business phone number; the required permissions and backend credentials; an OpenAI API project with an agreed testing budget; and a public HTTPS backend endpoint. I also need test participants and representative audio/call samples. If TestFlight distribution is required, I will need access to an Apple Developer team.

I can register my own Meta developer account and handle the configuration and implementation. Could you confirm whether the lab already has these project resources, who can grant access, and which accounts and costs I should arrange myself?

I suggest confirming the scope first, validating a real voice message, and then testing one opted-in business call through to the iOS Inbox. We can agree on accuracy, latency and other acceptance criteria before that test.

Best regards,
Christine
