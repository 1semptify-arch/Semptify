---
description: Future vault_sync module plan — do not build without approval
---

# vault_sync (On Hold)

Status: **ON HOLD**. Do not scaffold or build without explicit user approval.

## Idea

Live, incremental, encrypted replica of Semptify metadata (journal, timeline, letters, deadlines, document pointers) streamed to the user's OAuth-connected cloud drive. Documents are not duplicated — they already live in the user's cloud. Only user-authored metadata is backed up.

## Architecture

- App-level hooks enqueue tracked metadata changes to a `sync_log` queue table.
- Background drain loop:
  1. Reads `sync_log`.
  2. Batches rows.
  3. Encrypts each chunk with AES-256-GCM using a user-passphrase-derived key.
  4. Appends to a Dropbox upload session.
- File format: newline-delimited JSON, one encrypted chunk per line (`sync_<user_id>.jsonl.enc`).

## Provider reality

- **Dropbox** is the only provider with a true append API (`/files/upload_session/append_v2`). Prototype here first.
- Google Drive and OneDrive require chunked/rewrite workarounds.

## Open questions before greenlight

1. Dropbox-only prototype — confirm.
2. Passphrase model: per-session (A) vs persistent (B).
3. Final approval to scaffold.
