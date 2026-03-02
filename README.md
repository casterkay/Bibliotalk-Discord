# Bibliotalk

Bibliotalk is a Python monorepo for the Bibliotalk agent system (see `BLUEPRINT.md` for the full system design).

## Repo Layout

```text
bt_agent/            # FastAPI agent service (Matrix appservice, orchestration)
bt_cli/              # CLI helpers
bt_common/           # Shared Python utilities (incl. EverMemOS client wrapper)
bt_voice_sidecar/    # Node sidecar for MatrixRTC/WebRTC
evermemos_ingest/    # Standalone EverMemOS ingestion library + CLI
specs/               # Feature specs/plans/tasks
tests/               # Unit/contract/integration tests
```

## Development

- Sync deps:
  - `UV_CACHE_DIR=/tmp/uv-cache uv sync --extra dev --extra ingest`
- Run tests:
  - `.venv/bin/python -m pytest`

## EverMemOS Ingestion CLI

Docs/spec/tasks live under `specs/002-evermemos-content-ingest/`.

Environment variables:

- `EMOS_BASE_URL` (required)
- `EMOS_API_KEY` (optional)
- `INGEST_INDEX_PATH` (optional)

Examples:

- Ingest inline text:
  - `.venv/bin/python -m evermemos_ingest --emos-base-url "$EMOS_BASE_URL" ingest text --user-id <USER_ID> --platform local --external-id <ID> --title "<TITLE>" --text "<TEXT>"`
- Ingest a local file:
  - `.venv/bin/python -m evermemos_ingest --emos-base-url "$EMOS_BASE_URL" ingest file --user-id <USER_ID> --platform local --external-id <ID> --title "<TITLE>" --path /absolute/path/to/file.txt`
- Batch ingest from a manifest:
  - `.venv/bin/python -m evermemos_ingest --emos-base-url "$EMOS_BASE_URL" ingest manifest --path /absolute/path/to/manifest.yaml`

Local outputs (gitignored by default):

- `.evermemos_ingest/index.sqlite3`
- `.evermemos_ingest/reports/<run_id>.json`

