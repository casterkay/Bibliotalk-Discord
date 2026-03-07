# Contract: Collector Entry Point

**Package:** `discord_service`
**Entry point:** `python -m discord_service`
**Date:** 2026-03-07

The collector and Discord bot both run inside the same `discord_service` process per figure. There is no separate CLI for the collector — it starts automatically as a `discord.ext.tasks.loop` when the bot connects.

---

## Process Entry Point

```
python -m discord_service --figure <emos_user_id>
```

| Flag          | Type  | Required | Description                                                                                                                                    |
| ------------- | ----- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `--figure`    | `str` | Yes      | `emos_user_id` slug (e.g. `alan-watts`). Identifies which figure this process serves. Must match a `figures.emos_user_id` row in the database. |
| `--db`        | `str` | No       | SQLite database path. Overrides `BIBLIOTALK_DB_PATH`. Default: `~/.bibliotalk/bibliotalk.db`                                                   |
| `--log-level` | `str` | No       | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`. Default: `INFO`                                                                                    |

---

## Environment Variables

All secrets MUST be provided via environment variables. They MUST NOT appear in command arguments, logs, or config files committed to the repository.

| Variable               | Required | Description                                                                                                                                          |
| ---------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EMOS_BASE_URL`        | Yes      | EverMemOS API base URL                                                                                                                               |
| `EMOS_API_KEY`         | Yes      | EverMemOS API key                                                                                                                                    |
| `DISCORD_TOKEN_{SLUG}` | Yes      | Discord bot token for the figure identified by `--figure`. Variable name is uppercased: `DISCORD_TOKEN_ALAN_WATTS` for `emos_user_id = "alan-watts"` |
| `GOOGLE_API_KEY`       | Yes      | Gemini API key for the ADK agent                                                                                                                     |
| `BIBLIOTALK_DB_PATH`   | No       | SQLite database path (overridden by `--db`)                                                                                                          |

---

## Startup Sequence

```
1. Parse --figure slug
2. Load env vars; fail fast if any required secret is missing
3. Create SQLAlchemy async engine (create tables if not exist for dev; run alembic for prod)
4. Load Figure + DiscordMap + Subscriptions from DB; fail if figure not found
5. Instantiate EverMemOSClient (bt_common)
6. Instantiate LlmAgent for the figure (agents_service)
7. Instantiate discord_service.bot.client.FigureClient(figure, agent, db_session_factory)
8. asyncio.run(client.start(DISCORD_TOKEN))
   └── on_ready:
       ├── log connected guild + channel
       └── start collector polling loop (discord.ext.tasks.loop)
```

---

## Collector Polling Loop

- Interval: `subscription.poll_interval_minutes` (checked per subscription; default 30 min)
- On each tick:
  1. Fetch all active subscriptions for the figure from DB
  2. For each subscription: run yt-dlp flat extraction; diff against `ingest_state.last_seen_video_id`
  3. Enqueue new video IDs for ingest
  4. For each enqueued video: fetch transcript + metadata → chunk → persist → memorize in EMOS
  5. Derive `transcript_batches` for newly ingested videos
  6. Enqueue newly ingested videos for Discord feed posting
  7. Run feed publisher for pending `discord_posts`
  8. Update `ingest_state` cursor

- On consecutive failures: apply exponential backoff; increment `ingest_state.failure_count`; set `next_retry_at`
- On EverMemOS unavailability: local SQLite state is preserved; fail the EMOS step cleanly; retry on next poll

---

## Manual Re-Ingest

Manual single-video re-ingest is triggered by setting `source.manual_ingestion_requested_at` to the current UTC time. The polling loop detects this flag and:

1. Calls `evermemos_client.delete_by_group_id(group_id)` for the video's `group_id`
2. Marks all existing `segments` for this `source_id` as `is_superseded = True`
3. Clears `transcript_batches` for the `source_id` (those not yet posted to Discord)
4. Re-fetches transcript + metadata
5. Re-runs the full ingest pipeline
6. Clears `manual_ingestion_requested_at`

This path is explicitly separate from automated polling and is the only way to re-ingest a known `video_id` (FR-008, FR-009).

---

## Deployment (Docker Compose — one service per figure)

```yaml
# deploy/local/docker-compose.yml excerpt
services:
  bot-alan-watts:
    image: bibliotalk/discord-service:latest
    command: ["python", "-m", "discord_service", "--figure", "alan-watts"]
    environment:
      EMOS_BASE_URL: "${EMOS_BASE_URL}"
      EMOS_API_KEY: "${EMOS_API_KEY}"
      DISCORD_TOKEN_ALAN_WATTS: "${DISCORD_TOKEN_ALAN_WATTS}"
      GOOGLE_API_KEY: "${GOOGLE_API_KEY}"
      BIBLIOTALK_DB_PATH: "/data/bibliotalk.db"
    volumes:
      - bibliotalk-data:/data
    restart: unless-stopped
```
