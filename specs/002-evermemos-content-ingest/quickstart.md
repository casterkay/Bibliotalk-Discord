# Quickstart: EverMemOS Content Ingestion Package

**Feature**: `/Users/tcai/Projects/Bibliotalk/specs/002-evermemos-content-ingest/spec.md`  
**Created**: 2026-03-01

This quickstart describes the intended developer/operator workflow for the ingestion package once implemented.

## Prerequisites

- Python 3.11+
- EverMemOS base URL and API key (if required by the target EverMemOS instance)
- Curated source content (text/files/transcripts) and source attribution metadata (title + canonical link)

## Configuration

Environment variables (recommended):

- `EMOS_BASE_URL` (required): EverMemOS base URL, e.g. `https://<host>`
- `EMOS_API_KEY` (optional): API key for `Authorization: Bearer ...`
- `EMOS_TIMEOUT_S` (optional): request timeout
- `EMOS_RETRIES` (optional): retry count for transient failures
- `INGEST_INDEX_PATH` (optional): path to the local SQLite ingestion index

## Ingest One Source (P1)

Intended CLI shape:

- Ingest local text:
  - `python -m evermemos_ingest ingest text --user-id <USER_ID> --title "<TITLE>" --canonical-url "<URL>" --platform local --external-id "<ID>" --text "<TEXT>"`
- Ingest a local file:
  - `python -m evermemos_ingest ingest file --user-id <USER_ID> --title "<TITLE>" --canonical-url "<URL>" --platform local --external-id "<ID>" --path /absolute/path/to/file.txt`

Expected output:
- human-readable summary to stdout
- a JSON report file written to an operator-specified `--report-path`, or by default to `.evermemos_ingest/reports/<run_id>.json`

## Re-Run Safely (P2)

Re-running the same command with unchanged content is expected to:
- skip unchanged segments (no duplicates)
- report `skipped_unchanged` counts per source

## Batch Ingest (P3)

Intended CLI shape:

- `python -m evermemos_ingest ingest manifest --path /absolute/path/to/manifest.yaml`

The manifest format and report format are defined in:
- `/Users/tcai/Projects/Bibliotalk/specs/002-evermemos-content-ingest/contracts/ingest-manifest.md`
- `/Users/tcai/Projects/Bibliotalk/specs/002-evermemos-content-ingest/contracts/report-format.md`

## Non-Interactive Constraint

If a source requires interactive browsing (dynamic rendering, login, anti-bot challenges), ingestion must fail with an actionable error. Playwright/browser crawling is explicitly deferred in this feature.
