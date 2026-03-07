# Bibliotalk (Deprecated)

This repository is being deprecated in favor of a simpler system:

- Continuously collect YouTube transcripts for specific figures.
- Ingest transcripts into EverMemOS to construct per-figure memory.
- Run one Discord bot per figure.
  - Each figure has a Discord channel that shows a feed of ingested videos (one thread per video).
  - Users DM a figure’s bot for private chat; the bot searches relevant memory segments and cites them.

The current codebase still contains reusable pieces for this new direction (notably the YouTube ingestion pipeline and the EverMemOS client wrapper).

See `BLUEPRINT.md` for the rewritten target architecture.

## What Still Matters Here

- `services/ingestion_service/`: YouTube transcript ingestion + chunking + dedup + EverMemOS memorize.
- `packages/bt_common/`: shared EverMemOS client, config loading, logging, exceptions.

## Development

- Sync deps (workspace):
  - `UV_CACHE_DIR=/tmp/uv-cache uv sync --all-packages --all-extras`
- Run tests:
  - `uv --directory services/ingestion_service run --package ingestion_service -m pytest`
  - `uv --directory packages/bt_common run --package bt_common -m pytest`

## EverMemOS Ingestion CLI (One-shot)

Environment variables:

- `EMOS_BASE_URL` (required)
- `EMOS_API_KEY` (optional)
- `INGEST_INDEX_PATH` (optional)

YouTube ingest happens via the ingestion service CLI and manifest tooling.

Notes:

- `yt-dlp` must be available on PATH (used for YouTube metadata/discovery).
