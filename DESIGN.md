# Blueprint: YouTube -> EverMemOS -> Discord Figure Bots

This document defines the target design for a Discord-only figure bot system. Each figure is represented by a dedicated Discord bot backed by EverMemOS and a local verbatim evidence cache. The system continuously discovers new YouTube videos for each figure, ingests transcript segments into EverMemOS, preserves the same segments locally for retrieval and quote validation, publishes a batched ingest feed into Discord, and supports grounded DM chat with inline memory links.

The design intentionally reuses the strongest parts of this repository: YouTube transcript ingestion and chunking, local SQLite indexing patterns, the EverMemOS client wrapper, and evidence retrieval and grounding-validation logic. Matrix-specific runtime concerns are out of scope and should not shape the new system.

## Vision

Continuously collect YouTube transcripts for specific individuals, build figure-specific memory in EverMemOS, and expose each figure through Discord as:

- A dedicated bot for private DM conversation.
- A dedicated feed channel that shows ingested videos.
- A per-video thread containing batched original transcript excerpts.

Core principle: 言必有據.

Every non-trivial factual claim must be grounded in verbatim evidence that can be traced back to a cached transcript segment and a source URL.

## Product Goals

### MVP goals

- One Discord bot per figure.
- One Discord text channel per figure for ingest feed posting.
- One thread per ingested YouTube video.
- Feed posts batched into Discord messages using local transcript grouping rules rather than raw chunk.
- Grounded DM chat with inline memory links.
- Idempotent ingest and Discord posting.

### Non-goals

- Voice chat.
- Matrix integration.
- Multi-agent group conversation.
- Multi-human room semantics.
- Non-YouTube sources in MVP.

## Non-Negotiables

1. Grounding first: every response must search memory before answering.
2. No evidence means the bot explicitly says it lacks relevant evidence.
3. Verbatim cache is the source of truth for quote validation.
4. Figure isolation is strict across memory, cache, and bot runtime.
5. Ingest and feed posting must be idempotent.
6. Discord output must respect rate limits and avoid duplicate threads or messages.
7. DM responses must link directly to memory pages instead of using bracketed citation indices or a trailing sources block.

## High-Level Architecture

```text
YouTube
  |
  | discovery via yt-dlp flat extraction and optional RSS
  v
Collector / Ingestion Service
  - poll subscriptions per figure
  - fetch transcript via youtube-transcript-api
  - fetch metadata via yt-dlp
  - chunk transcript into stable segments
  - dedup and persist verbatim evidence in SQLite
  - memorize segments into EverMemOS
  - ingestion a single video on demand by delete-then-reingest
  - emit feed-post jobs for Discord
  v
EverMemOS
  - figure-scoped long-term memory
  - retrieval by semantic / RRF search
  ^
  | group_id candidates
  |
Evidence Cache (SQLite)
  - figures
  - subscriptions
  - sources
  - segments
  - transcript_batches
  - ingest_state
  - discord_posts
  v
Discord Runtime
  - one bot per figure
  - feed channel posting
  - thread creation per video
  - DM chat grounded on evidence
```

## Package Boundaries

The system should be split into three clean runtime areas.

### Ingestion package

Responsible for:

- YouTube discovery from channel and playlist URLs.
- Transcript and metadata fetch.
- Transcript chunking.
- Local evidence persistence.
- EverMemOS memorization.
- Idempotent ingest state tracking.

### Agent runtime package

Responsible for:

- Persona prompt construction per figure.
- EverMemOS search.
- Evidence loading from SQLite.
- BM25 reranking and evidence packaging.
- Memory-link emission and grounding validation.
- Final grounded response generation through Gemini via ADK.

### Discord runtime package

Responsible for:

- Running one bot per figure.
- Routing DM messages to the correct figure runtime.
- Posting new ingest feed entries.
- Creating and populating per-video threads.
- Tracking Discord-side idempotency and retry state.

The boundaries should stay strict. Do not import Matrix-era orchestration or SQLAlchemy-heavy app baggage into the new runtime unless there is a specific, justified need.

## Core Identifiers And Conventions

Each figure has a stable UUID `figure_id`, `display_name`, and readable-slug `emos_user_id`.

For YouTube ingest:

- `group_id = {emos_user_id}:youtube:{video_id}`
- `message_id = {emos_user_id}:youtube:{video_id}:seg:{seq}`
- `group_name = {figure_display_name} - {video_title}`
- `create_time` for each memorized chunk is `video_published_at + transcript_chunk_start_offset`
- `segment_id` should be stable and derivable from source identity and sequence.

Identifier rules:

- `figure_id` is an internal UUID primary key.
- `emos_user_id` is a readable slug in the format `alan-watts`.
- `emos_user_id` must stay stable forever once deployed.

## Data Model

