# Research: EverMemOS Content Ingestion Package

**Feature**: `/Users/tcai/Projects/Bibliotalk/specs/002-evermemos-content-ingest/spec.md`  
**Plan**: `/Users/tcai/Projects/Bibliotalk/specs/002-evermemos-content-ingest/plan.md`  
**Created**: 2026-03-01

This document records key technical decisions, rationale, and alternatives considered for the EverMemOS ingestion package.

## R1: EverMemOS Integration Approach

**Decision**: Use the existing EverMemOS Python SDK (`evermemos`) via a thin wrapper that supports retries, error mapping, and passing extra metadata fields.

**Rationale**:
- The repo already depends on `evermemos`, and `bt_common` demonstrates an async wrapper pattern that supports retries and extra payload fields.
- A wrapper allows consistent error handling and redaction rules while keeping EverMemOS interactions centralized.

**Alternatives considered**:
- Direct HTTP calls (manual `httpx` requests): rejected for duplicated error mapping and higher maintenance surface.

## R2: Stable Tenant + Source + Segment IDs

**Decision**: Follow the ID convention described in `BLUEPRINT.md`:
- `sender` (EverMemOS user) = operator-provided `user_id`
- `group_id` (per source) = `{user_id}:{platform}:{external_id}`
- `message_id` (per segment) = `{user_id}:{platform}:{external_id}:seg:{seq}`

**Rationale**:
- Stable IDs allow deterministic re-runs and make it possible to match citations back to exact ingested segments.
- Grouping by `group_id` gives EverMemOS cross-segment context for better memory extraction (source-level coherence).

**Alternatives considered**:
- Random UUIDs per run: rejected because re-runs cannot be made reliably idempotent without an additional mapping layer.

## R3: Idempotency / No-Duplicate Guarantee

**Decision**: Maintain a local ingestion index (SQLite by default) keyed by `(user_id, group_id, message_id)` and storing `sha256(text)` for every ingested segment.

**Rationale**:
- EverMemOS server-side idempotency semantics for repeated `message_id` submissions are not assumed.
- A local index enables “unchanged vs updated” reporting, robust retries, and duplicate prevention even if EverMemOS treats every call as an append.

**Alternatives considered**:
- Assume EverMemOS deduplicates by `message_id`: rejected because it is not guaranteed by the blueprint and would fail FR-007 if incorrect.
- Use a remote database (e.g., Supabase): rejected because this package must be standalone and usable outside the Bibliotalk stack.

## R4: Chunking / Segmentation Strategy

**Decision**: Provide deterministic, source-type-aware chunking strategies:
- Plain text: paragraph-aware packing into segments targeting ~1000–1500 characters.
- Time-coded transcript: timestamp-preserving packing into segments targeting ~800–1200 characters, maintaining `start_ms`/`end_ms` per segment.

**Rationale**:
- Deterministic chunking ensures stable `seq` and stable `message_id` across re-runs when content is unchanged.
- Target sizes align with the blueprint’s ingestion guidance and are practical for retrieval/citation.

**Alternatives considered**:
- Token-based chunking using a model tokenizer: rejected due to extra dependencies and reduced determinism across tokenizer/model versions.

## R5: Metadata & Citation Traceability

**Decision**:
- Store source-level metadata via EverMemOS conversation metadata (once per source/group).
- Store segment-level metadata as extra fields on each memorized message (e.g., `platform`, `external_id`, `seq`, `sha256`, and location markers like `start_ms`).

**Rationale**:
- Source metadata supports later citation rendering and debugging (title + canonical link, author/date when available).
- Segment metadata supports verification and report generation without relying on external state.

**Alternatives considered**:
- Store only text content with no metadata: rejected because it undermines actionable reporting and makes later citation verification harder.

## R6: Inputs Supported (Non-Interactive)

**Decision**: Support only non-interactive inputs:
- Operator-provided text and local files.
- Project Gutenberg plain-text download (no browser automation).
- YouTube transcript retrieval via a transcript API library (no browser automation).

**Rationale**:
- Meets FR-009 (“no interactive browsing”), keeps the package standalone, and avoids fragile scraping.

**Alternatives considered**:
- Playwright-based crawling: explicitly deferred by feature request.
- General URL-to-text extraction: deferred because many sites require dynamic rendering, auth, or anti-bot workarounds.

## R7: CLI + Report Artifacts

**Decision**:
- Provide a CLI with a stable command schema and predictable exit codes.
- Produce a machine-readable JSON report (per run) plus human-readable console output.
- Enforce strict redaction: never print credentials or raw authorization headers.

**Rationale**:
- The CLI is the primary operator interface and the simplest integration point for existing workers.
- Reports enable audits, retries, and quick diagnosis of failures.

**Alternatives considered**:
- Logs only, no report file: rejected because it weakens auditing and makes batch runs harder to manage.
