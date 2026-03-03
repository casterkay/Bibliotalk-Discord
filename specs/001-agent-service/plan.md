# Implementation Plan: Agent Service

**Feature**: `001-agent-service` | **Date**: 2026-03-03 | **Spec**: [spec.md](./spec.md)  
**Input**: `BLUEPRINT.md` + the design docs in `specs/001-agent-service/`

## Summary

Implement `agents_service`, the Matrix appservice + runtime that powers Ghosts (AI digital twins) with EverMemOS-grounded responses and verifiable citations (**言必有據**). The service also owns multi-agent discussion orchestration (floor control) and coordinates with `voice_call_service` for MatrixRTC voice sessions.

This repository contains an end-to-end text chat loop (Matrix appservice → retrieval → LLM composition → citations → Matrix response). The agent runtime is now wired to **Google ADK** for Gemini-backed text generation (see `services/agents_service/src/agent/providers/gemini.py`). Future work should extend ADK usage to richer tool-calling orchestration, additional providers (Bedrock Nova), and the planned multi-agent floor-control flows, while preserving the tool contracts (`memory_search`, `emit_citations`) and citation validation rules.

## Conflicts / Decisions (Read First)

This plan is sourced from `BLUEPRINT.md`, but it includes **local-dev** decisions that intentionally diverge from the blueprint’s proposed Supabase setup.

### C0: Supabase Postgres (blueprint) vs PocketBase (local dev)

- `BLUEPRINT.md` specifies **Supabase Postgres** tables for `agents`, `segments`, `profile_rooms`, `chat_history`, etc.
- This plan updates the local end-to-end flow to use **PocketBase** as a localhost backend replacing Supabase for dev.

**Resolution**:
- Treat the blueprint schema as the **logical data model**.
- Implement a DB abstraction in `agents_service` with a **PocketBase implementation** for local dev.
- Keep a path open for a future Supabase/Postgres implementation (or migration), but it is not required for the “let me chat with ghosts” local E2E goal.

### C1: EverMemOS is not a canonical segment store

EverMemOS search returns `group_id` and summaries, but it is **not** a reliable store to fetch canonical verbatim segment text for citation verification. Therefore, a separate canonical store is required for:
- Quote verification (citations must be substrings of canonical segments)
- Profile-room timeline posting (verbatim segments)

**Resolution**:
- Canonical segments live in PocketBase (`sources` / `segments` collections).
- Populate PocketBase by replaying ingestion outputs (see “Ingestion Replay → PocketBase Import”).

### C2: Local Matrix server_name

The local E2E flow uses `server_name=localhost` (so Matrix IDs are `@alice:localhost`). This is not a production posture; it is a dev convenience.

## Technical Context

**Languages**: Python 3.11+ (`services/agents_service`, `packages/bt_common`); Node.js 20+ (`services/voice_call_service`)  
**Key deps (current)**:
- Python: `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `httpx`, `evermemos`
- Node: `matrix-js-sdk`, `ws`
**Key deps (target, per blueprint)**: Google ADK, Gemini APIs, AWS Bedrock (Nova Lite v2 / Nova Sonic)

**Storage (local dev)**: PocketBase (agents, sources/segments, profile_rooms, chat_history), EverMemOS (retrieval + memory metadata)  
**Storage (blueprint target)**: Supabase Postgres (logical equivalent of the PocketBase collections), EverMemOS (memory)  
**Performance goals**: <5s text response latency; <3s voice response latency  
**Constraints**: unencrypted voice for MVP; single homeserver; appservice reserves `@bt_*` namespace; Ghosts never respond in profile rooms

## Constitution Check

*GATE: Must pass before major implementation changes. Re-check after each milestone.*

| Principle                        | Gate                                                                | Status |
| -------------------------------- | ------------------------------------------------------------------- | ------ |
| I. Design-First Architecture     | `spec.md` + `plan.md` exist before deeper build-out                 | PASS   |
| II. Test-Driven Quality          | Unit tests cover core business logic; contract tests cover EMOS edge | PASS   |
| III. Contract-Driven Integration | Explicit contracts for EMOS, citations, floor control, voice backend | PASS   |
| IV. Incremental Delivery         | US1 before US2 before US3 before US4                                | PASS   |
| V. Observable Systems            | Structured logs + correlation IDs at service entry points           | PASS   |
| VI. Principled Simplicity        | CLI-first harness for rapid iteration                               | PASS   |

## Repository Ownership (authoritative)

From `BLUEPRINT.md` and the current tree:
- `format_ghost_response` owner: `services/agents_service/src/matrix/appservice.py`
- Citation + segment domain models: `services/agents_service/src/models/`
- Agent runtime + tools: `services/agents_service/src/agent/`
- Infra-only shared lib (EMOS client, config, logging, exceptions): `packages/bt_common/src/`

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-service/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── emos-client.md
│   ├── citation-schema.md
│   ├── voice-backend.md
│   └── discussion-floor-control.md
└── tasks.md
```

