# Bibliotalk Monorepo Structure

## Layout

- `AGENTS.md`
- `BLUEPRINT.md`
- `README.md`
- `ROSTER.md`
- `docs/`
  - `knowledge/` — reference material (EverMemOS API, ADK, Nova Sonic, etc.)
- `specs/`
  - `001-agent-service/`
  - `002-evermemos-content-ingest/`
- `services/` — deployable services (each has its own `pyproject.toml` or `package.json`)
  - `agents_service/` — Python package: `agents_service`
    - `pyproject.toml` — depends on `bt_common` (path dep → `../../packages/bt_common`)
    - `src/`
      - `__init__.py`
      - `main.py` — FastAPI / uvicorn entrypoint
      - `appservice.py` — Matrix appservice handler (mautrix)
      - `agent_factory.py` — ADK LlmAgent creation + persona builder
      - `guards.py` — rate limiter, room-type checks
      - `llm_registry.py` — ADK LLMRegistry + Nova Lite backend
      - `tools/`
        - `__init__.py`
        - `memory_search.py` — EMOS retrieve → evidence list
        - `emit_citations.py` — attach citations to Matrix response
      - `discussion/`
        - `__init__.py`
        - `orchestrator.py` — LoopAgent multi-Clone discussion
        - `a2a_server.py` — A2A server per Clone
      - `voice/`
        - `__init__.py`
        - `session_manager.py` — voice session lifecycle
        - `transcript.py` — voice transcript handling
        - `backends/`
          - `__init__.py`
          - `base.py` — VoiceBackend ABC
          - `nova_sonic.py` — AWS Nova Sonic via Bedrock
          - `gemini_live.py` — Gemini Multimodal Live API
    - `tests/`
      - `__init__.py`
      - `unit/`
        - `__init__.py`
        - `test_agent.py`
        - `test_guards.py`
      - `contract/`
        - `__init__.py`
        - `test_a2a_protocol.py`
      - `integration/`
        - `__init__.py`
        - `test_chat_e2e.py`
        - `test_discussion.py`
  - `ingestion_service/` — Python package: `ingestion_service`
    - `pyproject.toml` — standalone (no project deps)
    - `src/`
      - `__init__.py`
      - `__main__.py` — CLI entrypoint
      - `cli.py` — Typer CLI app
      - `config.py` — pydantic-settings config
      - `errors.py` — domain error hierarchy
      - `ids.py` — EMOS ID builders (group_id, message_id)
      - `models.py` — Source, Segment, Report pydantic models
      - `chunking.py` — text/transcript chunking logic
      - `ingest.py` — core ingest pipeline orchestration
      - `index.py` — SQLite idempotency index
      - `manifest.py` — YAML manifest loader + resolver
      - `reporting.py` — report generation + secret redaction
      - `evermemos_client.py` — standalone EMOS HTTP client
      - `adapters/`
        - `__init__.py`
        - `base.py` — source adapter ABC
        - `gutenberg.py` — Project Gutenberg text fetcher
        - `local_text.py` — local file loader
        - `youtube_transcript.py` — youtube-transcript-api wrapper
    - `tests/`
      - `__init__.py`
      - `unit/`
        - `__init__.py`
        - `test_chunking.py`
        - `test_ids.py`
        - `test_index.py`
        - `test_manifest.py`
        - `test_pipeline.py`
  - `voice_call_service/` — Node.js package: `voice_call_service`
    - `package.json`
    - `.npmignore`
    - `src/`
      - `index.js` — sidecar entrypoint
      - `matrixrtc.js` — MatrixRTC signaling + WebRTC
      - `audio_bridge.js` — WebSocket bridge to agents_service
      - `mixer.js` — multi-participant audio mixer
