# v3.3 WhatsApp Chatbot Plan

Status: The first implementation of the lower-right chat assistant is complete. This document records the v3.3 product plan; the shipped scope and configuration requirements are described in the current code and setup guide. Date: 2026-10-27.

## Product direction

Bring WhatsApp contact management, invitation sending, and voice-reply review into a conversational assistant. Open it from a **floating icon in the lower-right corner**. The chat panel overlays the current content and closes back to the same page. Keep the existing upload, live translation, WhatsApp inbox, and settings pages; do not add a separate follow-up workspace or reorganize the main pages.

Contacts do not need to install Voice Notes or sign in. They reply with a voice message in WhatsApp. Staff describe the work in natural language, and the assistant interprets the request and uses authorized contact, follow-up, and messaging capabilities.

## User interaction

### Entry point and panel

- Keep a circular chat icon fixed in the lower-right corner of the application shell on the home, WhatsApp inbox, connection settings, and other pages. It may show the number of replies needing review.
- On desktop, open a floating chat panel about 400 px wide. On narrow screens and iPhone, use a full-width panel attached to the bottom, respecting the safe area, keyboard, and back gestures.
- The icon and panel belong to the existing application shell. Do not add bottom navigation, a new home page, or a separate follow-up list page. Support scrolling for long conversations and keep the input at the bottom of the panel.
- Show an assistant introduction, conversation history, short suggested actions, and pending-action cards. Suggestions are optional; the primary workflow uses natural language.

### Manage contacts and follow-ups through chat

Example workflow:

1. Staff: "Contact Marie, ask how she is doing this week, and ask her to reply by voice."
2. The assistant looks up the contact. If multiple contacts have the same name, show their names and full numbers so staff can choose. If no contact exists, ask for a number and permission status before creating one. Do not send without a confirmed number and permission.
3. Check the available WhatsApp template, the contact's preferred language, and the 24-hour conversation window. Create a follow-up draft and show the recipient, editable invitation preview, translation target, and task title in chat.
4. Staff explicitly select **Confirm and send**. Record the task and submit the message. Show the actual status, such as sending, delivered, failed, or unknown. Allow staff to cancel or edit the draft before sending.
5. When the contact replies with one or more voice messages, continue using the existing webhook, download, transcription, translation, and retry flow. Notify staff and show the contact, related task, processing status, and previews of the transcript and translation. Let staff open the corresponding result details.
6. After staff review, allow them to complete the task or start another follow-up. Show a plan and ask for confirmation before completing a task or sending another message.

The first implementation supports adding contacts through chat, recording permission status, creating follow-up drafts, viewing contacts and tasks, confirming sends, and completing tasks that need review. Replies appear in the chat panel. Editing drafts, cancelling tasks, manually linking ambiguous replies, sending non-template free-form messages, and voice input remain future work. Ask for clarification when a request is ambiguous; do not guess the contact, task association, or intent. Text input is required for the initial release; voice input is optional and not required for the main workflow.

### Conversation example

**Staff:** Send Marie a follow-up for this week and invite her to reply with a voice message.

**Assistant:** I found Marie Laurent · +1 …0101. She has agreed to receive WhatsApp messages. I will ask how she is doing and invite her to reply by voice. The current conversation window requires an approved English invitation template. Please review the preview.

**Invitation card in chat:**

> Hello Marie, this is the Voice Notes team. We would like to hear how you are doing. When convenient, please reply with a voice message in this chat. Thank you.

**Staff:** Confirm and send.

**Assistant:** Submitted. I will update the send status when WhatsApp returns a receipt. When a voice reply arrives, I will remind you to review its transcript and translation here.

## Assistant execution boundaries

The model interprets intent, asks clarifying questions, and drafts responses. All actual reads and writes go through an allowlisted set of backend operations, such as finding contacts, viewing pending tasks, preparing invitation previews, creating drafts, submitting confirmed sends, associating replies, and updating task status. The backend validates every operation; the model cannot access the database or make HTTP requests directly.

