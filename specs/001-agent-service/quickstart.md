# Quickstart: Agent Service

**Feature**: `001-agent-service`  
**Created**: 2026-02-28  
**Last Updated**: 2026-03-02  
**Prereqs**: Python 3.11+, Node.js 20+ (for `voice_call_service`)

This quickstart focuses on the fastest path to validate the Ghost grounding + citation loop without requiring a Synapse deployment.

## 1) Configure Environment

From the repo root:

```bash
cp .env.example .env
# edit .env (SUPABASE_*, EMOS_*, MATRIX_*, etc.)
```

## 2) Install Python deps (agents_service)

```bash
cd services/agents_service
UV_CACHE_DIR=/tmp/uv-cache uv sync --extra dev
source .venv/bin/activate
```

## 3) Quick Test (CLI harness)

Run from the repo root so `.env` is discovered:

```bash
cd ../..
python -m agents_service --agent confucius --mock-emos
```

## 4) Run Tests

`agents_service` tests:

```bash
cd services/agents_service
python -m pytest
```

`bt_common` tests (EverMemOS wrapper + infra):

```bash
cd packages/bt_common
UV_CACHE_DIR=/tmp/uv-cache uv sync --extra dev
python -m pytest
```

## 5) Start agents_service (FastAPI)

```bash
cd ../..
uvicorn agents_service.server:app --host 0.0.0.0 --port 8009
```

Note: `agents_service.server` currently uses a stub `send_message` implementation; use the CLI harness for end-to-end behavior until Matrix sending is wired up.

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
