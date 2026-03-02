# Bibliotalk Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-02

## Active Technologies

- Python 3.11+ + `evermemos` (EverMemOS SDK), `httpx`, `pydantic`, `typer`, `rich`, `tenacity` (002-evermemos-content-ingest)

## Project Structure

```text
bt_agent/
bt_cli/
bt_common/
bt_voice_sidecar/
specs/
tests/
```

## Commands

python -m pytest

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes

- 002-evermemos-content-ingest: Added Python 3.11+ + `evermemos` (EverMemOS SDK), `httpx`, `pydantic`, `typer`, `rich`, `tenacity`

<!-- MANUAL ADDITIONS START -->
## Manual Notes

### New Package: `evermemos_ingest/`

- Standalone EverMemOS ingestion library + CLI (see `specs/002-evermemos-content-ingest/`).
- Local artifacts (gitignored): `.evermemos_ingest/` (SQLite index + JSON reports).

### Common Commands

- Sync deps (avoids permission issues with the default uv cache dir):
  - `UV_CACHE_DIR=/tmp/uv-cache uv sync --extra dev --extra ingest`
- Run tests:
  - `.venv/bin/python -m pytest`
- CLI help:
  - `.venv/bin/python -m evermemos_ingest --help`
<!-- MANUAL ADDITIONS END -->