- `packages/` — reusable libraries (no service wiring)
  - `bt_common/` — Python package: `bt_common`
    - `pyproject.toml` — standalone shared library
    - `src/`
      - `__init__.py`
      - `citation.py` — Citation / Evidence models + validate_citations()
      - `segment.py` — Segment model + bm25_rerank()
      - `exceptions.py` — shared exception hierarchy
      - `config.py` — pydantic-settings (Settings, EMOSFallbackSettings)
      - `logging.py` — structured logging helpers
      - `emos_client.py` — async EMOS client (shared by agents_service)
      - `matrix_helpers.py` — Matrix message formatting
      - `supabase_helpers.py` — Supabase DB access patterns
    - `tests/`
      - `__init__.py`
      - `unit/`
        - `__init__.py`
        - `test_citation.py`
        - `test_segment.py`
        - `test_emos_client.py`
      - `contract/`
        - `__init__.py`
        - `test_emos_api.py`
        - `test_matrix_events.py`
      - `integration/`
        - `__init__.py`
        - `test_citation_roundtrip.py`
- `tools/` — developer utilities
  - `bt_cli/` — Python package: `bt_cli`
    - `pyproject.toml` — depends on `agents_service` + `bt_common`
    - `src/`
      - `__init__.py`
      - `__main__.py`

## Packaging

Each Python service/package uses `[tool.setuptools.package-dir]` to map `src/` to the package named after its folder. Example for `agents_service`:

```toml
[tool.setuptools.package-dir]
"agents_service" = "src"
```

This means `services/agents_service/src/main.py` is imported as `agents_service.main`. Internal imports within each package use relative imports (e.g. `from .tools.memory_search import ...`) and are unaffected by the move. Cross-package imports change to use the new package names (see Import Renames below).

## Import Renames

All cross-package imports must be updated to use the new package names:

| Old import | New import |
|---|---|
| `from bt_agent.* import ...` | `from agents_service.* import ...` |
| `from evermemos_ingest.* import ...` | `from ingestion_service.* import ...` |
| `from bt_common.* import ...` | `from bt_common.* import ...` (unchanged) |
| `from bt_cli.* import ...` | `from bt_cli.* import ...` (unchanged) |

## File Mappings (old → new)

### bt_agent → services/agents_service

| Old Path | New Path |
|---|---|
| `bt_agent/__init__.py` | `services/agents_service/src/__init__.py` |
| `bt_agent/main.py` | `services/agents_service/src/main.py` |
| `bt_agent/appservice.py` | `services/agents_service/src/appservice.py` |
| `bt_agent/agent_factory.py` | `services/agents_service/src/agent_factory.py` |
| `bt_agent/guards.py` | `services/agents_service/src/guards.py` |
| `bt_agent/llm_registry.py` | `services/agents_service/src/llm_registry.py` |
| `bt_agent/tools/` | `services/agents_service/src/tools/` |
| `bt_agent/discussion/` | `services/agents_service/src/discussion/` |
| `bt_agent/voice/` | `services/agents_service/src/voice/` |

### evermemos_ingest → services/ingestion_service

| Old Path | New Path |
|---|---|
| `evermemos_ingest/__init__.py` | `services/ingestion_service/src/__init__.py` |
| `evermemos_ingest/__main__.py` | `services/ingestion_service/src/__main__.py` |
| `evermemos_ingest/cli.py` | `services/ingestion_service/src/cli.py` |
| `evermemos_ingest/config.py` | `services/ingestion_service/src/config.py` |
| `evermemos_ingest/errors.py` | `services/ingestion_service/src/errors.py` |
| `evermemos_ingest/ids.py` | `services/ingestion_service/src/ids.py` |
| `evermemos_ingest/models.py` | `services/ingestion_service/src/models.py` |
| `evermemos_ingest/chunking.py` | `services/ingestion_service/src/chunking.py` |
| `evermemos_ingest/ingest.py` | `services/ingestion_service/src/ingest.py` |
| `evermemos_ingest/index.py` | `services/ingestion_service/src/index.py` |
| `evermemos_ingest/manifest.py` | `services/ingestion_service/src/manifest.py` |
| `evermemos_ingest/reporting.py` | `services/ingestion_service/src/reporting.py` |
| `evermemos_ingest/evermemos_client.py` | `services/ingestion_service/src/evermemos_client.py` |
| `evermemos_ingest/adapters/` | `services/ingestion_service/src/adapters/` |
| `evermemos_ingest/README.md` | `services/ingestion_service/README.md` |

### bt_voice_sidecar → services/voice_call_service

