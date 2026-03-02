# Data Model: Agent Service

**Feature**: 001-agent-service
**Date**: 2026-02-28
**Source**: BLUEPRINT.md sections 3, 4, 9

## Entities

### Agent

The core entity representing a Ghost (AI digital twin).

| Field          | Type      | Constraints                          | Description                           |
| -------------- | --------- | ------------------------------------ | ------------------------------------- |
| id             | UUID      | PK, auto-generated                   | Unique identifier                     |
| kind           | text      | CHECK ('figure', 'user')             | Figure Ghost or user Ghost            |
| display_name   | text      | NOT NULL                             | "Confucius (Ghost)"                   |
| matrix_user_id | text      | NOT NULL, UNIQUE                     | "@btghost_confucius:bibliotalk.space" |
| avatar_url     | text      | NULLABLE                             | Avatar image URL                      |
| bio            | text      | NULLABLE                             | Short biography                       |
| persona_prompt | text      | NOT NULL                             | System prompt for this Ghost          |
| llm_model      | text      | NOT NULL, DEFAULT 'gemini-2.5-flash' | LLM backend identifier                |
| is_active      | boolean   | NOT NULL, DEFAULT true               | Whether Ghost responds to messages    |
| created_at     | timestamp | NOT NULL, DEFAULT now()              | Creation time                         |

### AgentEmosConfig

Memory service connection for each agent.

| Field                  | Type | Constraints         | Description                           |
| ---------------------- | ---- | ------------------- | ------------------------------------- |
| agent_id               | UUID | PK, FK → agents(id) | One config per agent                  |
| emos_base_url          | text | NOT NULL            | EMOS API base URL                     |
| emos_api_key_encrypted | text | NULLABLE            | Encrypted API key (null for platform) |
| tenant_prefix          | text | NOT NULL            | EMOS user/sender ID for this agent    |

### Source

Upstream content items (episodes, books, videos) ingested for an agent.

| Field         | Type      | Constraints                                       | Description                      |
| ------------- | --------- | ------------------------------------------------- | -------------------------------- |
| id            | UUID      | PK, auto-generated                                | Unique identifier                |
| agent_id      | UUID      | NOT NULL, FK → agents(id)                         | Owner agent                      |
| platform      | text      | NOT NULL, CHECK ('podwise','gutenberg','youtube') | Content platform                 |
| external_id   | text      | NOT NULL                                          | Platform-specific ID             |
| external_url  | text      | NULLABLE                                          | Canonical URL                    |
| title         | text      | NOT NULL                                          | Content title                    |
| author        | text      | NULLABLE                                          | Author/creator                   |
| published_at  | timestamp | NULLABLE                                          | Original publication date        |
| raw_meta      | JSONB     | NULLABLE                                          | Platform-specific metadata       |
| emos_group_id | text      | NOT NULL, UNIQUE                                  | "{agent_id}:{platform}:{ext_id}" |
| created_at    | timestamp | NOT NULL, DEFAULT now()                           | Creation time                    |

**Unique**: (platform, external_id)

### Segment

Canonical chunks of source content. Used for EMOS memorize, profile
room posts, and citation validation.

| Field           | Type      | Constraints                | Description                                |
| --------------- | --------- | -------------------------- | ------------------------------------------ |
| id              | UUID      | PK, auto-generated         | Unique identifier                          |
| source_id       | UUID      | NOT NULL, FK → sources(id) | Parent source                              |
| agent_id        | UUID      | NOT NULL, FK → agents(id)  | Owner agent (denormalized)                 |
| platform        | text      | NOT NULL                   | Denormalized from source                   |
| seq             | int       | NOT NULL                   | Chunk index within source                  |
| text            | text      | NOT NULL                   | Verbatim chunk text                        |
| speaker         | text      | NULLABLE                   | Speaker label (conversations)              |
| start_ms        | int       | NULLABLE                   | Start timecode in milliseconds             |
| end_ms          | int       | NULLABLE                   | End timecode in milliseconds               |
| sha256          | text      | NOT NULL                   | Content hash for dedup                     |
| emos_message_id | text      | NOT NULL, UNIQUE           | "{agent_id}:{platform}:{ext_id}:seg:{seq}" |
| matrix_event_id | text      | NULLABLE                   | Profile room post event ID                 |
| created_at      | timestamp | NOT NULL, DEFAULT now()    | Creation time                              |

**Unique**: (source_id, seq)

### ChatHistory

Conversation records for audit and future memorization.

| Field                 | Type      | Constraints                                      | Description                      |
| --------------------- | --------- | ------------------------------------------------ | -------------------------------- |
| id                    | UUID      | PK, auto-generated                               | Unique identifier                |
| matrix_room_id        | text      | NOT NULL                                         | Room where conversation occurred |
| sender_agent_id       | UUID      | NULLABLE, FK → agents(id)                        | Null if sent by real user        |
| sender_matrix_user_id | text      | NOT NULL                                         | Matrix user ID of sender         |
| matrix_event_id       | text      | NULLABLE                                         | Null for voice turns             |
| modality              | text      | NOT NULL, DEFAULT 'text', CHECK ('text','voice') | Message modality                 |
| content               | text      | NOT NULL                                         | Text message or voice transcript |
| citations             | JSONB     | NOT NULL, DEFAULT '[]'                           | Structured citation objects      |
| created_at            | timestamp | NOT NULL, DEFAULT now()                          | Creation time                    |

### Citation (embedded in ChatHistory.citations and Matrix events)

| Field           | Type | Description                              |
| --------------- | ---- | ---------------------------------------- |
| index           | int  | Superscript number in response text      |
| segment_id      | UUID | FK → segments(id)                        |
| emos_message_id | text | Maps to segments.emos_message_id         |
| source_title    | text | Human-readable source title              |
| source_url      | text | Canonical URL (with timestamp for video) |
| quote           | text | Verbatim passage from segment.text       |
| platform        | text | 'podwise'                                | 'gutenberg' | 'youtube' |
| timestamp       | text | Publication date (ISO 8601)              |

## Relationships

```
agents 1──1 agent_emos_config     (each agent has one EMOS config)
agents 1──N sources               (each agent has many content sources)
sources 1──N segments             (each source has many segments)
agents 1──N segments              (denormalized: direct agent → segments)
agents 1──N chat_history          (each agent sends many messages)
```

## State Transitions

### Agent Lifecycle
```
Created (is_active=true) → Active → Deactivated (is_active=false)
```
Deactivated agents do not respond to messages but retain all data.

## EMOS ID Conventions

```
sender     = "{agent_id}"
group_id   = "{agent_id}:{platform}:{external_id}"
message_id = "{agent_id}:{platform}:{external_id}:seg:{seq}"
```

All IDs use the agent's Postgres UUID. Same `sender` across all
platforms so `GET /memories/search?user_id={agent_id}` returns all
memories regardless of source platform.
