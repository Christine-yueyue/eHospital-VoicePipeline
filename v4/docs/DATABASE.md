# Database Specification — Voice Notes v4

**Revision:** 1.0 · **Status:** Current local schema; external database destination pending TA confirmation

## Storage boundary

The prototype creates a SQLite file at `v4/backend/data/inbox.sqlite3`, overridden by `INBOX_DB_PATH`. Its table is **`messages`**. This is an implemented local table name, not evidence of an agreed lab database destination. Do not point v4 at v3's database or an existing project database without a reviewed migration/integration plan.

[inbox.py](../backend/inbox.py) is the schema and lifecycle authority. Every database connection ensures the base table exists and adds missing v4 columns. There is no versioned migration registry. The connection timeout is five seconds and `PRAGMA secure_delete=ON` is enabled. The primary key supplies deduplication; no additional indexes, foreign keys, user table or tenant boundaries exist.

## `messages` data dictionary

All fields except the primary key declaration explicitly use `NOT NULL`. Times are Unix seconds stored as REAL. Status/kind values are application conventions, not SQL CHECK constraints.

| Column | SQLite type / default | Meaning |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | Message ID, or `call:<call ID>`; deduplication key |
| `media_id` | TEXT | Media lookup ID; cleared on deletion |
| `sender` | TEXT | Masked identifier, ellipsis plus last four characters |
| `target` | TEXT | Target language captured at enqueue time |
| `created` | REAL | Receipt/insertion time; retention clock |
| `updated` | REAL | Processing/retry update time; not a full audit log |
| `status` | TEXT / `queued` | queued, processing, completed, partial, failed, deleted |
| `attempts` | INTEGER / 0 | Claims in the current retry cycle |
| `available` | REAL / 0 | Earliest retry or processing lease expiry |
| `transcript` | TEXT / empty | Saved original text |
| `translation` | TEXT / empty | Final translated text |
| `error` | TEXT / empty | Sanitized user-visible error |
| `kind` | TEXT / `voice_message` | voice_message or call_transcript |
| `call_id` | TEXT / empty | Provider call reference |
| `media_sha256` | TEXT / empty | Expected signed call-document digest |
| `event_at` | REAL / 0 | Provider event time, or receipt fallback |
| `details` | TEXT / `{}` | JSON containing parsed metadata and speaker segments |
| `stage` | TEXT / empty | Fine-grained processing step |
| `lease_token` | TEXT / empty | UUID used to reject obsolete worker writes |

The last seven columns are added when absent in an older schema. Existing rows keep the voice-message default; the schema-upgrade regression verifies their preservation. This does not validate arbitrary legacy schemas or production migrations.

## Transactions and recovery

Enqueue and claim use `BEGIN IMMEDIATE`. Enqueue checks deduplication and the 100-job pending limit before committing a webhook batch. On overflow the transaction is rolled back. Claim selects an eligible queued/expired processing row, increments attempts and grants a 660-second lease with a new token.

Call parsing checkpoints original text and details before translation. Checkpoint and completion updates require the current lease, a processing state and a result still within its retention period. A stale worker cannot overwrite a newer attempt or resurrect a deleted result. Translation chunks are not independently checkpointed; retry may repeat translation of earlier chunks.

Transient failures can requeue until three claims have occurred. Manual retry of failed/partial results resets attempts and preserves original text/details. A process restart recovers eligible work after lease expiry; it is not an immediate restart guarantee.

## Retention and deletion

At 24 hours since receipt, pruning changes a row to `deleted` and clears media ID, sender, original, translation, error, call reference, digest, event time, details, stage and lease token. Explicit deletion clears the same fields immediately. The row is hidden from Inbox.

The tombstone retains **id, kind, target, created, updated, attempts and available**. The ID itself may contain the provider call ID. It is therefore incorrect to describe tombstones as anonymous or as containing no identifiers. Rows are removed at seven days since original receipt, not seven days after deletion.

Pruning runs during database operations and periodically in the worker. A long job or stopped server can delay physical cleanup; the interval is not an exact deletion deadline. `secure_delete` does not erase exported files, filesystem snapshots, device copies or backups. SQLite content is not application-encrypted.

Only webhook voice/call results use this table. Upload and local live microphone results are not inserted. Raw webhook bodies, original media URLs, call audio and word-level metadata are not archived by this design.

## API projection and migration decision

The list endpoint exposes result fields described in [API Reference](API_REFERENCE.md); it excludes media ID, digest, lease, attempts, available and updated. It returns the newest 100 visible rows. A shared app token grants access to the entire Inbox.

Before integrating with a professor/TA database, confirm the database engine, host/environment, schema and exact existing table name, or authorization to create a new table; required columns and keys; owner/access roles; retention/backups; and migration/deployment responsibility. An adapter and migration tests will be needed for another engine. Renaming a configuration variable alone cannot replace SQLite.

Suggested request to the TA:

> Could you confirm where v4 should store the call transcripts and translations? The prototype currently uses a local SQLite database with a table named `messages`. Should we use an existing project database and table, or create a new table? If an existing table is required, please provide its database engine, schema/table name, column definitions, access procedure, retention policy, and the person responsible for approving schema changes. Please share credentials through the project's secure channel rather than email.