SQLite is the local source of truth for verbatim evidence and ingest state.

### Recommended tables

#### `figures`

- `figure_id`
- `display_name`
- `emos_user_id`
- `persona_summary`
- `status`

#### `subscriptions`

- `subscription_id`
- `figure_id`
- `platform` with value `youtube`
- `subscription_type` such as `channel` or `playlist`
- `subscription_url`
- `poll_interval_minutes`
- `is_active`

#### `sources`

- `source_id`
- `figure_id`
- `platform` with value `youtube`
- `external_id` for video id
- `group_id`
- `title`
- `source_url`
- `channel_name`
- `published_at`
- `raw_meta_json`
- `transcript_status`
- `manual_ingestion_requested_at`

#### `segments`

- `segment_id`
- `source_id`
- `seq`
- `text`
- `sha256`
- `start_ms`
- `end_ms`
- `create_time`
- `is_superseded`

#### `transcript_batches`

- `batch_id`
- `source_id`
- `speaker_label`
- `start_seq`
- `end_seq`
- `start_ms`
- `end_ms`
- `text`
- `batch_rule` with value based on speaker and silence-gap grouping
- `posted_to_discord`

#### `ingest_state`

- `subscription_id`
- `last_seen_video_id`
- `last_published_at`
- `last_polled_at`
- `failure_count`
- `next_retry_at`

#### `discord_map`

- `figure_id`
- `guild_id`
- `channel_id`
- `bot_application_id`
- `bot_user_id`

#### `discord_posts`

- `figure_id`
- `source_id`
- `parent_message_id`
- `thread_id`
- `batch_id`
- `posted_at`
- `post_status`

### Required query patterns

The schema must support these queries efficiently:

- Given EverMemOS search result `group_id` values, fetch all local segments for those groups.
- Given a `segment_id`, fetch the exact segment text for quote validation.
- Given EMOS retrieval fields `user_id` and `timestamp`, reconstruct the linked transcript timepoint and memory page id.
- Given a `source_id`, fetch transcript batches derived from local speaker and silence-gap grouping.
- Given a `figure_id`, fetch a figure's segment corpus for reranking, debugging, and fallback behavior.
- Given a `source_id` or YouTube `video_id`, determine whether Discord feed content was already posted.

## Discovery Design

### Subscription model

Each figure owns one or more YouTube subscriptions:

- Channel URLs.
- Playlist URLs.

### Discovery mechanism

Primary path:

- Use `yt-dlp` flat extraction to list recent items and metadata without API keys.

Fallback path:

- Support YouTube RSS where useful if `yt-dlp` becomes flaky for a particular source.

### Incrementality

- Persist a cursor per subscription in `ingest_state`.
- On each poll, compute the delta since the last successful cursor.
- Enqueue only newly discovered videos.
- Treat YouTube `video_id` as the immutable idempotency key for automated ingest; automated polling never re-ingests an already known video.

### Scheduler

- Start with a single asyncio polling loop.
- Support a configurable poll interval, typically 15 to 60 minutes.
- Bound concurrency globally and per figure.
- Apply exponential backoff after repeated failures.

## Ingest Pipeline

The ingest pipeline for a discovered video is:

1. Fetch transcript with `youtube-transcript-api`.
2. Fetch metadata with `yt-dlp`.
3. Normalize transcript text.
4. Chunk into sentence-aware segments of roughly 1200 characters.
5. Compute each chunk `create_time` as `video_published_at + chunk_start_offset`.
6. Persist source and segment data in SQLite.
7. Deduplicate by figure, video, sequence, and content hash.
8. Memorize each segment into EverMemOS using stable identifiers.
9. Derive local transcript batches from adjacent segments using speaker continuity and silence-gap threshold rules.
10. Mark ingest outcome for later Discord feed posting.

### Idempotency rules

- Automated ingestion never re-ingests an already known `video_id`.
- Rerunning Discord feed publication must not create duplicate parent posts or threads.
- Manual single-video ingestion is allowed through an explicit API path that first deletes existing EverMemOS memories for that video's `group_id` and then re-inserts the transcript.

### Manual ingestion endpoint

In addition to automated polling, the system may expose an API endpoint for one-off ingestion of a specific video.

Behavior:

1. Resolve `group_id = {emos_user_id}:youtube:{video_id}`.
2. Delete existing EverMemOS memories belonging to that `group_id`.
3. Clear or replace the corresponding local source, segment, and transcript-batch cache rows.
4. Fetch transcript and metadata again.
5. Recompute chunk `create_time` values from publish time plus transcript offsets.
6. Re-memorize the video into EverMemOS.
7. Rebuild the local transcript-batch feed state for that video.

This path is explicitly separate from automated polling so that routine ingestion remains simple and strictly idempotent by `video_id`.

### Error handling