### Source Code (repository root)

```text
packages/bt_common/src/
├── __init__.py
├── config.py                     # pydantic-settings + .env loading
├── logging.py                    # JSON logging + correlation IDs
├── exceptions.py                 # shared exception types
└── evermemos_client.py           # EverMemOS SDK wrapper + retry/error mapping

services/agents_service/src/
├── __init__.py
├── __main__.py                   # CLI harness (`python -m agents_service ...`)
├── server.py                     # FastAPI appservice transaction endpoint
├── agent/
│   ├── agent_factory.py          # Ghost agent creation + caching
│   ├── orchestrator.py           # (current) simple multi-ghost orchestration
│   ├── providers/                # LLM backends (Gemini/Nova)
│   └── tools/
│       ├── memory_search.py      # EMOS search + local rerank → Evidence
│       └── emit_citations.py     # Evidence → validated citations
├── database/
│   ├── store.py                  # DB interface (logical model from BLUEPRINT.md)
│   ├── pocketbase_store.py       # local-dev backend (canonical for E2E chat)
│   └── supabase_helpers.py       # legacy/compat (kept until removed)
├── matrix/
│   ├── appservice.py             # event handling + `format_ghost_response`
│   └── guards.py                 # per-room rate limiter
├── models/
│   ├── citation.py
│   └── segment.py
└── voice/
    ├── session_manager.py
    ├── transcript.py
    └── backends/
        ├── base.py
        ├── nova_sonic.py
        └── gemini_live.py

services/voice_call_service/src/
├── index.js
├── matrixrtc.js
├── audio_bridge.js
└── mixer.js
```

### Tests

```text
packages/bt_common/tests/
services/agents_service/tests/
```

## Phased Delivery (maps to spec priorities)

- **P1 (US1)**: Private text chat with a Ghost, grounded in EverMemOS with verifiable citations.
- **P2 (US2)**: Multi-agent text discussion with floor control (one speaker at a time; user preemption).
- **P3 (US3)**: Voice calls (MatrixRTC sidecar + voice backend tool-use + transcript + citations).
- **P4 (US4)**: Multi-agent voice discussions (floor-gated audio, barge-in, transcript + citations).

---

## Local End-to-End Flow (Synapse + Element Web + agents_service + PocketBase + EverMemOS)

### Single Goal

“Let me chat with ghosts” end-to-end:
- Create a Bibliotalk Space
- Create Ghost profile rooms (read-only to humans)
- Create DMs to Ghosts and get replies
- Create a group room; Ghosts respond only when mentioned
- Populate profile rooms with an “EMOS memory timeline” thread from canonical segments

### Local Topology

| Component | Runtime | URL / Port | Notes |
| --- | --- | --- | --- |
| Synapse homeserver | Docker | `http://localhost:8008` | Matrix Client-Server API |
| Element Web | Docker | `http://localhost:8080` | Local dev UI |
| PocketBase | Docker | `http://localhost:8090` | Canonical local data store (PocketBase v0.36.5) |
| agents_service | Host python | `http://localhost:8009` | Matrix appservice + agent runtime |
| EverMemOS | external/local | `EMOS_BASE_URL` | Retrieval; must already be reachable |

### Environment Variables (local dev)

At minimum, `.env` must include:

