# Bibliotalk Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-02

## Active Technologies

- Python 3.11+ + `evermemos` (EverMemOS SDK), `httpx`, `pydantic`, `typer`, `rich`, `tenacity` (002-evermemos-content-ingest)

## Project Structure

```text
services/
  agents_service/        # Python — appservice + agent runtime
    src/
      agent/             # agent factory, orchestration, tools, providers
      matrix/            # Matrix appservice handling + response formatting
      models/            # citation + segment domain models
      database/          # Supabase access helpers
      voice/             # voice session + backend adapters
  ingestion_service/     # Python — content ingestion pipelines + CLI
    src/
      adapters/          # source adapters (gutenberg, youtube, local_text)
      domain/            # errors, ids, data models
      pipeline/          # chunking, manifest, ingest, index
      runtime/           # config + reporting
  voice_call_service/    # Node.js — MatrixRTC/WebRTC sidecar
packages/
  bt_common/             # Python — shared infra library (EMOS client, config, logging, exceptions)
specs/
docs/
```

## Commands

- Run all tests for a service (from its directory):
  - `python -m pytest`
- Run ingestion CLI:
  - `python -m ingestion_service --help`

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes

- 002-evermemos-content-ingest: Added Python 3.11+ + `evermemos` (EverMemOS SDK), `httpx`, `pydantic`, `typer`, `rich`, `tenacity`

<!-- MANUAL ADDITIONS START -->
## Manual Notes

### Architecture Boundaries

- Treat current repository file layout as the source of truth for imports and ownership.
- The single `format_ghost_response` implementation is in `services/agents_service/src/matrix/appservice.py`.
- Citation and segment domain models live in `services/agents_service/src/models/`.
- `bt_common` is infra-only (`evermemos_client`, `config`, `logging`, `exceptions`) and should not own agent-domain models.

### ingestion_service

- Standalone EverMemOS ingestion library + CLI (see `specs/002-evermemos-content-ingest/`).
- Local artifacts (gitignored): `.ingestion_service/` (SQLite index + JSON reports).

### Common Commands

- Sync deps (from each service/package directory):
  - `UV_CACHE_DIR=/tmp/uv-cache uv sync --extra dev`
- Run tests (from each service/package directory):
  - `python -m pytest`
- Ingestion CLI help:
  - `python -m ingestion_service --help`
<!-- MANUAL ADDITIONS END -->