- If a transcript is unavailable, record the failure and skip the video.
- If metadata fetch fails, ingest should fail clearly and retry according to policy.
- If EverMemOS is unavailable, ingest should fail without losing local state needed for retry.

## Memory Search And Evidence Selection

Each DM turn should follow the same retrieval discipline.

1. Search EverMemOS for relevant groups using RRF-style retrieval.
2. If retrieval quality is weak, allow an agentic fallback strategy.
3. Fetch candidate verbatim segments from SQLite for the returned `group_id` values.
4. BM25-rerank the local segments against the user query.
5. Select the top evidence set for prompting and citation.

### Evidence object

The agent runtime should work with explicit evidence objects containing:

- `segment_id`
- `figure_id`
- `group_id`
- `memory_user_id`
- `memory_timestamp`
- `memory_page_id`
- `quote_snippet`
- `source_title`
- `source_url`
- `memory_url`
- `published_at`
- `platform`
- optional timestamped URL when available

## Agent Runtime

Gemini via ADK is the LLM runtime for MVP.

### Persona contract

Each figure should define:

- Name.
- Brief bio.
- Conversational style constraints.
- A hard rule that unsupported claims must be declined.

### Response contract

The model receives:

- The user message.
- Short recent DM context.
- Structured evidence blocks.
- Explicit instructions to answer only from evidence.

The model must return:

- A natural-language answer.
- Any grounded reference rendered directly as an inline markdown link in the form `[text](memory_url)`.
- No citation indices.
- No trailing `Sources:` section.

### Citation validation

Before sending a response to Discord:

- Validate that every linked memory belongs to the current figure and current retrieval set.
- Validate that every generated `memory_url` points to a resolvable memory page.
- Validate that every `memory_url` is derived from the EMOS `user_id` and `timestamp` pair returned by retrieval.
- Validate that any quoted span is a substring of cached local transcript text.
- Strip or repair invalid links before the final message is sent.

If no usable evidence remains after validation, the bot should respond that it could not find relevant supporting evidence.

### Memory URL pages

Grounded references in DM responses should point to lightweight public memory pages:

- URL pattern: `https://www.bibliotalk.space/memory/{user_id}_{timestamp}`.
- Pages are generated dynamically by a serverless worker.
- Each page should contain exactly one memory item retrieved from EMOS.
- Each page should contain the minimal EMOS summary for that single memory item and a link to the original video.
- The original video link should include the reconstructed transcript timepoint derived from `timestamp - video_published_at`.
- Pages should stay intentionally minimal and should not add extra commentary or unrelated chrome.

## Discord UX

### Bot topology

The product decision is one Discord application and token per figure.

Runtime model:

- One OS process per bot.
- Each process owns one Discord client and one figure runtime.

This is the default operational model for MVP because it maximizes isolation, keeps failure domains simple, and avoids thread-safety ambiguity in the Discord runtime.

### Feed channel

For each newly ingested video:

1. Send one parent message containing the video title and YouTube link.
2. Create one thread under that message.
3. Post batched transcript messages derived from local grouping rules in sequence order.

Feed batching model:

- Raw transcript chunks are still the atomic ingestion unit sent to `POST /memories`.
- Discord feed posts are not one-message-per-chunk.
- EverMemOS MemCells are internal and are not used for feed construction.
- Instead, successive chunks are grouped locally by speaker continuity and silence-gap threshold.
- Each Discord message should contain original transcript text, not an EMOS-generated summary.

Hard requirements:

- No duplicate thread for the same video.
- No duplicate parent post for the same video.
- No duplicate Discord post for the same local transcript batch.
- Sequential posting to reduce Discord rate-limit pressure.
- Clear retry handling if a thread is created but chunk posting fails partway through.

### DM chat

When a user sends a DM to a figure bot:

1. Route the message to that figure's agent runtime.
2. Retrieve evidence through EverMemOS and the local cache.
3. Generate a grounded response.
4. Validate memory links and quoted spans.
5. Send the final answer back to the user.

Short per-user DM context may be kept in memory or SQLite, but it must not replace evidence retrieval. Grounding remains mandatory on every meaningful turn.

## Operations And Configuration

### Required secrets

- `EMOS_BASE_URL`
- `EMOS_API_KEY`
- One `DISCORD_TOKEN` per figure

### Runtime configuration

- Per-figure polling interval override
- Global ingest concurrency
- Per-source ingest concurrency, where each source is a single channel or playlist subscription
- Discord posting rate controls
- Retry and backoff policy
- SQLite database path

### Local development

- Use a single SQLite database for evidence cache, ingest state, and Discord post tracking.
- Persist transcript-batch feed state so Discord posting can resume idempotently.
- Prefer rich structured logs for ingest failures, retry decisions, and Discord API failures.

### Deployment

Initial deployment target:

