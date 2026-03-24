# Contract: Discord Message Shapes

**Used by:** `services/discord_service/` · feed publishing and talk threads
**Date:** 2026-03-10

This document defines the Discord-side "message shapes" Bibliotalk relies on.

For the feed publisher, we keep strict Pydantic boundary models in `services/discord_service/src/bot/message_models.py`. For talks, the boundary is Discord interactions (slash commands) + thread messages, and the persistence contract is `bt_store` (`rooms`, `room_members`, `platform_user_settings`).

---

## Slash Commands

### DM

### `/talk`

- **Context:** DM only
- **Argument:** `characters: str` (comma-separated)
  - Example: `/talk Alan Watts, Naval`
- **Result:** bot creates or resumes a **private thread** under a guild channel named `#bibliotalk`, invites the user, and returns a thread jump link.

### `/talks`

- **Context:** DM only
- **Arguments:** none
- **Result:** bot lists recent talks as thread jump links with participant names.

### Guild

### `/voice join`

- **Context:** guild only
- **Arguments:**
  - `agent?: str`
  - `text_channel?: discord.TextChannel`
- **Result:** ensures a Discord voice bridge in `voip_service` for the caller’s current voice channel.

### `/voice leave`

- **Context:** guild only
- **Arguments:** none
- **Result:** stops the active voice bridge for the guild.

### `/voice status`

- **Context:** guild only
- **Arguments:** none
- **Result:** returns current bridge id/agent/channel if active.

---

## Talk Threads (Inbound/Outbound)

### Inbound

- **Type:** `discord.Message`
- **Location:** `discord.Thread` (private thread under `#bibliotalk`)
- **Author:** non-bot user
- **Content:** raw message text
  - Override routing by prefixing with `@slug` (e.g. `@alan-watts …`).

### Outbound

- **Type:** Discord message posted into the same thread
- **Persona:** sent as a webhook message (preferred) with a character name, falling back to a bot message prefixed with `**Character Name**:`
- **Constraints:**
  - ≤ 2,000 characters per Discord message
  - Long responses are split at sentence boundaries
  - Grounding links are inline markdown links: `[visible text]({BIBLIOTALK_WEB_URL}/memories/{id})`
  - No citation indices and no trailing `Sources:` blocks

---

## Voice Gateway Proxy Messages (`discord_service` ⇄ `voip_service`)

Internal websocket: `ws /v1/discord/gateway/ws?bridge_id=...`

### Discord service → voip service

- `gateway.voice_state_update` with raw dispatch payload in `payload.d`
- `gateway.voice_server_update` with raw dispatch payload in `payload.d`

### voip service → Discord service

- `gateway.request_change_voice_state`
  - payload: `{ guild_id, channel_id|null, self_mute, self_deaf }`
- `discord.transcription.input`
  - payload: `{ text, bridge_id, guild_id, voice_channel_id, text_channel_id?, text_thread_id?, agent_id }`
- `discord.transcription.output`
  - payload: same shape as input transcription

## Voice Transcript Messages (Discord Artifacts)

Voice sessions produce durable text artifacts in Discord (a channel or thread) derived from Gemini Live transcripts.

- Input transcripts are posted as plain text.
- Output transcripts are posted as plain text.
- After each transcript message is finalized, citations (if any) are appended as footnotes to that transcript message.
- Citations are derived from Gemini Live tool-calling outputs; citations are not transported over the Live Session WS.

---

## Feed Publisher Boundary Models (Pydantic)

These models are defined in `services/discord_service/src/bot/message_models.py`.

### `FeedParentMessage`

- One parent feed message per ingested source.
- Fields: `agent_id`, `source_id`, `channel_id`, `text`

### `FeedBatchMessage`

- One transcript batch message posted inside a per-video thread.
- Fields: `agent_id`, `source_id`, `batch_id`, `thread_id`, `text`, `seq_label`
