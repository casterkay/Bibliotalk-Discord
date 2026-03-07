# Bibliotalk Development Guidelines

## Coding Assistant Guidelines

- You are a top-tier designer and engineer. Excellence is in your blood. Mediocre work is unacceptable. Exert your highest intellectual and aesthetic capabilities in this project.
- Your technical competency should at least match a Google L8 engineer with over $1M package.
- Always put things in their right places! Use your common sense and artistic taste.
- Always maintain excellent abstraction design: modularity, generality, reusability, separation of concerns, elimination of abstraction leaks, etc.
- Focus on my true intent instead of always literally following my words. If you are confident, you can propose alternatives or raise opposition before executing my commands.
- Choose the latest suitable modern designs in both backend and frontend.
- After you make edits, think and suggest updates to maintain consistency and integrity throughout docs and code. In particular, ensure dev context files are up to date and have full coverage.
- When you find unexpected changes in code diverted from your read & write memory, always assume they are made by me and RESPECT them.
- Reduction over Multiplication: always consider lossless reduction of code or specs and avoid unnecessary multiplication.

## Active Technologies

- Python 3.11+
- EverMemOS: `evermemos` SDK + `httpx` + `tenacity`
- Ingestion: `youtube-transcript-api`, `yt-dlp`, `typer`, `rich`, SQLite
- Discord: `discord.py` (text-only bot + thread posting)
- Data/modeling: `pydantic`

## Commands

- Sync deps (workspace):
  - `UV_CACHE_DIR=/tmp/uv-cache uv sync --all-packages --all-extras`
- Run tests (run from each package directory to avoid pytest root collisions):
  - `uv --directory services/ingestion_service run --package ingestion_service -m pytest`
  - `uv --directory packages/bt_common run --package bt_common -m pytest`
- Run ingestion CLI:
  - `uv run --package ingestion_service -m ingestion_service --help`

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes

- This repository is being repurposed toward a YouTube → EverMemOS → Discord figure-bot pipeline.

<!-- MANUAL ADDITIONS START -->
## Manual Notes

### Architecture Boundaries

- Treat current repository file layout as the source of truth for imports and ownership.
- `bt_common` is infra-only (`evermemos_client`, `config`, `logging`, `exceptions`). Do not put agent-domain models here.
- The ingestion pipeline (YouTube transcript fetch + chunking + dedup + memorize) lives in `services/ingestion_service/`.

### ingestion_service

- Standalone EverMemOS ingestion library + CLI (see `specs/002-evermemos-content-ingest/`).
- Local artifacts (gitignored): `.ingestion_service/` (SQLite index + JSON reports).

### Common Commands

- Sync deps (workspace; installs all Python members):
  - `UV_CACHE_DIR=/tmp/uv-cache uv sync --all-packages --all-extras`
- Run tests:
  - `uv --directory services/ingestion_service run --package ingestion_service -m pytest`
  - `uv --directory packages/bt_common run --package bt_common -m pytest`
- Ingestion CLI help:
  - `uv run --package ingestion_service -m ingestion_service --help`
<!-- MANUAL ADDITIONS END -->