```bash
# Matrix / Synapse
MATRIX_HOMESERVER_URL="http://localhost:8008"
MATRIX_AS_TOKEN="..."    # appservice token (used by agents_service to send as Ghosts)
MATRIX_HS_TOKEN="..."    # synapse → agents_service auth token (hs_token)

# Synapse admin (for scripted provisioning)
MATRIX_SERVER_NAME="localhost"
MATRIX_ADMIN_USER="bt_admin"
MATRIX_ADMIN_PASSWORD="..."

# PocketBase (local canonical store)
POCKETBASE_URL="http://localhost:8090"
POCKETBASE_SUPERUSER_EMAIL="admin@bibliotalk.local"
POCKETBASE_SUPERUSER_PASSWORD="..."

# EverMemOS (retrieval + memorize during ingestion replay)
EMOS_BASE_URL="http://localhost:1995"
EMOS_API_KEY=""

# LLM
GOOGLE_API_KEY="..."
```

### Required agent_service Appservice Endpoints

To support Synapse appservice user resolution and reliable virtual user handling:
- `PUT`/`POST` `/_matrix/app/v1/transactions/{txn_id}` (already implemented)
- `GET` `/_matrix/app/v1/users/{userId}` (**implemented**)
  - Auth via `hs_token`
  - Return 200 only for `@bt_...:localhost` users that exist in PocketBase `agents`

### DB Design: PocketBase Collections (logical equivalents of BLUEPRINT tables)

PocketBase replaces Supabase for local dev. Collections mirror the blueprint tables closely:

- `agents`: Ghost identity + persona + model selection
- `agent_emos_config`: per-Ghost EMOS base URL + API key + `tenant_prefix`
- `profile_rooms`: agent_uuid ↔ matrix_room_id
- `sources`: canonical source metadata keyed by `emos_group_id`
- `segments`: canonical verbatim segments keyed by `emos_message_id` (citation verification)
- `chat_history`: audit trail for Matrix messages + citations

**Deterministic IDs (idempotent imports)**:
- `agent_uuid`: derived from slug (e.g., `confucius`, `alan_watts`)
- `source_uuid`: derived from `emos_group_id`
- `segment_uuid`: derived from `emos_message_id`

#### PocketBase collection field sketch (must be encoded in migrations)

`agents`
- `uuid` (text, unique; app-level stable ID)
- `kind` (text; `figure|user`)
- `display_name` (text)
- `matrix_user_id` (text, unique; `@bt_ghost_confucius:localhost`)
- `persona_prompt` (text)
- `llm_model` (text; default `gemini-2.5-flash`)
- `is_active` (bool; default true)

`agent_emos_config`
- `agent_uuid` (text, unique)
- `tenant_prefix` (text, unique; `confucius`, `alan_watts`)
- `emos_base_url` (text)
- `emos_api_key_encrypted` (text, optional; unused for now)

`profile_rooms`
- `agent_uuid` (text, unique)
- `matrix_room_id` (text, unique)

`sources`
- `uuid` (text, unique)
- `agent_uuid` (text)
- `platform` (text)
- `external_id` (text)
- `external_url` (text, optional)
- `title` (text)
- `raw_meta` (json/text)
- `emos_group_id` (text, unique)

`segments`
- `uuid` (text, unique)
- `source_uuid` (text)
- `agent_uuid` (text)
- `platform` (text)
- `seq` (number)
- `text` (text)
- `sha256` (text)
- `emos_message_id` (text, unique)
- `speaker` (text, optional)
- `start_ms` (number, optional)
- `end_ms` (number, optional)
- `matrix_event_id` (text, optional)

`chat_history`
- `uuid` (text, unique)
- `matrix_room_id` (text)
- `sender_agent_uuid` (text, optional)
- `sender_matrix_user_id` (text)
- `matrix_event_id` (text, optional)
- `modality` (text; `text|voice`)
- `content` (text)
- `citations` (json/text)

### Ingestion Replay → PocketBase Import (required for citations + profile timeline)

EverMemOS cannot reliably provide canonical segment text on demand, so the canonical segments must be imported into PocketBase.

