# Bibliotalk

Bibliotalk is a Python monorepo for the Bibliotalk agent system (see `BLUEPRINT.md` for the full system design).

## Repo Layout

```text
services/
  agents_service/        # FastAPI agent service (Matrix appservice, orchestration)
  ingestion_service/     # Standalone EverMemOS ingestion library + CLI
  voice_call_service/    # Node sidecar for MatrixRTC/WebRTC
packages/
  bt_common/             # Shared Python utilities (incl. EverMemOS client wrapper)
tools/
  bt_cli/                # CLI helpers
specs/                   # Feature specs/plans/tasks
docs/                    # Reference knowledge docs
```

## Development

- Sync deps (from each service/package directory):
  - `UV_CACHE_DIR=/tmp/uv-cache uv sync --extra dev`
- Run tests (from each service/package directory):
  - `python -m pytest`

## EverMemOS Ingestion CLI

Docs/spec/tasks live under `specs/002-evermemos-content-ingest/`.

Environment variables:

- `EMOS_BASE_URL` (required)
- `EMOS_API_KEY` (optional)
- `INGEST_INDEX_PATH` (optional)

Examples:

- Ingest inline text:
  - `python -m ingestion_service --emos-base-url "$EMOS_BASE_URL" ingest text --user-id <USER_ID> --platform local --external-id <ID> --title "<TITLE>" --text "<TEXT>"`
- Ingest a local file:
  - `python -m ingestion_service --emos-base-url "$EMOS_BASE_URL" ingest file --user-id <USER_ID> --platform local --external-id <ID> --title "<TITLE>" --path /absolute/path/to/file.txt`
- Batch ingest from a manifest:
  - `python -m ingestion_service --emos-base-url "$EMOS_BASE_URL" ingest manifest --path /absolute/path/to/manifest.yaml`

Local outputs (gitignored by default):

- `.ingestion_service/index.sqlite3`
- `.ingestion_service/reports/<run_id>.json`
