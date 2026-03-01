# Tasks: Agent Service

**Input**: Design documents from `/specs/001-agent-service/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included — plan.md constitution check explicitly requires unit tests for all business logic and contract tests for EMOS/Matrix/A2A boundaries.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **bt_common/**: Shared Python library (in-repo package)
- **bt_agent/**: Core agent service (FastAPI appservice)
- **bt_cli/**: CLI test harness (rapid iteration, no Matrix needed)
- **bt_voice_sidecar/**: Node.js MatrixRTC audio bridge
- **tests/**: unit/, contract/, integration/

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create monorepo package structure and shared configuration

- [ ] T001 Create monorepo package structure with pyproject.toml defining bt-common, bt-agent, bt-cli as installable packages, create bt_common/__init__.py, bt_agent/__init__.py, bt_agent/tools/__init__.py, bt_agent/voice/__init__.py, bt_agent/voice/backends/__init__.py, bt_agent/discussion/__init__.py, bt_cli/__init__.py, and tests/unit/, tests/contract/, tests/integration/ directories with __init__.py files
- [ ] T002 [P] Create pydantic-settings environment configuration in bt_common/config.py with fields: GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, EMOS_BASE_URL, AWS_REGION (default us-east-1), MATRIX_HOMESERVER_URL, MATRIX_AS_TOKEN, LOG_LEVEL
- [ ] T003 [P] Create typed domain exceptions in bt_common/exceptions.py: EMOSError (base), EMOSConnectionError, EMOSNotFoundError, EMOSValidationError, CitationValidationError, AgentNotFoundError, ProfileRoomViolationError, VoiceSessionError
- [ ] T004 [P] Create .env.example template at project root with all config fields from T002 plus comments explaining each key

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core shared library modules that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 [P] Create Citation and Evidence Pydantic models with validation logic in bt_common/citation.py: Citation(index, segment_id, emos_message_id, source_title, source_url, quote, platform, timestamp), Evidence(segment_id, emos_message_id, source_title, source_url, text, platform), validate_citations() that verifies segment_id exists and quote is substring of segment.text per contracts/citation-schema.md
- [ ] T006 [P] Create Source and Segment Pydantic models + BM25 local re-ranking in bt_common/segment.py: Source(id, agent_id, platform, external_id, external_url, title, author, published_at, raw_meta, emos_group_id), Segment(id, source_id, agent_id, platform, seq, text, speaker, start_ms, end_ms, sha256, emos_message_id), bm25_rerank(query, segments, top_k) function per data-model.md
- [ ] T007 [P] Implement Supabase helpers in bt_common/supabase_helpers.py: async get_agent(agent_id), get_agent_by_matrix_id(matrix_user_id), get_agent_emos_config(agent_id), get_segments_by_ids(segment_ids), get_segments_for_agent(agent_id), save_chat_history(record) using supabase-py async client per data-model.md entities
- [ ] T008 Implement async EMOS client in bt_common/emos_client.py using httpx.AsyncClient: memorize(), search(query, user_id, retrieve_method, top_k), get_conversation_meta(), save_conversation_meta(), with retry policy (3 attempts, exponential backoff on 5xx), custom headers (X-Organization-Id, X-Space-Id, X-API-Key), and JSON-body-on-GET for search per contracts/emos-client.md
- [ ] T009 [P] Write unit tests for Citation validation in tests/unit/test_citation.py: test valid citation passes, test citation with non-existent segment_id is stripped, test citation with mismatched quote is stripped, test cross-agent citation is rejected (segment.agent_id != responding agent), test Evidence→Citation conversion
- [ ] T010 [P] Write unit tests for Segment + BM25 re-ranking in tests/unit/test_segment.py: test Segment model creation, test BM25 scoring returns relevant segments first, test BM25 with empty query, test top_k limiting, test Source model validation
- [ ] T011 [P] Write unit tests for EMOS client in tests/unit/test_emos_client.py using respx: test memorize request serialization, test search with rrf retrieve_method, test "extracted" vs "accumulated" status_info handling, test 5xx retry logic, test 4xx no-retry, test connection error retry, test error envelope parsing
- [ ] T012 [P] Write contract tests for EMOS API in tests/contract/test_emos_api.py: mock EMOS /memories endpoint with fixture JSON matching contracts/emos-client.md response shapes, verify client correctly parses memorize response, search response (nested memory_types grouping), conversation-meta response, and error envelope

**Checkpoint**: Foundation ready — bt_common library complete with models, EMOS client, citation validation, segment re-ranking, all with passing unit and contract tests

---

## Phase 3: User Story 1 — Private Text Chat with a Clone (Priority: P1) 🎯 MVP

**Goal**: A user chats with a Clone via CLI or Matrix DM. The Clone searches its memory, responds in-character with inline citation markers, and every citation is validated against source segments before delivery.

**Independent Test**: Send a message via bt-cli (`python -m bt_cli --agent confucius --mock-emos`), verify the response contains numbered citation markers that reference real source passages. Alternatively, send a DM to a Clone's Matrix user and verify the response includes `com.bibliotalk.citations` in the event content.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [P] [US1] Write unit test for ADK agent with mock LLM in tests/unit/test_agent.py: test agent_factory creates LlmAgent with correct persona_prompt, test agent calls memory_search tool when given a factual question, test agent calls emit_citations with Evidence objects, test agent responds with "no evidence" when memory_search returns empty, test agent uses correct llm_model from config
- [ ] T014 [P] [US1] Write unit test for guards in tests/unit/test_guards.py: test profile room guard rejects messages in profile rooms, test profile room guard allows messages in DM rooms, test rate limiter enforces 5-second cooldown per room, test rate limiter allows messages after cooldown expires
- [ ] T015 [P] [US1] Write contract test for Matrix event schema in tests/contract/test_matrix_events.py: test Clone response event includes msgtype m.text, body with citation markers, formatted_body with HTML sup tags, com.bibliotalk.citations with version and items array matching contracts/citation-schema.md

### Implementation for User Story 1

- [ ] T016 [P] [US1] Implement memory_search tool in bt_agent/tools/memory_search.py: ADK FunctionTool that takes a query string, calls emos_client.search() with the agent's user_id and rrf retrieve_method, re-ranks results via bm25_rerank(), returns list of Evidence objects with segment_id, source_title, source_url, text, platform
- [ ] T017 [P] [US1] Implement emit_citations tool in bt_agent/tools/emit_citations.py: ADK FunctionTool that takes a list of Evidence references (segment_id + quote substring), creates Citation objects, validates each via validate_citations() against the segments table, strips invalid citations, stores valid citations on the tool context for later attachment to the response
- [ ] T018 [US1] Implement LLM registry with Nova Lite v2 custom backend in bt_agent/llm_registry.py: register Gemini models (built-in), create NovaLiteBackend(BaseLlm) subclass wrapping Bedrock Converse API with tool-use support, register via LLMRegistry.register() so agents.llm_model="nova-lite-v2" resolves correctly
- [ ] T019 [US1] Implement agent_factory in bt_agent/agent_factory.py: async create_clone_agent(agent_id) that loads Agent row from Supabase, loads AgentEmosConfig, creates ADK LlmAgent with name=display_name, model=llm_model, instruction=persona_prompt, tools=[memory_search, emit_citations], returns configured agent; cache agents by ID with TTL
- [ ] T020 [P] [US1] Implement profile room guard and rate limiter in bt_agent/guards.py: is_profile_room(room_id) check against room state, RateLimiter class enforcing max 1 response per 5 seconds per room (FR-013), both usable as middleware or direct checks
- [ ] T021 [P] [US1] Implement Matrix message formatting in bt_common/matrix_helpers.py: format_clone_response(text, citations) → dict with body (plain text with [^N] markers + Sources footer), formatted_body (HTML with sup tags + hr + sources list), com.bibliotalk.citations extension per contracts/citation-schema.md
- [ ] T022 [US1] Implement CLI test harness in bt_cli/__main__.py: argparse with --agent (slug), --mock-emos flag; create agent via agent_factory, run conversation loop using ADK InMemoryRunner, print responses with formatted citations to stdout; --mock-emos uses respx to intercept EMOS calls with fixture data
- [ ] T023 [US1] Implement mautrix event handler and room routing in bt_agent/appservice.py: handle m.room.message events, extract sender and room_id, check profile room guard, check rate limiter, determine addressed Clone (DM → room's Clone, group → mentioned Clone only per edge case), invoke Clone agent via InMemoryRunner, format response via matrix_helpers, send response to room, save to chat_history
- [ ] T024 [US1] Implement FastAPI appservice entry point in bt_agent/main.py: create FastAPI app, register mautrix AppService with transaction endpoint, health check endpoint, startup hook to initialize LLM registry and Supabase client, configure structured logging with correlation IDs

**Checkpoint**: User Story 1 complete — Clone text chat works via CLI harness (no external infra) and Matrix appservice (with Synapse). Citations are validated, profile rooms are guarded, rate limiting is enforced.

---

## Phase 4: User Story 2 — Multi-Agent Text Discussion (Priority: P2)

**Goal**: Users create discussion rooms with multiple Clones. Clones take turns responding to a topic, each citing only from their own memory. Users can observe, interject, and stop the discussion.

**Independent Test**: Start a discussion with two Clones (e.g., Confucius and Aristotle) on a topic via A2A client, verify each Clone responds in turn with citations from its own memory only, and the discussion stops after the configured turn count.

**Depends on**: US1 (agent_factory, memory_search, emit_citations, citation validation)

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T025 [P] [US2] Write contract test for A2A protocol in tests/contract/test_a2a_protocol.py: test Agent Card JSON at /.well-known/agent.json matches a2a-clone.md schema, test tasks/send JSON-RPC request format, test response with task status completed + artifacts containing text + citations data part, test task lifecycle states (submitted → working → completed)

### Implementation for User Story 2

- [ ] T026 [P] [US2] Implement per-Clone A2A HTTP server in bt_agent/discussion/a2a_server.py: JSON-RPC 2.0 endpoint handling tasks/send method, Agent Card at /.well-known/agent.json with clone name/description/skills, invoke clone agent via agent_factory, return Task with artifacts containing text response + citations DataPart per contracts/a2a-clone.md
- [ ] T027 [US2] Implement discussion orchestrator in bt_agent/discussion/orchestrator.py: ADK LoopAgent that acts as A2A client, accepts topic + list of clone agent_ids + max_turns + turn_order (round-robin or LLM-decided), for each turn sends accumulated context to next Clone via A2A tasks/send, collects response + citations, posts to Matrix room, handles user interjections as context additions, respects stop command, enforces citation isolation (each Clone only cites own memory)

**Checkpoint**: User Story 2 complete — Multi-agent discussions work with turn-taking, citation isolation, configurable turn count, and user interjection support.

---

## Phase 5: User Story 3 — Voice Call with a Clone (Priority: P3)

**Goal**: Users start a voice call with a Clone. The Clone listens, searches memory, responds in voice with grounded citations. A text transcript with citations is posted to a parallel text thread.

**Independent Test**: Feed a pre-recorded PCM audio file to NovaSonicBackend, verify the Clone responds with audio output, and a text transcript with citations appears.

**Depends on**: US1 (memory_search, emit_citations, agent_factory)

### Implementation for User Story 3

- [ ] T028 [US3] Implement VoiceBackend ABC in bt_agent/voice/backends/base.py: abstract methods start_session(system_prompt, tools), send_audio_chunk(pcm_16khz_bytes), receive() → AsyncIterator[VoiceEvent], end_session(); VoiceEvent types: AudioChunk(pcm_24khz), ToolCall(tool_name, args), Transcript(text, role), EndOfTurn per contracts/voice-backend.md
- [ ] T029 [US3] Implement NovaSonicBackend in bt_agent/voice/backends/nova_sonic.py: Bedrock InvokeModelWithBidirectionalStreamCommand, session lifecycle (setupPromptStart → setupSystemPrompt → setupStartAudio → stream audio → endAudioContent → endPrompt → close), handle tool-use events (pause audio, emit ToolCall, accept tool result, resume), audio format PCM 16kHz in / 24kHz out, 8-minute session limit handling per research.md R4
- [ ] T030 [US3] Implement GeminiLiveBackend in bt_agent/voice/backends/gemini_live.py: Gemini Live API WebSocket connection, same VoiceBackend interface, tool-use support via Gemini function calling, audio format conversion as needed
- [ ] T031 [US3] Implement voice session manager in bt_agent/voice/session_manager.py: create_session(agent_id, room_id, backend_type) → VoiceSession, manage session lifecycle (start, active, ending, ended), route tool calls to memory_search/emit_citations, handle backend selection (nova_sonic or gemini_live) per agent config, clean session teardown on disconnect or error
- [ ] T032 [US3] Implement voice transcript posting in bt_agent/voice/transcript.py: collect Transcript events from VoiceBackend.receive(), buffer per-turn transcripts, format with citations via matrix_helpers, post to text thread in same Matrix room, save to chat_history with modality="voice"
- [ ] T033 [US3] Initialize bt-voice-sidecar Node.js project in bt_voice_sidecar/package.json with dependencies for MatrixRTC client (matrix-js-sdk), WebSocket (ws), and audio processing
- [ ] T034 [US3] Implement MatrixRTC join in bt_voice_sidecar/matrixrtc.js: join Element Call as virtual user for a Clone, handle call setup/teardown events, establish audio track
- [ ] T035 [US3] Implement audio bridge in bt_voice_sidecar/audio_bridge.js: decode Opus from WebRTC to PCM 16kHz, encode PCM 24kHz to Opus for return path, WebSocket connection to bt-agent voice session manager for bidirectional PCM streaming

**Checkpoint**: User Story 3 complete — Single-Clone voice calls work with real-time speech, memory-grounded responses, and text transcript with citations.

---

## Phase 6: User Story 4 — Multi-Agent Voice Discussion (Priority: P4)

**Goal**: Users start voice calls with multiple Clones for "agentic podcast" discussions. Clones speak in turn, each grounded in their own memory. Text transcript captures all participants' citations.

**Independent Test**: Start a voice session with two Clones and a topic, verify both Clones produce distinct audio turns, turn-taking is enforced (no simultaneous speech), and the text transcript contains citations from each Clone's sources.

**Depends on**: US2 (discussion orchestrator, A2A), US3 (voice session manager, voice backends, sidecar)

### Implementation for User Story 4

- [ ] T036 [P] [US4] Implement audio mixer in bt_voice_sidecar/mixer.js: mix multiple Clone audio streams for user playback, mute non-speaking Clones during turn-taking, support N virtual MatrixRTC participants (one per Clone)
- [ ] T037 [US4] Extend voice session manager for multi-agent sessions in bt_agent/voice/session_manager.py: manage multiple concurrent VoiceBackend instances (one per Clone), coordinate with discussion orchestrator for turn order, route audio to active speaker's backend only, enforce turn-taking (< 5% simultaneous speech per SC-007)
- [ ] T038 [US4] Extend discussion orchestrator for voice mode in bt_agent/discussion/orchestrator.py: add voice_mode flag to discussion config, when voice_mode=true route Clone responses through voice session manager instead of text posting, coordinate audio turn handoffs, post transcript entries to text thread per turn via transcript.py

**Checkpoint**: User Story 4 complete — Multi-agent voice discussions work with turn-taking, per-Clone audio streams, and full transcript with citations.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration tests, observability, and end-to-end validation

- [ ] T039 [P] Write integration test for Clone text chat E2E in tests/integration/test_chat_e2e.py: start Docker Compose with EMOS, memorize sample segments, send question via InMemoryRunner, verify response contains valid citations referencing memorized segments
- [ ] T040 [P] Write integration test for citation round-trip in tests/integration/test_citation_roundtrip.py: memorize segment via EMOS client, search for it, create Citation from Evidence, validate citation against segments table, verify full round-trip integrity
- [ ] T041 [P] Write integration test for multi-agent discussion in tests/integration/test_discussion.py: start two Clone A2A servers, run discussion orchestrator with 3 turns, verify each Clone responded, citations are isolated (no cross-Clone citations), turn count respected
- [ ] T042 Add structured logging with correlation IDs across all service entry points in bt_agent/main.py, bt_agent/appservice.py, bt_agent/discussion/orchestrator.py, bt_agent/voice/session_manager.py
- [ ] T043 Run quickstart.md validation: execute all quickstart steps (setup, CLI harness with --mock-emos, unit tests, contract tests), verify all pass end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — **BLOCKS all user stories**
- **US1 (Phase 3)**: Depends on Foundational phase completion
- **US2 (Phase 4)**: Depends on US1 completion (reuses agent_factory, memory_search, emit_citations)
- **US3 (Phase 5)**: Depends on US1 completion (reuses memory_search, emit_citations, agent_factory)
- **US4 (Phase 6)**: Depends on BOTH US2 AND US3 completion (combines discussion orchestrator + voice backends)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational
    ↓
Phase 3: US1 (P1) ──── MVP STOP POINT
    ↓         ↓
Phase 4: US2  Phase 5: US3    ← can run in parallel after US1
    ↓         ↓
    └────┬────┘
         ↓
Phase 6: US4 (P4)
         ↓
Phase 7: Polish
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/contracts before services
- Tools before agent factory
- Agent factory before CLI harness
- CLI harness before Matrix appservice (per research.md R1)
- Core implementation before integration

### Parallel Opportunities

**Phase 1**: T002, T003, T004 can run in parallel (after T001)
**Phase 2**: T005, T006 can run in parallel; T009-T012 (tests) can run in parallel
**Phase 3**: T013-T015 (tests) in parallel; T016-T017 (tools) in parallel; T020-T021 (guards, formatting) in parallel
**Phase 4**: T025 (test) and T026 (A2A server) in parallel
**Phase 5**: T030 and T033-T035 (sidecar) can overlap with T029 once ABC is done
**Phase 6**: T036 (mixer) can run in parallel with T037-T038 (agent-side changes)
**Phase 7**: T039-T041 (integration tests) all in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (write first, ensure they fail):
Task: "Write unit test for ADK agent in tests/unit/test_agent.py"        # T013
Task: "Write unit test for guards in tests/unit/test_guards.py"           # T014
Task: "Write contract test for Matrix events in tests/contract/test_matrix_events.py" # T015

# Launch US1 tools together:
Task: "Implement memory_search tool in bt_agent/tools/memory_search.py"   # T016
Task: "Implement emit_citations tool in bt_agent/tools/emit_citations.py" # T017

# Launch US1 guards + formatting together:
Task: "Implement profile room guard in bt_agent/guards.py"                # T020
Task: "Implement Matrix formatting in bt_common/matrix_helpers.py"        # T021
```