- **Require explicit confirmation before sending external messages.** Show the final recipient, content, and sending method first. Call the Meta API only after staff select **Confirm and send**. If a request times out, show an unknown status and do not retry blindly.
- **Verify contact details.** Match by full number/WhatsApp `wa_id`. If multiple contacts match, show choices; do not match on a partial number. New contacts default to unknown permission. Before an invitation, ask staff to confirm permission and record its source.
- **Honor opt-outs.** Block sending to opted-out contacts, contacts without confirmed permission, or recipients the account is not allowed to message. When a contact asks to stop, record the opt-out and block future proactive sends.
- **Follow WhatsApp's messaging window and template rules.** For first contact or after the 24-hour reply window, use an approved, language-matched template. Within the window, use free-form text only where current Meta rules allow it. Treat model-written copy as a preview; do not assume generic copy is approved. Verify final requirements against the configured Meta account.
- **Represent status accurately.** Keep task progress, delivery receipts, and voice processing status distinct. Delivered does not mean the contact has replied; a transcription failure does not mean no reply was received. Staff must confirm task completion. If a reply cannot be matched confidently, list it as unlinked and ask staff to resolve it.
- **Do not make professional judgments.** The assistant organizes transcripts, translations, and processing status. The first release does not automatically reply to contacts or make medical or diagnostic judgments based on transcripts.
- **Preserve existing data-retention behavior.** Contact, task, and message status persist. The Voice Notes **Save to Database** setting continues to control long-term storage of reply audio and text. When disabled, retain content only under the existing 24-hour temporary policy and explain when results may expire in the assistant panel. Clearly identify content before deleting long-term records.

## Reuse existing pages and data

Do not restructure navigation. Add a shared overlay layer to the root Flutter `MaterialApp.builder` or application shell, containing the floating button, chat panel, focus handling, and keyboard behavior. Avoid implementing separate entry points in each `Scaffold`. Share the conversation between Flutter web and iOS; use a bottom-attached panel on narrow screens.

Add assistant orchestration and strictly defined business operations to FastAPI. Reuse the existing application access token; keep OpenAI and Meta credentials on the server. Continue using the signed webhook in `whatsapp.py`, the temporary voice queue in `inbox.py`, and long-term reply storage in `voice_feedback.py`.

The proposed persistent data model adds contacts, follow-up tasks, WhatsApp messages, and a durable outbox to the existing `voice_feedback.db`. Save voice results according to the existing setting and link them to tasks. In the target design, a send request creates the task, message, and idempotent outbox item in one transaction, then a background worker calls Meta. Legacy inbox records that only retain the last four digits remain unlinked; do not infer identity. Persist WhatsApp voice translations in the existing long-term records.

Do not retain the entire conversation indefinitely in model context. Read only the authorized contact and task data needed for the current request. Define minimum fields and cleanup rules before storing conversation transcripts. Logs must not contain full numbers, audio, message bodies, tokens, or chat input.

## Scope and acceptance criteria

### v3.3 target scope

The items below describe the target scope; see the status note and implementation limitations above for what is currently implemented.

- Open and close the assistant from any existing page without losing page state. Support a desktop floating panel and an iPhone bottom panel.
- Create and find contacts and follow-ups in natural language; confirm contact permission; edit drafts; preview invitations; explicitly confirm sends; and show send receipts.
- Process text and one or more voice replies; show processing status, transcript, and translation; support retries; and request manual association when a reply cannot be matched confidently.
- Find pending tasks, manually complete or cancel a task, and start a manual reminder through chat. Preview and confirm reminders and all other proactive messages.
- Explain requests the assistant cannot execute without changing data. Avoid duplicate sends after repeated confirmations, network retries, or server restarts.
- Preserve existing upload, live translation, WhatsApp inbox, connection settings, and EN/FR/AR display support.

### Future extensions

Bulk messaging, scheduled or recurring sends, automatic reminders without staff confirmation, automatic replies to contacts, multi-user roles and scheduling, and predictive or analytics dashboards are outside the first v3.3 release.

After the plan is approved, implement the vertical workflow: **root chat entry point → secure backend operations and contact/task records → send queue and Meta receipts → inbound message association → chat acceptance**. Preserve existing behavior at each step; the first release should be accepted as a complete end-to-end workflow.