**Workflow**:
1. Run `ingestion_service` with `user_id = tenant_prefix` (e.g. `confucius`) so that EMOS `group_id` / `message_id` match the ID convention used by retrieval.
2. `ingestion_service` writes JSONL cache lines to `.ingestion_service/segment_cache/{user_id}.jsonl`.
3. `agents_service` imports this cache into PocketBase (`sources` + `segments`).

#### Initial demo dataset (deterministic, rerunnable)

- Confucius: Gutenberg `3330` and `24055`
- Alan Watts: exactly one YouTube video (operator-provided `video_id`)

The ingestion manifest must use:
- `defaults.user_id: confucius` for Confucius sources
- `defaults.user_id: alan_watts` for Alan Watts sources

### Matrix Provisioning (scripted, idempotent)

Add a single bootstrap CLI that:
- Creates/updates Ghost records in PocketBase
- Ensures Ghost Matrix accounts exist (Synapse admin API)
- Creates Bibliotalk Space + rooms (profile rooms, DMs, group room)
- Invites Ghosts to DMs + group room (Ghost joins via appservice)
- Sets profile-room power levels so humans cannot send messages
- Posts profile-room “timeline” threads from canonical segments in PocketBase
- Smoke-tests DM response + citations

### Repo Additions (deployment assets)

Add:
- `deploy/local/docker-compose.yml`
  - Synapse, Element Web, PocketBase services
- `deploy/local/synapse/`
  - generate/config scripts
  - appservice registration YAML generation
- `deploy/local/pocketbase/`
  - `pb_migrations/` checked into repo (deterministic schema)
  - persistent `pb_data/` gitignored
- `services/agents_service/src/bootstrap.py`
  - the provisioning CLI described above

### Runbook (local dev)

The intended “happy path” commands (exact scripts/CLIs to be implemented under this plan):

1. Start infrastructure:
   - `docker compose -f deploy/local/docker-compose.yml up -d`
   - generate + enable the Synapse appservice:
     - `deploy/local/bin/generate-appservice.sh`
     - `(cd deploy/local && ./bin/enable-appservice.sh)`
     - `docker compose -f deploy/local/docker-compose.yml restart synapse`
2. Start `agents_service`:
   - `uvicorn agents_service.server:app --host 0.0.0.0 --port 8009`
3. Seed Ghosts in PocketBase:
   - `python -m agents_service.bootstrap seed-ghosts`
4. Replay ingestion:
   - `python -m ingestion_service ingest manifest --path "$(pwd)/deploy/local/ingest/manifest.yaml"`
5. Import canonical segments to PocketBase:
   - `python -m agents_service.bootstrap import-segment-cache --cache-dir .ingestion_service/segment_cache`
6. Provision Matrix Space + rooms:
   - `python -m agents_service.bootstrap provision-matrix`
7. Post profile timelines:
   - `python -m agents_service.bootstrap post-profile-timeline`
8. Validate:
   - `python -m agents_service.bootstrap smoke-test`
9. Chat:
   - open `http://localhost:8080` (Element Web), login, DM a Ghost

## Complexity Tracking

| Decision | Why it exists | Alternative rejected |
| --- | --- | --- |
| Node.js voice sidecar | MatrixRTC/WebRTC media handling is a separate runtime concern | A pure-Python stack still needs WebRTC media plumbing |
| VoiceBackend abstraction | Swap Nova Sonic ↔ Gemini Live without changing orchestration | Backend-specific logic would sprawl across the session manager |
| Domain models in `agents_service` | Keeps agent-domain ownership out of infra package (`bt_common`) | Putting agent models in `bt_common` breaks repository boundaries |

## Proposed Improvements (Non-Blocking)

- Wire `services/voice_call_service/package.json` to run `src/index.js` via `npm start`.
- Make `.env` discovery robust (support repo-root `.env` even when running from service directories).
- Add a dedicated Matrix event contract doc (appservice transactions + message send payloads).
- Implement the `BLUEPRINT.md` retrieval narrowing: EverMemOS `group_id` → `sources/segments` before reranking.
- Add a first-class “local E2E” developer flow (`deploy/local/*` + `agents_service.bootstrap`) that provisions Synapse + Element Web + PocketBase and seeds a working set of Ghosts + sources.
