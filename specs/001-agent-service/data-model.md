# Data Model: Agent Service

**Feature**: `001-agent-service`  
**Created**: 2026-02-28  
**Last Updated**: 2026-03-02  
**Source**: `BLUEPRINT.md` sections 2–4 and 9

This document summarizes the database entities `agents_service` reads/writes for Ghost chat, citations, and (eventually) discussion/voice transcripts.

## Core Tables

### agents

Ghost identity + runtime config.

| Field          | Type      | Notes |
| -------------- | --------- | ----- |
| id             | uuid      | PK |
| kind           | text      | `'figure' \| 'user'` |
| display_name   | text      | e.g. `"Confucius (Ghost)"` |
| matrix_user_id | text      | Matrix virtual user, unique |
| persona_prompt | text      | Ghost system/persona prompt |
| llm_model      | text      | e.g. `"gemini-2.5-flash"` |
| is_active      | boolean   | disables responses when false |
| created_at     | timestamptz | |

### agent_emos_config

Per-agent EverMemOS connection details.

| Field                  | Type | Notes |
| ---------------------- | ---- | ----- |
| agent_id               | uuid | PK/FK → `agents.id` |
| emos_base_url          | text | base URL for EverMemOS |
| emos_api_key_encrypted | text | nullable; platform instances may use service auth |
| tenant_prefix          | text | EverMemOS user/sender ID (often the agent UUID for figures) |

### users

Real user accounts on the Matrix homeserver, optionally linked to a Ghost.

| Field          | Type | Notes |
| -------------- | ---- | ----- |
| id             | uuid | PK |
| matrix_user_id | text | unique |
| display_name   | text | |
| agent_id       | uuid | nullable FK → `agents.id` (their Ghost) |
| created_at     | timestamptz | |

### profile_rooms

Public “profile rooms” for figure content. Ghosts never respond here.

| Field         | Type | Notes |
| ------------- | ---- | ----- |
| agent_id      | uuid | PK/FK → `agents.id` |
| matrix_room_id| text | unique |
| created_at    | timestamptz | |

## Ingestion-Backed Tables (Read by `agents_service` for citations)

These are populated by ingestion workflows and used by `agents_service` for grounding/citation validation.

### sources

Upstream content items (episodes, books, videos) per Ghost.

| Field         | Type  | Notes |
| ------------- | ----- | ----- |
| id            | uuid  | PK |
| agent_id      | uuid  | FK → `agents.id` |
| platform      | text  | `'podwise' \| 'gutenberg' \| 'youtube'` |
| external_id   | text  | platform-specific |
| external_url  | text  | canonical URL |
| title         | text  | |
| raw_meta      | jsonb | platform metadata |
| emos_group_id | text  | unique; `{agent_id}:{platform}:{external_id}` |
| created_at    | timestamptz | |

### segments

Canonical verbatim chunks used for memorize, profile-room posting, and citation validation.

| Field           | Type  | Notes |
| --------------- | ----- | ----- |
| id              | uuid  | PK |
| source_id       | uuid  | FK → `sources.id` |
| agent_id        | uuid  | FK → `agents.id` (denormalized) |
| platform        | text  | denormalized from source |
| seq             | int   | chunk index within source |
| text            | text  | verbatim canonical text |
| speaker         | text  | nullable (transcripts) |
| start_ms        | int   | nullable |
| end_ms          | int   | nullable |
| sha256          | text  | dedup |
| emos_message_id | text  | unique; `{agent_id}:{platform}:{external_id}:seg:{seq}` |
| matrix_event_id | text  | nullable (profile-room post event id) |
| created_at      | timestamptz | |

## Conversation / Audit

### chat_history

Audit trail for text chat and voice transcripts.

| Field                 | Type  | Notes |
| --------------------- | ----- | ----- |
| id                    | uuid  | PK |
| matrix_room_id        | text  | |
| sender_agent_id       | uuid  | nullable; null for real-user messages |
| sender_matrix_user_id | text  | |
| matrix_event_id       | text  | nullable; null for voice turns |
| modality              | text  | `'text' \| 'voice'` |
| content               | text  | message body or transcript |
| citations             | jsonb | array of Citation objects |
| created_at            | timestamptz | |

## Citation Object (embedded)

Citation objects are:
- embedded into Matrix events under `com.bibliotalk.citations`
- persisted in `chat_history.citations`

| Field           | Type | Description |
| --------------- | ---- | ----------- |
| index           | int  | citation marker number |
| segment_id      | uuid | referenced `segments.id` |
| emos_message_id | text | referenced `segments.emos_message_id` |
| source_title    | text | display title |
| source_url      | text | canonical URL (YouTube may include timestamp deep link) |
| quote           | text | verbatim substring of `segments.text` |
| platform        | text | `'podwise' \| 'gutenberg' \| 'youtube'` |
| timestamp       | string/date-time (optional) | publish date, if available |

## Relationships

```text
agents 1──1 agent_emos_config
users  N──1 agents            (optional: link user → their Ghost)
agents 1──1 profile_rooms     (figures)
agents 1──N sources
sources 1──N segments
agents 1──N chat_history
```

## EverMemOS Stable IDs

Per `BLUEPRINT.md`:

```text
sender     = "{agent_id}" (figures) or agent_emos_config.tenant_prefix (users)
group_id   = "{agent_id}:{platform}:{external_id}"
message_id = "{agent_id}:{platform}:{external_id}:seg:{seq}"
```

**Retrieval mapping**: EverMemOS search returns memories containing `group_id`. Map `group_id` → `sources.emos_group_id` → candidate `segments`, then locally rerank within those segments to produce citation-friendly verbatim evidence.
