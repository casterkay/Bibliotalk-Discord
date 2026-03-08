# Quickstart: Local Development

**Feature:** `003-discord-bot`
**Date:** 2026-03-07

---

## Prerequisites

- Python 3.11+
- `uv` (workspace package manager)
- `yt-dlp` installed and on `$PATH`
- A Discord bot application and token (one per figure) — create at https://discord.com/developers/applications
- An EverMemOS instance with API key
- A Google API key with Gemini access

---

## 1. Install dependencies

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --all-packages --all-extras
```

---

## 2. Set up the database

Run Alembic migrations (from the `ingestion_service` directory):

```bash
cd services/ingestion_service
uv run alembic upgrade head
```

For local dev without Alembic, the process auto-creates tables on startup.

---

## 3. Configure environment

Create a `.env` file at the repo root (gitignored):

```env
# EverMemOS
EMOS_BASE_URL=https://your-evermemos-instance.example.com
EMOS_API_KEY=your-emos-api-key

# Gemini
GOOGLE_API_KEY=your-google-api-key

# SQLite database path (optional — defaults to ~/.bibliotalk/bibliotalk.db)
BIBLIOTALK_DB_PATH=/path/to/bibliotalk.db

# Discord token — one per figure slug (uppercased, hyphens → underscores)
DISCORD_TOKEN_ALAN_WATTS=your-discord-token-for-alan-watts
```

---

## 4. Seed a test figure

Use the helper script:

```bash
uv run python services/discord_service/scripts/seed_figure.py \
  --figure alan-watts \
  --display-name "Alan Watts" \
  --persona-summary "Philosopher and interpreter of Eastern philosophy." \
  --subscription-url https://www.youtube.com/@AlanWattsOrg \
  --guild-id YOUR_TEST_GUILD_ID \
  --channel-id YOUR_TEST_FEED_CHANNEL_ID
```

---

## 5. Run the bot

```bash
uv run --package ingestion_service python -m ingestion_service --figure alan-watts
uv run --package discord_service python -m discord_service --figure alan-watts
uv run --package memory_page_service python -m memory_page_service
```

Expected output:

```
INFO  [ingestion_service] Starting collector for figure: alan-watts (Alan Watts)
INFO  [discord_service] Starting figure bot: alan-watts (Alan Watts)
INFO  [discord_service] Connected to Discord as AlanWattsBot#1234
INFO  [discord_service] Feed channel: #alan-watts-feed (guild: My Test Guild)
INFO  [ingestion_service] Collector polling loop started (interval: 60 min)
```

---

## 6. Validate ingest (manual one-shot)

To test ingest without waiting for the polling interval, use the manual helper:

```bash
uv run python services/ingestion_service/scripts/trigger_ingest.py \
  --figure alan-watts \
  --video-id KNOWN_YOUTUBE_VIDEO_ID
```

Then process the manual request immediately:

```bash
uv run --package ingestion_service python -m ingestion_service --figure alan-watts --once
```

---

## 7. Validate Discord feed

1. After a successful ingest, confirm the bot posts a parent message to your test feed channel.
2. A thread is created under the parent message.
3. Transcript batch messages appear in sequence inside the thread.
4. Re-run the bot process — confirm no duplicate parent message or thread.

---

## 8. Validate DM chat

1. DM the bot account on your test guild.
2. Ask a question related to a successfully ingested video.
3. Confirm the response contains an inline link in the form `[text](https://www.bibliotalk.space/memory/alan-watts_20260101T120000Z)`.
4. Ask a question with no supporting evidence.
5. Confirm the bot responds: *"I couldn't find relevant supporting evidence for that question."*

---

## Running tests

```bash
# ingestion_service unit tests
uv --directory services/ingestion_service run --package ingestion_service -m pytest

# agents_service unit tests (citation validation, BM25)
uv --directory services/agents_service run --package agents_service -m pytest

# discord_service tests
uv --directory services/discord_service run --package discord_service -m pytest

# bt_common contract tests
uv --directory packages/bt_common run --package bt_common -m pytest
```

---

## Docker Compose (local multi-figure)

```bash
cp deploy/local/.env.example deploy/local/.env
# fill in EMOS_BASE_URL, EMOS_API_KEY, GOOGLE_API_KEY, DISCORD_TOKEN_* values

docker compose -f deploy/local/docker-compose.yml up
```
