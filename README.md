# Bibliotalk

This repository is being reduced to the Discord-era MVP described in `specs/003-discord-bot/`.

What remains in scope:

- `packages/bt_common/`: shared EverMemOS client, config loading, logging, and common exceptions.
- `services/ingestion_service/`: retained YouTube/RSS ingestion primitives, chunking, and EverMemOS indexing logic.
- `services/agents_service/`: retained Gemini-grounded agent library, evidence models, and citation tooling.
- `specs/002-evermemos-content-ingest/` and `specs/003-discord-bot/`: active design artifacts.

Out-of-scope legacy surfaces from prior experiments have been removed.

## Development

- Sync deps (workspace): `UV_CACHE_DIR=/tmp/uv-cache uv sync --all-packages --all-extras`
- Run agent tests: `uv --directory services/agents_service run --package agents_service -m pytest`
- Run ingestion tests: `uv --directory services/ingestion_service run --package ingestion_service -m pytest`
- Run shared package tests: `uv --directory packages/bt_common run --package bt_common -m pytest`
- Unified CLI help: `uv run --package bt_cli bibliotalk --help`

## Local Runtime Quickstart

- Full quickstart guide: `specs/003-discord-bot/quickstart.md`
- Seed one figure mapping:
	- `uv run --package bt_cli bibliotalk figure seed --figure alan-watts --subscription-url https://www.youtube.com/@AlanWattsOrg --guild-id <GUILD_ID> --channel-id <CHANNEL_ID>`
- Trigger one manual ingest:
	- `uv run --package bt_cli bibliotalk ingest request --figure alan-watts --video-id <YOUTUBE_VIDEO_ID>`
	- Run services locally:
		- `uv run --package bt_cli bibliotalk collector run --figure alan-watts --once`
		- `uv run --package bt_cli bibliotalk discord run`
		- `uv run --package bt_cli bibliotalk memory-pages run --host 0.0.0.0 --port 8080`

## Docker Compose

- `cp deploy/local/.env.example deploy/local/.env`
- Fill values in `deploy/local/.env`
- Start stack:
	- `docker compose -f deploy/local/docker-compose.yml up`

## Notes

- `yt-dlp` must be available on `PATH` for YouTube metadata and discovery.
- The canonical target architecture is documented in `specs/003-discord-bot/plan.md`.