## Parallel Example: User Story 3 + User Story 2

```bash
# After US1 is complete, US2 and US3 can start in parallel:

# Developer A works on US2:
Task: "Write contract test for A2A protocol"                              # T025
Task: "Implement A2A server in bt_agent/discussion/a2a_server.py"         # T026
Task: "Implement orchestrator in bt_agent/discussion/orchestrator.py"     # T027

# Developer B works on US3:
Task: "Implement VoiceBackend ABC in bt_agent/voice/backends/base.py"     # T028
Task: "Implement NovaSonicBackend"                                        # T029
Task: "Initialize bt-voice-sidecar"                                       # T033
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test via `python -m bt_cli --agent confucius --mock-emos`
5. Verify: Clone responds in-character with valid citations
6. Deploy CLI harness for persona tuning and citation quality iteration

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test via CLI → Test via Matrix → **Deploy/Demo (MVP!)**
3. Add US2 → Test multi-agent discussion → Deploy/Demo
4. Add US3 → Test voice call → Deploy/Demo
5. Add US4 → Test multi-agent voice → Deploy/Demo
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. One developer completes US1 (MVP critical path)
3. Once US1 is done:
   - Developer A: US2 (multi-agent text)
   - Developer B: US3 (voice)
4. Once US2 AND US3 are done:
   - Either developer: US4 (multi-agent voice)
5. Team runs Polish phase together

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Research.md R1: CLI-first testing, defer Matrix infrastructure
- Research.md R2: Use ADK InMemoryRunner + before_model_callback for mock LLM tests
- Research.md R3: httpx.AsyncClient for EMOS with respx mocks in tests
- Research.md R5: A2A is JSON-RPC 2.0 over HTTP — test locally with multiple processes