- One host or VPS.
- Collector and Discord runtime deployed via systemd or Docker Compose.

## Migration And Extraction Guidance

This repository is being repurposed. Reuse should be selective.

- Reuse proven ingestion and chunking logic.
- Reuse EverMemOS client logic.
- Reuse retrieval, reranking, and link-validation patterns.
- Do not carry forward Matrix-specific transport code.
- Do not let legacy SQLAlchemy app structure dictate the new design if SQLite suffices.

When extracting logic into the new runtime, copy and simplify aggressively instead of preserving old abstractions that only made sense for the prior system.

## Reusable References In This Repository

- YouTube transcript ingestion: [services/ingestion_service/src/adapters/youtube_transcript.py](services/ingestion_service/src/adapters/youtube_transcript.py)
- Chunking logic: [services/ingestion_service/src/pipeline/chunking.py](services/ingestion_service/src/pipeline/chunking.py)
- Ingest orchestration: [services/ingestion_service/src/pipeline/ingest.py](services/ingestion_service/src/pipeline/ingest.py)
- Incremental index pattern: [services/ingestion_service/src/pipeline/index.py](services/ingestion_service/src/pipeline/index.py)
- Figure manifest and playlist expansion precedent: [services/ingestion_service/scripts/ingest_from_figures_json.py](services/ingestion_service/scripts/ingest_from_figures_json.py)
- EverMemOS client wrapper: [packages/bt_common/src/evermemos_client.py](packages/bt_common/src/evermemos_client.py)
- Memory search tool: [services/agents_service/src/agent/tools/memory_search.py](services/agents_service/src/agent/tools/memory_search.py)
- Citation emission tool: [services/agents_service/src/agent/tools/emit_citations.py](services/agents_service/src/agent/tools/emit_citations.py)
- Citation model: [services/agents_service/src/models/citation.py](services/agents_service/src/models/citation.py)
- Segment model: [services/agents_service/src/models/segment.py](services/agents_service/src/models/segment.py)

## Verification Plan

### Ingest validation

1. Run a one-shot ingest for a known public video with transcripts enabled.
2. Confirm EverMemOS receives the expected `group_id`, `message_id`, and chunk `create_time` sequence.
3. Confirm SQLite contains source metadata, segment text, segment `create_time`, and transcript-batch rows for that video.
4. Poll again and verify that the same `video_id` is skipped by automated ingestion without duplicate memorization.

### Manual ingestion validation

1. Trigger the single-video ingestion endpoint for an already ingested video.
2. Confirm existing EverMemOS memories for that `group_id` are deleted first.
3. Confirm the transcript is inserted again and local transcript-batch feed state is rebuilt cleanly.

### Discovery validation

1. Subscribe a test figure to a playlist or channel.
2. Poll twice.
3. Confirm that only newly discovered videos are enqueued on the second poll.

### Discord feed validation

1. In a test guild, confirm that a parent message and thread are created for a newly ingested video.
2. Confirm speaker-and-silence-gap batched messages appear in order.
3. Confirm each posted Discord message maps to one unique local transcript batch.
4. Re-run the publish path and confirm no duplicate thread, parent message, or transcript-batch post is created.

### DM chat validation

1. DM a figure bot with a question that should match a known transcript chunk.
2. Confirm the response uses inline markdown links in the form `[text](memory_url)`.
3. Confirm the linked page shows exactly one EMOS memory item and the original video link with the reconstructed timepoint.
4. Confirm the `memory_url` id is derived from the EMOS `user_id` and `timestamp` fields returned by retrieval.
5. Intentionally corrupt a cached quote or memory link and confirm validation strips the bad link before sending.
6. Ask a question with no supporting evidence and confirm the bot explicitly says that it lacks relevant evidence.

## Decisions

- Discord is the only UI surface in MVP.
- There is one bot per figure.
- YouTube discovery uses `yt-dlp` first and can optionally fall back to RSS.
- Gemini via ADK is the LLM runtime.
- `figure_id` is a UUID.
- `emos_user_id` is a readable, stable slug in the format `alan-watts`.
- `group_id` is `emos_user_id:youtube:video_id`.
- Automated ingest uses `video_id` as the no-reingest key.
- Manual single-video ingestion deletes existing EverMemOS data for the video's `group_id` before re-ingesting.
- Chunk `create_time` is computed as `video_published_at + transcript_chunk_start_offset` so EMOS retrieval timestamps can be mapped back to video timepoints.
- Feed UX is one parent post per video plus one thread containing locally batched original transcript messages.
- SQLite is the local evidence cache and ingest-state store.
- EverMemOS MemCells are internal and are not part of the feed UX.
- DM grounded references are inline markdown links to `www.bibliotalk.space/memory/{id}` pages, where `{id}` is derived from EMOS `user_id` and `timestamp`.
- Runtime model is process-per-bot.
