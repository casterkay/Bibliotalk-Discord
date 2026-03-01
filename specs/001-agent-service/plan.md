# Implementation Plan: Agent Service

**Branch**: `001-agent-service` | **Date**: 2026-02-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-agent-service/spec.md`

## Summary

Build the core Bibliotalk agent service: Clone agents powered by Google
ADK with EverMemOS memory grounding, citation validation, multi-agent
discussions via A2A protocol, and voice chat via Nova Sonic / Gemini
Live backends. Matrix integration is deferred after agent core is
validated via a CLI test harness (see research.md R1).

## Technical Context

**Language/Version**: Python 3.11+ (bt_agent, bt_common, bt_cli); Node.js 20+ (bt_voice_sidecar)
**Primary Dependencies**: google-adk, google-genai, mautrix, httpx, supabase, boto3, pydantic, uvicorn, FastAPI
**Storage**: Supabase (PostgreSQL) for agents, sources, segments, chat_history; EverMemOS for vector memory
**Testing**: pytest + respx (unit/contract), Docker Compose + EMOS (integration), ADK InMemoryRunner (agent tests)
**Target Platform**: Linux server (AWS ECS Fargate, us-east-1)
**Project Type**: Multi-service backend (appservice + voice sidecar + shared library + CLI harness)
**Performance Goals**: <5s text response latency, <3s voice response latency, 50 concurrent conversations
**Constraints**: us-east-1 region (Nova Sonic availability), unencrypted voice in MVP, single homeserver
**Scale/Scope**: ~25 figure Clones initially, growing to 100+; user Clones unbounded

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle                        | Gate                                                                             | Status                      |
| -------------------------------- | -------------------------------------------------------------------------------- | --------------------------- |
| I. Design-First Architecture     | spec.md + plan.md exist before coding                                            | PASS                        |
| II. Test-Driven Quality          | Unit tests for all business logic, contract tests for EMOS/Matrix/A2A boundaries | PASS — test plan defined    |
| III. Contract-Driven Integration | Pydantic schemas for EMOS, citations, Matrix events, A2A messages                | PASS — contracts/ defined   |
| IV. Incremental Delivery         | P1 (text chat) works before P2 (multi-agent) before P3 (voice)                   | PASS — phased by user story |
| V. Observable Systems            | Structured logging with correlation IDs on all service entry points              | PASS — included in plan     |
| VI. Principled Simplicity        | CLI-first testing defers Matrix infrastructure; reuse ADK primitives             | PASS                        |

**Post-Phase 1 Re-check**: All gates remain PASS. No violations identified.

## Project Structure

### Documentation (this feature)

```text
specs/001-agent-service/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── emos-client.md   # EMOS HTTP API contract
│   ├── citation-schema.md # Citation object schema
│   ├── voice-backend.md # VoiceBackend ABC contract
│   └── a2a-clone.md     # A2A server per Clone
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
bt_common/                  # Shared Python library (in-repo package)
├── __init__.py
├── emos_client.py          # Async httpx client for EMOS API
├── citation.py             # Citation Pydantic models + validation
├── segment.py              # Segment models + BM25 local re-ranking
├── matrix_helpers.py       # Message formatting (HTML + plain + citations field)
├── supabase_helpers.py     # Common DB access patterns
├── config.py               # pydantic-settings env config
└── exceptions.py           # Typed domain exceptions

bt_agent/                   # Core agent service (FastAPI appservice)
├── main.py                 # Uvicorn entry point
├── appservice.py           # mautrix event handler + room routing
├── agent_factory.py        # ADK LlmAgent creation from DB rows
├── llm_registry.py         # NovaLiteBackend + LLMRegistry setup
├── tools/
│   ├── memory_search.py    # EMOS search → re-rank → Evidence list
│   └── emit_citations.py   # Attach citations to current response
├── voice/
│   ├── session_manager.py  # Voice session lifecycle management
│   ├── backends/
│   │   ├── base.py         # VoiceBackend ABC
│   │   ├── nova_sonic.py   # Bedrock bidirectional stream
│   │   └── gemini_live.py  # Gemini Live API WebSocket
│   └── transcript.py       # Voice transcript → text thread posting
├── discussion/
│   ├── orchestrator.py     # LoopAgent + A2A client
│   └── a2a_server.py       # Per-Clone A2A HTTP server
└── guards.py               # Rate limiter
	
bt_voice_sidecar/           # Node.js MatrixRTC audio bridge
├── package.json
├── index.js                # Entry point
├── matrixrtc.js            # Join Element Call as virtual user
├── audio_bridge.js         # PCM encode/decode, WebSocket to bt_agent
└── mixer.js                # Audio mixing for multi-agent voice
	
bt_cli/                     # CLI test harness (rapid iteration)
├── __init__.py
└── __main__.py             # stdin/stdout chat with a Clone

tests/
├── unit/
│   ├── test_citation.py    # Citation validation logic
│   ├── test_segment.py     # Chunking + BM25 re-ranking
│   ├── test_emos_client.py # Client serialization + error handling
│   ├── test_agent.py       # ADK agent with mock LLM
│   └── test_guards.py      # Rate limiter
├── contract/
│   ├── test_emos_api.py    # Mock EMOS responses, verify parsing
│   ├── test_matrix_events.py # Matrix event schema compliance
│   └── test_a2a_protocol.py  # A2A request/response format
└── integration/
    ├── test_chat_e2e.py    # Clone text chat end-to-end
    ├── test_citation_roundtrip.py # Memorize → search → cite → validate
    └── test_discussion.py  # Multi-agent discussion flow
```

**Structure Decision**: Multi-package monorepo. `bt_common` is a shared
Python library used by both `bt_agent` and `bt_cli`. `bt_voice_sidecar`
is a separate Node.js package. This follows the blueprint's service
architecture while keeping shared logic in one place.

## Complexity Tracking

| Violation                                                  | Why Needed                                                                                                    | Simpler Alternative Rejected Because                                                                                         |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 4 packages (bt_common, bt_agent, bt_voice_sidecar, bt_cli) | Python and Node.js runtimes are incompatible; CLI harness enables rapid testing without Matrix infrastructure | Single Python package would still need a separate Node.js sidecar for WebRTC; CLI harness pays for itself in iteration speed |
| VoiceBackend abstraction                                   | Two voice backends (Nova Sonic, Gemini Live) with same interface                                              | Direct implementation would duplicate session management, tool-use routing, and transcript handling                          |

