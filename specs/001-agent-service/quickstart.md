# Quickstart: Agent Service

**Feature**: `001-agent-service`
**Created**: 2026-02-28
**Last Updated**: 2026-03-06
**Prereqs**: Python 3.11+, Node.js 20+ (for `voice_call_service`)

This quickstart offers two paths:

- **A) One-shot local E2E setup**: run a single script to prepare everything.
- **B) Fast dev loop**: CLI harness for grounding + citations (no Synapse).
- **C) Local E2E (“chat with ghosts”)**: Synapse + Element Web + SQLite + `agents_service` + EverMemOS.

## 1) One-Shot Local E2E (recommended)

From the repo root:

```bash
chmod +x deploy/local/bin/*.sh
deploy/local/bin/setup-all.sh
```

This script is **idempotent-ish** and will:

- set up `.env` (if missing),
- install Python deps for `agents_service` and `ingestion_service` via `uv`,
- start local Docker infra (Synapse + Element Web),
- generate + enable the Synapse appservice,
- create the Synapse admin user (if needed),
- seed Ghost agents into SQLite,
- run the local ingestion manifest into EverMemOS,
- import the resulting segment cache into SQLite, and
- provision Matrix rooms/permissions + run a smoke test.

When it completes, start `agents_service` in a separate terminal:

```bash
uv run --package agents_service uvicorn agents_service.server:app --host 0.0.0.0 --port 8009
```

Then open Element Web at `http://localhost:8080`, log in as `MATRIX_ADMIN_USER`, and chat with a Ghost (e.g. Confucius).

## 1) Configure Environment

From the repo root:

```bash
cp .env.example .env
# edit .env (SQLite DB, EMOS, Matrix, etc.)
```

If you want to use Gemini via Google ADK for text generation, set:

```bash
export GOOGLE_API_KEY="..."
```

## 3) Install Python deps (workspace)

```bash
UV_CACHE_DIR=/tmp/uv-cache uv sync --all-packages --all-extras
```

## 4A) Fast dev loop: Quick Test (CLI harness)

Run from the repo root so `.env` is discovered:

```bash
uv run --package agents_service -m agents_service --agent confucius --mock-emos
```

To exercise Gemini (requires `GOOGLE_API_KEY`):

```bash
uv run --package agents_service -m agents_service --agent confucius --mock-emos --model gemini-2.5-flash
```

## 4B) Local E2E: Synapse + Element Web + SQLite

1. Generate Synapse config + appservice registration (idempotent):

```bash
chmod +x deploy/local/bin/*.sh
deploy/local/bin/setup-appservice.sh
```

2. Start infrastructure (Synapse + Element Web):

```bash
docker compose -f deploy/local/docker-compose.yml up -d
```

3. Create a Synapse admin user (first run only):

```bash
docker compose -f deploy/local/docker-compose.yml exec synapse \
  register_new_matrix_user -c /data/homeserver.yaml http://localhost:8008 \
  -u "$MATRIX_ADMIN_USER" -p "$MATRIX_ADMIN_PASSWORD" -a
```

4. Start `agents_service`:

```bash
uv run --package agents_service uvicorn agents_service.server:app --host 0.0.0.0 --port 8009
```

5. Seed Ghosts in SQLite:

```bash
uv run --package agents_service -m agents_service.bootstrap seed-ghosts
```

6. Replay ingestion (build canonical segments + memorize into EverMemOS):

```bash
uv run --package ingestion_service -m ingestion_service ingest manifest --path "$(pwd)/deploy/local/ingest/manifest.yaml"
```

7. Import `.ingestion_service/segment_cache/*.jsonl` into SQLite:

```bash
uv run --package agents_service -m agents_service.bootstrap import-segment-cache --cache-dir .ingestion_service/segment_cache
```

8. Provision Matrix Space + rooms + profile-room permissions:

```bash
uv run --package agents_service -m agents_service.bootstrap provision-matrix
uv run --package agents_service -m agents_service.bootstrap post-profile-timeline
uv run --package agents_service -m agents_service.bootstrap smoke-test
```

9. Chat:
- open Element Web (`http://localhost:8080`)
- login as `MATRIX_ADMIN_USER`
- open “DM — Confucius”, send a message, and verify a cited reply.

## 4) Run Tests

`agents_service` tests:

```bash
uv --directory services/agents_service run --package agents_service -m pytest
```

`bt_common` tests (EverMemOS wrapper + infra):

```bash
uv --directory packages/bt_common run --package bt_common -m pytest
```

## 5) Start agents_service (Litestar)

```bash
uv run --package agents_service uvicorn agents_service.server:app --host 0.0.0.0 --port 8009
```

## 6) Start voice_call_service (Node sidecar)

```bash
cd services/voice_call_service
npm install
npm start
```

## Repository Map (authoritative)

- `format_ghost_response`: `services/agents_service/src/matrix/appservice.py`
- Agent runtime/tools: `services/agents_service/src/agent/`
- Citation/segment models: `services/agents_service/src/models/`
- EverMemOS wrapper + config/logging/exceptions: `packages/bt_common/src/`