| Old Path | New Path |
|---|---|
| `bt_voice_sidecar/package.json` | `services/voice_call_service/package.json` |
| `bt_voice_sidecar/.npmignore` | `services/voice_call_service/.npmignore` |
| `bt_voice_sidecar/index.js` | `services/voice_call_service/src/index.js` |
| `bt_voice_sidecar/matrixrtc.js` | `services/voice_call_service/src/matrixrtc.js` |
| `bt_voice_sidecar/audio_bridge.js` | `services/voice_call_service/src/audio_bridge.js` |
| `bt_voice_sidecar/mixer.js` | `services/voice_call_service/src/mixer.js` |

### bt_common → packages/bt_common

| Old Path | New Path |
|---|---|
| `bt_common/__init__.py` | `packages/bt_common/src/__init__.py` |
| `bt_common/citation.py` | `packages/bt_common/src/citation.py` |
| `bt_common/segment.py` | `packages/bt_common/src/segment.py` |
| `bt_common/exceptions.py` | `packages/bt_common/src/exceptions.py` |
| `bt_common/config.py` | `packages/bt_common/src/config.py` |
| `bt_common/logging.py` | `packages/bt_common/src/logging.py` |
| `bt_common/emos_client.py` | `packages/bt_common/src/emos_client.py` |
| `bt_common/matrix_helpers.py` | `packages/bt_common/src/matrix_helpers.py` |
| `bt_common/supabase_helpers.py` | `packages/bt_common/src/supabase_helpers.py` |

### bt_cli → tools/bt_cli

| Old Path | New Path |
|---|---|
| `bt_cli/__init__.py` | `tools/bt_cli/src/__init__.py` |
| `bt_cli/__main__.py` | `tools/bt_cli/src/__main__.py` |

### Tests → distributed into service/package test dirs

| Old Path | New Path |
|---|---|
| `tests/unit/test_agent.py` | `services/agents_service/tests/unit/test_agent.py` |
| `tests/unit/test_guards.py` | `services/agents_service/tests/unit/test_guards.py` |
| `tests/contract/test_a2a_protocol.py` | `services/agents_service/tests/contract/test_a2a_protocol.py` |
| `tests/integration/test_chat_e2e.py` | `services/agents_service/tests/integration/test_chat_e2e.py` |
| `tests/integration/test_discussion.py` | `services/agents_service/tests/integration/test_discussion.py` |
| `tests/unit/test_evermemos_ingest_chunking.py` | `services/ingestion_service/tests/unit/test_chunking.py` |
| `tests/unit/test_evermemos_ingest_ids.py` | `services/ingestion_service/tests/unit/test_ids.py` |
| `tests/unit/test_evermemos_ingest_index.py` | `services/ingestion_service/tests/unit/test_index.py` |
| `tests/unit/test_evermemos_ingest_manifest.py` | `services/ingestion_service/tests/unit/test_manifest.py` |
| `tests/unit/test_evermemos_ingest_pipeline.py` | `services/ingestion_service/tests/unit/test_pipeline.py` |
| `tests/unit/test_citation.py` | `packages/bt_common/tests/unit/test_citation.py` |
| `tests/unit/test_segment.py` | `packages/bt_common/tests/unit/test_segment.py` |
| `tests/unit/test_emos_client.py` | `packages/bt_common/tests/unit/test_emos_client.py` |
| `tests/contract/test_emos_api.py` | `packages/bt_common/tests/contract/test_emos_api.py` |
| `tests/contract/test_matrix_events.py` | `packages/bt_common/tests/contract/test_matrix_events.py` |
| `tests/integration/test_citation_roundtrip.py` | `packages/bt_common/tests/integration/test_citation_roundtrip.py` |

### Removed

| Old Path | Reason |
|---|---|
| `pyproject.toml` (root) | Replaced by per-package pyproject.toml files |
| `uv.lock` (root) | Each package manages its own lock |
| `tests/` (root) | Distributed into service/package dirs |
| `scripts/restructure_services.sh` | Superseded by this restructuring |

## Dependency Graph

```
packages/bt_common          (standalone)
services/ingestion_service   (standalone)
services/voice_call_service  (standalone, Node.js)
services/agents_service      → packages/bt_common
tools/bt_cli                 → services/agents_service, packages/bt_common
```

Services never depend on each other. Shared Python code lives in `packages/bt_common`.
The ingestion service has its own EMOS client and is fully independent.
