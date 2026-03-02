# Bibliotalk Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-02

## Active Technologies

- Python 3.11+ + `evermemos` (EverMemOS SDK), `httpx`, `pydantic`, `typer`, `rich`, `tenacity` (002-evermemos-content-ingest)

## Project Structure

```text
services/
  agents_service/        # Python — appservice + agent runtime
  ingestion_service/     # Python — content ingestion pipelines + CLI
  voice_call_service/    # Node.js — MatrixRTC/WebRTC sidecar
packages/
  bt_common/             # Python — shared library (citations, EMOS client, etc.)
tools/
  bt_cli/                # Python — developer CLI
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
