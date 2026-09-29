# Requirements Traceability — Voice Notes v4

**Revision:** 1.0 · **Baseline:** [SRS-V4](REQUIREMENTS.md) · **Evidence:** [TR-V4-001](TEST_REPORT.md)

The table maps all 15 functional and six non-functional requirement IDs to representative checks. A passing related test does not establish complete requirement coverage or stakeholder acceptance. Test names below omit parameter suffixes; the [backend inventory](evidence/20260929T031940Z/backend-cases.json) records each executed parameter case.

Source aliases: **B** = [test_backend.py](../backend/tests/test_backend.py); **W** = [test_whatsapp.py](../backend/tests/test_whatsapp.py); **C** = [test_calls.py](../backend/tests/test_calls.py); **FC** = [connection_test.dart](../frontend/test/connection_test.dart); **FI** = [call_inbox_test.dart](../frontend/test/call_inbox_test.dart); **FW** = [widget_test.dart](../frontend/test/widget_test.dart).

| Requirement | Implementation | Representative passing evidence | Remaining evidence / qualification |
| --- | --- | --- | --- |
| FR-01 | `auth.py`, `app.py`, frontend connection | W `test_unconfigured_app_fails_closed`; FC wrong-token and connection/disconnect cases; FI v3 rejection | UAT-01 actual server/device |
| FR-02 | `app.py`, `services.py` | B `test_bad_upload_rejected_before_provider`, `test_upload_limit`, `test_provider_failure_cleans_upload`, `test_real_ogg_is_decoded_to_wav_before_api` | Real recognition across required formats; crash cleanup not guaranteed |
| FR-03 | `services.py`, `whatsapp.py` | B `test_upload_returns_both_languages_and_cleans_file`, `test_translation_failure_keeps_transcript`; FW language switch | UAT-07 quality and language approval |
| FR-04 | `live.py`, `auth.py`, frontend microphone | B `test_live_stream_drains_final_words`, `test_browser_auth_frame_precedes_stream`, `test_live_rejects_invalid_pcm`, `test_live_provider_error_is_sanitized` | Device microphone, real upstream models, full ten-minute session UAT-01 |
| FR-05 | `whatsapp.py` verification | W `test_verify_challenge_and_reject_wrong_token` | Real dashboard challenge UAT-02/03 |
| FR-06 | `whatsapp.py`, `inbox.py` | W `test_signature_checked_before_json`, `test_webhook_body_size_is_bounded`, `test_queue_limit_rolls_back_webhook_batch`; C `test_call_signature_tenant_sender_and_bsuid_filters` | Real subscriptions/permissions UAT-02/03 |
| FR-07 | Audio extraction/download and worker | W `test_worker_processes_queued_audio_and_cleans_temporary_file`, `test_status_and_non_audio_events_are_acknowledged` | Real voice media and ASR UAT-02 |
| FR-08 | `call_transcripts.py` event extraction | C `test_irrelevant_or_invalid_calls_ignored`, `test_invalid_document_references_not_queued`, `test_call_signature_tenant_sender_and_bsuid_filters` | Actual eligible call event UAT-03 |
| FR-09 | `call_transcripts.py` download; call worker | C `test_download_only_sends_bearer_to_trusted_hosts`, `test_download_integrity_mime_size_and_redirects`, `test_signed_event_through_real_worker_download_parse_translate_inbox` | Real Meta lookup/download UAT-03 |
| FR-10 | Transcript parser | C `test_parser_preserves_text_and_can_render_segments`, `test_invalid_or_empty_documents_have_clear_failure`, `test_parser_rejects_bad_segments_and_oversized_transcripts` | Real document variants and metadata quality UAT-03/07 |
| FR-11 | Chunking, checkpoints, worker | C `test_translation_retry_keeps_original_and_metadata`, `test_long_translation_requests_are_bounded_without_losing_content` | Controlled integration retry UAT-05; real long-call quality |
| FR-12 | Frontend Inbox | FI call timeline and progress/retry cases; FC Inbox/delete case | Physical-device copy, refresh, background/resume and accessibility UAT-08 |
| FR-13 | `inbox.py` leases/retry | C `test_call_checkpoint_survives_restart_and_stale_worker_cannot_overwrite`, `test_meta_failures_visible_and_only_transient_errors_auto_retry`; W `test_failed_jobs_are_visible_and_can_retry` | Actual deployed restart UAT-06; concurrency/load not qualified |
| FR-14 | `inbox.py` pruning/delete | C `test_call_deletion_and_retention_erase_segments_and_block_resurrection`; W `test_retention_removes_content_but_keeps_dedupe_tombstone` | Operational cleanup/backup review UAT-06 and D-06 |
| FR-15 | Separate v4 tree/config/bundle; call IDs | Source preservation manifest; simulator build; FI v3 rejection; C `test_mixed_batch_dedupes_calls_and_voice_messages_atomically` | Actual callback isolation decision and redelivery UAT-04 |
| NFR-01 | Auth, CORS, configuration projection | W `test_no_provider_secrets_in_config`, `test_webhook_has_independent_signature_auth`, `test_cors_allows_app_auth_header`; B `test_live_rejects_bad_origin` | Deployment security review; no penetration test |
| NFR-02 | Frontend URL checks; TLS upstreams | FC `Only HTTPS or local debug addresses accepted`; source review | Real trusted HTTPS/WSS UAT-01; operational token handling |
| NFR-03 | Parser/download/queue/time limits | W body/queue/download limits; C oversize/chunk cases; constants reviewed | Long-running timeout boundaries and agreed-load timing UAT-08 |
| NFR-04 | Masking, data projection, pruning | W/C deletion and retention tests; [schema review](DATABASE.md) | Data owner approval, backup and access policy D-06/07 |
| NFR-05 | Flutter app and iOS project | Nine widget tests; simulator build | Physical device, accessibility, signed release UAT-01/08 |
| NFR-06 | Runner and technical documents | Logs, source hashes, this mapping, runbook | Named operational owner and reviewed release revision |

All referenced automated cases passed in TR-V4-001. Every manual/UAT reference remains not run. Approval of an implementation default, such as retention or shared-token access, must be recorded separately from its test outcome.
